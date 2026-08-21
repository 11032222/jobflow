"""面试会话接口：独立于面试日程的对话记录、问答、复盘与语音转写。"""
import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.agents.interview_agent import interview_agent
from app.agents.llm import llm_service
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.media import VIDEO_SUFFIXES, extract_audio, is_video
from app.models.interview import InterviewQuestion, InterviewReview, InterviewSession
from app.models.user import User
from app.schemas.interview import (
    QuestionIn,
    QuestionOut,
    ReviewOut,
    SessionDetailOut,
    SessionIn,
    SessionOut,
    TranscribeParseOut,
)

router = APIRouter()

AUDIO_MIME = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".mpeg": "audio/mpeg",
    ".mpga": "audio/mpeg",
    ".aac": "audio/aac",
    ".opus": "audio/opus",
    ".amr": "audio/amr",
}
ALLOWED_SUFFIXES = set(AUDIO_MIME) | VIDEO_SUFFIXES


def _get_session(db: Session, session_id: int, user_id: int) -> InterviewSession:
    item = db.get(InterviewSession, session_id)
    if item is None or item.user_id != user_id:
        raise HTTPException(status_code=404, detail="面试会话不存在")
    return item


def _review_to_out(review: InterviewReview) -> ReviewOut:
    def parse(value):
        if not value:
            return []
        if isinstance(value, list):
            return value
        try:
            data = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
        return data if isinstance(data, list) else []

    return ReviewOut(
        id=review.id,
        interview_id=review.interview_id,
        session_id=review.session_id,
        summary=review.summary,
        focus_areas=parse(review.focus_areas),
        weaknesses=parse(review.weaknesses),
        knowledge_points=parse(review.knowledge_points),
        review_advice=review.review_advice,
        model=review.model,
        created_at=review.created_at,
    )


def _session_detail(db: Session, session: InterviewSession) -> SessionDetailOut:
    questions = (
        db.query(InterviewQuestion)
        .filter(InterviewQuestion.session_id == session.id, InterviewQuestion.user_id == session.user_id)
        .order_by(InterviewQuestion.id.asc())
        .all()
    )
    review = (
        db.query(InterviewReview)
        .filter(InterviewReview.session_id == session.id, InterviewReview.user_id == session.user_id)
        .order_by(InterviewReview.id.desc())
        .first()
    )
    out = SessionDetailOut.model_validate(session)
    out.question_count = len(questions)
    out.questions = [QuestionOut.model_validate(q) for q in questions]
    out.review = _review_to_out(review) if review else None
    return out


@router.get("", response_model=list[SessionOut])
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == current_user.id)
        .order_by(InterviewSession.id.desc())
        .all()
    )
    result = []
    for s in sessions:
        qc = (
            db.query(func.count(InterviewQuestion.id))
            .filter(InterviewQuestion.session_id == s.id)
            .scalar()
        )
        out = SessionOut.model_validate(s)
        out.question_count = qc or 0
        result.append(out)
    return result


