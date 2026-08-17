"""Agent 任务接口。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.agent_task import AgentTask
from app.models.user import User
from app.schemas.task import TaskOut

router = APIRouter()


@router.get("", response_model=list[TaskOut])
def list_tasks(
    task_type: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(AgentTask).filter(AgentTask.user_id == current_user.id)
    if task_type:
        query = query.filter(AgentTask.task_type == task_type)
    if status:
        query = query.filter(AgentTask.status == status)
    return query.order_by(AgentTask.created_at.desc()).limit(100).all()


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.get(AgentTask, task_id)
    if task is None or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task
