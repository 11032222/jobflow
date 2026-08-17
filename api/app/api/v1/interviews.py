"""面试接口。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.company import Company
from app.models.interview import Interview
from app.models.job import Job
from app.models.user import User
from app.schemas.application import InterviewIn, InterviewOut

router = APIRouter()


def _to_out(item: Interview, db: Session) -> InterviewOut:
    out = InterviewOut.model_validate(item)
    company = db.get(Company, item.company_id) if item.company_id else None
    out.company_name = company.name if company else None
    job = db.get(Job, item.job_id) if item.job_id else None
    out.job_title = job.title if job else None
    return out


@router.get("", response_model=list[InterviewOut])
def list_interviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = (
        db.query(Interview)
        .filter(Interview.user_id == current_user.id)
        .order_by(Interview.scheduled_at.asc().nulls_last())
        .all()
    )
    return [_to_out(i, db) for i in items]


@router.post("", response_model=InterviewOut)
def create_interview(
    data: InterviewIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = Interview(user_id=current_user.id, **data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_out(item, db)


@router.put("/{interview_id}", response_model=InterviewOut)
def update_interview(
    interview_id: int,
    data: InterviewIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.get(Interview, interview_id)
    if item is None or item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="面试记录不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return _to_out(item, db)


@router.delete("/{interview_id}")
def delete_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.get(Interview, interview_id)
    if item is None or item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="面试记录不存在")
    db.delete(item)
    db.commit()
    return {"message": "已删除"}
