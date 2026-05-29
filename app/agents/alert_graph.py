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

    report = await chat_simple(
        prompt,
        system_prompt="你是项目管理专家，擅长识别项目风险并给出可执行建议。输出简洁有力。",
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
    graph.add_node("push_alert", push_alert)
    graph.add_node("save_to_kb", save_to_kb)

    graph.add_edge(START, "scan_overdue")
    graph.add_edge("scan_overdue", "analyze_sentiment")
    graph.add_edge("analyze_sentiment", "generate_report")
    graph.add_edge("generate_report", "push_alert")
    graph.add_edge("push_alert", "save_to_kb")
    graph.add_edge("save_to_kb", END)

    checkpointer = await get_checkpointer_async()
    return graph.compile(checkpointer=checkpointer)
