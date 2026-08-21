"""推荐接口。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.job import Job
from app.models.match_result import MatchResult
from app.models.preference import Preference
from app.models.profile import CandidateProfile
from app.models.user import User
from app.schemas.job import JobOut
from app.services import recommendation_service

router = APIRouter()


def _current_profile(db: Session, user_id: int) -> CandidateProfile | None:
    return (
        db.query(CandidateProfile)
        .filter(CandidateProfile.user_id == user_id, CandidateProfile.is_current.is_(True))
        .first()
    )


@router.get("", response_model=dict)
def recommendation_list(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = _current_profile(db, current_user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="请先建立求职画像，再进行智能推荐")
    pref = db.query(Preference).filter(Preference.user_id == current_user.id).first()
    jobs = (
        db.query(Job)
        .filter(
            Job.is_active.is_(True),
            or_(Job.status.is_(None), Job.status.notin_(["CLOSED", "EXPIRED", "OFFLINE"])),
        )
        .limit(200)
        .all()
    )
    for job in jobs:
        recommendation_service.compute_match(db, current_user.id, profile, job, pref)

    results = (
        db.query(MatchResult)
        .filter(MatchResult.profile_id == profile.id)
        .order_by(MatchResult.hard_fail.asc(), MatchResult.match_score.desc())
        .limit(limit)
        .all()
    )
    items = []
    for r in results:
        job = db.get(Job, r.job_id)
        if job is None or not job.is_active or job.status in ("CLOSED", "EXPIRED", "OFFLINE"):
            continue
        out = JobOut.model_validate(job)
        from app.models.company import Company

        company = db.get(Company, job.company_id) if job.company_id else None
        out.company_name = company.name if company else None
        out.match = r
        items.append(out)
    return {"items": items}


@router.post("/jobs/{job_id}/match", response_model=JobOut)
def match_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = _current_profile(db, current_user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="请先建立求职画像")
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="岗位不存在")
    pref = db.query(Preference).filter(Preference.user_id == current_user.id).first()
    recommendation_service.compute_match(db, current_user.id, profile, job, pref)

    from app.models.company import Company

    out = JobOut.model_validate(job)
    company = db.get(Company, job.company_id) if job.company_id else None
    out.company_name = company.name if company else None
    result = (
        db.query(MatchResult)
        .filter(MatchResult.profile_id == profile.id, MatchResult.job_id == job.id)
        .first()
    )
    out.match = result
    return out
