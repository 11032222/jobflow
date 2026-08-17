"""岗位表（标准化 Job 对象）。"""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
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


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source", "source_job_id", name="uq_job_source_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(128), index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    city: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    district: Mapped[str | None] = mapped_column(String(64), nullable=True)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 元/月
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_text: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 原始薪资文本
    education: Mapped[str | None] = mapped_column(String(32), nullable=True)
    experience: Mapped[str | None] = mapped_column(String(32), nullable=True)
    job_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # 全职/实习/校招
    industry: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组
    responsibilities: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    publish_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="mock", index=True)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_job_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    dedup_hash: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(default=False)
    duplicate_group_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")  # ACTIVE/EXPIRED/CLOSED
    raw_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # 原始数据 JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
