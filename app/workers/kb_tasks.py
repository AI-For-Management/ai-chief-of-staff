"""知识库管理 Celery 任务"""
import logging
import asyncio

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.kb_tasks.run_kb_manage")
def run_kb_manage():
    """每天凌晨触发，扫描重复+分类"""
    logger.info("开始知识库管理任务")
    try:
        from app.agents.kb_manager_graph import run_kb_manager
        result = asyncio.run(run_kb_manager())
        logger.info(f"知识库管理完成: {result}")
        return result
    except Exception as e:
        logger.error(f"知识库管理失败: {e}")
        return {"error": str(e)}
