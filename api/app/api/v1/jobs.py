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
from app.schemas.job import JobImportRequest, JobOut, MatchOut

router = APIRouter()


def _to_out(
    job: Job,
    db: Session,
    user_id: int,
    include_match: bool = True,
    profile_id: int | None = None,
) -> JobOut:
    from app.services.job_text import format_job_text, split_job_description

    out = JobOut.model_validate(job)
    if job.company_id:
        company = db.get(Company, job.company_id)
        out.company_name = company.name if company else None
        if company and not out.industry:
            out.industry = company.industry
    try:
        out.tags = json.loads(job.tags or "[]")
    except (json.JSONDecodeError, TypeError):
        out.tags = []
    out.description = format_job_text(job.description) or job.description
    duties = format_job_text(job.responsibilities) or job.responsibilities
    reqs = format_job_text(job.requirements) or job.requirements
    if out.description and not (duties and reqs):
        split_d, split_r = split_job_description(out.description)
        duties = duties or split_d
        reqs = reqs or split_r
    out.responsibilities = duties
    out.requirements = reqs
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
            out.match = MatchOut.model_validate(match)
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
    query = db.query(Job).filter(
        Job.is_active.is_(True),
        or_(Job.status.is_(None), Job.status.notin_(["CLOSED", "EXPIRED", "OFFLINE"])),
    )
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


@router.get("/collectors")
def list_collectors():
    """采集器状态：哪些平台可用、BOSS 调试 Chrome 是否在线。"""
    from app.collectors.registry import PLATFORM_LABELS, supported_platforms
    from app.collectors.zhipin import zhipin_ready

    items = []
    for pid in supported_platforms():
        if pid == "zhipin":
            items.append(zhipin_ready())
        else:
            items.append({"id": pid, "name": PLATFORM_LABELS.get(pid, pid), "ready": True, "hint": None})
    return {"items": items}


@router.post("/collectors/zhipin/launch")
def launch_zhipin_chrome(current_user: User = Depends(get_current_user)):
    """启动独立调试 Chrome（9222），打开 BOSS 登录页。"""
    from app.collectors.zhipin_cdp import launch_debug_chrome

    try:
        return launch_debug_chrome()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/import")
def import_jobs(
    data: JobImportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """触发多平台采集（后台异步，前端轮询 /jobs/sources）。

    关键词/城市/薪资可手填；use_profile=true 时用画像与求职偏好补全。
    """
    from app.collectors.registry import PLATFORM_LABELS, supported_platforms
    from app.models.job_source import JobSource
    from app.services.job_import_service import import_jobs_from_platform, resolve_search_query

    available = supported_platforms()
    requested: list[str] = []
    if data.platforms:
        requested.extend(data.platforms)
    if data.platform:
        requested.append(data.platform)
    requested = [p.lower() for p in requested if p]
    if "all" in requested:
        requested = [p for p in available if p != "mock"]
    # 去重且保序
    seen: set[str] = set()
    platforms = []
    for p in requested:
        if p not in seen:
            seen.add(p)
            platforms.append(p)
    if not platforms:
        platforms = ["zhaopin"]

    unknown = [p for p in platforms if p not in available]
    if unknown:
        raise HTTPException(status_code=400, detail=f"不支持的平台 {unknown}，可用: {available}")

    query = resolve_search_query(db, current_user.id, data)
    tasks = []
    labels = []
    source_ids: list[int] = []
    for platform in platforms:
        source = JobSource(
            user_id=current_user.id,
            platform=platform,
            keyword=query["keyword"],
            city=query["city"],
            salary_min=query["salary_min"],
            salary_max=query["salary_max"],
            pages=query["pages"],
            status="QUEUED",
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        source_ids.append(source.id)
        tasks.append({"platform": platform, "job_source_id": source.id, "status": "QUEUED"})
        labels.append(PLATFORM_LABELS.get(platform, platform))

    def _run_imports(ids: list[int]) -> None:
        from concurrent.futures import ThreadPoolExecutor

        workers = max(1, min(len(ids), 3))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(import_jobs_from_platform, ids))

    background_tasks.add_task(_run_imports, source_ids)

    salary_hint = ""
    if query["salary_min"] or query["salary_max"]:
        salary_hint = f" / {query['salary_min'] or '?'}~{query['salary_max'] or '?'}元"
    return {
        "message": f"已启动 {' + '.join(labels)} 采集（{query['keyword']} / {query['city']}{salary_hint}）",
        "query": query,
        "tasks": tasks,
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
