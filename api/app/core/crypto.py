"""敏感凭据（如 API Key）的对称加密工具。

设计目标：即使数据库被泄露/导出，没有应用密钥也读不出明文。应用密钥来自
`.env` 的 DATA_ENCRYPTION_KEY；未配置时回退到 JWT_SECRET，保证开箱即用。

存储约定：密文统一带 `enc:` 前缀，用于区分历史遗留明文，便于启动时迁移。
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

_PREFIX = "enc:"


def _fernet() -> Fernet:
    material = (settings.DATA_ENCRYPTION_KEY or settings.JWT_SECRET or "jobflow-dev-secret").encode("utf-8")
    key = base64.urlsafe_b64encode(hashlib.sha256(material).digest())
    return Fernet(key)


def is_encrypted(value: str | None) -> bool:
    return bool(value) and value.startswith(_PREFIX)


def encrypt_secret(plain: str | None) -> str:
    """加密明文；已加密或空值原样返回，避免重复加密。"""
    if not plain:
        return ""
    if is_encrypted(plain):
        return plain
    token = _fernet().encrypt(plain.encode("utf-8"))
    return f"{_PREFIX}{token.decode('utf-8')}"


def decrypt_secret(value: str | None) -> str:
    """解密存储值；历史明文或空值原样返回。"""
    if not value:
        return ""
    if not is_encrypted(value):
        return value
    try:
        return _fernet().decrypt(value[len(_PREFIX):].encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""
