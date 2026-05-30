"""应用配置 — 从.env加载所有环境变量"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://chief:chief_secret_2024@postgres:5432/chief_of_staff"
    DATABASE_URL_SYNC: str = "postgresql://chief:chief_secret_2024@postgres:5432/chief_of_staff"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # LLM
    SILICONFLOW_API_KEY: str = ""
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    LLM_MODEL_FAST: str = "deepseek-ai/DeepSeek-V3"
    LLM_MODEL_STRONG: str = "deepseek-ai/DeepSeek-V4-Pro"
    EMBEDDING_MODEL: str = "BAAI/bge-large-zh-v1.5"

    # Feishu
    FEISHU_APP_ID: str = ""
    FEISHU_APP_SECRET: str = ""
    FEISHU_ENCRYPT_KEY: str = ""
    FEISHU_VERIFICATION_TOKEN: str = ""

    # App
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # 安全（生产部署必填）
    APP_ENCRYPTION_KEY: str = ""  # Fernet 密钥（44字符base64），用于加密 DB 中敏感字段
    ADMIN_API_TOKEN: str = ""     # /api/admin/* 端点的 Bearer 令牌
    ADMIN_PASSWORD_HASH: str = "" # Streamlit admin 用户的 bcrypt 哈希（强制必填）

    # 可观测性（可选）
    SENTRY_DSN: str = ""          # 留空则不初始化

    # 认证用户列表（兼容旧版，新部署建议用 ADMIN_PASSWORD_HASH）
    AUTH_USERS: str = ""          # "user1:pass1,user2:pass2"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
