"""求职偏好模型。"""
import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

LIST_FIELDS = ("target_positions", "cities", "job_types", "industries", "company_types", "keywords")


class PreferenceIn(BaseModel):
    target_positions: list[str] = []
    cities: list[str] = []
    salary_min: int | None = None
    salary_max: int | None = None
    job_types: list[str] = []
    industries: list[str] = []
    company_types: list[str] = []
    keywords: list[str] = []
    is_auto_match: bool = True


class PreferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    target_positions: list[str] = []
    cities: list[str] = []
    salary_min: int | None = None
    salary_max: int | None = None
    job_types: list[str] = []
    industries: list[str] = []
    company_types: list[str] = []
    keywords: list[str] = []
    is_auto_match: bool = True
    created_at: datetime

    @field_validator(*LIST_FIELDS, mode="before")
    @classmethod
    def _parse_json(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        return v or []
