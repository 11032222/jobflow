"""面试业务服务：状态机与流转事件。

状态定义对齐《概要设计说明书》8.4，实现方式与 application_service.transition 对称。
"""
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.interview import Interview, InterviewEvent

logger = logging.getLogger(__name__)

# 面试状态机（文档 8.4）：SCHEDULED → IN_PROGRESS → COMPLETED → REVIEWED
# CANCELLED 为保留的既有功能，与投递状态 CLOSED 语义对称
TRANSITIONS: dict[str, set[str]] = {
    "SCHEDULED": {"IN_PROGRESS", "CANCELLED"},
    "IN_PROGRESS": {"COMPLETED", "CANCELLED"},
    "COMPLETED": {"REVIEWED", "CANCELLED"},
    "REVIEWED": set(),
    "CANCELLED": set(),
}

VALID_STATUSES = set(TRANSITIONS.keys())


def create(db: Session, user_id: int, fields: dict) -> Interview:
    """新建面试并写入审计链起点事件。

    与 applications 创建投递时写 None -> PENDING 的做法对称，
    保证详情页事件时间线从创建开始，而不是从第一次流转开始。
    """
    interview = Interview(user_id=user_id, status="SCHEDULED", **fields)
    db.add(interview)
    db.flush()
    db.add(
        InterviewEvent(
            interview_id=interview.id,
            from_status=None,
            to_status="SCHEDULED",
            operator="USER",
            comment="创建面试记录",
        )
    )
    db.commit()
    db.refresh(interview)
    return interview


def transition(
    db: Session,
    interview: Interview,
    new_status: str,
    operator: str = "USER",
    comment: str | None = None,
) -> Interview:
    """执行状态流转并记录事件。非法流转抛 ValueError。"""
    if new_status not in VALID_STATUSES:
        raise ValueError(f"未知状态: {new_status}")
    if new_status not in TRANSITIONS.get(interview.status, set()):
        raise ValueError(f"状态不允许从 {interview.status} 流转到 {new_status}")
    old = interview.status
    interview.status = new_status
    interview.updated_at = datetime.now()
    db.add(
        InterviewEvent(
            interview_id=interview.id,
            from_status=old,
            to_status=new_status,
            operator=operator,
            comment=comment,
        )
    )
    db.commit()
    db.refresh(interview)
    logger.info("面试状态流转 interview_id=%s %s -> %s", interview.id, old, new_status)
    return interview
