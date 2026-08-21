"""岗位与匹配模型。"""
import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company_id: int | None = None
    company_name: str | None = None
    city: str | None = None
    district: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_text: str | None = None
    education: str | None = None
    experience: str | None = None
    job_type: str | None = None
    industry: str | None = None
    tags: list[str] = []
    responsibilities: str | None = None
    requirements: str | None = None
    description: str | None = None
    publish_time: datetime | None = None
    source: str
    source_url: str | None = None
    status: str | None = None
    is_duplicate: bool = False
    is_favorite: bool = False
    is_applied: bool = False
    match: "MatchOut | None" = None

    @field_validator("tags", mode="before")
    @classmethod
    def _parse_tags(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        return v or []


class JobImportRequest(BaseModel):
    platform: str | None = None
    platforms: list[str] | None = None
    keyword: str | None = None
    city: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    pages: int = 1
    use_profile: bool = True


class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    match_score: float | None = None
    skill_score: float | None = None
    experience_score: float | None = None
    education_score: float | None = None
    requirement_score: float | None = None
    preference_score: float | None = None
    recommend_level: str | None = None
    recommend_reason: str | None = None
    strengths: str | None = None
    weaknesses: str | None = None
    hard_fail: bool = False
    hard_fail_reasons: list[str] = []
    status: str
    model_used: str | None = None

    @field_validator("hard_fail_reasons", mode="before")
    @classmethod
    def _parse_hard_fail_reasons(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else [v]
            except (json.JSONDecodeError, TypeError):
                return [v] if v else []
        return v or []
