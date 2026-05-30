"""员工定期询问 Agent — 周二/周五 9:00 飞书私聊问员工项目进展"""
import logging
import secrets
from typing import TypedDict
from datetime import datetime

from langgraph.graph import StateGraph, START, END

from app.agents import get_checkpointer_async

logger = logging.getLogger(__name__)


class InquiryState(TypedDict):
    sent_count: int
    skipped_count: int
    pairs: list  # [{"employee_id","employee_name","open_id","project_id","project_name"}]


async def load_active_employees(state: InquiryState) -> dict:
    """加载所有 (员工, 在进项目) 对，要求员工有 feishu_open_id"""
    from sqlalchemy import select
    from app.database import async_session
    from app.models import Employee, Project, ProjectMember

    pairs = []
    async with async_session() as session:
        result = await session.execute(
            select(ProjectMember, Employee, Project)
            .join(Employee, Employee.id == ProjectMember.employee_id)
            .join(Project, Project.id == ProjectMember.project_id)
            .where(
                Project.status == "in_progress",
                Employee.is_active == True,
            )
        )
        for member, emp, proj in result.all():
            if not emp.feishu_open_id:
                continue
            pairs.append({
                "employee_id": str(emp.id),
                "employee_name": emp.name,
                "open_id": emp.feishu_open_id,
                "project_id": str(proj.id),
                "project_name": proj.name,
            })

    logger.info(f"询问对加载: {len(pairs)} 组 (员工×项目)")
    return {"pairs": pairs}


async def send_dm_questions(state: InquiryState) -> dict:
    """对每对发送飞书私聊问询，并写 inquiry_requests"""
    from sqlalchemy import select
    from app.database import async_session
    from app.models import InquiryRequest, Project
    from app.services.feishu.messages import send_text
    from app.services.llm import chat_simple
    from app.agents.prompts import inquiry_prompt

    pairs = state.get("pairs", [])
    sent_count = 0
    skipped_count = 0

    async with async_session() as session:
        for pair in pairs:
            try:
                # 生成短码
                token = "inq-" + secrets.token_hex(4)

                # 加载该项目最近的 timeline events（最多3条）
                proj = await session.get(Project, pair["project_id"])
                events = (proj.timeline_events or [])[-3:] if proj else []
                if events:
                    timeline_text = "\n".join(
                        f"- {e.get('time','')}: {e.get('event','')[:120]}（by {e.get('author','')}）"
                        for e in events
                    )
                else:
                    timeline_text = "（暂无最近时间轴记录）"

                # LLM 动态生成针对性问题（带短码前缀以便后续匹配）
                try:
                    body = await chat_simple(
                        f"请基于以上情境，生成针对该员工的私聊问询消息正文。",
                        system_prompt=inquiry_prompt(
                            employee_name=pair["employee_name"],
                            project_name=pair["project_name"],
                            recent_timeline_events=timeline_text,
                        ),
                        use_strong=False,
                    )
                    body = (body or "").strip()
                except Exception as e:
                    logger.warning(f"生成问询消息失败，回退模板: {e}")
                    body = (
                        f"你好 {pair['employee_name']}，"
                        f"想了解你在【{pair['project_name']}】项目上的最近进展，"
                        f"目前完成到哪一步？是否有阻碍？"
                    )

                # 强制加上短码前缀方便回复匹配
                question = f"[项目问询#{token}] {body}"

                resp = await send_text(
                    receive_id=pair["open_id"],
                    text=question,
                    receive_id_type="open_id",
                )
                msg_id = resp.get("message_id", "") if isinstance(resp, dict) else ""

                inquiry = InquiryRequest(
                    employee_id=pair["employee_id"],
                    project_id=pair["project_id"],
                    feishu_message_id=msg_id,
                    prefix_token=token,
                    question_text=question,
                    status="sent",
                )
                session.add(inquiry)
                sent_count += 1
                logger.info(f"询问已发送: {pair['employee_name']} × {pair['project_name']} → {token}")
            except Exception as e:
                logger.warning(f"发送询问失败 {pair.get('employee_name')}: {e}")
                skipped_count += 1

        if sent_count:
            await session.commit()

    return {"sent_count": sent_count, "skipped_count": skipped_count}


