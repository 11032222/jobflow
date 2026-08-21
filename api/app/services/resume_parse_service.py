"""简历解析服务：提取文本 → Resume Agent → 生成结构化画像。"""
import logging
from datetime import datetime
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


_IMAGE_MIME = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "bmp": "image/bmp",
    "gif": "image/gif",
}


def image_mime_type(file_type: str) -> str:
    """根据 file_type 推断 MIME；默认 image/png。"""
    return _IMAGE_MIME.get((file_type or "").lower(), "image/png")


def ocr_extract_image(file_path: str) -> str:
    """用本机可用的 OCR 引擎识别图片文字（RapidOCR → PaddleOCR → Tesseract）。"""
    path = Path(file_path)
    if not path.exists():
        return ""

    # 1) RapidOCR（纯 Python/ONNX，最轻量）
    try:
        from rapidocr_onnxruntime import RapidOCR

        engine = RapidOCR()
        result, _ = engine(str(path))
        if result:
            return "\n".join(str(item[1]) for item in result if len(item) > 1)
    except Exception as exc:  # noqa: BLE001
        logger.debug("RapidOCR 不可用: %s", exc)

    # 2) PaddleOCR
    try:
        from paddleocr import PaddleOCR

        ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
        result = ocr.ocr(str(path), cls=True)
        lines = []
        for page in result or []:
            for item in page or []:
                if item and len(item) > 0 and item[1]:
                    lines.append(str(item[1][0]))
        return "\n".join(lines)
    except Exception as exc:  # noqa: BLE001
        logger.debug("PaddleOCR 不可用: %s", exc)

    # 3) Tesseract
    try:
        import pytesseract
        from PIL import Image

        return pytesseract.image_to_string(Image.open(str(path)), lang="chi_sim+eng")
    except Exception as exc:  # noqa: BLE001
        logger.debug("Tesseract 不可用: %s", exc)

    return ""


def _to_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y/%m/%d", "%Y/%m"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None

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
        if not isinstance(exp, dict) or not (exp.get("school_or_company") or exp.get("title")):
            continue
        db.add(
            ProfileExperience(
                profile_id=profile.id,
                type=exp.get("type", "other"),
                school_or_company=exp.get("school_or_company"),
                degree=exp.get("degree"),
                major=exp.get("major"),
                title=exp.get("title"),
                start_date=_to_date(exp.get("start_date")),
                end_date=_to_date(exp.get("end_date")),
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

        ftype = (resume.file_type or "").lower()
        if ftype in _IMAGE_MIME:
            # 图片简历：视觉大模型优先，OCR 兜底
            result = resume_agent.parse_image(
                resume.file_path, image_mime_type(ftype), user_id=resume.user_id
            )
        else:
            text = extract_text(resume.file_path, resume.file_type)
            resume.raw_text = text
            result = resume_agent.parse(text, user_id=resume.user_id)

        if result["status"] == "SUCCESS" and result.get("profile"):
            _create_profile_from_result(db, resume.user_id, resume, result["profile"])
            resume.parse_status = "SUCCESS"
        else:
            resume.parse_status = "FAILED"
            if result.get("message"):
                resume.fail_reason = result["message"][:500]
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
