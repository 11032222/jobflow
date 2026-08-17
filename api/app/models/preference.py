"""求职偏好表。"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Preference(Base):
    __tablename__ = "preferences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), unique=True, index=True
    )
    target_positions: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组
    cities: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 元/月
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    job_types: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组
    industries: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组
    company_types: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组
    keywords: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组
    is_auto_match: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
