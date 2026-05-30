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


async def _load_employee_names_str() -> str:
    """返回所有在职员工姓名+部门的逗号分隔字符串（用于规划Agent prompt）"""
    from sqlalchemy import select
    from app.database import async_session
    from app.models import Employee

    try:
        async with async_session() as session:
            r = await session.execute(
                select(Employee).where(Employee.is_active == True)
            )
            emps = r.scalars().all()
        if not emps:
            return "（员工库为空）"
        return "、".join(f"{e.name}（{e.department or '未填部门'}）" for e in emps)
    except Exception:
        return "（员工列表加载失败）"


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
    """结合知识库和对话历史，生成任务规划方案（合并两次LLM调用为一次）"""
    from app.services.llm import chat
    from app.agents.prompts import planner_prompt

    user_input = state["user_input"]
    rag_context = state.get("rag_context", "")
    history = state.get("conversation_history", [])

    # 加载员工列表用于注入 prompt
    employee_list = await _load_employee_names_str()
    system = planner_prompt(employee_list=employee_list)

    messages = [{"role": "system", "content": system}]

    if rag_context:
        messages.append({"role": "system", "content": f"【公司内部资料与最新情报】\n{rag_context}"})

    for msg in history:
        messages.append(msg)

    messages.append({"role": "user", "content": f"请为以下CEO指令制定详细执行方案:\n\n{user_input}"})

    raw = await chat(messages, use_strong=True, max_tokens=4096)

    # 切分 markdown + JSON
    plan, tasks = _split_plan_and_tasks(raw)

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
    """根据CEO反馈修订方案（同样合并2次LLM为1次）"""
    from app.services.llm import chat
    from app.agents.prompts import planner_revise_prompt

    history = state.get("conversation_history", [])
    rag_context = state.get("rag_context", "")

    employee_list = await _load_employee_names_str()
    system = planner_revise_prompt(employee_list=employee_list)

    messages = [{"role": "system", "content": system}]
    if rag_context:
        messages.append({"role": "system", "content": f"【公司内部资料】\n{rag_context[:3000]}"})

    for msg in history:
        messages.append(msg)

    raw = await chat(messages, use_strong=True, max_tokens=4096)
    plan, tasks = _split_plan_and_tasks(raw)

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

    # 写入多维表格 — 如未配置，自动创建一个新Bitable
    app_token = state.get("bitable_app_token", "")
    table_id = state.get("bitable_table_id", "")

    if not (app_token and table_id):
        try:
            from app.services.feishu.bitable import create_app_with_default_table
            from sqlalchemy import select
            from app.database import async_session
            from app.models import LarkAsset, LarkConfig
            from datetime import datetime

            bitable_name = f"AI规划任务表-{datetime.now().strftime('%Y%m%d-%H%M')}"
            app_token, table_id = await create_app_with_default_table(bitable_name)
            logger.info(f"自动创建Bitable: {bitable_name} → app={app_token[:12]}.. table={table_id[:12]}..")

            # 写回 LarkAsset 表（关联到第一个活跃 lark_config）
            async with async_session() as session:
                cfg_r = await session.execute(
                    select(LarkConfig).where(LarkConfig.is_active == True).limit(1)
                )
                cfg = cfg_r.scalar_one_or_none()
                if cfg:
                    new_asset = LarkAsset(
                        config_id=cfg.id,
                        asset_type="bitable",
                        asset_token=app_token,
                        asset_name=bitable_name,
                        table_id=table_id,
                        cron_expression="0 */6 * * *",
                    )
                    session.add(new_asset)
                    await session.commit()
                    logger.info(f"LarkAsset 已写入：{bitable_name}")
        except Exception as e:
            logger.error(f"自动创建Bitable失败，跳过表写入: {e}")
            app_token = ""
            table_id = ""

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

    # 创建飞书任务（带定点派发）
    # 1. 先建立姓名 → 飞书 open_id 的映射表
    name_to_openid = {}
    name_to_dept = {}
    try:
        from sqlalchemy import select
        from app.database import async_session
        from app.models import Employee
        async with async_session() as session:
            r = await session.execute(select(Employee).where(Employee.is_active == True))
            for emp in r.scalars().all():
                if emp.feishu_open_id:
                    name_to_openid[emp.name] = emp.feishu_open_id
                name_to_dept[emp.name] = emp.department
    except Exception as e:
        logger.warning(f"加载员工映射失败: {e}")

    # 2. 逐个创建+派发
    unassigned_count = 0
    try:
        from app.services.feishu.tasks import create_task
        for t in tasks:
            try:
                # 解析 assignee：可能是"陈思琪"、"陈思琪/产品经理" 等
                assignee_raw = t.get("assignee", "") or ""
                # 在映射表中查找姓名
                matched_name = None
                for emp_name in name_to_openid:
                    if emp_name in assignee_raw:
                        matched_name = emp_name
                        break

                assignee_ids = []
                if matched_name:
                    assignee_ids = [name_to_openid[matched_name]]
                else:
                    unassigned_count += 1
                    logger.info(f"任务 [{t.get('name','?')}] 无法匹配员工 '{assignee_raw}' 到 open_id，未派发")

                result = await create_task(
                    summary=t.get("name", "未命名任务"),
                    description=(
                        f"优先级: {t.get('priority', '-')}\n"
                        f"负责人: {assignee_raw or '待分配'}\n"
                        f"截止: {t.get('deadline', '-')}\n"
                        f"前置依赖: {', '.join(t.get('dependencies', [])) or '无'}"
                    ),
                    assignee_ids=assignee_ids,
                )
                task_obj = result.get("task", {}) if isinstance(result, dict) else {}
                tid = task_obj.get("guid") or task_obj.get("task_id") or task_obj.get("id", "")
                if tid:
                    created_ids.append(tid)
                    logger.info(
                        f"飞书任务已创建: {t.get('name','?')} -> {tid[:12]} "
                        f"(派发给: {matched_name or '未派发'})"
                    )
                else:
                    logger.warning(f"飞书任务返回无guid/task_id: name={t.get('name')}, result={result}")
            except Exception as inner:
                logger.error(f"创建单个任务失败 [{t.get('name','?')}]: {inner}")
    except Exception as e:
        logger.error(f"创建飞书任务失败: {e}")

    assigned_count = len(created_ids) - unassigned_count
    msg = f"已派发 {len(tasks)} 个任务。飞书任务: {len(created_ids)} 个已创建（{assigned_count} 个已指派给具体员工，{unassigned_count} 个未派发）。"
    if unassigned_count > 0:
        msg += "\n\n⚠️ 未派发的任务说明AI拆解的负责人无法在员工库中匹配，或员工没有飞书 Open ID。请到「人事管理」补全员工的 Feishu Open ID。"

    return {
        "created_task_ids": created_ids,
        "approval_status": "approved",
        "result": msg,
    }


