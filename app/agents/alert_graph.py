"""主动预警Agent — scan_overdue → analyze_sentiment → generate_report → push"""
import logging
from langgraph.graph import StateGraph, START, END

from app.agents.state import AlertState
from app.agents import get_checkpointer_async

logger = logging.getLogger(__name__)

# 默认风险关键词
DEFAULT_RISK_KEYWORDS = [
    "严重阻碍", "无法按期交付", "延期", "风险", "卡住", "blocker",
    "紧急", "失败", "崩溃", "客户投诉", "资源不足", "人手不够",
]


async def scan_overdue(state: AlertState) -> dict:
    """扫描多维表格中的逾期任务"""
    from sqlalchemy import select
    from app.database import async_session
    from app.models import LarkAsset

    overdue_items = []

    try:
        async with async_session() as session:
            result = await session.execute(
                select(LarkAsset).where(
                    LarkAsset.asset_type == "bitable",
                    LarkAsset.is_active == True,
                )
            )
            assets = result.scalars().all()

        for asset in assets:
            try:
                from app.services.feishu.bitable import list_records
                data = await list_records(asset.asset_token, asset.table_id)
                items = data.get("items", [])

                for item in items:
                    fields = item.get("fields", {})
                    status = str(fields.get("状态", fields.get("status", ""))).lower()
                    if status in ("done", "完成", "已完成"):
                        continue

                    # 简单检测：有截止日期字段且有内容的都标记为潜在风险
                    deadline = fields.get("截止日期", fields.get("deadline", ""))
                    if deadline:
                        overdue_items.append({
                            "table": asset.asset_name or asset.asset_token,
                            "task": str(fields.get("任务名称", fields.get("name", "未知"))),
                            "assignee": str(fields.get("负责人", fields.get("assignee", "未知"))),
                            "deadline": str(deadline),
                            "status": status,
                        })
            except Exception as e:
                logger.warning(f"扫描Bitable {asset.asset_token} 失败: {e}")

    except Exception as e:
        logger.error(f"数据库查询失败: {e}")

    logger.info(f"逾期扫描: 发现 {len(overdue_items)} 个待办项")
    return {"overdue_items": overdue_items}


async def analyze_sentiment(state: AlertState) -> dict:
    """分析群聊历史中的风险关键词"""
    from sqlalchemy import select
    from app.database import async_session
    from app.models import LarkAsset

    risk_found = []

    try:
        async with async_session() as session:
            result = await session.execute(
                select(LarkAsset).where(
                    LarkAsset.asset_type == "chat",
                    LarkAsset.is_active == True,
                )
            )
            assets = result.scalars().all()

        for asset in assets:
            try:
                from app.services.feishu.messages import get_chat_history
                import json

                messages = await get_chat_history(asset.asset_token, page_size=50)
                for msg in messages:
                    content_str = msg.get("body", {}).get("content", "{}")
                    try:
                        content = json.loads(content_str)
                        text = content.get("text", "")
                    except (json.JSONDecodeError, AttributeError):
                        text = str(content_str)

                    for keyword in DEFAULT_RISK_KEYWORDS:
                        if keyword in text:
                            risk_found.append({
                                "chat": asset.asset_name or asset.asset_token,
                                "keyword": keyword,
                                "snippet": text[:100],
                                "sender": msg.get("sender", {}).get("id", ""),
                            })
            except Exception as e:
                logger.warning(f"获取群聊 {asset.asset_token} 历史失败: {e}")

    except Exception as e:
        logger.error(f"情绪分析数据库查询失败: {e}")

    logger.info(f"情绪分析: 发现 {len(risk_found)} 条风险信号")
    return {"risk_keywords_found": risk_found}


async def generate_report(state: AlertState) -> dict:
    """生成风险报告"""
    from app.services.llm import chat_simple

    overdue = state.get("overdue_items", [])
    risk_kw = state.get("risk_keywords_found", [])

    # 判断风险等级
    total_signals = len(overdue) + len(risk_kw)
    if total_signals == 0:
        return {"risk_level": "low", "report_content": "当前无风险信号，一切正常。"}
    elif total_signals <= 3:
        risk_level = "medium"
    elif total_signals <= 8:
        risk_level = "high"
    else:
        risk_level = "critical"

    # 用LLM生成分析报告
    context = f"""逾期/待办项 ({len(overdue)}个):
{chr(10).join(f"- {o['task']} | 负责: {o['assignee']} | 截止: {o['deadline']} | 状态: {o['status']}" for o in overdue[:10])}

群聊风险信号 ({len(risk_kw)}条):
{chr(10).join(f"- [{k['keyword']}] {k['snippet']}" for k in risk_kw[:10])}"""

    prompt = f"""基于以下项目风险数据，生成一份简洁的"项目风险红线报告"。

{context}

要求：
1. 风险等级: {risk_level.upper()}
2. 列出最紧急的3个风险点
3. 每个风险点给出建议行动
4. Markdown格式，CEO能快速扫读"""

    from app.agents.prompts import alert_prompt
    report = await chat_simple(
        prompt,
        system_prompt=alert_prompt(),
        use_strong=True,
    )

    return {"risk_level": risk_level, "report_content": report}


