"""字段级加密（基于 Fernet）— 用于 DB 中敏感字段（飞书 secret 等）"""
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings

logger = logging.getLogger(__name__)

_cached_fernet: Optional[Fernet] = None


def _get_fernet() -> Optional[Fernet]:
    """获取 Fernet 实例。未配置 APP_ENCRYPTION_KEY 时返回 None（兼容旧部署）"""
    global _cached_fernet
    if _cached_fernet is not None:
        return _cached_fernet

    key = (get_settings().APP_ENCRYPTION_KEY or "").strip()
    if not key:
        return None

    try:
        _cached_fernet = Fernet(key.encode() if isinstance(key, str) else key)
        return _cached_fernet
    except Exception as e:
        logger.error(f"APP_ENCRYPTION_KEY 无效: {e}")
        return None


# 加密标记前缀 — 区分密文和明文（向后兼容）
ENC_PREFIX = "enc:v1:"


def encrypt_field(plaintext: str) -> str:
    """
    加密字段。
    - 输入为空: 返回空
    - 已是密文（以 ENC_PREFIX 开头）: 直接返回
    - Fernet 未配置: 返回原文（开发模式）
    - 否则: 加密并返回 enc:v1:<token>
    """
    if not plaintext:
        return plaintext
    if plaintext.startswith(ENC_PREFIX):
        return plaintext

    f = _get_fernet()
    if f is None:
        return plaintext  # 未配置加密密钥，明文存储（仅开发模式）

    token = f.encrypt(plaintext.encode("utf-8")).decode("ascii")
    return f"{ENC_PREFIX}{token}"


def decrypt_field(value: str) -> str:
    """
    解密字段。
    - 输入为空 / 不带前缀: 当作明文返回
    - 带前缀: 用 Fernet 解密
    - 解密失败: 返回原值（避免崩溃，但记录错误）
    """
    if not value:
        return value
    if not value.startswith(ENC_PREFIX):
        return value  # 旧明文兼容

    f = _get_fernet()
    if f is None:
        logger.error("DB 中存在密文但未配置 APP_ENCRYPTION_KEY")
        return value

    token = value[len(ENC_PREFIX):]
    try:
        return f.decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        logger.error("Fernet 解密失败，密钥可能已变更")
        return value
    except Exception as e:
        logger.error(f"解密异常: {e}")
        return value


def is_encryption_enabled() -> bool:
    """是否已配置加密密钥"""
    return _get_fernet() is not None
