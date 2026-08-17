"""岗位采集导入服务：Adapter → 公司/岗位落库 → 去重。"""
import hashlib
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.collectors.registry import get_adapter
from app.models.company import Company
from app.models.job import Job
from app.models.job_source import JobSource

logger = logging.getLogger(__name__)


def _dedup_hash(job: dict) -> str:
    raw = "|".join([
        str(job.get("company_name", "")),
        str(job.get("title", "")),
        str(job.get("city", "")),
        str(job.get("salary_text", "")),
        str((job.get("description") or "")[:80]),
    ])
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


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
    db.commit()

    stats = {"total_found": 0, "imported": 0, "duplicated": 0, "skipped": 0}
    try:
        adapter = get_adapter(source.platform)
        raw_jobs = adapter.search_jobs(
            keyword=source.keyword or "Java",
            city=source.city or "北京",
            page=1,
            page_size=30,
        )
        stats["total_found"] = len(raw_jobs)

        existing_hashes = set()  # 本次会话内去重
        for job in raw_jobs:
            # 同一平台同一条目的岗位已存在 → 跳过
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
            is_dup = dup is not None or h in existing_hashes
            if is_dup:
                stats["duplicated"] += 1
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
                is_duplicate=is_dup,
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
        source.status = "FAILED"
        source.finished_at = datetime.now()
        db.commit()
        stats["error"] = str(exc)
        return stats


def _json_dumps(value) -> str:
    import json

    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return None