async def push_alert(state: AlertState) -> dict:
    """推送风险报告到CEO"""
    chat_id = state.get("chat_id", "")
    content = state.get("report_content", "")
    risk_level = state.get("risk_level", "low")

    if risk_level == "low":
        logger.info("风险等级低，跳过推送")
        return {"sent": False}

    if not chat_id:
        logger.info("未配置推送目标，跳过")
        return {"sent": False}

    try:
        from app.services.feishu.messages import send_interactive_card, build_report_card

        template_map = {"medium": "yellow", "high": "orange", "critical": "red"}
        template = template_map.get(risk_level, "blue")

        card = build_report_card(
            title=f"🚨 项目风险报告 [{risk_level.upper()}]",
            content=content,
            template=template,
        )
        await send_interactive_card(chat_id, card)
        logger.info(f"风险报告已推送: risk_level={risk_level}")
        return {"sent": True}
    except Exception as e:
        logger.error(f"推送风险报告失败: {e}")
        return {"sent": False}


async def update_project_timelines(state: AlertState) -> dict:
    """把风险信号通过模糊匹配写入对应项目的 timeline_events（D阶段新节点）。"""
    from datetime import datetime
    from sqlalchemy import select
    from app.database import async_session
    from app.models import Project
    from app.services.llm import chat_json

    overdue = state.get("overdue_items", []) or []
    risks = state.get("risk_keywords_found", []) or []
    if not (overdue or risks):
        return {}

    # 准备风险信号清单
    signals = []
    for o in overdue[:15]:
        signals.append({
            "type": "overdue",
            "summary": f"逾期任务 [{o.get('task','?')}] 负责人:{o.get('assignee','?')} 截止:{o.get('deadline','?')} 状态:{o.get('status','?')}",
        })
    for r in risks[:15]:
        signals.append({
            "type": "sentiment",
            "summary": f"群聊风险词 [{r.get('keyword','?')}] 上下文:{r.get('snippet','')[:80]}",
        })

    if not signals:
        return {}

    # 加载在进项目
    projects_info = []
    async with async_session() as session:
        r = await session.execute(
            select(Project).where(Project.status == "in_progress")
        )
        all_projs = r.scalars().all()
        for p in all_projs:
            projects_info.append({"id": str(p.id), "name": p.name, "description": p.description[:200]})

    if not projects_info:
        return {}

    # LLM 模糊匹配
    prompt = f"""为每条风险信号判断是否与某个进行中项目相关。

进行中的项目:
{chr(10).join(f"[{i}] {p['name']}: {p['description']}" for i, p in enumerate(projects_info))}

风险信号:
{chr(10).join(f"[{i}] {s['summary']}" for i, s in enumerate(signals))}

返回JSON数组，每条对应一个风险信号:
[{{"signal_index": 0, "project_index": 1, "confidence": 0.85}}, ...]

要求:
- project_index 用 -1 表示与所有项目都无关
- confidence 0-1，<0.4 也用 -1
- 只列有匹配的（置信度>=0.4）"""

    try:
        matches = await chat_json(prompt, use_strong=False)
        if isinstance(matches, dict):
            matches = matches.get("matches") or matches.get("items") or []
    except Exception as e:
        logger.warning(f"风险-项目模糊匹配失败: {e}")
        return {}

    if not isinstance(matches, list) or not matches:
        return {}

    # 写 timeline_events
    update_count = 0
    async with async_session() as session:
        for m in matches:
            try:
                si = int(m.get("signal_index", -1))
                pi = int(m.get("project_index", -1))
                conf = float(m.get("confidence", 0))
                if si < 0 or si >= len(signals) or pi < 0 or pi >= len(projects_info) or conf < 0.4:
                    continue

                proj_id = projects_info[pi]["id"]
                proj = await session.get(Project, proj_id)
                if not proj:
                    continue

                events = list(proj.timeline_events or [])
                events.append({
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "event": f"[预警·模糊匹配·{conf:.0%}] {signals[si]['summary']}",
                    "author": "预警Agent",
                })
                proj.timeline_events = events
                update_count += 1
            except Exception as e:
                logger.warning(f"写入 project timeline 失败: {e}")

        if update_count > 0:
            await session.commit()

    logger.info(f"预警Agent 写入项目 timeline {update_count} 条")
    return {}


async def save_to_kb(state: AlertState) -> dict:
    """把风险报告存入知识库"""
    from datetime import datetime
    import hashlib
    from app.services.rag import upsert_document

    content = state.get("report_content", "")
    risk_level = state.get("risk_level", "low")
    if not content or risk_level == "low":
        return {}

    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    doc_token = f"alert-{timestamp}"
    title = f"风险报告 [{risk_level.upper()}] {timestamp}"
    content_hash = hashlib.md5(content.encode()).hexdigest()
    try:
        await upsert_document(doc_token, title, content, content_hash)
        logger.info(f"风险报告已入库: {title}")
    except Exception as e:
        logger.error(f"风险报告入库失败: {e}")
    return {}


async def build_alert_graph():
    """构建预警图"""
    graph = StateGraph(AlertState)

    graph.add_node("scan_overdue", scan_overdue)
    graph.add_node("analyze_sentiment", analyze_sentiment)
    graph.add_node("generate_report", generate_report)
    graph.add_node("update_project_timelines", update_project_timelines)
    graph.add_node("push_alert", push_alert)
    graph.add_node("save_to_kb", save_to_kb)

    graph.add_edge(START, "scan_overdue")
    graph.add_edge("scan_overdue", "analyze_sentiment")
    graph.add_edge("analyze_sentiment", "generate_report")
    graph.add_edge("generate_report", "update_project_timelines")
    graph.add_edge("update_project_timelines", "push_alert")
    graph.add_edge("push_alert", "save_to_kb")
    graph.add_edge("save_to_kb", END)

    checkpointer = await get_checkpointer_async()
    return graph.compile(checkpointer=checkpointer)
