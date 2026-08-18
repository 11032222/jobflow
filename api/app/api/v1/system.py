"""系统状态接口（设置页用，不暴露敏感信息）。"""
from fastapi import APIRouter, Depends

from app.agents.llm import llm_service
from app.core.config import settings
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/status")
def system_status(current_user: User = Depends(get_current_user)):
    from app.agents.llm import llm_service

    return {
        "llm_available": llm_service.is_available(current_user.id),
        "llm_model": (llm_service._resolve(current_user.id) or {}).get("model"),
        "mail_mode": settings.MAIL_MODE,
        "smtp_configured": settings.smtp_configured,
        "demo_inbox": settings.DEMO_INBOX,
        "database": "mysql" if settings.database_url.startswith("mysql") else "sqlite",
        "job_count_sources": None,
    }
