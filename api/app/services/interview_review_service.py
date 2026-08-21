"""面试复盘服务：异步编排 Interview Agent，落库并推进面试状态。

结构对齐 resume_parse_service：独立会话 + try/except/finally，异常写 FAILED。
与简历解析不同的是，本链路会正确调用 agent_service.set_status 维护 AgentTask 状态。
"""
import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.agents.interview_agent import interview_agent
from app.models.company import Company
from app.models.interview import Interview, InterviewQuestion, InterviewReview
from app.models.job import Job
from app.services import agent_service, interview_service

logger = logging.getLogger(__name__)


def start_review(db: Session, interview: Interview) -> InterviewReview:
    """同步创建复盘任务与 RUNNING 记录，供接口立即返回。

    旧版本置 is_latest=False 保留（沿用 CandidateProfile.is_current 模式）。
    """
    db.query(InterviewReview).filter(
        InterviewReview.interview_id == interview.id,
        InterviewReview.is_latest.is_(True),
    ).update({"is_latest": False})

    task = agent_service.create_task(
        db, interview.user_id, "INTERVIEW_REVIEW", interview_id=interview.id
    )
    review = InterviewReview(
        interview_id=interview.id,
        user_id=interview.user_id,
        status="RUNNING",
        is_latest=True,
        agent_task_id=task.id,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def _collect_questions(db: Session, interview_id: int) -> list[dict]:
    rows = (
        db.query(InterviewQuestion)
        .filter(InterviewQuestion.interview_id == interview_id)
        .order_by(InterviewQuestion.sort_order.asc(), InterviewQuestion.id.asc())
        .all()
    )
    return [
        {
            "id": r.id,
            "question": r.question,
            "my_answer": r.my_answer,
            "mastery": r.mastery,
            "category": r.category if r.source == "USER" else None,
            "knowledge_point": r.knowledge_point if r.source == "USER" else None,
        }
        for r in rows
    ]


def _apply_labels(db: Session, interview_id: int, labels: list[dict]) -> int:
    """把 Agent 的分类/知识点写回问题表。

    人工可接管原则：source == 'USER' 的问题是用户亲自标注过的，跳过不覆盖。
    """
    if not labels:
        return 0
    by_id = {lab["question_id"]: lab for lab in labels}
    rows = (
        db.query(InterviewQuestion)
        .filter(
            InterviewQuestion.interview_id == interview_id,
            InterviewQuestion.id.in_(by_id.keys()),
        )
        .all()
    )
    applied = 0
    for row in rows:
        # 用户标注过任一维度即整条锁定，与 update_question 置 USER 的条件保持一致。
        # 只判 category 会让「只改了知识点」的纠正被静默覆盖。
        if row.source == "USER" and (row.category or row.knowledge_point):
            continue
        # 裸题（source=USER 但两个维度都空）不算标注过，仍交给 Agent 分类
        lab = by_id[row.id]
        if lab.get("category"):
            row.category = lab["category"]
        if lab.get("knowledge_point"):
            row.knowledge_point = lab["knowledge_point"]
        row.source = "AGENT"
        applied += 1
    return applied


def _mark_failed(db: Session, review_id: int, exc: Exception) -> None:
    """分析阶段失败：复盘与任务同时置 FAILED。"""
    review = db.get(InterviewReview, review_id)
    if review is None:
        return
    review.status = "FAILED"
    review.error_message = str(exc)[:500]
    review.finished_at = datetime.now()
    db.commit()
    task = agent_service.get_task(db, review.agent_task_id)
    if task:
        agent_service.set_status(db, task, "FAILED", error=str(exc)[:500])


def _finalize(
    db: Session, review: InterviewReview, interview: Interview, source: str, applied: int
) -> None:
    """分析结果已落库后的收尾：推进面试状态、结束任务。

    这里的异常不得回改复盘状态——分析确实成功了，
    否则会出现「面试已 REVIEWED、复盘却是 FAILED」的矛盾。
    """
    try:
        # 文档 8.4：复盘完成后面试进入 REVIEWED
        if interview.status == "COMPLETED":
            interview_service.transition(
                db, interview, "REVIEWED", operator="AGENT", comment="Interview Agent 复盘完成"
            )
        task = agent_service.get_task(db, review.agent_task_id)
        if task:
            agent_service.set_status(
                db, task, "SUCCESS", progress=100,
                message=f"复盘完成，来源 {source}，标注 {applied} 题",
            )
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.exception(
            "复盘收尾失败（分析结果已保存，复盘状态保持 SUCCESS）review_id=%s", review.id
        )


def run_interview_review(review_id: int) -> None:
    """后台执行面试复盘（独立 DB 会话，由 BackgroundTasks 调用）。"""
    from app.core.database import SessionLocal

    db = SessionLocal()
    started = datetime.now()
    try:
        review = db.get(InterviewReview, review_id)
        if review is None:
            logger.warning("复盘记录不存在 review_id=%s", review_id)
            return

        # ---- 分析阶段：失败则整条复盘标 FAILED ----
        try:
            interview = db.get(Interview, review.interview_id)
            if interview is None:
                raise ValueError("面试记录不存在")

            task = agent_service.get_task(db, review.agent_task_id)
            if task:
                agent_service.set_status(db, task, "RUNNING", progress=10, message="开始面试复盘")

            questions = _collect_questions(db, interview.id)
            job = db.get(Job, interview.job_id) if interview.job_id else None
            company = db.get(Company, interview.company_id) if interview.company_id else None
            job_brief = (
                {"title": job.title, "company_name": company.name if company else None}
                if job
                else None
            )

            result = interview_agent.review(
                interview={"round_no": interview.round_no, "round_type": interview.round_type},
                questions=questions,
                job=job_brief,
                user_id=interview.user_id,
            )
            applied = _apply_labels(db, interview.id, result.get("question_labels") or [])

            review.status = "SUCCESS"
            review.source = result.get("source")
            review.model_name = result.get("model_name")
            review.summary = result.get("summary")
            review.dimensions_json = json.dumps(result.get("dimensions") or [], ensure_ascii=False)
            review.weak_points_json = json.dumps(result.get("weak_points") or [], ensure_ascii=False)
            review.review_points_json = json.dumps(
                result.get("review_points") or [], ensure_ascii=False
            )
            review.duration_ms = int((datetime.now() - started).total_seconds() * 1000)
            review.finished_at = datetime.now()
            db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("面试复盘分析失败 review_id=%s", review_id)
            db.rollback()
            _mark_failed(db, review_id, exc)
            return

        # ---- 收尾阶段：失败只记日志，不回改已成功的复盘 ----
        _finalize(db, review, interview, result.get("source"), applied)
        logger.info(
            "面试复盘完成 interview_id=%s source=%s 耗时=%sms",
            interview.id, result.get("source"), review.duration_ms,
        )
    finally:
        db.close()
