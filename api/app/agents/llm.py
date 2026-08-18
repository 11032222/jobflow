"""统一 LLM Service：兼容 OpenAI 协议的接口（通义千问 / GLM-4 / DeepSeek / 任意兼容端点）。

支持两种配置来源：
1. 用户自定义（user_llm_configs 表，设置页可配置）—— 优先
2. 全局 .env（LLM_API_KEY / LLM_BASE_URL / LLM_MODEL）—— 兜底
"""
import json
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_user_llm_config(user_id: int | None) -> dict | None:
    """从数据库读取用户自定义模型配置。"""
    if user_id is None:
        return None
    from app.core.database import SessionLocal
    from app.models.system_config import UserLLMConfig

    db = SessionLocal()
    try:
        row = (
            db.query(UserLLMConfig)
            .filter(UserLLMConfig.user_id == user_id, UserLLMConfig.enabled.is_(True))
            .first()
        )
        if row and row.api_key and row.base_url:
            return {
                "api_key": row.api_key,
                "base_url": row.base_url.rstrip("/"),
                "model": row.model or "qwen-plus",
                "protocol": row.protocol or "openai-compatible",
            }
    finally:
        db.close()
    return None


class LLMService:
    """LLM 统一访问层。未配置时 available=False，上层走规则引擎 fallback。"""

    def __init__(self) -> None:
        self.global_api_key = (settings.LLM_API_KEY or "").strip()
        self.global_base_url = (settings.LLM_BASE_URL or "").strip().rstrip("/")
        self.global_model = (settings.LLM_MODEL or "").strip() or "qwen-plus"

    @property
    def available(self) -> bool:
        return bool(self.global_api_key and self.global_base_url)

    def is_available(self, user_id: int | None = None) -> bool:
        return self._resolve(user_id) is not None

    def _resolve(self, user_id: int | None = None) -> dict | None:
        cfg = get_user_llm_config(user_id)
        if cfg:
            return cfg
        if self.available:
            return {
                "api_key": self.global_api_key,
                "base_url": self.global_base_url,
                "model": self.global_model,
                "protocol": "openai-compatible",
            }
        return None

    def _endpoint(self, base_url: str) -> str:
        if base_url.endswith(("/chat/completions", "/completions", "/v1/messages")):
            return base_url
        return f"{base_url}/chat/completions"

    def chat_json(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        user_id: int | None = None,
    ) -> dict | None:
        """调用 LLM 并要求返回 JSON。解析失败返回 None。"""
        cfg = self._resolve(user_id)
        if not cfg:
            return None
        payload = {
            "model": cfg["model"],
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        try:
            with httpx.Client(timeout=90) as client:
                resp = client.post(
                    self._endpoint(cfg["base_url"]),
                    headers={
                        "Authorization": f"Bearer {cfg['api_key']}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                content = content.strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
                return json.loads(content)
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM 调用失败(user_id=%s)，降级规则引擎: %s", user_id, exc)
            return None

    def chat_text(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        user_id: int | None = None,
    ) -> str | None:
        cfg = self._resolve(user_id)
        if not cfg:
            return None
        payload = {
            "model": cfg["model"],
            "messages": messages,
            "temperature": temperature,
        }
        try:
            with httpx.Client(timeout=90) as client:
                resp = client.post(
                    self._endpoint(cfg["base_url"]),
                    headers={
                        "Authorization": f"Bearer {cfg['api_key']}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM 调用失败(user_id=%s): %s", user_id, exc)
            return None


llm_service = LLMService()