async def build_inquiry_graph():
    graph = StateGraph(InquiryState)
    graph.add_node("load_active_employees", load_active_employees)
    graph.add_node("send_dm_questions", send_dm_questions)
    graph.add_edge(START, "load_active_employees")
    graph.add_edge("load_active_employees", "send_dm_questions")
    graph.add_edge("send_dm_questions", END)
    cp = await get_checkpointer_async()
    return graph.compile(checkpointer=cp)


async def run_inquiry() -> dict:
    """对外接口"""
    import uuid
    graph = await build_inquiry_graph()
    thread_id = f"inquiry-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}
    state = {"sent_count": 0, "skipped_count": 0, "pairs": []}
    result = await graph.ainvoke(state, config=config)
    return {
        "sent_count": result.get("sent_count", 0),
        "skipped_count": result.get("skipped_count", 0),
        "thread_id": thread_id,
    }


# ===========================================================
# 员工回复处理（被 webhook 调用）
# ===========================================================

async def process_employee_reply(
    open_id: str, text: str, parent_message_id: str = ""
) -> dict:
    """
    处理员工回复：
    1. 通过 prefix_token 或 parent_message_id 找 inquiry_request
    2. LLM 提取 (progress, blockers)
    3. 写项目 timeline_events
    4. 标记 inquiry 为 replied
    """
    from sqlalchemy import select
    from app.database import async_session
    from app.models import InquiryRequest, Employee, Project
    from app.services.llm import chat_json
    from datetime import datetime
    import re

    # 提取短码
    match = re.search(r"inq-[a-f0-9]{8}", text)
    token = match.group(0) if match else ""

    async with async_session() as session:
        inquiry = None
        if parent_message_id:
            r = await session.execute(
                select(InquiryRequest).where(
                    InquiryRequest.feishu_message_id == parent_message_id
                )
            )
            inquiry = r.scalar_one_or_none()
        if not inquiry and token:
            r = await session.execute(
                select(InquiryRequest).where(InquiryRequest.prefix_token == token)
            )
            inquiry = r.scalar_one_or_none()

        # Fallback: 通过 open_id 找该员工24小时内最新一条 sent 状态的询问
        if not inquiry:
            from sqlalchemy import desc
            from datetime import timedelta
            r = await session.execute(
                select(Employee).where(Employee.feishu_open_id == open_id)
            )
            emp_for_fallback = r.scalar_one_or_none()
            if emp_for_fallback:
                cutoff = datetime.now() - timedelta(hours=24)
                r = await session.execute(
                    select(InquiryRequest)
                    .where(
                        InquiryRequest.employee_id == emp_for_fallback.id,
                        InquiryRequest.status == "sent",
                        InquiryRequest.sent_at >= cutoff,
                    )
                    .order_by(desc(InquiryRequest.sent_at))
                    .limit(1)
                )
                inquiry = r.scalar_one_or_none()
                if inquiry:
                    logger.info(f"通过 fallback 关联询问: open_id={open_id[:12]}.. → {inquiry.prefix_token}")

        if not inquiry:
            return {"matched": False, "reason": "no_matching_inquiry"}

        # 验证回复者
        emp = await session.get(Employee, inquiry.employee_id)
        if not emp or emp.feishu_open_id != open_id:
            return {"matched": False, "reason": "wrong_replier"}

        proj = await session.get(Project, inquiry.project_id)
        if not proj:
            return {"matched": False, "reason": "project_gone"}

        # LLM 提炼
        try:
            extract = await chat_json(
                f"""员工回复了项目问询，请提炼核心信息。

员工: {emp.name}
项目: {proj.name}
回复原文: {text}

返回JSON: {{"progress": "进展简述（一句）", "blockers": "阻碍或需要支持（如无则空）"}}""",
                use_strong=False,
            )
            progress = extract.get("progress", "").strip() or text[:120]
            blockers = extract.get("blockers", "").strip()
        except Exception:
            progress = text[:120]
            blockers = ""

        # 写 timeline
        events = list(proj.timeline_events or [])
        evt_text = f"[员工反馈] {progress}"
        if blockers:
            evt_text += f" | 阻碍: {blockers}"
        events.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "event": evt_text,
            "author": emp.name,
        })
        proj.timeline_events = events

        inquiry.status = "replied"
        inquiry.reply_text = text
        inquiry.replied_at = datetime.now()

        await session.commit()

    logger.info(f"员工 {emp.name} 回复 {proj.name} 已记录")
    return {
        "matched": True,
        "employee_name": emp.name,
        "project_name": proj.name,
        "progress": progress,
        "blockers": blockers,
    }