async def detect_and_create_projects(state: TaskState) -> dict:
    """从规划方案中识别并自动创建项目（C阶段新节点）。

    用LLM从 plan_draft 提取项目信息，做防护后写入 projects 表。
    """
    from datetime import datetime, timedelta
    from sqlalchemy import select, func as sqlfunc
    from app.database import async_session
    from app.models import Employee, Project, ProjectMember
    from app.services.llm import chat_json

    plan = state.get("plan_draft", "") or state.get("result", "")
    if not plan or len(plan) < 50:
        return {"created_project_ids": []}

    prompt = f"""从下面的规划方案中识别需要创建的项目。

规划方案:
{plan[:4000]}

返回JSON数组（最多5个项目）。如果方案描述的是单一目标，就只返回一个项目；如果包含多个独立工作流，可以返回多个。
[
  {{
    "name": "项目名称（简短，10字内）",
    "description": "1-2句项目目标",
    "owner_name": "项目负责人姓名（必须是方案中明确指定的人，否则留空）",
    "members": [{{"name": "成员姓名", "role": "角色"}}],
    "milestones": [{{"date": "YYYY-MM-DD", "title": "里程碑"}}]
  }}
]

要求：
1. 只识别明确表示"启动新工作"的部分。如果规划只是给现有项目分任务，返回空数组 []
2. owner_name 必须是方案中明确点名的人（不要编造）
3. 至少要有 name 和 description
4. 如果不确定，宁可少识别"""

    try:
        proposals = await chat_json(prompt, use_strong=True)
        if isinstance(proposals, dict):
            proposals = proposals.get("projects") or proposals.get("items") or []
        if not isinstance(proposals, list):
            proposals = []
    except Exception as e:
        logger.warning(f"项目提取失败: {e}")
        return {"created_project_ids": []}

    if not proposals:
        return {"created_project_ids": []}

    proposals = proposals[:5]  # 单次最多5个

    # 加载员工映射
    name_to_emp = {}
    async with async_session() as session:
        r = await session.execute(select(Employee).where(Employee.is_active == True))
        for emp in r.scalars().all():
            name_to_emp[emp.name] = emp.id

        # 30天内已存在同名项目的列表（去重保护）
        cutoff = datetime.now() - timedelta(days=30)
        existing_q = await session.execute(
            select(Project.name).where(Project.created_at >= cutoff)
        )
        recent_names = {row[0] for row in existing_q.all()}

        created_ids = []
        for p in proposals:
            name = (p.get("name") or "").strip()
            description = (p.get("description") or "").strip()
            owner_name = (p.get("owner_name") or "").strip()

            if not name or not description:
                logger.info(f"项目缺name/description跳过: {p}")
                continue

            if name in recent_names:
                logger.info(f"30天内已有同名项目跳过: {name}")
                continue

            owner_id = None
            if owner_name and owner_name in name_to_emp:
                owner_id = name_to_emp[owner_name]
            elif owner_name:
                logger.info(f"项目owner '{owner_name}' 在员工库中找不到，置空")

            # 创建项目
            proj = Project(
                name=name,
                description=description,
                owner_id=owner_id,
                status="planning",
                milestones=p.get("milestones") or [],
                timeline_events=[
                    {
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "event": f"[规划Agent自动创建] {plan[:800]}",
                        "author": "规划Agent",
                    }
                ],
            )
            session.add(proj)
            await session.flush()  # 拿到proj.id

            # 加成员
            for m in (p.get("members") or []):
                m_name = (m.get("name") or "").strip()
                m_role = (m.get("role") or "").strip()
                if m_name in name_to_emp:
                    session.add(
                        ProjectMember(
                            project_id=proj.id,
                            employee_id=name_to_emp[m_name],
                            role=m_role,
                            responsibilities="",
                        )
                    )

            created_ids.append(str(proj.id))
            logger.info(f"自动创建项目: {name} (owner={owner_name or '空'}) → {proj.id}")

        if created_ids:
            await session.commit()

    # 把创建结果追加到result
    if created_ids:
        suffix = f"\n\n📋 已自动创建 {len(created_ids)} 个项目，请到「项目进程」页查看。"
    else:
        suffix = ""

    return {
        "created_project_ids": created_ids,
        "result": (state.get("result", "") + suffix),
    }


