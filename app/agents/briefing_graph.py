"""情报简报Agent — crawl → summarize → send"""
import logging
from langgraph.graph import StateGraph, START, END

from app.agents.state import BriefingState
from app.agents import get_checkpointer_async

logger = logging.getLogger(__name__)


async def crawl_news(state: BriefingState) -> dict:
    """抓取新闻"""
    from app.services.news import search_news

    topics = state["topics"]
    raw_news = []

    for topic in topics:
        results = search_news(topic, max_results=5)
        raw_news.append({"topic": topic, "articles": results})

    logger.info(f"抓取完成: {len(topics)}个话题, 共{sum(len(g['articles']) for g in raw_news)}条新闻")
    return {"raw_news": raw_news}


async def summarize(state: BriefingState) -> dict:
    """用LLM生成结构化简报，结合公司项目现状评估影响"""
    from datetime import datetime
    from app.services.llm import chat_simple

    raw_news = state["raw_news"]

    news_text = ""
    for group in raw_news:
        news_text += f"\n## {group['topic']}\n"
        for i, a in enumerate(group["articles"], 1):
            news_text += f"{i}. **{a.get('title', '')}**\n"
            news_text += f"   {a.get('body', '')[:200]}\n"
            news_text += f"   来源: {a.get('source', '')} | {a.get('date', '')}\n\n"

    if not news_text.strip():
        return {"briefing_content": "今日未抓取到相关新闻。"}

    # 加载公司当前项目作为上下文
    company_context = await _load_company_context()
    today = datetime.now().strftime("%Y年%m月%d日")
    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][datetime.now().weekday()]

    prompt = f"""【今天日期】{today} {weekday}

【公司当前业务】
{company_context}

【新闻素材】
{news_text}

请基于以上信息，生成 CEO 每日情报简报。

**硬性要求**:
1. 简报开头**必须**写上今天日期：{today}（不要用其他日期）
2. 每个话题下，至少要有 1 条 **直接点名** 公司项目的影响分析（例如"对智能客服Bot v2.0的影响："），把项目名嵌入分析中，而不是泛泛而谈
3. CEO决策建议部分，**必须围绕公司当前业务**写（提及具体项目或业务），不要写通用建议
4. 用 Markdown 格式：## 一级标题 / **加粗关键点**"""

    briefing = await chat_simple(
        prompt,
        system_prompt=(
            "你是资深商业情报分析师，为'星辰科技'CEO服务。"
            "你的简报必须紧密结合公司项目和业务现状，避免泛泛而谈。"
            "今天是 " + today + "，所有日期都以这个为准。"
        ),
        use_strong=True,
    )

    return {"briefing_content": briefing}


async def _load_company_context() -> str:
    """从数据库加载公司当前的项目、团队、业务上下文"""
    from sqlalchemy import select
    from app.database import async_session
    from app.models import Project, Employee

    parts = ["公司：星辰科技（一家做AI客服SaaS的初创公司）"]
    try:
        async with async_session() as session:
            # 进行中和规划中的项目
            result = await session.execute(
                select(Project).where(Project.status.in_(["in_progress", "planning"])).limit(10)
            )
            projects = result.scalars().all()
            if projects:
                parts.append("\n**当前项目**:")
                for p in projects:
                    status_label = {"in_progress": "进行中", "planning": "规划中"}.get(p.status, p.status)
                    parts.append(f"- 项目【{p.name}】（{status_label}）: {p.description[:120]}")

            # 团队规模
            emp_result = await session.execute(
                select(Employee).where(Employee.is_active == True)
            )
            emps = emp_result.scalars().all()
            if emps:
                depts = set(e.department for e in emps if e.department)
                parts.append(f"\n**团队**: {len(emps)}人，分布在 {', '.join(depts)}")
    except Exception as e:
        logger.warning(f"加载公司上下文失败: {e}")

    return "\n".join(parts)


async def send_briefing(state: BriefingState) -> dict:
    """通过飞书发送简报"""
    chat_id = state.get("chat_id", "")
    content = state["briefing_content"]

    if not chat_id:
        logger.info("未配置发送目标，跳过飞书推送")
        return {"sent": False}

    try:
        from app.services.feishu.messages import send_interactive_card, build_report_card

        # 飞书卡片对单个markdown元素长度有限制（约30000字符）
        # 如果太长，做截断 + 提示
        display_content = content
        max_chars = 5000
        if len(display_content) > max_chars:
            display_content = display_content[:max_chars] + "\n\n...（内容过长已截断，完整版请到管理后台查看）"

        card = build_report_card(
            title="CEO每日情报简报",  # 去掉emoji，避免飞书卡片报错
            content=display_content,
            template="blue",
        )
        await send_interactive_card(chat_id, card)
        logger.info(f"情报简报已发送到 {chat_id}")
        return {"sent": True}
    except Exception as e:
        logger.error(f"发送简报失败: {type(e).__name__}: {e}", exc_info=True)
        return {"sent": False}


async def save_to_knowledge(state: BriefingState) -> dict:
    """将简报存入知识库（KB管理员会自动生成检索精华版做embedding）"""
    from datetime import datetime
    import hashlib
    from app.services.rag import upsert_document

    full_content = state.get("briefing_content", "")
    if not full_content or "未抓取到" in full_content:
        return {}

    today = datetime.now().strftime("%Y-%m-%d")
    doc_token = f"briefing-{today}"
    title = f"CEO每日情报简报 {today}"
    content_hash = hashlib.md5(full_content.encode()).hexdigest()

    try:
        result = await upsert_document(doc_token, title, full_content, content_hash)
        logger.info(f"简报已入库: {title} -> {result}")
    except Exception as e:
        logger.error(f"简报入库失败: {e}")

    return {}


async def build_briefing_graph():
    """构建情报简报图"""
    graph = StateGraph(BriefingState)

    graph.add_node("crawl_news", crawl_news)
    graph.add_node("summarize", summarize)
    graph.add_node("send_briefing", send_briefing)
    graph.add_node("save_to_knowledge", save_to_knowledge)

    graph.add_edge(START, "crawl_news")
    graph.add_edge("crawl_news", "summarize")
    graph.add_edge("summarize", "send_briefing")
    graph.add_edge("send_briefing", "save_to_knowledge")
    graph.add_edge("save_to_knowledge", END)

    checkpointer = await get_checkpointer_async()
    return graph.compile(checkpointer=checkpointer)
