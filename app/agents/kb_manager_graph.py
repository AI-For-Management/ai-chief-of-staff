"""知识库管理员 Agent — 去重、分类、打标签"""
import logging
from typing import TypedDict
from datetime import datetime

from langgraph.graph import StateGraph, START, END

from app.agents import get_checkpointer_async

logger = logging.getLogger(__name__)


def _kb_condense_sysprompt() -> str:
    from app.agents.prompts import kb_condense_prompt
    return kb_condense_prompt()


def _kb_answer_sysprompt() -> str:
    from app.agents.prompts import kb_answer_prompt
    return kb_answer_prompt()


class KBState(TypedDict):
    duplicates: list  # [{"doc_a": "...", "doc_b": "...", "similarity": 0.92}]
    categorized_count: int
    consolidate_report: str
    saved_to_kb: bool


async def scan_duplicates(state: KBState) -> dict:
    """用向量距离找出疑似重复文档"""
    from sqlalchemy import text
    from app.database import async_session

    duplicates = []

    # SQL: 自连接，找distance < 0.2 的对（不含自己）
    sql = text("""
        SELECT a.id::text, a.doc_token AS token_a, a.title AS title_a,
               b.id::text, b.doc_token AS token_b, b.title AS title_b,
               (a.embedding <=> b.embedding) AS distance
        FROM document_versions a, document_versions b
        WHERE a.embedding IS NOT NULL
          AND b.embedding IS NOT NULL
          AND a.id < b.id
          AND a.doc_token != b.doc_token
          AND (a.embedding <=> b.embedding) < 0.20
        ORDER BY distance ASC
        LIMIT 30
    """)

    try:
        async with async_session() as session:
            result = await session.execute(sql)
            rows = result.fetchall()
            for r in rows:
                duplicates.append({
                    "id_a": r[0], "token_a": r[1], "title_a": r[2],
                    "id_b": r[3], "token_b": r[4], "title_b": r[5],
                    "similarity": float(1.0 - r[6]),
                })
    except Exception as e:
        logger.error(f"去重扫描失败: {e}")

    logger.info(f"知识库去重扫描发现 {len(duplicates)} 对疑似重复")
    return {"duplicates": duplicates}


async def categorize(state: KBState) -> dict:
    """根据 doc_token 前缀给文档打分类标签"""
    from sqlalchemy import select, update
    from app.database import async_session
    from app.models import DocumentVersion

    category_map = {
        "briefing-": "情报",
        "alert-": "风险",
        "employee-profile-": "员工",
        "employee-update-": "员工",
        "hr-summary-": "员工",
        "project-": "项目",
        "kb-report-": "系统",
        "resume-": "员工",
    }

    count = 0
    async with async_session() as session:
        result = await session.execute(select(DocumentVersion))
        docs = result.scalars().all()
        for d in docs:
            cat = "其他"
            for prefix, c in category_map.items():
                if d.doc_token.startswith(prefix):
                    cat = c
                    break
            current_meta = d.doc_metadata or {}
            if current_meta.get("category") != cat:
                current_meta["category"] = cat
                d.doc_metadata = current_meta
                count += 1
        await session.commit()

    logger.info(f"知识库分类: 更新 {count} 条")
    return {"categorized_count": count}


async def generate_report(state: KBState) -> dict:
    """生成知识库管理报告"""
    duplicates = state.get("duplicates", [])
    categorized = state.get("categorized_count", 0)

    report = f"""# 知识库管理报告 {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 文档分类
共更新 **{categorized}** 条文档分类标签。

## 疑似重复文档 ({len(duplicates)} 对)

"""
    if duplicates:
        for d in duplicates[:20]:
            report += f"- **{d['title_a']}** ↔ **{d['title_b']}** （相似度 {d['similarity']*100:.1f}%）\n"
            report += f"  - tokens: `{d['token_a']}` ↔ `{d['token_b']}`\n"
        report += "\n建议: 由人工审核以上文档对，决定是否合并或删除。\n"
    else:
        report += "未发现疑似重复文档。\n"

    return {"consolidate_report": report}


async def save_report_to_kb(state: KBState) -> dict:
    """把报告本身存入知识库"""
    import hashlib
    from app.services.rag import upsert_document

    content = state.get("consolidate_report", "")
    if not content:
        return {"saved_to_kb": False}

    today = datetime.now().strftime("%Y-%m-%d")
    try:
        await upsert_document(
            doc_token=f"kb-report-{today}",
            title=f"知识库管理报告 {today}",
            content=content,
            content_hash=hashlib.md5(content.encode()).hexdigest(),
        )
        return {"saved_to_kb": True}
    except Exception as e:
        logger.error(f"知识库报告入库失败: {e}")
        return {"saved_to_kb": False}


async def build_kb_manager_graph():
    graph = StateGraph(KBState)
    graph.add_node("scan_duplicates", scan_duplicates)
    graph.add_node("categorize", categorize)
    graph.add_node("generate_report", generate_report)
    graph.add_node("save_report_to_kb", save_report_to_kb)
    graph.add_edge(START, "scan_duplicates")
    graph.add_edge("scan_duplicates", "categorize")
    graph.add_edge("categorize", "generate_report")
    graph.add_edge("generate_report", "save_report_to_kb")
    graph.add_edge("save_report_to_kb", END)
    cp = await get_checkpointer_async()
    return graph.compile(checkpointer=cp)


