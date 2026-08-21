"""用户模型服务配置接口（设置页）。"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.llm import llm_service
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.crypto import decrypt_secret, encrypt_secret
from app.models.system_config import UserLLMConfig
from app.models.user import User

router = APIRouter()


class LLMConfigIn(BaseModel):
    name: str = "模型配置"
    provider: str = ""
    protocol: str = "openai-compatible"
    api_key: str = ""
    base_url: str = ""
    model: str = "qwen-plus"
    asr_model: str = "whisper-1"
    enabled: bool = True


class LLMConfigOut(LLMConfigIn):
    id: int
    is_active: bool = False
    api_key_masked: str = ""


def _row_to_out(row: UserLLMConfig) -> LLMConfigOut:
    return LLMConfigOut(
        id=row.id,
        name=row.name or "模型配置",
        provider=row.provider or "",
        protocol=row.protocol or "openai-compatible",
        api_key="",
        api_key_masked=_mask(decrypt_secret(row.api_key)),
        base_url=row.base_url or "",
        model=row.model or "qwen-plus",
        asr_model=row.asr_model or "whisper-1",
        enabled=row.enabled,
        is_active=row.is_active,
    )


def _get_owned_row(db: Session, user_id: int, config_id: int) -> UserLLMConfig:
    row = (
        db.query(UserLLMConfig)
        .filter(UserLLMConfig.id == config_id, UserLLMConfig.user_id == user_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    return row


@router.get("/models", response_model=List[LLMConfigOut])
def list_model_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(UserLLMConfig)
        .filter(UserLLMConfig.user_id == current_user.id)
        .order_by(UserLLMConfig.is_active.desc(), UserLLMConfig.id.asc())
        .all()
    )
    return [_row_to_out(r) for r in rows]


@router.post("/models", response_model=LLMConfigOut, status_code=201)
def create_model_config(
    data: LLMConfigIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = (
        db.query(UserLLMConfig)
        .filter(UserLLMConfig.user_id == current_user.id)
        .count()
    )
    row = UserLLMConfig(
        user_id=current_user.id,
        name=(data.name or "模型配置").strip(),
        provider=(data.provider or "").strip(),
        protocol=data.protocol,
        api_key=encrypt_secret(data.api_key.strip()),
        base_url=(data.base_url or "").strip(),
        model=(data.model or "").strip() or "qwen-plus",
        asr_model=(data.asr_model or "").strip() or "whisper-1",
        enabled=data.enabled,
        is_active=count == 0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_out(row)


@router.put("/models/{config_id}", response_model=LLMConfigOut)
def update_model_config(
    config_id: int,
    data: LLMConfigIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = _get_owned_row(db, current_user.id, config_id)
    row.name = (data.name or "模型配置").strip()
    row.provider = (data.provider or "").strip()
    row.protocol = data.protocol
    # 未填写 api_key 时保留原值（前端只回显掩码）
    if data.api_key:
        row.api_key = encrypt_secret(data.api_key.strip())
    row.base_url = (data.base_url or "").strip()
    row.model = (data.model or "").strip() or "qwen-plus"
    row.asr_model = (data.asr_model or "").strip() or "whisper-1"
    row.enabled = data.enabled
    db.commit()
    db.refresh(row)
    return _row_to_out(row)


@router.delete("/models/{config_id}")
def delete_model_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = _get_owned_row(db, current_user.id, config_id)
    was_active = row.is_active
    db.delete(row)
    db.commit()
    if was_active:
        next_row = (
            db.query(UserLLMConfig)
            .filter(UserLLMConfig.user_id == current_user.id)
            .order_by(UserLLMConfig.id.asc())
            .first()
        )
        if next_row:
            next_row.is_active = True
            db.commit()
    return {"ok": True}


@router.post("/models/{config_id}/activate", response_model=LLMConfigOut)
def activate_model_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = _get_owned_row(db, current_user.id, config_id)
    db.query(UserLLMConfig).filter(
        UserLLMConfig.user_id == current_user.id
    ).update({UserLLMConfig.is_active: False})
    row.is_active = True
    db.commit()
    db.refresh(row)
    return _row_to_out(row)


@router.post("/models/{config_id}/test")
def test_saved_model_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """用已保存的配置直接测试连接（无需再次输入 Key）。"""
    import time

    from app.agents.llm import LLMService

    row = _get_owned_row(db, current_user.id, config_id)
    base_url = (row.base_url or "").strip().rstrip("/")
    local = any(m in base_url for m in ("localhost", "127.0.0.1", "0.0.0.0"))
    if not base_url or (not row.api_key and not local):
        return {"ok": False, "error": "该配置缺少 API Key 或 Base URL"}

    tester = LLMService()
    tester.global_api_key = decrypt_secret(row.api_key)
    tester.global_base_url = base_url
    tester.global_model = row.model or "qwen-plus"
    tester.global_protocol = (row.protocol or "openai-compatible").strip().lower()
    start = time.time()
    result = tester.chat_text(
        [{"role": "user", "content": "请回复：连接成功"}], temperature=0.1
    )
    cost_ms = int((time.time() - start) * 1000)
    if result:
        return {"ok": True, "latency_ms": cost_ms, "reply": result[:80]}
    return {"ok": False, "latency_ms": cost_ms, "error": "模型连接失败，请检查配置"}


@router.get("/model", response_model=LLMConfigOut)
def get_model_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (
        db.query(UserLLMConfig)
        .filter(UserLLMConfig.user_id == current_user.id)
        .order_by(UserLLMConfig.is_active.desc(), UserLLMConfig.id.asc())
        .first()
    )
    if row is None:
        return LLMConfigOut(
            id=0,
            name="模型配置",
            provider="",
            protocol="openai-compatible",
            api_key="",
            api_key_masked="",
            base_url="",
            model="qwen-plus",
            asr_model="whisper-1",
            enabled=True,
            is_active=False,
        )
    return _row_to_out(row)


@router.put("/model", response_model=LLMConfigOut)
def save_model_config(
    data: LLMConfigIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (
        db.query(UserLLMConfig)
        .filter(UserLLMConfig.user_id == current_user.id)
        .order_by(UserLLMConfig.is_active.desc(), UserLLMConfig.id.asc())
        .first()
    )
    if row is None:
        row = UserLLMConfig(user_id=current_user.id, is_active=True)
        db.add(row)
    row.name = (data.name or row.name or "模型配置").strip()
    row.provider = (data.provider or row.provider or "").strip()
    row.protocol = data.protocol
    if data.api_key:
        row.api_key = encrypt_secret(data.api_key.strip())
    row.base_url = (data.base_url or "").strip()
    row.model = (data.model or "").strip() or "qwen-plus"
    row.asr_model = (data.asr_model or "").strip() or "whisper-1"
    row.enabled = data.enabled
    db.commit()
    db.refresh(row)
    return _row_to_out(row)


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
    tester.global_protocol = (data.protocol or "openai-compatible").strip().lower()

    if not tester.global_base_url or (not tester.global_api_key and not any(m in tester.global_base_url for m in ("localhost", "127.0.0.1", "0.0.0.0"))):
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
