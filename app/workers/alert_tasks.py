"""风险预警Celery定时任务"""
import logging
import asyncio
import uuid

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.alert_tasks.scan_risks")
def scan_risks(chat_id: str = ""):
    """扫描项目风险并推送预警"""
    logger.info("开始风险扫描任务")
    try:
        result = asyncio.run(_run_alert(chat_id))
        logger.info(f"风险扫描完成: risk_level={result.get('risk_level')}")
        return result
    except Exception as e:
        logger.error(f"风险扫描失败: {e}")
        return {"error": str(e)}


async def _run_alert(chat_id: str) -> dict:
    """运行预警图"""
    from app.agents.alert_graph import build_alert_graph

    graph = await build_alert_graph()
    thread_id = f"alert-{uuid.uuid4().hex[:8]}"

    config = {"configurable": {"thread_id": thread_id}}
    input_state = {
        "overdue_items": [],
        "risk_keywords_found": [],
        "risk_level": "low",
        "report_content": "",
        "chat_id": chat_id,
        "sent": False,
    }

    result = await graph.ainvoke(input_state, config=config)
    return {
        "risk_level": result.get("risk_level", "low"),
        "report_content": result.get("report_content", ""),
        "sent": result.get("sent", False),
        "thread_id": thread_id,
    }
