"""用户模型服务配置接口（设置页）。"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.llm import llm_service
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.system_config import UserLLMConfig
from app.models.user import User

router = APIRouter()


class LLMConfigIn(BaseModel):
    protocol: str = "openai-compatible"
    api_key: str = ""
    base_url: str = ""
    model: str = "qwen-plus"
    enabled: bool = True


class LLMConfigOut(LLMConfigIn):
    api_key_masked: str = ""


@router.get("/model", response_model=LLMConfigOut)
def get_model_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (
        db.query(UserLLMConfig)
        .filter(UserLLMConfig.user_id == current_user.id)
        .first()
    )
    if row is None:
        return LLMConfigOut(
            protocol="openai-compatible",
            api_key="",
            base_url="",
            model="qwen-plus",
            enabled=True,
        )
    return LLMConfigOut(
        protocol=row.protocol or "openai-compatible",
        api_key=row.api_key or "",
        api_key_masked=_mask(row.api_key),
        base_url=row.base_url or "",
        model=row.model or "qwen-plus",
        enabled=row.enabled,
    )


@router.put("/model", response_model=LLMConfigOut)
def save_model_config(
    data: LLMConfigIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (
        db.query(UserLLMConfig)
        .filter(UserLLMConfig.user_id == current_user.id)
        .first()
    )
    if row is None:
        row = UserLLMConfig(user_id=current_user.id)
        db.add(row)
    # 未填写 api_key 时保留原值（前端可能只回显掩码）
    row.protocol = data.protocol
    if data.api_key:
        row.api_key = data.api_key.strip()
    row.base_url = (data.base_url or "").strip()
    row.model = (data.model or "").strip() or "qwen-plus"
    row.enabled = data.enabled
    db.commit()
    db.refresh(row)
    return LLMConfigOut(
        protocol=row.protocol,
        api_key=row.api_key or "",
        api_key_masked=_mask(row.api_key),
        base_url=row.base_url or "",
        model=row.model or "",
        enabled=row.enabled,
    )


@router.post("/model/test")
def test_model_config(
    data: LLMConfigIn,
    current_user: User = Depends(get_current_user),
):
    """测试模型连接（返回 {ok, latency_ms, error}）。"""
    import time

    from app.agents.llm import LLMService

    tester = LLMService()
    tester.global_api_key = data.api_key.strip()
    tester.global_base_url = (data.base_url or "").strip().rstrip("/")
    tester.global_model = (data.model or "").strip() or "qwen-plus"

    if not (tester.global_api_key and tester.global_base_url):
        return {"ok": False, "error": "请填写 API Key 与 Base URL"}
    start = time.time()
    result = tester.chat_text(
        [{"role": "user", "content": "请回复：连接成功"}], temperature=0.1
    )
    cost_ms = int((time.time() - start) * 1000)
    if result:
        return {"ok": True, "latency_ms": cost_ms, "reply": result[:80]}
    return {"ok": False, "latency_ms": cost_ms, "error": "模型连接失败，请检查配置"}


@router.get("/status")
def model_status(
    current_user: User = Depends(get_current_user),
):
    user_available = llm_service.is_available(current_user.id)
    global_available = llm_service.available
    return {
        "user_configured": user_available,
        "global_configured": global_available,
        "active_model": (
            llm_service._resolve(current_user.id) or {}
        ).get("model")
        if user_available or global_available
        else None,
    }


def _mask(api_key: str | None) -> str:
    if not api_key:
        return ""
    if len(api_key) <= 6:
        return "*" * len(api_key)
    return api_key[:4] + "*" * (len(api_key) - 6) + api_key[-2:]
