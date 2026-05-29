"""LangGraph Agent全局初始化 — AsyncRedisSaver checkpoint"""
import os
import logging
import asyncio

from app.config import get_settings

logger = logging.getLogger(__name__)

# 缓存策略：每个事件循环各自缓存自己的 checkpointer
# 防止 Celery 反复 asyncio.run() 时跨 loop 复用导致 'attached to a different loop'
_checkpointer_per_loop: dict[int, object] = {}


async def get_checkpointer_async():
    """获取当前事件循环的 Redis checkpoint 存储"""
    loop_id = id(asyncio.get_event_loop())

    if loop_id in _checkpointer_per_loop:
        return _checkpointer_per_loop[loop_id]

    try:
        from langgraph.checkpoint.redis.aio import AsyncRedisSaver
        settings = get_settings()
        cm = AsyncRedisSaver.from_conn_string(settings.REDIS_URL)
        cp = await cm.__aenter__()
        logger.info(f"LangGraph AsyncRedisSaver 初始化 (loop={loop_id})")
    except Exception as e:
        logger.warning(f"AsyncRedisSaver初始化失败，使用内存checkpoint: {e}")
        from langgraph.checkpoint.memory import MemorySaver
        cp = MemorySaver()

    _checkpointer_per_loop[loop_id] = cp

    # 清理旧loop的checkpointer，避免内存泄漏
    if len(_checkpointer_per_loop) > 5:
        oldest_key = next(iter(_checkpointer_per_loop))
        if oldest_key != loop_id:
            _checkpointer_per_loop.pop(oldest_key, None)

    return cp
