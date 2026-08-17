"""适配器注册表：platform -> adapter 实例。"""
from app.collectors.base import PlatformAdapter
from app.collectors.mock import MockAdapter
from app.collectors.zhaopin import ZhaopinAdapter

_REGISTRY = {
    "zhaopin": ZhaopinAdapter,
    "liepin": None,  # 预留
    "ncss": None,    # 预留（24365）
    "mock": MockAdapter,
}


def get_adapter(platform: str) -> PlatformAdapter:
    cls = _REGISTRY.get(platform.lower())
    if cls is None:
        raise ValueError(f"暂不支持平台: {platform}（可用: {list(_REGISTRY)}）")
    return cls()


def supported_platforms() -> list[str]:
    return [k for k, v in _REGISTRY.items() if v is not None]
