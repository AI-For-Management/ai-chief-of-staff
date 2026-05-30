"""健康检查端点 — 三档：/health /health/live /health/ready"""
from fastapi import APIRouter, Response, status
from sqlalchemy import text
from redis.asyncio import Redis

from app.database import async_session
from app.config import get_settings

router = APIRouter()


@router.get("/health")
async def health_check(response: Response):
    """整体健康检查 — 任一依赖故障返回 503"""
    settings = get_settings()
    result = {"db": "error", "redis": "error"}

    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        result["db"] = "ok"
    except Exception as e:
        result["db"] = str(e)[:100]

    try:
        r = Redis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        result["redis"] = "ok"
    except Exception as e:
        result["redis"] = str(e)[:100]

    if result["db"] != "ok" or result["redis"] != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result


@router.get("/health/live")
async def liveness():
    """Liveness — 进程是否在跑（始终返回 200，进程死了就连不上）"""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness(response: Response):
    """Readiness — 是否可以承接流量（依赖全部就绪才返回 200）"""
    settings = get_settings()
    checks = {}

    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = str(e)[:100]

    try:
        r = Redis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = str(e)[:100]

    if any(v != "ok" for v in checks.values()):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"ready": False, "checks": checks}
    return {"ready": True, "checks": checks}
