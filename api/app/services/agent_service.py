"""Agent 任务服务：任务创建与状态更新。"""
import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.agent_task import AgentLog, AgentTask


def create_task(db: Session, user_id: int, task_type: str, **input_data) -> AgentTask:
    task = AgentTask(
        user_id=user_id,
        task_type=task_type,
        status="CREATED",
        input_json=json.dumps(input_data, ensure_ascii=False),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def set_status(
    db: Session,
    task: AgentTask,
    status: str,
    progress: int | None = None,
    message: str | None = None,
    error: str | None = None,
) -> AgentTask:
    task.status = status
    if progress is not None:
        task.progress = progress
    if status == "RUNNING" and task.started_at is None:
        task.started_at = datetime.now()
    if status in ("SUCCESS", "FAILED"):
        task.finished_at = datetime.now()
    if error:
        task.error_message = error
    if message:
        db.add(AgentLog(task_id=task.id, level="INFO", message=message))
    db.commit()
    db.refresh(task)
    return task


def add_log(db: Session, task_id: int | None, level: str, message: str, payload=None) -> None:
    db.add(
        AgentLog(
            task_id=task_id,
            level=level,
            message=message,
            payload_json=json.dumps(payload, ensure_ascii=False) if payload else None,
        )
    )
    db.commit()
