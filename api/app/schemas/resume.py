"""简历模型。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    file_name: str
    file_path: str
    file_type: str
    file_size: int | None = None
    parse_status: str
    raw_text: str | None = None
    version: int
    created_at: datetime


class ResumeUpdate(BaseModel):
    parse_status: str | None = None
    raw_text: str | None = None
