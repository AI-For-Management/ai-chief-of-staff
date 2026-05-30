"""员工对话 Agent — CEO 与具体员工的智能对话工具（支持跨员工对比）"""
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
    employee_context: str  # 主员工 + 提到的其他员工档案
    conversation_history: Annotated[list, operator.add]
    reply: str


async def _build_employee_brief(emp, session) -> str:
    """构建单个员工的简要档案文本"""
    from sqlalchemy import select, desc
    from app.models import EmployeeMetrics, ProjectMember, Project

    parts = []
    parts.append(f"姓名: {emp.name}")
    parts.append(f"部门: {emp.department}")
    parts.append(f"职位: {emp.position}")

    if emp.skills:
        parts.append(f"技能标签: {', '.join(emp.skills.keys())}")

    if emp.profile_data and isinstance(emp.profile_data, dict):
        p = emp.profile_data
        if p.get("summary"):
            parts.append(f"画像: {p['summary']}")
        if p.get("strengths"):
            parts.append(f"优势: {', '.join(p['strengths'])}")
        if p.get("weaknesses"):
            parts.append(f"待提升: {', '.join(p['weaknesses'])}")
        if p.get("preferred_roles"):
            parts.append(f"适合的角色: {', '.join(p['preferred_roles'])}")

    # 最近月度指标
    result = await session.execute(
        select(EmployeeMetrics)
        .where(EmployeeMetrics.employee_id == emp.id, EmployeeMetrics.period_type == "monthly")
        .order_by(desc(EmployeeMetrics.period_date))
        .limit(1)
    )
    m = result.scalar_one_or_none()
    if m:
        parts.append(
            f"近月指标: 贡献分 {m.contribution_score:.1f}, "
            f"完成率 {m.completion_rate*100:.0f}%, 负荷 {m.workload_score:.0f}"
        )

    # 当前项目
    result = await session.execute(
        select(ProjectMember, Project)
        .join(Project, Project.id == ProjectMember.project_id)
        .where(ProjectMember.employee_id == emp.id, Project.status == "in_progress")
    )
    active_projects = []
    for member, proj in result.all():
        active_projects.append(f"{proj.name} ({member.role})")
    if active_projects:
        parts.append(f"在进项目: {'; '.join(active_projects)}")

    return "\n".join(parts)


async def load_context(state: EmpChatState) -> dict:
    """加载主员工档案 + 自动检测用户消息中提到的其他员工"""
    from sqlalchemy import select
    from app.database import async_session
    from app.models import Employee
    import uuid

    main_emp_id = uuid.UUID(state["employee_id"])
    user_message = state.get("user_message", "")
    history = state.get("conversation_history", [])

    # 收集会话上下文中所有出现过的文本（用于匹配员工名）
    all_text = user_message
    for msg in history[-6:]:  # 最近3轮
        all_text += " " + msg.get("content", "")

    async with async_session() as session:
        # 主员工
        main_emp = await session.get(Employee, main_emp_id)
        if not main_emp:
            return {"employee_context": "员工不存在", "employee_name": "未知"}

        sections = []
        sections.append(f"=== 当前讨论的主员工 ===")
        sections.append(await _build_employee_brief(main_emp, session))

        # 检测其他员工：拉所有在职员工，看名字是否在文本里出现
        result = await session.execute(
            select(Employee).where(
                Employee.is_active == True,
                Employee.id != main_emp_id,
            )
        )
        other_emps = result.scalars().all()

        mentioned = [e for e in other_emps if e.name in all_text]
        if mentioned:
            sections.append(f"\n=== 用户提到的其他员工（共 {len(mentioned)} 人）===")
            for e in mentioned:
                sections.append(f"\n--- {e.name} ---")
                sections.append(await _build_employee_brief(e, session))

    return {
        "employee_name": main_emp.name,
        "employee_context": "\n".join(sections),
    }


async def respond(state: EmpChatState) -> dict:
    """LLM 基于员工上下文 + 历史对话回答"""
    from app.services.llm import chat
    from app.agents.prompts import employee_chat_prompt

    system = employee_chat_prompt(
        employee_name=state["employee_name"],
        employee_context=state["employee_context"],
    )

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
