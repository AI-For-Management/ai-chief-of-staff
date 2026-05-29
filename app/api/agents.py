"""Agent API — 手动触发Agent运行、审批操作"""
import logging

from fastapi import APIRouter
from pydantic import BaseModel

from app.schemas.intel import BriefingRequest, BriefingResponse
from app.schemas.task import TaskDecomposeRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("/briefing", response_model=BriefingResponse)
async def trigger_briefing(req: BriefingRequest):
    """手动触发情报简报生成"""
    from app.services.news import generate_briefing

    content = await generate_briefing(req.topics)

    sent = False
    if req.send_to_chat_id:
        try:
            from app.services.feishu.messages import send_interactive_card, build_report_card
            card = build_report_card(title="📊 CEO每日情报简报", content=content)
            await send_interactive_card(req.send_to_chat_id, card)
            sent = True
        except Exception as e:
            logger.error(f"发送简报失败: {e}")

    return BriefingResponse(
        content=content,
        topic_count=len(req.topics),
        sent=sent,
    )


@router.post("/briefing/async")
async def trigger_briefing_async(req: BriefingRequest):
    """异步触发情报简报（通过Celery后台执行）"""
    from app.workers.intel_tasks import generate_daily_briefing
    task = generate_daily_briefing.delay(req.topics, req.send_to_chat_id)
    return {"task_id": task.id, "status": "submitted"}


@router.post("/rag/search")
async def rag_search(query: str, top_k: int = 5):
    """RAG向量检索"""
    from app.services.rag import search
    results = await search(query, top_k=top_k)
    return {"query": query, "results": results, "count": len(results)}


@router.post("/knowledge/scan")
async def trigger_doc_scan():
    """手动触发文档扫描"""
    from app.workers.knowledge_tasks import scan_documents
    task = scan_documents.delay()
    return {"task_id": task.id, "status": "submitted"}


@router.post("/knowledge/reembed")
async def trigger_reembed(doc_token: str):
    """手动触发单文档re-embed"""
    from app.workers.knowledge_tasks import reembed_document
    task = reembed_document.delay(doc_token)
    return {"task_id": task.id, "status": "submitted"}


@router.post("/alerts/scan")
async def trigger_risk_scan(chat_id: str = ""):
    """手动触发风险扫描"""
    from app.workers.alert_tasks import scan_risks
    task = scan_risks.delay(chat_id)
    return {"task_id": task.id, "status": "submitted"}


@router.post("/tasks/decompose")
async def decompose_tasks(req: TaskDecomposeRequest):
    """CEO输入战略指令 → AI拆解任务 → 等待审批"""
    from app.agents.task_graph import run_task_decomposition
    result = await run_task_decomposition(
        user_input=req.user_input,
        bitable_app_token=req.bitable_app_token,
        bitable_table_id=req.bitable_table_id,
        chat_id=req.chat_id,
    )
    return result


class ReviseRequest(BaseModel):
    thread_id: str
    feedback: str


@router.post("/tasks/revise")
async def revise_plan(req: ReviseRequest):
    """CEO反馈修改意见，AI修订方案"""
    from app.agents.task_graph import revise_task_plan
    result = await revise_task_plan(req.thread_id, req.feedback)
    return result


@router.post("/approve")
async def approve_action(thread_id: str, action: str = "approve"):
    """
    审批Agent操作（HITL恢复）
    action: approve | reject
    """
    logger.info(f"审批操作: thread_id={thread_id}, action={action}")
    from app.agents.task_graph import resume_task_dispatch
    approved = action == "approve"
    result = await resume_task_dispatch(thread_id, approved)
    return result
