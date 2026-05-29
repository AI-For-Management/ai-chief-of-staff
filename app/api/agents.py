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
    """手动触发情报简报生成（走 LangGraph，包含日期注入、公司上下文、自动入库）"""
    import uuid
    from app.agents.briefing_graph import build_briefing_graph

    graph = await build_briefing_graph()
    thread_id = f"briefing-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}
    input_state = {
        "topics": req.topics,
        "raw_news": [],
        "briefing_content": "",
        "chat_id": req.send_to_chat_id,
        "sent": False,
    }

    result = await graph.ainvoke(input_state, config=config)

    return BriefingResponse(
        content=result.get("briefing_content", ""),
        topic_count=len(req.topics),
        sent=result.get("sent", False),
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


class RAGAnswerRequest(BaseModel):
    query: str
    top_k: int = 8
    threshold: float = 0.4


@router.post("/rag/answer")
async def rag_answer(req: RAGAnswerRequest):
    """RAG综合回答 — KB管理员基于知识库相关文档生成回答"""
    from app.agents.kb_manager_graph import answer_question
    result = await answer_question(req.query, top_k=req.top_k, threshold=req.threshold)
    return result


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


@router.post("/kb/manage")
async def trigger_kb_manage():
    """触发知识库管理员（去重+分类）"""
    from app.agents.kb_manager_graph import run_kb_manager
    result = await run_kb_manager()
    return result


class EmployeeChatRequest(BaseModel):
    employee_id: str
    message: str
    thread_id: str = ""


@router.post("/employees/chat")
async def employee_chat(req: EmployeeChatRequest):
    """与AI讨论某位员工"""
    from app.agents.employee_chat_graph import chat_about_employee
    result = await chat_about_employee(req.employee_id, req.message, req.thread_id)
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
