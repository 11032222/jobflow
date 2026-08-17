"""简历解析服务：提取文本 → Resume Agent → 生成结构化画像。"""
import logging
from pathlib import Path

from app.agents.resume_agent import resume_agent
from app.models.profile import CandidateProfile, ProfileExperience, ProfileSkill
from app.models.resume import Resume

logger = logging.getLogger(__name__)


def extract_text(file_path: str, file_type: str) -> str:
    """从简历文件中提取纯文本。"""
    path = Path(file_path)
    if not path.exists():
        return ""
    suffix = file_type.lower()
    try:
        if suffix == "pdf" or path.suffix.lower() == ".pdf":
            import pdfplumber

            with pdfplumber.open(path) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        if suffix in ("docx", "doc") or path.suffix.lower() == ".docx":
            import docx

            doc = docx.Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs if p.text)
        if suffix in ("txt", "md"):
            return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:  # noqa: BLE001
        logger.warning("简历文本提取失败 %s: %s", file_path, exc)
    # 图片暂不支持 OCR，返回空
    return ""


def _create_profile_from_result(db, user_id: int, resume: Resume, profile_data: dict) -> CandidateProfile:
    """将 Agent 结构化结果写入画像（先取消旧当前画像）。"""
    db.query(CandidateProfile).filter(
        CandidateProfile.user_id == user_id, CandidateProfile.is_current.is_(True)
    ).update({"is_current": False})

    profile = CandidateProfile(
        user_id=user_id,
        resume_id=resume.id,
        name=profile_data.get("name"),
        title=profile_data.get("title"),
        phone=profile_data.get("phone"),
        email=profile_data.get("email"),
        city=profile_data.get("city"),
        years_of_experience=profile_data.get("years_of_experience"),
        education_level=profile_data.get("education_level"),
        school=profile_data.get("school"),
        major=profile_data.get("major"),
        summary=profile_data.get("summary"),
        source=profile_data.get("source", "RULE"),
        status="DRAFT",
        is_current=True,
    )
    db.add(profile)
    db.flush()

    for skill in profile_data.get("skills") or []:
        if skill and skill.get("name"):
            db.add(
                ProfileSkill(
                    profile_id=profile.id,
                    name=skill["name"],
                    level=skill.get("level"),
                    years=skill.get("years"),
                )
            )
    for idx, exp in enumerate(profile_data.get("experiences") or []):
        if not isinstance(exp, dict) or not exp.get("school_or_company"):
            continue
        db.add(
            ProfileExperience(
                profile_id=profile.id,
                type=exp.get("type", "other"),
                school_or_company=exp.get("school_or_company"),
                degree=exp.get("degree"),
                major=exp.get("major"),
                title=exp.get("title"),
                start_date=exp.get("start_date"),
                end_date=exp.get("end_date"),
                description=exp.get("description"),
                sort_order=idx,
            )
        )
    db.commit()
    db.refresh(profile)
    return profile


def run_resume_parse(resume_id: int) -> None:
    """后台执行简历解析（独立 DB 会话，由 BackgroundTasks 调用）。"""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        resume = db.get(Resume, resume_id)
        if resume is None:
            return
        resume.parse_status = "PARSING"
        db.commit()

        text = extract_text(resume.file_path, resume.file_type)
        resume.raw_text = text
        result = resume_agent.parse(text)

        if result["status"] == "SUCCESS" and result.get("profile"):
            _create_profile_from_result(db, resume.user_id, resume, result["profile"])
            resume.parse_status = "SUCCESS"
        else:
            resume.parse_status = "FAILED"
        db.commit()
        logger.info("简历解析完成 resume_id=%s status=%s", resume_id, resume.parse_status)
    except Exception as exc:  # noqa: BLE001
        logger.exception("简历解析异常 resume_id=%s", resume_id)
        db.rollback()
        resume = db.get(Resume, resume_id)
        if resume:
            resume.parse_status = "FAILED"
            db.commit()
    finally:
        db.close()
