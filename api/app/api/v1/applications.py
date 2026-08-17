"""投递接口。"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.application import Application, ApplicationEvent
from app.models.company import Company
from app.models.job import Job
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationOut,
    ApplicationStatusUpdate,
)
from app.services import application_service
from app.services.agent_service import create_task

router = APIRouter()


def _to_out(app: Application, db: Session) -> ApplicationOut:
    out = ApplicationOut.model_validate(app)
    job = db.get(Job, app.job_id) if app.job_id else None
    out.job_title = job.title if job else None
    company = db.get(Company, job.company_id) if job and job.company_id else None
    out.company_name = company.name if company else None
    out.events = (
        db.query(ApplicationEvent)
        .filter(ApplicationEvent.application_id == app.id)
        .order_by(ApplicationEvent.created_at.asc())
        .all()
    )
    return out


@router.post("", response_model=ApplicationOut)
def create_application(
    data: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.get(Job, data.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="岗位不存在")
    exists = (
        db.query(Application)
        .filter(Application.user_id == current_user.id, Application.job_id == data.job_id)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="该岗位已投递，可在投递看板查看")
    app = Application(
        user_id=current_user.id,
        job_id=data.job_id,
        resume_id=data.resume_id,
        note=data.note,
        status="PENDING",
        channel="EMAIL",
    )
    db.add(app)
    db.flush()
    db.add(
        ApplicationEvent(
            application_id=app.id,
            from_status=None,
            to_status="PENDING",
            operator="USER",
            comment="创建投递申请",
        )
    )
    db.commit()
    db.refresh(app)
    return _to_out(app, db)


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Application).filter(Application.user_id == current_user.id)
    if status:
        query = query.filter(Application.status == status)
    apps = query.order_by(Application.updated_at.desc()).all()
    return [_to_out(a, db) for a in apps]


@router.get("/{app_id}", response_model=ApplicationOut)
def get_application(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = db.get(Application, app_id)
    if app is None or app.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="投递记录不存在")
    return _to_out(app, db)


@router.post("/{app_id}/submit", response_model=ApplicationOut)
def submit_application(
    app_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """触发邮件投递（后台执行，前端可轮询任务/投递状态）。"""
    app = db.get(Application, app_id)
    if app is None or app.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="投递记录不存在")
    if app.status not in ("PENDING", "FAILED"):
        raise HTTPException(status_code=400, detail=f"当前状态 {app.status} 不可重复投递")
    task = create_task(db, current_user.id, "JOB_APPLY", application_id=app.id)
    app.agent_task_id = task.id
    db.commit()
    background_tasks.add_task(application_service.submit_application_by_email, app.id)
    return _to_out(app, db)


@router.post("/{app_id}/status", response_model=ApplicationOut)
def update_status(
    app_id: int,
    data: ApplicationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = db.get(Application, app_id)
    if app is None or app.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="投递记录不存在")
    try:
        application_service.transition(db, app, data.status, operator="USER", comment=data.comment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(app, db)
