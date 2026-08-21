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
from app.services.job_text import format_job_text, split_job_description

logger = logging.getLogger(__name__)


def _norm_text(value: str | None) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[\s\-_/（）()【】\[\]·•\.]+", "", text)
    for suffix in ("股份有限公司", "有限责任公司", "科技有限公司", "有限公司", "集团", "控股"):
        text = text.replace(suffix, "")
    return text


def _salary_bucket(value) -> str:
    """把月薪（元）规整为整数 K（如 20000 → '20K'），用于跨平台薪资归一化。"""
    if not value:
        return "?"
    try:
        k = int(float(value) / 1000.0)
    except (TypeError, ValueError):
        return "?"
    return f"{k}K"


def _norm_salary(job: dict) -> str:
    """归一化薪资：优先用解析后的 min/max，缺失时回退解析 salary_text。"""
    lo = job.get("salary_min")
    hi = job.get("salary_max")
    if lo is None and hi is None:
        text = (job.get("salary_text") or "").strip()
        if not text:
            return "?"
        unit = 10000 if ("万" in text and "元" not in text) else 1
        nums = [float(n) for n in re.findall(r"[\d.]+", text)]
        if not nums:
            return "?"
        lo = nums[0] * unit
        hi = nums[1] * unit if len(nums) >= 2 else lo
    return f"{_salary_bucket(lo)}-{_salary_bucket(hi)}"


def _norm_experience(value: str | None) -> str:
    """归一化经验年限区间：'3-5年' → 3-5；'3年以上' → 3-；'经验不限' → any。"""
    text = (value or "").strip().lower()
    if not text or "不限" in text or "应届" in text and "年" not in text:
        return "any"
    years = [float(n) for n in re.findall(r"[\d.]+", text)]
    if not years:
        return "unknown"
    lo = int(years[0])
    hi = int(years[-1]) if len(years) > 1 else lo
    return f"{lo}-{hi}"


def _dedup_hash(job: dict) -> str:
    """跨平台去重键：公司 + 职位 + 城市 + 归一化薪资 + 经验区间。

    薪资/经验都做格式归一化，因此 '20-30K' 与 '2-3万/月'、'3-5年' 与
    '3到5年' 会被识别为同一岗位；不同薪资区间的同职位保留为不同岗位。
    """
    raw = "|".join([
        _norm_text(job.get("company_name")),
        _norm_text(job.get("title")),
        _norm_text(job.get("city")),
        _norm_salary(job),
        _norm_experience(job.get("experience")),
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


def _apply_company_info(company: Company, info: dict | None) -> None:
    if not info:
        return
    if info.get("industry") and not company.industry:
        company.industry = info["industry"]
    if info.get("scale") and not company.scale:
        company.scale = info["scale"]
    if info.get("company_type") and not company.company_type:
        company.company_type = info["company_type"]
    if info.get("address") and not company.address:
        company.address = info["address"]
    if info.get("logo_url") and not company.logo_url:
        company.logo_url = info["logo_url"]
    desc = info.get("description")
    if desc and (not company.description or "是一家" in (company.description or "") and len(company.description) < 40):
        company.description = desc[:800]


def _get_or_create_company(db: Session, name: str, info: dict | None) -> Company | None:
    if not name:
        return None
    company = db.query(Company).filter(Company.name == name).first()
    if company:
        _apply_company_info(company, info)
        return company
    info = info or {}
    company = Company(
        name=name,
        industry=info.get("industry"),
        company_type=info.get("company_type"),
        scale=info.get("scale"),
        address=info.get("address"),
        description=info.get("description"),
        logo_url=info.get("logo_url"),
        profile_status="NOT_ANALYZED",
    )
    db.add(company)
    db.flush()
    return company


def _fill_job_row(row: Job, job: dict, company: Company | None) -> None:
    desc = format_job_text(job.get("description"))
    duties = format_job_text(job.get("responsibilities")) or None
    reqs = format_job_text(job.get("requirements")) or None
    if desc and not (duties and reqs):
        split_d, split_r = split_job_description(desc)
        duties = duties or split_d
        reqs = reqs or split_r
    status = (job.get("status") or "ACTIVE").upper()
    if status not in ("ACTIVE", "CLOSED", "EXPIRED"):
        status = "ACTIVE"
    row.title = job["title"]
    row.company_id = company.id if company else None
    row.city = job.get("city")
    row.district = job.get("district")
    row.salary_min = job.get("salary_min")
    row.salary_max = job.get("salary_max")
    row.salary_text = job.get("salary_text")
    row.education = job.get("education")
    row.experience = job.get("experience")
    row.job_type = job.get("job_type")
    row.industry = job.get("industry")
    row.tags = _json_dumps(job.get("tags", [])) or row.tags
    if duties:
        row.responsibilities = duties
    if reqs:
        row.requirements = reqs
    if desc:
        row.description = desc
    row.publish_time = job.get("publish_time") or row.publish_time
    row.source_url = job.get("source_url")
    row.status = status
    row.is_active = status == "ACTIVE"
    row.raw_data = _json_dumps(job)
    row.updated_at = datetime.now()


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

    stats = {
        "total_found": 0,
        "imported": 0,
        "updated": 0,
        "closed": 0,
        "duplicated": 0,
        "skipped": 0,
        "filtered": 0,
    }
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

            company = _get_or_create_company(db, job["company_name"], job.get("company_info"))
            h = _dedup_hash(job)
            exists = (
                db.query(Job)
                .filter(
                    Job.source == job["source"],
                    Job.source_job_id == job["source_job_id"],
                )
                .first()
            )
            if exists:
                _fill_job_row(exists, job, company)
                exists.dedup_hash = h
                if exists.status == "CLOSED":
                    stats["closed"] += 1
                else:
                    stats["updated"] += 1
                continue

            dup = db.query(Job).filter(Job.dedup_hash == h).first()
            if dup is not None or h in existing_hashes:
                # 跨平台重复：仍覆盖更新已有记录的详情（若新数据更完整）
                if dup is not None and (job.get("description") or job.get("requirements")):
                    if not dup.description or len(dup.description or "") < len(job.get("description") or ""):
                        _fill_job_row(dup, job, company)
                        stats["updated"] += 1
                    else:
                        stats["duplicated"] += 1
                else:
                    stats["duplicated"] += 1
                existing_hashes.add(h)
                continue
            existing_hashes.add(h)

            new_job = Job(
                source=job["source"],
                source_job_id=job["source_job_id"],
                dedup_hash=h,
                is_duplicate=False,
            )
            _fill_job_row(new_job, job, company)
            db.add(new_job)
            if new_job.status == "CLOSED":
                stats["closed"] += 1
            else:
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
