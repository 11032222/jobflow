"""面试接口：面试记录、问答记录、复盘与语音转写。"""
import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.agents.interview_agent import interview_agent
from app.agents.llm import llm_service
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.company import Company
from app.models.interview import Interview, InterviewQuestion, InterviewReview
from app.models.job import Job
from app.models.user import User
from app.schemas.application import InterviewIn, InterviewOut
from app.schemas.interview import QuestionIn, QuestionOut, ReviewOut, TranscribeOut

router = APIRouter()

# 面试状态机：SCHEDULED → IN_PROGRESS → COMPLETED → REVIEWED，CANCELLED 为旁路终态
INTERVIEW_TRANSITIONS: dict[str, set[str]] = {
    "SCHEDULED": {"IN_PROGRESS", "CANCELLED"},
    "IN_PROGRESS": {"COMPLETED", "CANCELLED"},
    "COMPLETED": {"REVIEWED"},
    "REVIEWED": set(),
    "CANCELLED": set(),
}
INTERVIEW_STATUSES = set(INTERVIEW_TRANSITIONS.keys())

ALLOWED_AUDIO_TYPES = {
    ".mp3", ".wav", ".m4a", ".webm", ".ogg", ".flac", ".mp4", ".mpeg", ".mpga",
}
AUDIO_MIME = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".mp4": "audio/mp4",
    ".mpeg": "audio/mpeg",
    ".mpga": "audio/mpeg",
}


def _check_transition(current: str, new: str) -> None:
    if new not in INTERVIEW_STATUSES:
        raise HTTPException(status_code=400, detail=f"未知面试状态: {new}")
    if new == current:
        return
    if new not in INTERVIEW_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=400,
            detail=f"面试状态不允许从 {current} 流转到 {new}",
        )


def _to_out(item: Interview, db: Session) -> InterviewOut:
    out = InterviewOut.model_validate(item)
    company = db.get(Company, item.company_id) if item.company_id else None
    out.company_name = company.name if company else None
    job = db.get(Job, item.job_id) if item.job_id else None
    out.job_title = job.title if job else None
    return out


def _get_interview(db: Session, interview_id: int, user_id: int) -> Interview:
    item = db.get(Interview, interview_id)
    if item is None or item.user_id != user_id:
        raise HTTPException(status_code=404, detail="面试记录不存在")
    return item


def _get_question(db: Session, interview_id: int, question_id: int, user_id: int) -> InterviewQuestion:
    item = (
        db.query(InterviewQuestion)
        .filter(
            InterviewQuestion.id == question_id,
            InterviewQuestion.interview_id == interview_id,
            InterviewQuestion.user_id == user_id,
        )
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="面试问题记录不存在")
    return item


def _parse_json_list(value: str | None) -> list:
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        data = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []
    return data if isinstance(data, list) else []


def _review_to_out(review: InterviewReview) -> ReviewOut:
    return ReviewOut(
        id=review.id,
        interview_id=review.interview_id,
        summary=review.summary,
        focus_areas=_parse_json_list(review.focus_areas),
        weaknesses=_parse_json_list(review.weaknesses),
        knowledge_points=_parse_json_list(review.knowledge_points),
        review_advice=review.review_advice,
        model=review.model,
        created_at=review.created_at,
    )


@router.get("", response_model=list[InterviewOut])
def list_interviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = (
        db.query(Interview)
        .filter(Interview.user_id == current_user.id)
        .order_by(Interview.scheduled_at.asc().nulls_last())
        .all()
    )
    return [_to_out(i, db) for i in items]