@router.post("", response_model=SessionDetailOut, status_code=201)
def create_session(
    data: SessionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    title = (data.title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="会话标题不能为空")
    item = InterviewSession(
        user_id=current_user.id,
        title=title,
        company_name=(data.company_name or "").strip() or None,
        job_title=(data.job_title or "").strip() or None,
        interview_id=data.interview_id,
        source=(data.source or "manual").strip() or "manual",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _session_detail(db, item)


@router.get("/{session_id}", response_model=SessionDetailOut)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = _get_session(db, session_id, current_user.id)
    return _session_detail(db, item)


@router.put("/{session_id}", response_model=SessionDetailOut)
def update_session(
    session_id: int,
    data: SessionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = _get_session(db, session_id, current_user.id)
    updates = data.model_dump(exclude_unset=True)
    if "title" in updates and not (updates.get("title") or "").strip():
        raise HTTPException(status_code=400, detail="会话标题不能为空")
    for field, value in updates.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return _session_detail(db, item)


@router.delete("/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = _get_session(db, session_id, current_user.id)
    db.query(InterviewQuestion).filter(InterviewQuestion.session_id == item.id).delete()
    db.query(InterviewReview).filter(InterviewReview.session_id == item.id).delete()
    db.delete(item)
    db.commit()
    return {"message": "已删除"}


# ===== 会话问答 =====


@router.post("/{session_id}/questions", response_model=QuestionOut, status_code=201)
def create_question(
    session_id: int,
    data: QuestionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_session(db, session_id, current_user.id)
    item = InterviewQuestion(
        user_id=current_user.id,
        session_id=session.id,
        interview_id=session.interview_id,
        **data.model_dump(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{session_id}/questions/{question_id}", response_model=QuestionOut)
def update_question(
    session_id: int,
    question_id: int,
    data: QuestionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_session(db, session_id, current_user.id)
    item = (
        db.query(InterviewQuestion)
        .filter(
            InterviewQuestion.id == question_id,
            InterviewQuestion.session_id == session_id,
            InterviewQuestion.user_id == current_user.id,
        )
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="问答记录不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{session_id}/questions/{question_id}")
def delete_question(
    session_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_session(db, session_id, current_user.id)
    item = (
        db.query(InterviewQuestion)
        .filter(
            InterviewQuestion.id == question_id,
            InterviewQuestion.session_id == session_id,
            InterviewQuestion.user_id == current_user.id,
        )
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="问答记录不存在")
    db.delete(item)
    db.commit()
    return {"message": "已删除"}


# ===== 会话复盘 =====


@router.get("/{session_id}/review", response_model=ReviewOut)
def get_review(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_session(db, session_id, current_user.id)
    review = (
        db.query(InterviewReview)
        .filter(
            InterviewReview.session_id == session_id,
            InterviewReview.user_id == current_user.id,
        )
        .order_by(InterviewReview.id.desc())
        .first()
    )
    if review is None:
        raise HTTPException(status_code=404, detail="暂无复盘结果")
    return _review_to_out(review)


@router.post("/{session_id}/review", response_model=ReviewOut)
def generate_review(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_session(db, session_id, current_user.id)
    questions = (
        db.query(InterviewQuestion)
        .filter(
            InterviewQuestion.session_id == session_id,
            InterviewQuestion.user_id == current_user.id,
        )
        .order_by(InterviewQuestion.id.asc())
        .all()
    )
    if not questions:
        raise HTTPException(status_code=400, detail="请先录入面试问答记录")

    interview_payload = {
        "company_name": session.company_name,
        "job_title": session.job_title,
        "interview_type": None,
        "round_no": None,
        "notes": None,
        "feedback": None,
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
        session_id=session.id,
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


# ===== 整段录音 / 录屏转写拆分 =====


@router.post("/transcribe", response_model=TranscribeParseOut)
async def transcribe_session(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    company_name: str | None = Form(None),
    job_title: str | None = Form(None),
    interview_id: int | None = Form(None),
    source: str = Form("upload"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"不支持的音频/视频类型: {suffix or '未知'}")
    if not llm_service.is_available(current_user.id):
        raise HTTPException(status_code=400, detail="未配置可用的模型服务，无法进行语音转写")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="文件为空")

    audio_bytes = raw
    audio_name = file.filename or f"audio{suffix}"
    audio_mime = AUDIO_MIME.get(suffix)
    if is_video(suffix):
        extracted = extract_audio(raw, suffix)
        if not extracted:
            raise HTTPException(
                status_code=400,
                detail="无法从视频中抽取音轨，请确认已安装 imageio-ffmpeg，或改传音频文件",
            )
        audio_bytes, audio_name, audio_mime = extracted
    if not audio_mime:
        audio_mime = "application/octet-stream"

    text = llm_service.transcribe(audio_bytes, audio_name, audio_mime, user_id=current_user.id)
    if not text:
        raise HTTPException(status_code=400, detail="语音转写失败，请检查模型服务或音频文件")

    questions_data = interview_agent.parse_transcript(text, user_id=current_user.id)

    fallback_title = (
        (title or "").strip()
        or (company_name or "").strip()
        or (job_title or "").strip()
        or Path(file.filename or "").stem
        or "面试会话"
    )
    session = InterviewSession(
        user_id=current_user.id,
        title=fallback_title,
        company_name=(company_name or "").strip() or None,
        job_title=(job_title or "").strip() or None,
        interview_id=interview_id,
        source=(source or "upload").strip() or "upload",
        raw_transcript=text,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    for q in questions_data:
        db.add(
            InterviewQuestion(
                user_id=current_user.id,
                session_id=session.id,
                interview_id=session.interview_id,
                question=q.get("question") or "",
                my_answer=q.get("my_answer"),
            )
        )
    db.commit()
    return _session_detail(db, session)
