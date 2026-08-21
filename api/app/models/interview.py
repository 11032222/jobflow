"""面试记录表。"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    application_id: Mapped[int | None] = mapped_column(ForeignKey("applications.id"), nullable=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    interview_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # 电话/视频/现场/笔试
    round_no: Mapped[int] = mapped_column(Integer, default=1)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # SCHEDULED → IN_PROGRESS → COMPLETED → REVIEWED；CANCELLED 为旁路终态
    status: Mapped[str] = mapped_column(String(32), default="SCHEDULED")
    contact_person: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meeting_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class InterviewSession(Base):
    """一次完整面试对话/复盘会话：对应一段录音、一次会议录屏或手动录入的问答集合。"""

    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    company_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(128), nullable=True)
    interview_id: Mapped[int | None] = mapped_column(ForeignKey("interviews.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="manual")  # recording / upload / manual
    raw_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class InterviewQuestion(Base):
    """面试过程中记录的问题、回答与结果，AI 复盘后回填分类与掌握度。"""

    __tablename__ = "interview_questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    interview_id: Mapped[int | None] = mapped_column(ForeignKey("interviews.id"), nullable=True, index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("interview_sessions.id"), nullable=True, index=True)
    question: Mapped[str] = mapped_column(Text)
    my_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(String(32), nullable=True)  # 完整/部分/不会
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mastery: Mapped[str | None] = mapped_column(String(16), nullable=True)  # mastered/partial/missed
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class InterviewReview(Base):
    """面试复盘结果，由 Interview Agent 生成。"""

    __tablename__ = "interview_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    interview_id: Mapped[int | None] = mapped_column(ForeignKey("interviews.id"), nullable=True, index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("interview_sessions.id"), nullable=True, index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    focus_areas: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    weaknesses: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    knowledge_points: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    review_advice: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
