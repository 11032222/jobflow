"""岗位采集导入服务：多平台 Adapter → 公司/岗位落库 → 跨源去重。"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.collectors.registry import get_adapter
from app.models.company import Company
from app.models.job import Job
from app.models.job_source import JobSource
from app.models.preference import Preference
from app.models.profile import CandidateProfile

logger = logging.getLogger(__name__)


def _norm_text(value: str | None) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[\s\-_/（）()【】\[\]·•\.]+", "", text)
    for suffix in ("股份有限公司", "有限责任公司", "科技有限公司", "有限公司", "集团", "控股"):
        text = text.replace(suffix, "")
    return text


def _dedup_hash(job: dict) -> str:
    """跨平台去重键：公司 + 职位 + 城市（忽略薪资文案差异）。"""
    raw = "|".join([
        _norm_text(job.get("company_name")),
        _norm_text(job.get("title")),
        _norm_text(job.get("city")),
    ])
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _json_list(value) -> list:
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def resolve_search_query(db: Session, user_id: int, data) -> dict:
    """关键词/城市/薪资：请求显式值优先，否则用画像 + 求职偏好。"""
    keyword = (getattr(data, "keyword", None) or "").strip()
    city = (getattr(data, "city", None) or "").strip()
    salary_min = getattr(data, "salary_min", None)
    salary_max = getattr(data, "salary_max", None)
    use_profile = bool(getattr(data, "use_profile", True))

    pref = db.query(Preference).filter(Preference.user_id == user_id).first()
    profile = (
        db.query(CandidateProfile)
        .filter(CandidateProfile.user_id == user_id, CandidateProfile.is_current.is_(True))
        .first()
    )

    if use_profile:
        if not keyword:
            positions = _json_list(pref.target_positions if pref else None)
            keywords = _json_list(pref.keywords if pref else None)
            keyword = (
                (positions[0] if positions else "")
                or (profile.title if profile else "")
                or (keywords[0] if keywords else "")
                or (profile.skills[0].name if profile and profile.skills else "")
            )
        if not city:
            cities = _json_list(pref.cities if pref else None)
            city = (cities[0] if cities else "") or (profile.city if profile else "")
        if salary_min is None and pref:
            salary_min = pref.salary_min
        if salary_max is None and pref:
            salary_max = pref.salary_max

    keyword = keyword or "Java"
    city = city or "北京"
    pages = max(1, min(int(getattr(data, "pages", 1) or 1), 5))
    return {
        "keyword": keyword,
        "city": city,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "pages": pages,
        "from_profile": use_profile,
    }


def _salary_overlap(job: dict, salary_min: int | None, salary_max: int | None) -> bool:
    if salary_min is None and salary_max is None:
        return True
    jmin = job.get("salary_min")
    jmax = job.get("salary_max")
    if jmin is None and jmax is None:
        return True
    if salary_min is not None and jmax is not None and jmax < salary_min:
        return False
    if salary_max is not None and jmin is not None and jmin > salary_max:
        return False
    return True


def _get_or_create_company(db: Session, name: str, info: dict | None) -> Company | None:
    if not name:
        return None
    company = db.query(Company).filter(Company.name == name).first()
    if company:
        return company
    company = Company(
        name=name,
        industry=info.get("industry") if info else None,
        company_type=None,
        scale=info.get("scale") if info else None,
        description=info.get("description") if info else None,
        profile_status="NOT_ANALYZED",
    )
    db.add(company)
    db.flush()
    return company


def import_jobs_from_platform(job_source_id: int) -> dict:
    """执行一次采集导入（后台任务调用，独立 DB 会话）。"""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        return _import(db, job_source_id)
    finally:
        db.close()


def _import(db: Session, job_source_id: int) -> dict:
    source = db.get(JobSource, job_source_id)
    if source is None:
        return {"error": "采集任务不存在"}
    source.status = "RUNNING"
    source.started_at = datetime.now()
    source.error_message = None
    db.commit()

    stats = {"total_found": 0, "imported": 0, "duplicated": 0, "skipped": 0, "filtered": 0}
    try:
        adapter = get_adapter(source.platform)
        raw_jobs = adapter.search_jobs(
            keyword=source.keyword or "Java",
            city=source.city or "北京",
            page=1,
            page_size=30,
            pages=source.pages or 1,
            salary_min=source.salary_min,
            salary_max=source.salary_max,
        )
        stats["total_found"] = len(raw_jobs)

        existing_hashes = set()
        for job in raw_jobs:
            if not _salary_overlap(job, source.salary_min, source.salary_max):
                stats["filtered"] += 1
                continue

            exists = (
                db.query(Job)
                .filter(
                    Job.source == job["source"],
                    Job.source_job_id == job["source_job_id"],
                )
                .first()
            )
            if exists:
                stats["skipped"] += 1
                continue

            h = _dedup_hash(job)
            dup = db.query(Job).filter(Job.dedup_hash == h).first()
            if dup is not None or h in existing_hashes:
                stats["duplicated"] += 1
                existing_hashes.add(h)
                continue
            existing_hashes.add(h)

            company = _get_or_create_company(db, job["company_name"], None)
            new_job = Job(
                title=job["title"],
                company_id=company.id if company else None,
                city=job.get("city"),
                district=job.get("district"),
                salary_min=job.get("salary_min"),
                salary_max=job.get("salary_max"),
                salary_text=job.get("salary_text"),
                education=job.get("education"),
                experience=job.get("experience"),
                job_type=job.get("job_type"),
                industry=job.get("industry"),
                tags=_json_dumps(job.get("tags", [])),
                responsibilities=job.get("responsibilities"),
                requirements=job.get("requirements"),
                description=job.get("description"),
                publish_time=job.get("publish_time"),
                source=job["source"],
                source_url=job.get("source_url"),
                source_job_id=job["source_job_id"],
                dedup_hash=h,
                is_duplicate=False,
                status="ACTIVE",
                raw_data=_json_dumps(job),
            )
            db.add(new_job)
            stats["imported"] += 1

        db.commit()
        source.total_found = stats["total_found"]
        source.imported_count = stats["imported"]
        source.status = "SUCCESS"
        source.finished_at = datetime.now()
        db.commit()
        logger.info("采集导入完成 %s: %s", source.platform, stats)
        return stats
    except Exception as exc:  # noqa: BLE001
        logger.exception("采集导入失败 job_source_id=%s", job_source_id)
        db.rollback()
        source = db.get(JobSource, job_source_id)
        if source:
            source.status = "FAILED"
            source.finished_at = datetime.now()
            source.error_message = str(exc)[:500]
            db.commit()
        stats["error"] = str(exc)
        return stats


def _json_dumps(value) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return None
