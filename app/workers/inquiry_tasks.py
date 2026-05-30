"""员工询问 Celery 任务（每周二/周五 9:00 自动）"""
import logging
import asyncio

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.inquiry_tasks.run_employee_inquiry")
def run_employee_inquiry():
    """每周二/周五早9点触发：向所有 in_progress 项目的成员发飞书私聊询问"""
    logger.info("开始员工询问任务")
    try:
        from app.agents.employee_inquiry_graph import run_inquiry
        result = asyncio.run(run_inquiry())
        logger.info(f"员工询问完成: {result}")
        return result
    except Exception as e:
        logger.error(f"员工询问失败: {e}")
        return {"error": str(e)}
