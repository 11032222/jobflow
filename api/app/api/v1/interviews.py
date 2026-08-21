"""面试接口。"""
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.company import Company
from app.models.interview import (
    Interview,
    InterviewEvent,
    InterviewQuestion,
    InterviewReview,
)
from app.models.job import Job
from app.models.user import User
from app.schemas.interview import (
    InterviewIn,
    InterviewOut,
    InterviewQuestionIn,
    InterviewQuestionOut,
    InterviewQuestionUpdate,
    InterviewReviewOut,
    KnowledgeOut,
    InterviewStatusUpdate,
)
from app.services import (
    interview_knowledge_service,
    interview_review_service,
    interview_service,
)

router = APIRouter()


def _get_owned(db: Session, interview_id: int, user_id: int) -> Interview:
    """取本人的面试记录，不存在或不属于本人一律 404。"""
    item = db.get(Interview, interview_id)
    if item is None or item.user_id != user_id:
        raise HTTPException(status_code=404, detail="面试记录不存在")
    return item


def _to_out(item: Interview, db: Session) -> InterviewOut:
    out = InterviewOut.model_validate(item)
    company = db.get(Company, item.company_id) if item.company_id else None
    out.company_name = company.name if company else None
    job = db.get(Job, item.job_id) if item.job_id else None
    out.job_title = job.title if job else None
    out.events = (
        db.query(InterviewEvent)
        .filter(InterviewEvent.interview_id == item.id)
        .order_by(InterviewEvent.created_at.asc())
        .all()
    )
    return out


@router.get("", response_model=list[InterviewOut])
def list_interviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = (
        db.query(Interview)
        .filter(Interview.user_id == current_user.id)
        # MySQL 不支持 NULLS LAST；用 IS NULL 排在前面等价实现，SQLite/MySQL 通用
        .order_by(Interview.scheduled_at.is_(None), Interview.scheduled_at.asc())
        .all()
    )
    return [_to_out(i, db) for i in items]


