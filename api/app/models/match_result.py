"""匹配结果表。"""
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MatchResult(Base):
    __tablename__ = "match_results"
    __table_args__ = (
        UniqueConstraint("profile_id", "job_id", name="uq_match_profile_job"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    match_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)  # 0-100
    skill_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    experience_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    education_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    requirement_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    preference_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    recommend_level: Mapped[str | None] = mapped_column(String(4), nullable=True)  # S/A/B/C/D
    recommend_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    strengths: Mapped[str | None] = mapped_column(Text, nullable=True)
    weaknesses: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING")  # PENDING/RUNNING/SUCCESS/FAILED
    model_used: Mapped[str | None] = mapped_column(String(64), nullable=True)  # rule/llm
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
