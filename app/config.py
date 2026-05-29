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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