@router.get("/knowledge", response_model=KnowledgeOut)
def get_knowledge(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """面试知识库：跨面试聚合能力画像与薄弱项趋势。

    路由必须注册在 /{interview_id} 之前，否则 "knowledge" 会被当成路径参数。
    """
    return interview_knowledge_service.build_knowledge(db, current_user.id)


@router.get("/{interview_id}", response_model=InterviewOut)
def get_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _to_out(_get_owned(db, interview_id, current_user.id), db)


@router.post("", response_model=InterviewOut)
def create_interview(
    data: InterviewIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """新建面试。状态固定为 SCHEDULED，并写入审计链起点事件。"""
    item = interview_service.create(db, current_user.id, data.model_dump())
    return _to_out(item, db)


@router.put("/{interview_id}", response_model=InterviewOut)
def update_interview(
    interview_id: int,
    data: InterviewIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """编辑面试字段。不含状态——状态请调用 /status 接口。"""
    item = _get_owned(db, interview_id, current_user.id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return _to_out(item, db)


@router.post("/{interview_id}/status", response_model=InterviewOut)
def update_status(
    interview_id: int,
    data: InterviewStatusUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """按文档 8.4 状态机流转面试状态，并记录流转事件。

    流转到 COMPLETED 且已录入问题时，自动创建 Interview Review 任务（文档 8.4 结尾）。
    """
    item = _get_owned(db, interview_id, current_user.id)
    try:
        interview_service.transition(db, item, data.status, operator="USER", comment=data.comment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if data.status == "COMPLETED" and db.query(InterviewQuestion).filter(
        InterviewQuestion.interview_id == item.id
    ).first():
        review = interview_review_service.start_review(db, item)
        background_tasks.add_task(interview_review_service.run_interview_review, review.id)
    return _to_out(item, db)


# ---------------------------------------------------------------- 面试复盘


def _review_to_out(review: InterviewReview | None) -> InterviewReviewOut:
    """无复盘记录时返回 status=NONE，前端无需区分 404。"""
    if review is None:
        return InterviewReviewOut(status="NONE")
    return InterviewReviewOut(
        status=review.status,
        id=review.id,
        interview_id=review.interview_id,
        source=review.source,
        model_name=review.model_name,
        summary=review.summary,
        dimensions=json.loads(review.dimensions_json) if review.dimensions_json else [],
        weak_points=json.loads(review.weak_points_json) if review.weak_points_json else [],
        review_points=json.loads(review.review_points_json) if review.review_points_json else [],
        error_message=review.error_message,
        duration_ms=review.duration_ms,
        created_at=review.created_at,
        finished_at=review.finished_at,
    )


def _latest_review(db: Session, interview_id: int) -> InterviewReview | None:
    return (
        db.query(InterviewReview)
        .filter(
            InterviewReview.interview_id == interview_id,
            InterviewReview.is_latest.is_(True),
        )
        .order_by(InterviewReview.id.desc())
        .first()
    )


@router.post("/{interview_id}/review", response_model=InterviewReviewOut)
def trigger_review(
    interview_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """触发面试复盘（异步）。立即返回 RUNNING，前端轮询 GET 同路径。"""
    item = _get_owned(db, interview_id, current_user.id)
    if item.status not in ("COMPLETED", "REVIEWED"):
        raise HTTPException(status_code=400, detail="面试尚未完成，无法复盘")
    if not db.query(InterviewQuestion).filter(
        InterviewQuestion.interview_id == item.id
    ).first():
        raise HTTPException(status_code=400, detail="请先录入面试问题再复盘")
    existing = _latest_review(db, item.id)
    if existing is not None and existing.status == "RUNNING":
        raise HTTPException(status_code=400, detail="复盘正在进行中")

    review = interview_review_service.start_review(db, item)
    background_tasks.add_task(interview_review_service.run_interview_review, review.id)
    return _review_to_out(review)


@router.get("/{interview_id}/review", response_model=InterviewReviewOut)
def get_review(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned(db, interview_id, current_user.id)
    return _review_to_out(_latest_review(db, interview_id))


# ---------------------------------------------------------------- 面试问题记录


def _get_owned_question(
    db: Session, interview_id: int, question_id: int, user_id: int
) -> InterviewQuestion:
    _get_owned(db, interview_id, user_id)  # 先校验面试归属
    q = db.get(InterviewQuestion, question_id)
    if q is None or q.interview_id != interview_id:
        raise HTTPException(status_code=404, detail="面试问题不存在")
    return q


@router.get("/{interview_id}/questions", response_model=list[InterviewQuestionOut])
def list_questions(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned(db, interview_id, current_user.id)
    return (
        db.query(InterviewQuestion)
        .filter(InterviewQuestion.interview_id == interview_id)
        .order_by(InterviewQuestion.sort_order.asc(), InterviewQuestion.id.asc())
        .all()
    )


@router.post("/{interview_id}/questions", response_model=InterviewQuestionOut)
def create_question(
    interview_id: int,
    data: InterviewQuestionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """录入一条面试问题。用户手工录入，source 固定为 USER。"""
    interview = _get_owned(db, interview_id, current_user.id)
    item = InterviewQuestion(
        interview_id=interview.id,
        user_id=current_user.id,
        source="USER",
        **data.model_dump(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{interview_id}/questions/{question_id}", response_model=InterviewQuestionOut)
def update_question(
    interview_id: int,
    question_id: int,
    data: InterviewQuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """修改面试问题。

    人工可接管原则：用户一旦改动分类或知识点，source 置为 USER，
    S4 的 Interview Agent 复盘时不再覆盖这条的标注。
    """
    item = _get_owned_question(db, interview_id, question_id, current_user.id)
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(item, field, value)
    if "category" in changes or "knowledge_point" in changes:
        item.source = "USER"
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
    item = _get_owned_question(db, interview_id, question_id, current_user.id)
    db.delete(item)
    db.commit()
    return {"message": "已删除"}


@router.delete("/{interview_id}")
def delete_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = _get_owned(db, interview_id, current_user.id)
    # 子表外键为 ON DELETE NO ACTION，必须先清子表再删主表
    for child in (InterviewQuestion, InterviewReview, InterviewEvent):
        db.query(child).filter(child.interview_id == item.id).delete()
    db.delete(item)
    db.commit()
    return {"message": "已删除"}
