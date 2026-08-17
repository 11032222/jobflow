"""Agent 任务与日志表。"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# Agent 任务状态机
AGENT_TASK_STATUSES = [
    "CREATED", "QUEUED", "RUNNING", "SUCCESS", "FAILED", "RETRYING", "WAITING_USER",
]
AGENT_TASK_TYPES = [
    "RESUME_PARSE", "JOB_SEARCH", "JOB_MATCH", "COMPANY_ANALYZE", "JOB_APPLY",
]


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    task_type: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default="CREATED", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    input_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    user_message: Mapped[str | None] = mapped_column(Text, nullable=True)  # 需人工介入提示
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("agent_tasks.id"), index=True, nullable=True)
    level: Mapped[str] = mapped_column(String(16), default="INFO")  # INFO/WARN/ERROR
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