@router.post("", response_model=InterviewOut)
def create_interview(
    data: InterviewIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.status not in INTERVIEW_STATUSES:
        raise HTTPException(status_code=400, detail=f"未知面试状态: {data.status}")
    item = Interview(user_id=current_user.id, **data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_out(item, db)


@router.put("/{interview_id}", response_model=InterviewOut)
def update_interview(
    interview_id: int,
    data: InterviewIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = _get_interview(db, interview_id, current_user.id)
    updates = data.model_dump(exclude_unset=True)
    if "status" in updates:
        _check_transition(item.status, updates["status"])
    for field, value in updates.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return _to_out(item, db)


@router.delete("/{interview_id}")
def delete_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = _get_interview(db, interview_id, current_user.id)
    db.delete(item)
    db.commit()
    return {"message": "已删除"}


# ===== 面试问答记录 =====


@router.get("/{interview_id}/questions", response_model=list[QuestionOut])
def list_questions(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_interview(db, interview_id, current_user.id)
    return (
        db.query(InterviewQuestion)
        .filter(
            InterviewQuestion.interview_id == interview_id,
            InterviewQuestion.user_id == current_user.id,
        )
        .order_by(InterviewQuestion.id.asc())
        .all()
    )


@router.post("/{interview_id}/questions", response_model=QuestionOut, status_code=201)
def create_question(
    interview_id: int,
    data: QuestionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_interview(db, interview_id, current_user.id)
    item = InterviewQuestion(
        user_id=current_user.id,
        interview_id=interview_id,
        **data.model_dump(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{interview_id}/questions/{question_id}", response_model=QuestionOut)
def update_question(
    interview_id: int,
    question_id: int,
    data: QuestionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = _get_question(db, interview_id, question_id, current_user.id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{interview_id}/questions/{question_id}")
def delete_question(
    interview_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = _get_question(db, interview_id, question_id, current_user.id)
    db.delete(item)
    db.commit()
    return {"message": "已删除"}


# ===== 面试复盘 =====


@router.get("/{interview_id}/review", response_model=ReviewOut)
def get_review(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_interview(db, interview_id, current_user.id)
    review = (
        db.query(InterviewReview)
        .filter(
            InterviewReview.interview_id == interview_id,
            InterviewReview.user_id == current_user.id,
        )
        .order_by(InterviewReview.id.desc())
        .first()
    )
    if review is None:
        raise HTTPException(status_code=404, detail="暂无复盘结果")
    return _review_to_out(review)


@router.post("/{interview_id}/review", response_model=ReviewOut)
def generate_review(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview = _get_interview(db, interview_id, current_user.id)
    questions = (
        db.query(InterviewQuestion)
        .filter(
            InterviewQuestion.interview_id == interview_id,
            InterviewQuestion.user_id == current_user.id,
        )
        .order_by(InterviewQuestion.id.asc())
        .all()
    )
    if not questions:
        raise HTTPException(status_code=400, detail="请先录入面试问答记录")

    company = db.get(Company, interview.company_id) if interview.company_id else None
    job = db.get(Job, interview.job_id) if interview.job_id else None
    interview_payload = {
        "company_name": company.name if company else None,
        "job_title": job.title if job else None,
        "interview_type": interview.interview_type,
        "round_no": interview.round_no,
        "notes": interview.notes,
        "feedback": interview.feedback,
    }
    question_payload = [
        {
            "id": q.id,
            "question": q.question,
            "my_answer": q.my_answer,
            "result": q.result,
            "category": q.category,
            "mastery": q.mastery,
        }
        for q in questions
    ]
    result = interview_agent.review(interview_payload, question_payload, user_id=current_user.id)
    if not result:
        raise HTTPException(status_code=400, detail="AI 复盘失败，请检查模型服务配置")

    by_id = {
        int(q["id"]): q
        for q in result.get("questions", [])
        if isinstance(q, dict) and q.get("id") is not None
    }
    for q in questions:
        meta = by_id.get(q.id)
        if meta:
            q.category = meta.get("category") or q.category
            q.mastery = meta.get("mastery") or q.mastery

    review = InterviewReview(
        user_id=current_user.id,
        interview_id=interview_id,
        summary=result.get("summary"),
        focus_areas=json.dumps(result.get("focus_areas") or [], ensure_ascii=False),
        weaknesses=json.dumps(result.get("weaknesses") or [], ensure_ascii=False),
        knowledge_points=json.dumps(result.get("knowledge_points") or [], ensure_ascii=False),
        review_advice=result.get("review_advice"),
        model=(llm_service._resolve(current_user.id) or {}).get("model"),
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return _review_to_out(review)


# ===== 语音转写 =====


@router.post("/transcribe", response_model=TranscribeOut)
async def transcribe_audio(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的音频类型: {suffix or '未知'}")
    if not llm_service.is_available(current_user.id):
        raise HTTPException(status_code=400, detail="未配置可用的模型服务，无法进行语音转写")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="音频文件为空")

    text = llm_service.transcribe(
        audio_bytes,
        file.filename or f"audio{suffix}",
        AUDIO_MIME.get(suffix, "application/octet-stream"),
        user_id=current_user.id,
    )
    if not text:
        raise HTTPException(status_code=400, detail="语音转写失败，请检查模型服务或音频文件")
    return {"text": text}
