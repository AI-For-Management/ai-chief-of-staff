"""LangGraph Agent全局初始化 — AsyncRedisSaver checkpoint"""
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)

_checkpointer = None


async def get_checkpointer_async():
    """获取全局异步Redis checkpoint存储（延迟初始化）"""
    global _checkpointer
    if _checkpointer is None:
        try:
            from langgraph.checkpoint.redis.aio import AsyncRedisSaver
            settings = get_settings()
            cm = AsyncRedisSaver.from_conn_string(settings.REDIS_URL)
            _checkpointer = await cm.__aenter__()
            logger.info("LangGraph AsyncRedisSaver checkpoint 初始化成功")
        except Exception as e:
            logger.warning(f"AsyncRedisSaver初始化失败，使用内存checkpoint: {e}")
            from langgraph.checkpoint.memory import MemorySaver
            _checkpointer = MemorySaver()
    return _checkpointer
