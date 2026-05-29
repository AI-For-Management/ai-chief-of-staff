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
    """用LLM生成结构化简报"""
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

    prompt = f"""基于以下新闻素材，生成CEO每日科技与行业情报简报。

要求：
1. 按话题分类，每个话题提炼3-5条核心要点
2. 突出关键数字、趋势和潜在影响
3. 如有值得CEO关注的风险或机会，单独标注
4. Markdown格式

新闻素材：
{news_text}"""

    briefing = await chat_simple(
        prompt,
        system_prompt="你是资深商业情报分析师，擅长从零散新闻提炼战略洞察。简洁有力，有数据支撑。",
        use_strong=True,
    )

    return {"briefing_content": briefing}


async def send_briefing(state: BriefingState) -> dict:
    """通过飞书发送简报"""
    chat_id = state.get("chat_id", "")
    content = state["briefing_content"]

    if not chat_id:
        logger.info("未配置发送目标，跳过飞书推送")
        return {"sent": False}

    try:
        from app.services.feishu.messages import send_interactive_card, build_report_card

        card = build_report_card(
            title="📊 CEO每日情报简报",
            content=content,
            template="blue",
        )
        await send_interactive_card(chat_id, card)
        logger.info(f"情报简报已发送到 {chat_id}")
        return {"sent": True}
    except Exception as e:
        logger.error(f"发送简报失败: {e}")
        return {"sent": False}


async def save_to_knowledge(state: BriefingState) -> dict:
    """将简报存入知识库（document_versions + embedding）"""
    from datetime import datetime
    import hashlib
    from app.services.rag import upsert_document

    content = state.get("briefing_content", "")
    if not content or "未抓取到" in content:
        return {}

    today = datetime.now().strftime("%Y-%m-%d")
    doc_token = f"briefing-{today}"
    title = f"CEO每日情报简报 {today}"
    content_hash = hashlib.md5(content.encode()).hexdigest()

    try:
        result = await upsert_document(doc_token, title, content, content_hash)
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
