"""统一 LLM Service：兼容 OpenAI 协议的接口（通义千问 / GLM-4 / 任意兼容端点）。"""
import json
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """LLM 统一访问层。未配置 Key 时 available=False，上层走规则引擎 fallback。"""

    def __init__(self) -> None:
        self.api_key = (settings.LLM_API_KEY or "").strip()
        self.base_url = (settings.LLM_BASE_URL or "").strip().rstrip("/")
        self.model = (settings.LLM_MODEL or "").strip() or "qwen-plus"

    @property
    def available(self) -> bool:
        return bool(self.api_key and self.base_url)

    def _endpoint(self) -> str:
        # 兼容 base_url 已含 /v1 或 /v4 的情况
        if self.base_url.endswith(("/chat/completions", "/completions")):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    def chat_json(self, messages: list[dict], temperature: float = 0.2) -> dict | None:
        """调用 LLM 并要求返回 JSON。解析失败返回 None。"""
        if not self.available:
            return None
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        try:
            with httpx.Client(timeout=60) as client:
                resp = client.post(
                    self._endpoint(),
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                # 兼容返回被 ```json 包裹的情况
                content = content.strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
                return json.loads(content)
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM 调用失败，降级规则引擎: %s", exc)
            return None

    def chat_text(self, messages: list[dict], temperature: float = 0.2) -> str | None:
        if not self.available:
            return None
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        try:
            with httpx.Client(timeout=60) as client:
                resp = client.post(
                    self._endpoint(),
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM 调用失败: %s", exc)
            return None


llm_service = LLMService()
