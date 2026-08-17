"""简历接口。"""
import shutil
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.resume import Resume
from app.models.user import User
from app.schemas.resume import ResumeOut

router = APIRouter()

ALLOWED_TYPES = {".pdf", ".doc", ".docx", ".txt", ".png", ".jpg", ".jpeg"}


@router.post("", response_model=ResumeOut)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {suffix}")
    user_dir = Path(settings.UPLOAD_DIR) / str(current_user.id)
    user_dir.mkdir(parents=True, exist_ok=True)

    import uuid

    stored_name = f"{uuid.uuid4().hex}{suffix}"
    dest = user_dir / stored_name
    with dest.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    resume = Resume(
        user_id=current_user.id,
        file_name=file.filename or stored_name,
        file_path=str(dest),
        file_type=suffix.lstrip("."),
        file_size=dest.stat().st_size,
        parse_status="PENDING",
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.get("", response_model=list[ResumeOut])
def list_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .all()
    )


@router.get("/{resume_id}", response_model=ResumeOut)
def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = db.get(Resume, resume_id)
    if resume is None or resume.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="简历不存在")
    return resume


@router.post("/{resume_id}/parse")
def parse_resume(
    resume_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """触发简历解析（后台异步）：提取文本 → Resume Agent → 生成结构化画像。"""
    from app.services.agent_service import create_task
    from app.services.resume_parse_service import run_resume_parse

    resume = db.get(Resume, resume_id)
    if resume is None or resume.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="简历不存在")
    if resume.parse_status == "PARSING":
        raise HTTPException(status_code=400, detail="简历正在解析中")
    task = create_task(db, current_user.id, "RESUME_PARSE", resume_id=resume.id)
    resume.parse_status = "PARSING"
    db.commit()
    background_tasks.add_task(run_resume_parse, resume.id)
    return {"message": "简历解析任务已启动", "task_id": task.id, "parse_status": "PARSING"}


@router.delete("/{resume_id}")
def delete_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = db.get(Resume, resume_id)
    if resume is None or resume.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="简历不存在")
    try:
        Path(resume.file_path).unlink(missing_ok=True)
    except OSError:
        pass
    db.delete(resume)
    db.commit()
    return {"message": "已删除"}
