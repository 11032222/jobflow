"""岗位接口。"""
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.application import Application
from app.models.company import Company
from app.models.favorite import Favorite
from app.models.job import Job
from app.models.match_result import MatchResult
from app.models.user import User
from app.schemas.job import JobImportRequest, JobOut

router = APIRouter()


def _to_out(
    job: Job,
    db: Session,
    user_id: int,
    include_match: bool = True,
    profile_id: int | None = None,
) -> JobOut:
    out = JobOut.model_validate(job)
    if job.company_id:
        company = db.get(Company, job.company_id)
        out.company_name = company.name if company else None
    try:
        out.tags = json.loads(job.tags or "[]")
    except (json.JSONDecodeError, TypeError):
        out.tags = []
    out.is_favorite = (
        db.query(Favorite)
        .filter(Favorite.user_id == user_id, Favorite.job_id == job.id)
        .first()
        is not None
    )
    out.is_applied = (
        db.query(Application)
        .filter(Application.user_id == user_id, Application.job_id == job.id)
        .first()
        is not None
    )
    if include_match and profile_id:
        match = (
            db.query(MatchResult)
            .filter(MatchResult.profile_id == profile_id, MatchResult.job_id == job.id)
            .first()
        )
        if match:
            out.match = match
    return out


@router.get("", response_model=dict)
def list_jobs(
    keyword: str | None = Query(default=None, description="关键词：匹配职位名/公司名"),
    city: str | None = None,
    salary_min: int | None = None,
    salary_max: int | None = None,
    education: str | None = None,
    experience: str | None = None,
    job_type: str | None = None,
    source: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Job).filter(Job.is_active.is_(True))
    if keyword:
        like = f"%{keyword}%"
        query = query.join(Company, Job.company_id == Company.id, isouter=True).filter(
            or_(Job.title.like(like), Company.name.like(like))
        )
    if city:
        query = query.filter(Job.city.like(f"%{city}%"))
    if salary_min is not None:
        query = query.filter(Job.salary_max >= salary_min)
    if salary_max is not None:
        query = query.filter(Job.salary_min <= salary_max)
    if education:
        query = query.filter(Job.education == education)
    if experience:
        query = query.filter(Job.experience.like(f"%{experience}%"))
    if job_type:
        query = query.filter(Job.job_type == job_type)
    if source:
        query = query.filter(Job.source == source)

    total = query.count()
    jobs = (
        query.order_by(Job.publish_time.desc(), Job.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    # 当前画像，用于附带匹配结果
    from app.models.profile import CandidateProfile

    profile = (
        db.query(CandidateProfile)
        .filter(
            CandidateProfile.user_id == current_user.id,
            CandidateProfile.is_current.is_(True),
        )
        .first()
    )
    items = [
        _to_out(j, db, current_user.id, profile_id=profile.id if profile else None)
        for j in jobs
    ]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.post("/{job_id}/favorite")
def add_favorite(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="岗位不存在")
    exists = (
        db.query(Favorite)
        .filter(Favorite.user_id == current_user.id, Favorite.job_id == job_id)
        .first()
    )
    if exists:
        return {"message": "已收藏"}
    db.add(Favorite(user_id=current_user.id, job_id=job_id))
    db.commit()
    return {"message": "收藏成功"}


@router.delete("/{job_id}/favorite")
def remove_favorite(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    fav = (
        db.query(Favorite)
        .filter(Favorite.user_id == current_user.id, Favorite.job_id == job_id)
        .first()
    )
    if fav:
        db.delete(fav)
        db.commit()
    return {"message": "已取消收藏"}


@router.post("/import")
def import_jobs(
    data: JobImportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """触发平台采集任务（后台异步执行，前端可轮询 /jobs/sources 查看进度）。"""
    from app.collectors.registry import supported_platforms
    from app.models.job_source import JobSource
    from app.services.job_import_service import import_jobs_from_platform

    if data.platform not in supported_platforms():
        raise HTTPException(status_code=400, detail=f"不支持的平台 {data.platform}，可用: {supported_platforms()}")

    source = JobSource(
        user_id=current_user.id,
        platform=data.platform,
        keyword=data.keyword,
        city=data.city,
        status="QUEUED",
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    background_tasks.add_task(import_jobs_from_platform, source.id)
    return {
        "message": f"已启动 {data.platform} 平台采集任务（关键词: {data.keyword} / {data.city}）",
        "job_source_id": source.id,
        "status": "QUEUED",
    }


@router.get("/sources")
def list_job_sources(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.job_source import JobSource

    return (
        db.query(JobSource)
        .filter(JobSource.user_id == current_user.id)
        .order_by(JobSource.created_at.desc())
        .limit(20)
        .all()
    )


@router.get("/{job_id}", response_model=JobOut)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="岗位不存在")
    from app.models.profile import CandidateProfile

    profile = (
        db.query(CandidateProfile)
        .filter(
            CandidateProfile.user_id == current_user.id,
            CandidateProfile.is_current.is_(True),
        )
        .first()
    )
    return _to_out(
        job, db, current_user.id, profile_id=profile.id if profile else None
    )
