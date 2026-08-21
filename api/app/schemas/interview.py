"""面试模块 Schema：面试记录、状态流转。

从 schemas/application.py 拆出，与面试管理模块对应（模块化原则）。
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.interview import (
    INTERVIEW_RESULTS,
    INTERVIEW_TYPES,
    MASTERY_VALUES,
    ROUND_TYPES,
)


def _blank_to_none(value: str | None) -> str | None:
    """空串归一为 None。前端清空输入框提交的是 ''，与 NULL 混存会让聚合查询漏数据。"""
    if value is None:
        return None
    value = value.strip()
    return value or None


def _check_enum(value: str | None, allowed: list[str], label: str) -> str | None:
    """空值放行；非空则必须落在枚举内。"""
    if value is None or value == "":
        return None
    if value not in allowed:
        raise ValueError(f"{label} 取值非法，应为 {'/'.join(allowed)} 之一")
    return value


class InterviewIn(BaseModel):
    """新建 / 编辑面试的字段。

    不含 status：状态一律走 POST /interviews/{id}/status 状态机接口。
    """

    application_id: int | None = None
    company_id: int | None = None
    job_id: int | None = None
    interview_type: str | None = None  # PHONE/VIDEO/ONSITE
    round_type: str | None = None  # TECHNICAL/HR/BOSS/CROSS/WRITTEN
    round_no: int = 1
    scheduled_at: datetime | None = None
    interviewer: str | None = None
    result: str | None = None  # PASS/FAIL/PENDING
    contact_person: str | None = None
    contact_phone: str | None = None
    address: str | None = None
    meeting_url: str | None = None
    notes: str | None = None
    feedback: str | None = None

    @field_validator("interview_type")
    @classmethod
    def _validate_type(cls, v: str | None) -> str | None:
        return _check_enum(v, INTERVIEW_TYPES, "面试方式")

    @field_validator("round_type")
    @classmethod
    def _validate_round_type(cls, v: str | None) -> str | None:
        return _check_enum(v, ROUND_TYPES, "面试性质")

    @field_validator("result")
    @classmethod
    def _validate_result(cls, v: str | None) -> str | None:
        return _check_enum(v, INTERVIEW_RESULTS, "面试结果")


class InterviewStatusUpdate(BaseModel):
    """状态流转请求，与 ApplicationStatusUpdate 对称。"""

    status: str
    comment: str | None = None


class InterviewEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_status: str | None = None
    to_status: str
    operator: str
    comment: str | None = None
    created_at: datetime


class InterviewOut(InterviewIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: str
    created_at: datetime
    company_name: str | None = None
    job_title: str | None = None
    events: list[InterviewEventOut] = []


class InterviewQuestionIn(BaseModel):
    """录入一条面试问题（文档 3.10：问题 / 我的回答 / 结果）。"""

    question: str = Field(min_length=1, description="面试问题")
    my_answer: str | None = None
    mastery: str = "PARTIAL"  # MASTERED/PARTIAL/FAILED
    category: str | None = None
    knowledge_point: str | None = None
    sort_order: int = 0

    @field_validator("category", "knowledge_point", "my_answer")
    @classmethod
    def _normalize_blank(cls, v: str | None) -> str | None:
        return _blank_to_none(v)

    @field_validator("mastery")
    @classmethod
    def _validate_mastery(cls, v: str) -> str:
        if v not in MASTERY_VALUES:
            raise ValueError(f"掌握度取值非法，应为 {'/'.join(MASTERY_VALUES)} 之一")
        return v

    @field_validator("question")
    @classmethod
    def _strip_question(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("面试问题不能为空")
        return v


class InterviewQuestionUpdate(BaseModel):
    """部分更新。用户改动分类/知识点后，source 会被置为 USER，S4 复盘不再覆盖。"""

    question: str | None = None
    my_answer: str | None = None
    mastery: str | None = None
    category: str | None = None
    knowledge_point: str | None = None
    sort_order: int | None = None

    @field_validator("category", "knowledge_point", "my_answer")
    @classmethod
    def _normalize_blank(cls, v: str | None) -> str | None:
        return _blank_to_none(v)

    @field_validator("mastery")
    @classmethod
    def _validate_mastery(cls, v: str | None) -> str | None:
        return _check_enum(v, MASTERY_VALUES, "掌握度")

    @field_validator("question")
    @classmethod
    def _strip_question(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("面试问题不能为空")
        return v


class InterviewReviewOut(BaseModel):
    """复盘结果。status=NONE 表示尚未复盘过（此时其余字段为空）。"""

    status: str  # NONE/RUNNING/SUCCESS/FAILED
    id: int | None = None
    interview_id: int | None = None
    source: str | None = None  # LLM/RULE
    model_name: str | None = None
    summary: str | None = None
    dimensions: list[dict] = []
    weak_points: list[str] = []
    review_points: list[str] = []
    error_message: str | None = None
    duration_ms: int | None = None
    created_at: datetime | None = None
    finished_at: datetime | None = None


class KnowledgeCategoryOut(BaseModel):
    """能力画像的一个维度。earlier/recent/delta 仅在面试场次 >= 2 时有值。"""

    category: str
    count: int
    interview_count: int
    mastered: int
    partial: int
    failed: int
    score: float
    stars: int
    earlier_score: float | None = None
    recent_score: float | None = None
    delta: float | None = None


class KnowledgeReviewPointOut(BaseModel):
    knowledge_point: str
    count: int


class KnowledgeOut(BaseModel):
    """面试知识库：跨面试聚合的个人能力画像。"""

    total_questions: int
    uncategorized: int
    interview_count: int
    categories: list[KnowledgeCategoryOut] = []
    weak_categories: list[str] = []
    review_points: list[KnowledgeReviewPointOut] = []


class InterviewQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    interview_id: int
    user_id: int
    question: str
    my_answer: str | None = None
    mastery: str
    category: str | None = None
    knowledge_point: str | None = None
    source: str  # USER/AGENT
    sort_order: int
    created_at: datetime


# ---------------------------------------------------------------------------
# 面试会话（独立于面试日程的对话记录、复盘与语音转写）——本地增量能力
# ---------------------------------------------------------------------------


class QuestionIn(BaseModel):
    question: str
    my_answer: str | None = None
    mastery: str | None = None  # MASTERED/PARTIAL/FAILED


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    interview_id: int | None = None
    session_id: int | None = None
    question: str
    my_answer: str | None = None
    mastery: str = "PARTIAL"
    category: str | None = None
    knowledge_point: str | None = None
    source: str = "USER"
    sort_order: int = 0
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


class ReviewOut(BaseModel):
    id: int
    interview_id: int | None = None
    session_id: int | None = None
    status: str = "SUCCESS"
    source: str | None = None
    model_name: str | None = None
    summary: str | None = None
    dimensions: list[dict] = []
    weak_points: list[str] = []
    review_points: list[str] = []
    knowledge_points: list[dict] = []
    review_advice: str | None = None
    created_at: datetime | None = None


class SessionDetailOut(SessionOut):
    raw_transcript: str | None = None
    questions: list[QuestionOut] = []
    review: ReviewOut | None = None


class TranscribeOut(BaseModel):
    text: str


class TranscribeParseOut(BaseModel):
    session: SessionDetailOut
