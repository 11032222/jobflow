"""公司表。"""
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    logo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(64), nullable=True)
    company_type: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 民营/国企/外企
    scale: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 100-299人
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # Company Agent 输出
    risk_level: Mapped[str] = mapped_column(String(16), default="NORMAL")  # NORMAL/WARNING/HIGH
    risk_reasons: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_status: Mapped[str] = mapped_column(
        String(32), default="NOT_ANALYZED"
    )  # NOT_ANALYZED/PENDING/ANALYZED/FAILED
    profile_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
