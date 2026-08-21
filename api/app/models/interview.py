"""面试记录、面试问题、面试复盘与状态流转事件表。

对应《概要设计说明书》7.1 核心实体中的 Interview / InterviewQuestion / InterviewReview，
InterviewEvent 为状态流转审计，与已有 ApplicationEvent 对称。
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# 面试状态机（文档 8.4）
INTERVIEW_STATUSES = [
    "SCHEDULED",    # 已安排
    "IN_PROGRESS",  # 进行中
    "COMPLETED",    # 已完成
    "REVIEWED",     # 已复盘
    "CANCELLED",    # 已取消
]

# 面试方式（线上/线下形式）
INTERVIEW_TYPES = ["PHONE", "VIDEO", "ONSITE"]

# 面试性质（轮次类型）
ROUND_TYPES = ["TECHNICAL", "HR", "BOSS", "CROSS", "WRITTEN"]

# 面试结果
INTERVIEW_RESULTS = ["PASS", "FAIL", "PENDING"]

# 面试问题自评（文档 3.10：已掌握 / 回答不完整 / 完全不会）
SELF_RESULTS = ["MASTERED", "PARTIAL", "FAILED"]

# 自评 -> 掌握度分值，Interview Agent 与知识库聚合共用
SELF_RESULT_SCORE: dict[str, float] = {"MASTERED": 1.0, "PARTIAL": 0.5, "FAILED": 0.0}

# 复盘任务状态
REVIEW_STATUSES = ["RUNNING", "SUCCESS", "FAILED"]


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    application_id: Mapped[int | None] = mapped_column(ForeignKey("applications.id"), nullable=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    interview_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # PHONE/VIDEO/ONSITE
    round_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # TECHNICAL/HR/BOSS/CROSS/WRITTEN
    round_no: Mapped[int] = mapped_column(Integer, default=1)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="SCHEDULED")  # 见 INTERVIEW_STATUSES
    interviewer: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 面试官
    result: Mapped[str | None] = mapped_column(String(32), nullable=True)  # PASS/FAIL/PENDING
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


class InterviewQuestion(Base):
    """面试问题记录（文档 3.10：问题 / 我的回答 / 结果）。"""

    __tablename__ = "interview_questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id"), index=True)
    # 有意冗余：面试知识库需跨全部面试聚合，冗余后可单表 GROUP BY，无需 JOIN
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    question: Mapped[str] = mapped_column(Text)
    my_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    self_result: Mapped[str] = mapped_column(String(16), default="PARTIAL")  # 见 SELF_RESULTS
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 问题分类
    knowledge_point: Mapped[str | None] = mapped_column(String(512), nullable=True)  # 需复习知识点
    source: Mapped[str] = mapped_column(String(16), default="USER")  # USER/AGENT，人工可接管标记
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class InterviewReview(Base):
    """面试复盘结果（Interview Agent 产出）。可重跑，旧版本保留并置 is_latest=False。"""

    __tablename__ = "interview_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="RUNNING")  # 见 REVIEW_STATUSES
    source: Mapped[str | None] = mapped_column(String(16), nullable=True)  # LLM/RULE
    model_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    dimensions_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # 考察方向 + 星级
    weak_points_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_points_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True)
    agent_task_id: Mapped[int | None] = mapped_column(ForeignKey("agent_tasks.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class InterviewEvent(Base):
    """面试状态流转事件（结构与 application_events 对称）。"""

    __tablename__ = "interview_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32))
    operator: Mapped[str] = mapped_column(String(16), default="SYSTEM")  # USER/SYSTEM/AGENT
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
