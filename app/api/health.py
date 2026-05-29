"""健康检查端点"""
from fastapi import APIRouter
from sqlalchemy import text
from redis.asyncio import Redis

from app.database import async_session
from app.config import get_settings

router = APIRouter()


@router.get("/health")
async def health_check():
    settings = get_settings()
    result = {"db": "error", "redis": "error"}

    # Check PostgreSQL
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        result["db"] = "ok"
    except Exception as e:
        result["db"] = str(e)

    # Check Redis
    try:
        r = Redis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        result["redis"] = "ok"
    except Exception as e:
        result["redis"] = str(e)

    status_code = 200 if result["db"] == "ok" and result["redis"] == "ok" else 503
    return result
