"""统一 LLM Service：支持 OpenAI 兼容 / Anthropic / Google Gemini 三种协议。

配置来源：
1. 用户自定义（user_llm_configs 表，设置页可配置）—— 优先
2. 全局 .env（LLM_API_KEY / LLM_BASE_URL / LLM_MODEL / LLM_PROTOCOL）—— 兜底
"""
import json
import logging
import re

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_LOCAL_BASE_URL_MARKERS = ("localhost", "127.0.0.1", "0.0.0.0")


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
            .order_by(UserLLMConfig.is_active.desc(), UserLLMConfig.id.asc())
            .first()
        )
        if row and row.base_url:
            base_url = (row.base_url or "").strip()
            local = any(marker in base_url for marker in _LOCAL_BASE_URL_MARKERS)
            if row.api_key or local:
                return {
                    "api_key": row.api_key or "",
                    "base_url": base_url.rstrip("/"),
                    "model": row.model or "qwen-plus",
                    "protocol": (row.protocol or "openai-compatible").lower(),
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
        self.global_protocol = (settings.LLM_PROTOCOL or "openai-compatible").strip().lower()

    @property
    def available(self) -> bool:
        return self._global_configured()

    def _global_configured(self) -> bool:
        if not self.global_base_url:
            return False
        local = any(marker in self.global_base_url for marker in _LOCAL_BASE_URL_MARKERS)
        return bool(self.global_api_key or local)

    def is_available(self, user_id: int | None = None) -> bool:
        return self._resolve(user_id) is not None

    def _resolve(self, user_id: int | None = None) -> dict | None:
        cfg = get_user_llm_config(user_id)
        if cfg:
            return cfg
        if self._global_configured():
            return {
                "api_key": self.global_api_key,
                "base_url": self.global_base_url,
                "model": self.global_model,
                "protocol": self.global_protocol,
            }
        return None

    def _endpoint(self, base_url: str, protocol: str, model: str) -> str:
        base_url = (base_url or "").strip().rstrip("/")
        protocol = (protocol or "openai-compatible").lower()

        if protocol == "anthropic":
            if base_url.endswith("/messages"):
                return base_url
            if base_url.endswith("/v1"):
                return f"{base_url}/messages"
            return f"{base_url}/v1/messages"

        if protocol == "gemini":
            if base_url.endswith(f"/models/{model}:generateContent"):
                return base_url
            if re.search(r"/v\d+(beta)?$", base_url):
                return f"{base_url}/models/{model}:generateContent"
            return f"{base_url}/v1beta/models/{model}:generateContent"

        # 默认 OpenAI 兼容协议
        if base_url.endswith(("/chat/completions", "/completions", "/v1/messages")):
            return base_url
        return f"{base_url}/chat/completions"

    def _parse_json(self, text: str) -> dict | None:
        text = (text or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            for start_ch, end_ch in (("{", "}"), ("[", "]")):
                start = text.find(start_ch)
                end = text.rfind(end_ch)
                if start != -1 and end > start:
                    try:
                        return json.loads(text[start:end + 1])
                    except (json.JSONDecodeError, ValueError):
                        continue
        return None

    def _chat_openai(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: list[dict],
        temperature: float,
        json_mode: bool,
    ) -> str | None:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=90) as client:
            resp = client.post(
                self._endpoint(base_url, "openai-compatible", model),
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    def _chat_anthropic(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: list[dict],
        temperature: float,
        json_mode: bool,
    ) -> str | None:
        system_parts = [m.get("content", "") for m in messages if m.get("role") == "system"]
        system = "\n".join(system_parts) if system_parts else None
        if json_mode:
            instruction = "You are a JSON API. Return only valid JSON, no markdown code fences."
            system = f"{instruction}\n{system}" if system else instruction
        conversation = [m for m in messages if m.get("role") in ("user", "assistant")]
        payload = {
            "model": model,
            "max_tokens": 4096,
            "temperature": temperature,
            "messages": conversation,
        }
        if system:
            payload["system"] = system
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=90) as client:
            resp = client.post(
                self._endpoint(base_url, "anthropic", model),
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]

    def _chat_gemini(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: list[dict],
        temperature: float,
        json_mode: bool,
    ) -> str | None:
        system_text = "\n".join(
            m["content"] for m in messages if m.get("role") == "system"
        )
        contents = [
            {"role": "user", "parts": [{"text": m["content"]}]}
            for m in messages
            if m.get("role") in ("user", "assistant")
        ]
        generation_config = {"temperature": temperature}
        if json_mode:
            generation_config["responseMimeType"] = "application/json"
        payload = {"contents": contents, "generationConfig": generation_config}
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}
        params = {"key": api_key} if api_key else {}
        headers = {"Content-Type": "application/json"}
        with httpx.Client(timeout=90) as client:
            resp = client.post(
                self._endpoint(base_url, "gemini", model),
                headers=headers,
                params=params,
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

    def _chat_text(
        self,
        cfg: dict,
        messages: list[dict],
        temperature: float,
        json_mode: bool = False,
    ) -> str | None:
        protocol = (cfg.get("protocol") or "openai-compatible").lower()
        if protocol == "anthropic":
            return self._chat_anthropic(
                cfg["base_url"], cfg.get("api_key", ""), cfg["model"], messages, temperature, json_mode
            )
        if protocol == "gemini":
            return self._chat_gemini(
                cfg["base_url"], cfg.get("api_key", ""), cfg["model"], messages, temperature, json_mode
            )
        return self._chat_openai(
            cfg["base_url"], cfg.get("api_key", ""), cfg["model"], messages, temperature, json_mode
        )

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
        try:
            text = self._chat_text(cfg, messages, temperature, json_mode=True)
            if not text:
                return None
            return self._parse_json(text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM JSON 调用失败(user_id=%s)，降级规则引擎: %s", user_id, exc)
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
        try:
            return self._chat_text(cfg, messages, temperature)
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM 调用失败(user_id=%s): %s", user_id, exc)
            return None


llm_service = LLMService()