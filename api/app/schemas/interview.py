"""面试问题、复盘与知识库相关 Schema。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class QuestionIn(BaseModel):
    question: str
    my_answer: str | None = None
    result: str | None = None  # 完整/部分/不会


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    interview_id: int | None = None
    session_id: int | None = None
    question: str
    my_answer: str | None = None
    result: str | None = None
    category: str | None = None
    mastery: str | None = None
    created_at: datetime


class SessionIn(BaseModel):
    title: str
    company_name: str | None = None
    job_title: str | None = None
    interview_id: int | None = None
    source: str = "manual"  # recording / upload / manual


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company_name: str | None = None
    job_title: str | None = None
    interview_id: int | None = None
    source: str
    duration_seconds: int | None = None
    created_at: datetime
    updated_at: datetime
    question_count: int = 0


class SessionDetailOut(SessionOut):
    raw_transcript: str | None = None
    questions: list[QuestionOut] = []
    review: "ReviewOut | None" = None


class ReviewOut(BaseModel):
    id: int
    interview_id: int | None = None
    session_id: int | None = None
    summary: str | None = None
    focus_areas: list[str] = []
    weaknesses: list[str] = []
    knowledge_points: list[dict] = []
    review_advice: str | None = None
    model: str | None = None
    created_at: datetime


class TranscribeOut(BaseModel):
    text: str


class TranscribeParseOut(BaseModel):
    session: SessionDetailOut