def _split_plan_and_tasks(raw: str) -> tuple[str, list[dict]]:
    """
    切分 LLM 一次性输出的 markdown方案 + JSON任务清单。

    分隔符: ===TASKS_JSON===
    返回: (plan_markdown, tasks_list)

    若分隔符缺失或JSON解析失败，仍返回完整原文+空任务列表（避免崩溃）。
    """
    import json
    import re

    if not raw:
        return "", []

    sep = "===TASKS_JSON==="
    if sep not in raw:
        return raw.strip(), []

    plan_part, json_part = raw.split(sep, 1)
    plan = plan_part.strip()

    # 清理 JSON 部分：去 markdown 代码块、找数组首尾
    js = json_part.strip()
    if js.startswith("```"):
        # 去掉首行 ```json 和末行 ```
        lines = js.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        js = "\n".join(lines)

    # 截取 [ 到最后一个 ]
    start = js.find("[")
    end = js.rfind("]")
    if start == -1 or end == -1:
        return plan, []

    js_arr = js[start : end + 1]

    try:
        tasks = json.loads(js_arr)
        if isinstance(tasks, list):
            return plan, tasks
    except Exception:
        pass

    return plan, []


async def _extract_structured_tasks(plan_text: str) -> list[dict]:
    """从方案文本中提取结构化任务列表（旧版兜底，已不在主路径用）"""
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
    graph.add_node("detect_and_create_projects", detect_and_create_projects)

    graph.add_edge(START, "retrieve_context")
    graph.add_edge("retrieve_context", "draft_plan")
    graph.add_edge("draft_plan", "execute_dispatch")
    graph.add_edge("execute_dispatch", "detect_and_create_projects")
    graph.add_edge("detect_and_create_projects", END)

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
        "created_project_ids": [],
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

    from app.agents.prompts import planner_revise_prompt
    employee_list = await _load_employee_names_str()
    system = planner_revise_prompt(employee_list=employee_list)

    messages = [{"role": "system", "content": system}]
    if rag_context:
        messages.append({"role": "system", "content": f"【内部资料】\n{rag_context[:2000]}"})
    for msg in history:
        messages.append(msg)

    raw = await chat(messages, use_strong=True, max_tokens=4096)
    revised, tasks = _split_plan_and_tasks(raw)

    history.append({"role": "assistant", "content": revised})

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
