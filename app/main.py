"""FastAPI应用入口"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.api.health import router as health_router
from app.api.webhook import router as webhook_router
from app.api.admin import router as admin_router
from app.api.agents import router as agents_router
from app.api.hr import router as hr_router
from app.api.projects import router as projects_router

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)


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

app.include_router(health_router)
app.include_router(webhook_router)
app.include_router(admin_router)
app.include_router(agents_router)
app.include_router(hr_router)
app.include_router(projects_router)
