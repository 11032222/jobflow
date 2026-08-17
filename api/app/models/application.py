"""投递记录与状态流转事件表。"""
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# 投递业务状态机
APPLICATION_STATUSES = [
    "PENDING",       # 待投递
    "SUBMITTING",    # 投递中
    "SUBMITTED",     # 已投递
    "FAILED",        # 投递失败
    "WAITING",       # 待反馈
    "TEST",          # 笔试
    "INTERVIEW",     # 面试
    "OFFER",         # 录用
    "REJECTED",      # 未通过
    "CLOSED",        # 已关闭
]


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_app_user_job"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    resume_id: Mapped[int | None] = mapped_column(ForeignKey("resumes.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    channel: Mapped[str] = mapped_column(String(16), default="EMAIL")  # EMAIL/MOCK/PLATFORM
    platform: Mapped[str | None] = mapped_column(String(64), nullable=True)  # zhaopin/email...
    email_to: Mapped[str | None] = mapped_column(String(128), nullable=True)
    email_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_task_id: Mapped[int | None] = mapped_column(ForeignKey("agent_tasks.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ApplicationEvent(Base):
    __tablename__ = "application_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id"), index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32))
    operator: Mapped[str] = mapped_column(String(16), default="SYSTEM")  # USER/SYSTEM/AGENT
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
