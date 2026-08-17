"""求职画像模型。"""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

EXPERIENCE_TYPE = Literal["education", "work", "project", "certificate", "award", "other"]


class ExperienceIn(BaseModel):
    type: EXPERIENCE_TYPE
    school_or_company: str | None = None
    degree: str | None = None
    major: str | None = None
    title: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None
    sort_order: int = 0


class ExperienceOut(ExperienceIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    profile_id: int


class SkillIn(BaseModel):
    name: str
    level: str | None = None
    years: int | None = None


class SkillOut(SkillIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    profile_id: int


class ProfileIn(BaseModel):
    name: str | None = None
    title: str | None = None
    phone: str | None = None
    email: str | None = None
    gender: str | None = None
    birth_date: date | None = None
    city: str | None = None
    years_of_experience: int | None = None
    education_level: str | None = None
    school: str | None = None
    major: str | None = None
    summary: str | None = None


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    resume_id: int | None = None
    source: str
    status: str
    is_current: bool
    created_at: datetime
    experiences: list[ExperienceOut] = []
    skills: list[SkillOut] = []
