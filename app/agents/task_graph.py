"""项目管理Agent — 多轮对话式规划
流程: retrieve_context → draft_plan → [HITL讨论] → revise_plan → [HITL确认] → execute_dispatch
"""
import json
import logging
import uuid

from langgraph.graph import StateGraph, START, END

from app.agents.state import TaskState
from app.agents import get_checkpointer_async

logger = logging.getLogger(__name__)


async def retrieve_context(state: TaskState) -> dict:
    """从知识库检索与CEO指令相关的文档和历史简报"""
    user_input = state["user_input"]
    rag_context = ""

    try:
        from app.services.rag import search
        results = await search(user_input, top_k=5)

        if results:
            rag_context = "以下是从公司知识库中检索到的相关资料:\n\n"
            for i, r in enumerate(results, 1):
                rag_context += f"**{i}. {r['title']}** (v{r['version']})\n"
                rag_context += f"{r['content']}\n\n"

            logger.info(f"RAG检索到 {len(results)} 条相关文档")
        else:
            logger.info("知识库中未找到相关文档")
    except Exception as e:
        logger.warning(f"RAG检索失败: {e}")

    return {"rag_context": rag_context}


async def draft_plan(state: TaskState) -> dict:
    """结合知识库和对话历史，生成任务规划方案"""
    from app.services.llm import chat

    user_input = state["user_input"]
    rag_context = state.get("rag_context", "")
    history = state.get("conversation_history", [])

    # 构建LLM消息
    system = """你是CEO的首席参谋（Chief of Staff）。你的职责是将CEO的战略意图拆解为可执行的具体方案。

要求：
1. 结合公司内部资料和最新情报进行分析
2. 输出包含：项目背景分析、任务分解表、里程碑时间线、资源需求、风险提示
3. 任务分解表格式：编号 | 任务名称 | 负责人/角色 | 截止日期 | 优先级 | 前置依赖
4. 使用Markdown格式，专业、清晰、可执行
5. 截止日期用具体日期（如2026-06-15），不要用"3天后"这种模糊表达"""

    messages = [{"role": "system", "content": system}]

    # 注入知识库上下文
    if rag_context:
        messages.append({"role": "system", "content": f"【公司内部资料与最新情报】\n{rag_context}"})

    # 加入对话历史
    for msg in history:
        messages.append(msg)

    messages.append({"role": "user", "content": f"请为以下CEO指令制定详细执行方案:\n\n{user_input}"})

    plan = await chat(messages, use_strong=True, max_tokens=4096)

    # 同时尝试提取结构化任务
    tasks = await _extract_structured_tasks(plan)

    new_history = history + [
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": plan},
    ]

    return {
        "plan_draft": plan,
        "decomposed_tasks": tasks,
        "conversation_history": new_history,
        "result": plan,
        "approval_status": "pending",
    }


async def revise_plan(state: TaskState) -> dict:
    """根据CEO反馈修订方案"""
    from app.services.llm import chat

    history = state.get("conversation_history", [])
    rag_context = state.get("rag_context", "")

    system = """你是CEO的首席参谋。CEO对你之前的方案提出了修改意见。
请根据反馈修订方案，保持相同的输出格式（项目背景、任务分解表、时间线、风险）。
只修改CEO要求修改的部分，其余保持不变。"""

    messages = [{"role": "system", "content": system}]
    if rag_context:
        messages.append({"role": "system", "content": f"【公司内部资料】\n{rag_context[:3000]}"})

    for msg in history:
        messages.append(msg)

    plan = await chat(messages, use_strong=True, max_tokens=4096)
    tasks = await _extract_structured_tasks(plan)

    return {
        "plan_draft": plan,
        "decomposed_tasks": tasks,
        "result": plan,
    }


async def execute_dispatch(state: TaskState) -> dict:
    """审批通过后执行派发"""
    approval = state.get("approval_status", "")

    if approval == "rejected":
        return {"result": "CEO已拒绝此方案。"}

    tasks = state.get("decomposed_tasks", [])
    created_ids = []

    # 写入多维表格
    app_token = state.get("bitable_app_token", "")
    table_id = state.get("bitable_table_id", "")

    if app_token and table_id:
        try:
            from app.services.feishu.bitable import create_records
            records = [
                {
                    "任务名称": t.get("name", ""),
                    "负责人": t.get("assignee", ""),
                    "截止日期": t.get("deadline", ""),
                    "优先级": t.get("priority", "medium"),
                    "状态": "待开始",
                }
                for t in tasks
            ]
            await create_records(app_token, table_id, records)
            logger.info(f"已写入Bitable: {len(records)}条")
        except Exception as e:
            logger.error(f"写入Bitable失败: {e}")

    # 创建飞书任务
    try:
        from app.services.feishu.tasks import create_task
        for t in tasks:
            result = await create_task(
                summary=t.get("name", "未命名任务"),
                description=f"优先级: {t.get('priority', '-')}\n负责人: {t.get('assignee', '待分配')}",
            )
            task_id = result.get("task", {}).get("id", "")
            if task_id:
                created_ids.append(task_id)
    except Exception as e:
        logger.error(f"创建飞书任务失败: {e}")

    return {
        "created_task_ids": created_ids,
        "approval_status": "approved",
        "result": f"已派发 {len(tasks)} 个任务。飞书任务: {len(created_ids)}个已创建。",
    }


