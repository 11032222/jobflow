"""面试知识库：跨面试聚合个人能力画像（文档 3.10 结尾、4.x「与历史面试对比→判断进步情况」）。

聚合源是 interview_questions，不读 interview_reviews——问题表本身已按
「分类 + 自评」归一化，是天然的聚合源；复盘记录是每场面试的一次性产物。
"""
import logging

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.interview import MASTERY_SCORE, Interview, InterviewQuestion

logger = logging.getLogger(__name__)

_WEAK_THRESHOLD = 0.6


def _stars(score: float) -> int:
    return max(1, round(score * 5))


def _categorized(query):
    """已分类的题：category 非 NULL 且非空串。

    前端清空输入框可能提交空串，虽已在 Schema 归一为 None，
    但历史数据可能仍有空串，聚合时两者都要排除。
    """
    return query.filter(
        InterviewQuestion.category.isnot(None),
        InterviewQuestion.category != "",
    )


def _score_by_category(db: Session, user_id: int, interview_ids: list[int]) -> dict[str, float]:
    """给定面试范围内，各分类的掌握度均值。用于前后期对比。"""
    if not interview_ids:
        return {}
    rows = _categorized(
        db.query(
            InterviewQuestion.category,
            func.count(InterviewQuestion.id),
            func.sum(
                case(
                    (InterviewQuestion.mastery == "MASTERED", 1.0),
                    (InterviewQuestion.mastery == "PARTIAL", 0.5),
                    else_=0.0,
                )
            ),
        ).filter(
            InterviewQuestion.user_id == user_id,
            InterviewQuestion.interview_id.in_(interview_ids),
        )
    ).group_by(InterviewQuestion.category).all()
    return {c: round(float(total or 0) / n, 2) for c, n, total in rows if n}


def build_knowledge(db: Session, user_id: int) -> dict:
    """构建个人面试能力画像。"""
    # 1) 总体计数
    total_questions = (
        db.query(func.count(InterviewQuestion.id))
        .filter(InterviewQuestion.user_id == user_id)
        .scalar()
        or 0
    )
    uncategorized = total_questions - (
        _categorized(
            db.query(func.count(InterviewQuestion.id)).filter(
                InterviewQuestion.user_id == user_id
            )
        ).scalar()
        or 0
    )

    # 2) 按分类聚合：题数 / 三档自评计数 / 掌握度 / 覆盖面试场次
    rows = _categorized(
        db.query(
            InterviewQuestion.category,
            func.count(InterviewQuestion.id).label("cnt"),
            func.count(func.distinct(InterviewQuestion.interview_id)).label("iv_cnt"),
            func.sum(case((InterviewQuestion.mastery == "MASTERED", 1), else_=0)),
            func.sum(case((InterviewQuestion.mastery == "PARTIAL", 1), else_=0)),
            func.sum(case((InterviewQuestion.mastery == "FAILED", 1), else_=0)),
        ).filter(InterviewQuestion.user_id == user_id)
    ).group_by(InterviewQuestion.category).all()

    # 3) 前后期对比：按面试时间排序后对半分（文档「与历史面试对比→判断进步情况」）
    ordered_ids = [
        r[0]
        for r in db.query(Interview.id)
        .join(InterviewQuestion, InterviewQuestion.interview_id == Interview.id)
        .filter(Interview.user_id == user_id)
        .group_by(Interview.id)
        .order_by(func.coalesce(Interview.scheduled_at, Interview.created_at).asc())
        .all()
    ]
    earlier_scores: dict[str, float] = {}
    recent_scores: dict[str, float] = {}
    if len(ordered_ids) >= 2:
        mid = len(ordered_ids) // 2
        earlier_scores = _score_by_category(db, user_id, ordered_ids[:mid])
        recent_scores = _score_by_category(db, user_id, ordered_ids[mid:])

    categories = []
    for category, cnt, iv_cnt, mastered, partial, failed in rows:
        mastered, partial, failed = int(mastered or 0), int(partial or 0), int(failed or 0)
        score = round(
            (mastered * MASTERY_SCORE["MASTERED"] + partial * MASTERY_SCORE["PARTIAL"])
            / cnt,
            2,
        )
        earlier = earlier_scores.get(category)
        recent = recent_scores.get(category)
        categories.append(
            {
                "category": category,
                "count": cnt,
                "interview_count": iv_cnt,
                "mastered": mastered,
                "partial": partial,
                "failed": failed,
                "score": score,
                "stars": _stars(score),
                "earlier_score": earlier,
                "recent_score": recent,
                # 两期都有数据才给趋势，否则为 None（前端显示「-」）
                "delta": round(recent - earlier, 2)
                if earlier is not None and recent is not None
                else None,
            }
        )
    categories.sort(key=lambda c: (c["score"], -c["count"]))

    # 4) 薄弱分类与待复习知识点（按出现频次排序，去重）
    weak_categories = [c["category"] for c in categories if c["score"] < _WEAK_THRESHOLD]
    review_rows = (
        db.query(
            InterviewQuestion.knowledge_point,
            func.count(InterviewQuestion.id).label("cnt"),
        )
        .filter(
            InterviewQuestion.user_id == user_id,
            InterviewQuestion.mastery != "MASTERED",
            InterviewQuestion.knowledge_point.isnot(None),
            InterviewQuestion.knowledge_point != "",
        )
        .group_by(InterviewQuestion.knowledge_point)
        .order_by(func.count(InterviewQuestion.id).desc())
        .limit(20)
        .all()
    )

    return {
        "total_questions": total_questions,
        "uncategorized": uncategorized,
        "interview_count": len(ordered_ids),
        "categories": categories,
        "weak_categories": weak_categories,
        "review_points": [{"knowledge_point": kp, "count": cnt} for kp, cnt in review_rows],
    }
