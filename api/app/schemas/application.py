"""投递模型。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ApplicationCreate(BaseModel):
    job_id: int
    resume_id: int | None = None
    note: str | None = None


class ApplicationStatusUpdate(BaseModel):
    status: str
    comment: str | None = None


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    job_id: int
    job_title: str | None = None
    company_name: str | None = None
    resume_id: int | None = None
    status: str
    channel: str
    platform: str | None = None
    email_to: str | None = None
    email_message_id: str | None = None
    sent_at: datetime | None = None
    note: str | None = None
    created_at: datetime
    updated_at: datetime
    events: list["ApplicationEventOut"] = []


class ApplicationEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_status: str | None = None
    to_status: str
    operator: str
    comment: str | None = None
    created_at: datetime


# 面试相关 Schema 已拆分至 app/schemas/interview.py
