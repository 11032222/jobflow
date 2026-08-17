"""求职画像：结构化简历信息（Candidate Profile）。"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    resume_id: Mapped[int | None] = mapped_column(ForeignKey("resumes.id"), nullable=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str | None] = mapped_column(String(128), nullable=True)  # 求职意向职位
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    city: Mapped[str | None] = mapped_column(String(64), nullable=True)
    years_of_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    education_level: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )  # 博士/硕士/本科/大专
    school: Mapped[str | None] = mapped_column(String(128), nullable=True)
    major: Mapped[str | None] = mapped_column(String(64), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # 个人简介
    source: Mapped[str] = mapped_column(String(16), default="MANUAL")  # MANUAL/LLM/RULE
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")  # DRAFT/CONFIRMED
    is_current: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    experiences: Mapped[list["ProfileExperience"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="ProfileExperience.sort_order",
    )
    skills: Mapped[list["ProfileSkill"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class ProfileExperience(Base):
    __tablename__ = "profile_experiences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id"), index=True)
    type: Mapped[str] = mapped_column(
        String(32), index=True
    )  # education/work/project/certificate/award/other
    school_or_company: Mapped[str | None] = mapped_column(String(128), nullable=True)
    degree: Mapped[str | None] = mapped_column(String(32), nullable=True)
    major: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str | None] = mapped_column(String(128), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    profile: Mapped[CandidateProfile] = relationship(back_populates="experiences")


class ProfileSkill(Base):
    __tablename__ = "profile_skills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    years: Mapped[int | None] = mapped_column(Integer, nullable=True)

    profile: Mapped[CandidateProfile] = relationship(back_populates="skills")
