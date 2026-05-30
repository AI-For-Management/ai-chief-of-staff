"""FastAPI应用入口"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.observability.logging import setup_json_logging
from app.observability.middleware import RequestLoggingMiddleware
from app.api.health import router as health_router
from app.api.version import router as version_router
from app.api.webhook import router as webhook_router, limiter as webhook_limiter
from app.api.admin import router as admin_router
from app.api.agents import router as agents_router
from app.api.hr import router as hr_router
from app.api.projects import router as projects_router
from app.api.knowledge import router as knowledge_router

settings = get_settings()

# 结构化 JSON 日志（替代默认 basicConfig）
setup_json_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Sentry 错误追踪（DSN 为空则跳过）
if settings.SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.APP_ENV,
            integrations=[StarletteIntegration(), FastApiIntegration()],
            traces_sample_rate=0.1,
            send_default_pii=False,
        )
        logger.info("Sentry 已初始化")
    except Exception as e:
        logger.warning(f"Sentry 初始化失败（已跳过）: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AI Chief of Staff starting up...")
    yield
    logger.info("AI Chief of Staff shutting down...")


app = FastAPI(
    title="AI Chief of Staff",
    description="企业级AI秘书 — 飞书集成、情报分析、任务派发、风险预警",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)

# slowapi 速率限制（webhook 防风暴）
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
app.state.limiter = webhook_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(health_router)
app.include_router(version_router)
app.include_router(webhook_router)
app.include_router(admin_router)
app.include_router(agents_router)
app.include_router(hr_router)
app.include_router(projects_router)
app.include_router(knowledge_router)
