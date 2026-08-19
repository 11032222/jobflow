"""适配器注册表：platform -> adapter 实例。"""
from app.collectors.base import PlatformAdapter
from app.collectors.mock import MockAdapter
from app.collectors.zhaopin import ZhaopinAdapter
from app.collectors.zhipin import ZhipinAdapter

_REGISTRY = {
    "zhaopin": ZhaopinAdapter,
    "zhipin": ZhipinAdapter,
    "liepin": None,  # 预留
    "ncss": None,    # 预留（24365）
    "mock": MockAdapter,
}

PLATFORM_LABELS = {
    "zhaopin": "智联招聘",
    "zhipin": "BOSS直聘",
    "mock": "模拟数据",
    "liepin": "猎聘",
    "ncss": "24365",
}


def get_adapter(platform: str) -> PlatformAdapter:
    cls = _REGISTRY.get(platform.lower())
    if cls is None:
        raise ValueError(f"暂不支持平台: {platform}（可用: {list(_REGISTRY)}）")
    return cls()


def supported_platforms() -> list[str]:
    return [k for k, v in _REGISTRY.items() if v is not None]
