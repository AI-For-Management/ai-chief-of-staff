"""员工对话 Agent — CEO 与具体员工的智能对话工具"""
import logging
from typing import TypedDict, Annotated
import operator

from langgraph.graph import StateGraph, START, END

from app.agents import get_checkpointer_async

logger = logging.getLogger(__name__)


class EmpChatState(TypedDict):
    employee_id: str
    employee_name: str
    user_message: str
    employee_context: str  # 员工的所有相关信息
    conversation_history: Annotated[list, operator.add]
    reply: str


async def load_context(state: EmpChatState) -> dict:
    """加载员工 profile + 最近指标 + 当前项目"""
    from sqlalchemy import select, desc
    from app.database import async_session
    from app.models import Employee, EmployeeMetrics, ProjectMember, Project
    import uuid

    emp_id = uuid.UUID(state["employee_id"])
    ctx_parts = []

    async with async_session() as session:
        emp = await session.get(Employee, emp_id)
        if not emp:
            return {"employee_context": "员工不存在", "employee_name": "未知"}

        ctx_parts.append(f"姓名: {emp.name}")
        ctx_parts.append(f"部门: {emp.department}")
        ctx_parts.append(f"职位: {emp.position}")

        if emp.skills:
            ctx_parts.append(f"技能标签: {', '.join(emp.skills.keys())}")

        # profile_data
        if emp.profile_data and isinstance(emp.profile_data, dict):
            p = emp.profile_data
            if p.get("summary"):
                ctx_parts.append(f"画像: {p['summary']}")
            if p.get("strengths"):
                ctx_parts.append(f"优势: {', '.join(p['strengths'])}")
            if p.get("weaknesses"):
                ctx_parts.append(f"待提升: {', '.join(p['weaknesses'])}")

        # 最近月度指标
        result = await session.execute(
            select(EmployeeMetrics)
            .where(EmployeeMetrics.employee_id == emp_id, EmployeeMetrics.period_type == "monthly")
            .order_by(desc(EmployeeMetrics.period_date))
            .limit(1)
        )
        m = result.scalar_one_or_none()
        if m:
            ctx_parts.append(
                f"近月指标: 贡献分 {m.contribution_score:.1f}, "
                f"完成率 {m.completion_rate*100:.0f}%, 负荷 {m.workload_score:.0f}"
            )

        # 当前项目
        result = await session.execute(
            select(ProjectMember, Project)
            .join(Project, Project.id == ProjectMember.project_id)
            .where(ProjectMember.employee_id == emp_id, Project.status == "in_progress")
        )
        active_projects = []
        for member, proj in result.all():
            active_projects.append(f"{proj.name} ({member.role})")
        if active_projects:
            ctx_parts.append(f"在进项目: {'; '.join(active_projects)}")

    return {
        "employee_name": emp.name,
        "employee_context": "\n".join(ctx_parts),
    }


async def respond(state: EmpChatState) -> dict:
    """LLM 基于员工上下文 + 历史对话回答"""
    from app.services.llm import chat

    system = f"""你是CEO的员工分析助手。CEO询问关于员工 {state['employee_name']} 的问题，请基于以下上下文回答。

【员工档案】
{state['employee_context']}

回答要求:
1. 客观、有数据支撑
2. 如建议派任务，结合该员工的优势/负荷给出理由
3. 对涉及隐私的问题保持中立和建设性
4. 简洁，3-5句话即可
"""

    messages = [{"role": "system", "content": system}]
    for msg in state.get("conversation_history", []):
        messages.append(msg)
    messages.append({"role": "user", "content": state["user_message"]})

    reply = await chat(messages, use_strong=True, max_tokens=1024)

    new_history = [
        {"role": "user", "content": state["user_message"]},
        {"role": "assistant", "content": reply},
    ]
    return {"reply": reply, "conversation_history": new_history}


async def build_employee_chat_graph():
    graph = StateGraph(EmpChatState)
    graph.add_node("load_context", load_context)
    graph.add_node("respond", respond)
    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "respond")
    graph.add_edge("respond", END)
    cp = await get_checkpointer_async()
    return graph.compile(checkpointer=cp)


async def chat_about_employee(employee_id: str, message: str, thread_id: str = "") -> dict:
    """对外接口"""
    import uuid
    if not thread_id:
        thread_id = f"emp-chat-{employee_id[:8]}-{uuid.uuid4().hex[:6]}"
    graph = await build_employee_chat_graph()
    config = {"configurable": {"thread_id": thread_id}}
    state = {
        "employee_id": employee_id, "employee_name": "",
        "user_message": message, "employee_context": "",
        "conversation_history": [], "reply": "",
    }
    result = await graph.ainvoke(state, config=config)
    return {
        "thread_id": thread_id,
        "employee_name": result.get("employee_name", ""),
        "reply": result.get("reply", ""),
    }