async def _extract_structured_tasks(plan_text: str) -> list[dict]:
    """从方案文本中提取结构化任务列表"""
    from app.services.llm import chat_json

    prompt = f"""从以下方案中提取任务列表，返回JSON数组。

方案:
{plan_text[:3000]}

返回格式:
[{{"name":"任务名","assignee":"负责人","deadline":"YYYY-MM-DD","priority":"high/medium/low","dependencies":[]}}]

如果无法提取，返回空数组 []"""

    try:
        tasks = await chat_json(prompt, use_strong=False)
        if isinstance(tasks, dict) and "tasks" in tasks:
            tasks = tasks["tasks"]
        if isinstance(tasks, list):
            return tasks
    except Exception:
        pass
    return []


async def build_task_graph():
    """构建项目管理图（含HITL中断）"""
    graph = StateGraph(TaskState)

    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("draft_plan", draft_plan)
    graph.add_node("execute_dispatch", execute_dispatch)

    graph.add_edge(START, "retrieve_context")
    graph.add_edge("retrieve_context", "draft_plan")
    graph.add_edge("draft_plan", "execute_dispatch")
    graph.add_edge("execute_dispatch", END)

    checkpointer = await get_checkpointer_async()
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["execute_dispatch"],
    )


async def run_task_decomposition(
    user_input: str,
    bitable_app_token: str = "",
    bitable_table_id: str = "",
    chat_id: str = "",
) -> dict:
    """启动任务拆解流程"""
    graph = await build_task_graph()
    thread_id = f"task-{uuid.uuid4().hex[:8]}"

    config = {"configurable": {"thread_id": thread_id}}
    input_state = {
        "user_input": user_input,
        "conversation_history": [],
        "rag_context": "",
        "decomposed_tasks": [],
        "plan_draft": "",
        "bitable_app_token": bitable_app_token,
        "bitable_table_id": bitable_table_id,
        "chat_id": chat_id,
        "approval_status": "pending",
        "created_task_ids": [],
        "result": "",
    }

    result = await graph.ainvoke(input_state, config=config)

    return {
        "thread_id": thread_id,
        "status": "waiting_approval",
        "tasks": result.get("decomposed_tasks", []),
        "message": result.get("result", ""),
    }


async def revise_task_plan(thread_id: str, feedback: str) -> dict:
    """CEO反馈后修订方案"""
    from app.services.llm import chat

    # 加载当前checkpoint状态
    checkpointer = await get_checkpointer_async()

    # 直接用LLM修订（不重走图，因为图已在HITL中断）
    # 从session中获取历史
    graph = await build_task_graph()
    config = {"configurable": {"thread_id": thread_id}}

    # 获取当前状态
    state = await graph.aget_state(config)
    current = state.values if state else {}

    history = current.get("conversation_history", [])
    rag_context = current.get("rag_context", "")

    # 添加CEO反馈到历史
    history.append({"role": "user", "content": feedback})

    system = """你是CEO的首席参谋。CEO对之前的方案提出了修改意见。
请根据反馈修订方案，保持格式：项目背景、任务分解表、时间线、风险。"""

    messages = [{"role": "system", "content": system}]
    if rag_context:
        messages.append({"role": "system", "content": f"【内部资料】\n{rag_context[:2000]}"})
    for msg in history:
        messages.append(msg)

    revised = await chat(messages, use_strong=True, max_tokens=4096)

    history.append({"role": "assistant", "content": revised})
    tasks = await _extract_structured_tasks(revised)

    # 更新checkpoint状态
    await graph.aupdate_state(config, {
        "conversation_history": history,
        "plan_draft": revised,
        "decomposed_tasks": tasks,
        "result": revised,
    })

    return {
        "thread_id": thread_id,
        "status": "waiting_approval",
        "tasks": tasks,
        "message": revised,
    }


async def resume_task_dispatch(thread_id: str, approved: bool) -> dict:
    """CEO审批后恢复执行"""
    graph = await build_task_graph()
    config = {"configurable": {"thread_id": thread_id}}

    if not approved:
        return {"thread_id": thread_id, "status": "rejected", "result": "CEO已拒绝此方案。"}

    # 更新审批状态并恢复图执行
    await graph.aupdate_state(config, {"approval_status": "approved"})
    result = await graph.ainvoke(None, config=config)

    return {
        "thread_id": thread_id,
        "status": "completed",
        "result": result.get("result", ""),
        "created_task_ids": result.get("created_task_ids", []),
    }
