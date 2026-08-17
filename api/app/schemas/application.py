"""投递与面试模型。"""
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


class InterviewIn(BaseModel):
    application_id: int | None = None
    company_id: int | None = None
    job_id: int | None = None
    interview_type: str | None = None
    round_no: int = 1
    scheduled_at: datetime | None = None
    status: str = "SCHEDULED"
    contact_person: str | None = None
    contact_phone: str | None = None
    address: str | None = None
    meeting_url: str | None = None
    notes: str | None = None
    feedback: str | None = None


class InterviewOut(InterviewIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    company_name: str | None = None
    job_title: str | None = None
