"""新闻/情报抓取服务 — 多种搜索源 + LLM结构化"""
import os
import logging
import httpx

logger = logging.getLogger(__name__)


def _get_proxy() -> str | None:
    """获取代理配置"""
    return os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or None


def search_news(query: str, max_results: int = 8) -> list[dict]:
    """搜索新闻，依次尝试多种方式"""
    # 方式1: DuckDuckGo (ddgs)
    results = _ddgs_search(query, max_results)
    if results:
        return results

    # 方式2: 搜狗新闻（国内可直连）
    results = _sogou_search(query, max_results)
    if results:
        return results

    return []


def search_web(query: str, max_results: int = 8) -> list[dict]:
    """搜索网页"""
    results = _ddgs_web_search(query, max_results)
    if results:
        return results
    return _sogou_search(query, max_results)


def _ddgs_search(query: str, max_results: int) -> list[dict]:
    """DuckDuckGo新闻搜索"""
    try:
        from ddgs import DDGS
        proxy = _get_proxy()
        ddgs = DDGS(proxy=proxy) if proxy else DDGS()
        results = ddgs.news(query, max_results=max_results)
        return [
            {
                "title": r.get("title", ""),
                "body": r.get("body", ""),
                "url": r.get("url", ""),
                "source": r.get("source", ""),
                "date": r.get("date", ""),
            }
            for r in results
        ]
    except Exception as e:
        logger.warning(f"DuckDuckGo新闻失败: {e}")
        return []


def _ddgs_web_search(query: str, max_results: int) -> list[dict]:
    """DuckDuckGo网页搜索"""
    try:
        from ddgs import DDGS
        proxy = _get_proxy()
        ddgs = DDGS(proxy=proxy) if proxy else DDGS()
        results = ddgs.text(query, max_results=max_results)
        return [
            {
                "title": r.get("title", ""),
                "body": r.get("body", ""),
                "url": r.get("href", ""),
                "source": "",
                "date": "",
            }
            for r in results
        ]
    except Exception as e:
        logger.warning(f"DuckDuckGo网页失败: {e}")
        return []


def _sogou_search(query: str, max_results: int) -> list[dict]:
    """搜狗搜索（国内可直连，不需要代理）"""
    import re
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = httpx.get(
            f"https://www.sogou.com/web?query={query}",
            headers=headers,
            timeout=10,
            follow_redirects=True,
        )

        if resp.status_code != 200:
            return []

        results = []
        # 提取标题和摘要
        blocks = re.findall(r'<h3.*?>(.*?)</h3>.*?<p.*?>(.*?)</p>', resp.text, re.DOTALL)
        for title_html, body_html in blocks[:max_results]:
            title = re.sub(r'<[^>]+>', '', title_html).strip()
            body = re.sub(r'<[^>]+>', '', body_html).strip()
            if title:
                results.append({
                    "title": title,
                    "body": body,
                    "url": "",
                    "source": "搜狗",
                    "date": "",
                })

        # 如果正则没匹配到，降级提取标题
        if not results:
            titles = re.findall(r'<h3.*?>(.*?)</h3>', resp.text, re.DOTALL)
            for t in titles[:max_results]:
                clean = re.sub(r'<[^>]+>', '', t).strip()
                if clean and len(clean) > 4:
                    results.append({
                        "title": clean,
                        "body": "",
                        "url": "",
                        "source": "搜狗",
                        "date": "",
                    })

        return results
    except Exception as e:
        logger.warning(f"搜狗搜索失败: {e}")
        return []


async def generate_briefing(topics: list[str]) -> str:
    """
    抓取多个话题的新闻并生成结构化简报。
    """
    from app.services.llm import chat_simple

    all_news = []
    for topic in topics:
        results = search_news(topic, max_results=5)
        if results:
            all_news.append({"topic": topic, "articles": results})

    if not all_news:
        return "未抓取到任何新闻，请检查网络连接。"

    news_text = ""
    for group in all_news:
        news_text += f"\n## 话题: {group['topic']}\n"
        for i, a in enumerate(group["articles"], 1):
            news_text += f"{i}. **{a['title']}**\n"
            news_text += f"   {a['body'][:200]}\n"
            if a['source']:
                news_text += f"   来源: {a['source']}"
            if a['date']:
                news_text += f" | {a['date']}"
            news_text += "\n\n"

    prompt = f"""请基于以下新闻素材，生成一份CEO每日科技与行业情报简报。

要求：
1. 分话题归类，每个话题3-5条核心要点
2. 提炼关键数字和趋势
3. 对CEO的决策建议（如有）
4. 使用Markdown格式，简洁有力

新闻素材：
{news_text}"""

    from app.agents.prompts import briefing_prompt
    briefing = await chat_simple(
        prompt,
        system_prompt=briefing_prompt(),
        use_strong=True,
    )

    return briefing