async def run_kb_manager() -> dict:
    """运行知识库管理任务"""
    import uuid
    graph = await build_kb_manager_graph()
    thread_id = f"kb-manager-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}
    state = {
        "duplicates": [], "categorized_count": 0,
        "consolidate_report": "", "saved_to_kb": False,
    }
    result = await graph.ainvoke(state, config=config)
    return {
        "duplicates_count": len(result.get("duplicates", [])),
        "categorized_count": result.get("categorized_count", 0),
        "report": result.get("consolidate_report", ""),
        "saved_to_kb": result.get("saved_to_kb", False),
    }


# ===========================================================
# 文档检索精华生成（被 rag.upsert_document 调用）
# ===========================================================

async def condense_for_embedding(title: str, content: str) -> str:
    """
    把任意文档浓缩为"检索友好"的精华版（用于 embedding 输入）。
    完整原文仍然存 content，但 embedding 用这个精华版生成，
    既避免 BGE 模型 512 token 上限，又确保检索精度。
    """
    from app.services.llm import chat_simple

    # 短文档直接用原文
    if len(content) < 400:
        return f"{title}\n\n{content}"

    try:
        condensed = await chat_simple(
            f"""把下面这份文档浓缩为 250 字以内的检索精华，用于知识库语义检索。

**必须保留**：
- 标题/类型（开头一句话点明这是什么文档）
- 所有人名、项目名、产品名等专有名词
- 关键数据、日期、百分比
- 主要结论或决策建议
- 加入这些语义词便于检索：公司、项目、挑战、机会、风险、决策

**格式**：纯文本，不要 markdown 标记。

文档标题：{title}

文档内容：
{content[:4000]}""",
            system_prompt=_kb_condense_sysprompt(),
            use_strong=False,
        )
        # 安全保险：超过 1000 字也截断
        return condensed[:1000]
    except Exception as e:
        logger.warning(f"condense 失败，使用 title+前300字: {e}")
        return f"{title}\n\n{content[:300]}"


# ===========================================================
# RAG 问答：基于知识库相关文档综合回答
# ===========================================================

async def answer_question(
    query: str,
    top_k: int = 8,
    threshold: float = 0.4,
    use_strong: bool = False,
) -> dict:
    """
    基于知识库的相关文档（相关度 >= threshold）综合回答。

    Args:
        query: 用户问题
        top_k: 最多检索多少条
        threshold: 相关度下限（1 - distance），低于此阈值的文档不纳入回答

    Returns:
        {
          "answer": "AI综合回答",
          "sources": [{"title", "doc_token", "relevance"}, ...],
          "no_match": False  # 如果完全没相关文档则True
        }
    """
    from app.services.rag import search
    from app.services.llm import chat_simple

    # 1. 检索
    raw_results = await search(query, top_k=top_k)
    relevant = [r for r in raw_results if (1 - r["distance"]) >= threshold]

    # Fallback: 如果固定阈值过滤后结果太少，按相对排序+top_k_min兜底
    # 适用于"宽泛元问题"场景（如"公司最近发生了什么"），向量绝对相似度低但相对排序仍有意义
    MIN_DOCS = 5
    if len(relevant) < MIN_DOCS and raw_results:
        # 按相关度排序，取前 MIN_DOCS 个，但相关度必须高于 0.15（避免完全无关的）
        sorted_results = sorted(raw_results, key=lambda r: r["distance"])
        relevant = [r for r in sorted_results[:MIN_DOCS] if (1 - r["distance"]) >= 0.15]
        logger.info(f"RAG fallback: 相关度阈值 {threshold} 过滤后只剩 {len([r for r in raw_results if (1 - r['distance']) >= threshold])}，启用 top-{MIN_DOCS} 兜底（实际 {len(relevant)} 条）")

    if not relevant:
        return {
            "answer": "知识库中暂无与该问题相关的文档。\n\n如需获取此类信息，建议：\n- 生成相关的情报简报\n- 上传相关文档（如简历、会议纪要）\n- 让 HR Agent 跑一次更新员工指标",
            "sources": [],
            "no_match": True,
        }

    # 2. 拼接上下文（带编号方便LLM引用）
    context_blocks = []
    sources = []
    for i, r in enumerate(relevant, 1):
        context_blocks.append(
            f"[文档{i}] 《{r['title']}》（相关度 {(1-r['distance'])*100:.0f}%）\n{r['content']}"
        )
        sources.append({
            "index": i,
            "title": r["title"],
            "doc_token": r["doc_token"],
            "relevance": round((1 - r["distance"]) * 100, 1),
            "content_preview": r["content"][:300],
        })

    context_text = "\n\n---\n\n".join(context_blocks)

    # 3. 调强模型综合回答
    prompt = f"""请基于以下从公司知识库检索到的相关文档，回答用户的问题。

【用户问题】
{query}

【知识库相关文档】
{context_text}

回答要求：
1. **必须**基于上述文档作答，**严禁**编造文档没有的信息
2. 若文档信息不足以回答，明确告知"知识库中相关信息有限，仅能提供..."
3. 在涉及具体数据/结论时，标注引用来源（如"根据《CEO每日情报简报》..."）
4. 简洁有力，3-5 段，重要观点用 **加粗** 突出
5. 用 Markdown 格式输出"""

    try:
        answer = await chat_simple(
            prompt,
            system_prompt=_kb_answer_sysprompt(),
            use_strong=use_strong,
        )
    except Exception as e:
        logger.error(f"RAG 综合回答失败: {e}")
        answer = f"生成回答时出错：{e}"

    return {
        "answer": answer,
        "sources": sources,
        "no_match": False,
    }
