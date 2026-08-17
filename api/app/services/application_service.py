"""投递业务服务：状态机、事件记录、邮件投递。"""
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application import Application, ApplicationEvent
from app.models.company import Company
from app.models.job import Job
from app.models.profile import CandidateProfile
from app.models.resume import Resume
from app.services.email_service import email_service

logger = logging.getLogger(__name__)

# 状态机：允许的转移
TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"SUBMITTING", "CLOSED"},
    "SUBMITTING": {"SUBMITTED", "FAILED", "CLOSED"},
    "SUBMITTED": {"WAITING", "TEST", "INTERVIEW", "OFFER", "REJECTED", "CLOSED"},
    "WAITING": {"TEST", "INTERVIEW", "OFFER", "REJECTED", "CLOSED"},
    "TEST": {"INTERVIEW", "OFFER", "REJECTED", "CLOSED"},
    "INTERVIEW": {"OFFER", "REJECTED", "CLOSED"},
    "OFFER": {"CLOSED"},
    "REJECTED": {"CLOSED"},
    "FAILED": {"SUBMITTING", "CLOSED"},
    "CLOSED": set(),
}

VALID_STATUSES = set(TRANSITIONS.keys())


def transition(
    db: Session,
    app: Application,
    new_status: str,
    operator: str = "USER",
    comment: str | None = None,
) -> Application:
    """执行状态流转并记录事件。非法流转抛 ValueError。"""
    if new_status not in VALID_STATUSES:
        raise ValueError(f"未知状态: {new_status}")
    if new_status not in TRANSITIONS.get(app.status, set()):
        raise ValueError(f"状态不允许从 {app.status} 流转到 {new_status}")
    old = app.status
    app.status = new_status
    app.updated_at = datetime.now()
    db.add(
        ApplicationEvent(
            application_id=app.id,
            from_status=old,
            to_status=new_status,
            operator=operator,
            comment=comment,
        )
    )
    db.commit()
    db.refresh(app)
    return app


def build_application_email(
    app: Application,
    job: Job,
    company: Company | None,
    profile: CandidateProfile | None,
    resume: Resume | None,
) -> tuple[str, str, str, list[tuple[str, bytes]]]:
    """生成投递邮件。返回 (收件人, 主题, 正文html, 附件列表)。"""
    to_addr = settings.DEMO_INBOX or settings.SMTP_FROM or settings.SMTP_USER
    name = (profile.name if profile else None) or "求职者"
    title = profile.title if profile else None
    job_title = job.title
    company_name = company.name if company else "该公司"

    subject = f"[JobFlow演示投递] {name} · {job_title} · {company_name}"

    profile_html = ""
    if profile:
        rows = [
            ("姓名", profile.name),
            ("求职意向", profile.title),
            ("学历", profile.education_level),
            ("学校", profile.school),
            ("专业", profile.major),
            ("工作年限", f"{profile.years_of_experience or 0} 年" if profile.years_of_experience is not None else None),
            ("所在城市", profile.city),
            ("电话", profile.phone),
            ("邮箱", profile.email),
        ]
        profile_html = "<tr><th>候选人信息</th><td>" + " · ".join(
            f"{k}: {v}" for k, v in rows if v
        ) + "</td></tr>"

    summary = (profile.summary if profile else None) or (
        f"我叫{name}，正在寻找{title or '合适'}的职位，希望有机会加入贵公司。"
    )

    job_rows = [
        ("职位", job.title),
        ("薪资", job.salary_text),
        ("城市", job.city),
        ("学历要求", job.education),
        ("经验要求", job.experience),
        ("岗位类型", job.job_type),
        ("职位链接", job.source_url),
    ]
    job_html = "".join(
        f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in job_rows if v
    )

    body = f"""
<html><body style="font-family: 'Microsoft YaHei', sans-serif; line-height: 1.6; color: #333;">
<div style="max-width: 640px; margin: 0 auto; border: 1px solid #eee; border-radius: 8px; overflow: hidden;">
  <div style="background: #2b6cb0; color: #fff; padding: 16px 24px;">
    <h2 style="margin: 0;">求职投递信（JobFlow 演示）</h2>
  </div>
  <div style="padding: 24px;">
    <p>尊敬的招聘负责人：</p>
    <p>您好！我是<strong>{name}</strong>，看到贵公司发布的「{job_title}」职位，非常契合我的职业方向，特此投递申请。</p>
    <blockquote style="border-left: 4px solid #2b6cb0; margin: 12px 0; padding: 8px 16px; background: #f7fafc;">{summary}</blockquote>
    <h3 style="border-bottom: 1px solid #eee; padding-bottom: 8px;">投递岗位信息</h3>
    <table style="border-collapse: collapse; width: 100%;">{job_html}{profile_html}</table>
    <p style="margin-top: 20px;">个人简历详见附件，期待您的回复，谢谢！</p>
    <p>此邮件由 JobFlow 简历投递系统自动发送（演示模式，所有投递发送至演示收件箱）。</p>
  </div>
</div>
</body></html>
    """

    attachments: list[tuple[str, bytes]] = []
    if resume and resume.file_path and Path(resume.file_path).exists():
        try:
            attachments.append(
                (
                    resume.file_name or Path(resume.file_path).name,
                    Path(resume.file_path).read_bytes(),
                )
            )
        except OSError as exc:
            logger.warning("读取简历附件失败: %s", exc)

    return to_addr, subject, body, attachments


def submit_application_by_email(app_id: int) -> None:
    """后台执行邮件投递（独立 DB 会话，由 BackgroundTasks 调用）。"""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        app = db.get(Application, app_id)
        if app is None:
            return
        if app.status == "PENDING":
            transition(db, app, "SUBMITTING", operator="SYSTEM", comment="开始投递")

        job = db.get(Job, app.job_id)
        company = db.get(Company, job.company_id) if job and job.company_id else None
        profile = (
            db.query(CandidateProfile)
            .filter(
                CandidateProfile.user_id == app.user_id,
                CandidateProfile.is_current.is_(True),
            )
            .first()
        )
        resume = db.get(Resume, app.resume_id) if app.resume_id else None

        to_addr, subject, body, attachments = build_application_email(
            app, job, company, profile, resume
        )
        ok, message_id, error = email_service.send(to_addr, subject, body, attachments)

        if ok:
            app.email_to = to_addr
            app.email_message_id = message_id
            app.sent_at = datetime.now()
            transition(
                db, app, "SUBMITTED", operator="SYSTEM", comment="邮件已发送至演示收件箱"
            )
        else:
            app.note = f"邮件发送失败: {error}"
            transition(
                db,
                app,
                "FAILED",
                operator="SYSTEM",
                comment=f"邮件发送失败: {error[:300]}",
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("投递任务异常 application_id=%s", app_id)
        db.rollback()
    finally:
        db.close()

