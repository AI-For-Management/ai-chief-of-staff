"""情报简报Celery定时任务"""
import logging
import asyncio

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.intel_tasks.generate_daily_briefing")
def generate_daily_briefing(topics: list[str] = None, chat_id: str = ""):
    """
    生成每日情报简报（Celery任务）

    Args:
        topics: 搜索话题列表
        chat_id: 飞书群ID
    """
    if topics is None:
        topics = ["AI行业动态", "半导体产业", "科技公司"]

    logger.info(f"开始生成每日情报简报: topics={topics}")

    try:
        result = asyncio.run(_run_briefing(topics, chat_id))
        logger.info(f"情报简报生成完成: sent={result.get('sent', False)}")
        return result
    except Exception as e:
        logger.error(f"情报简报生成失败: {e}")
        return {"error": str(e)}


async def _run_briefing(topics: list[str], chat_id: str) -> dict:
    """运行情报简报图"""
    import uuid
    from app.agents.briefing_graph import build_briefing_graph

    graph = await build_briefing_graph()
    thread_id = f"briefing-{uuid.uuid4().hex[:8]}"

    config = {"configurable": {"thread_id": thread_id}}
    input_state = {
        "topics": topics,
        "raw_news": [],
        "briefing_content": "",
        "chat_id": chat_id,
        "sent": False,
    }

    result = await graph.ainvoke(input_state, config=config)
    return {
        "briefing_content": result.get("briefing_content", ""),
        "sent": result.get("sent", False),
        "thread_id": thread_id,
    }
