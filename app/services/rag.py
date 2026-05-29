"""RAG检索服务 — pgvector相似度搜索"""
import logging
import uuid

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.document_version import DocumentVersion
from app.services.embedding import embed_text

logger = logging.getLogger(__name__)


async def search(query: str, top_k: int = 5) -> list[dict]:
    """
    向量相似度检索文档。

    Args:
        query: 用户查询文本
        top_k: 返回结果数量
    Returns:
        按相关性排序的文档列表
    """
    query_embedding = await embed_text(query)

    async with async_session() as session:
        # pgvector cosine distance: <=> 运算符
        sql = text("""
            SELECT id, doc_token, title, content, version, last_updated,
                   embedding <=> :query_vec AS distance
            FROM document_versions
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> :query_vec
            LIMIT :top_k
        """)

        result = await session.execute(sql, {
            "query_vec": str(query_embedding),
            "top_k": top_k,
        })

        rows = result.fetchall()

    return [
        {
            "id": str(row[0]),
            "doc_token": row[1],
            "title": row[2],
            "content": row[3][:500],  # 截断预览
            "version": row[4],
            "last_updated": row[5].isoformat() if row[5] else "",
            "distance": float(row[6]),
        }
        for row in rows
    ]


async def upsert_document(
    doc_token: str,
    title: str,
    content: str,
    content_hash: str,
) -> dict:
    """
    插入或更新文档版本。
    内容hash变化时创建新版本并重新向量化。
    """
    async with async_session() as session:
        # 查找该文档最新版本
        result = await session.execute(
            select(DocumentVersion)
            .where(DocumentVersion.doc_token == doc_token)
            .order_by(DocumentVersion.version.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()

        if latest and latest.content_hash == content_hash:
            return {"action": "unchanged", "version": latest.version}

        # 生成新embedding
        embedding = await embed_text(content[:8000])  # 截断避免超token

        new_version = latest.version + 1 if latest else 1
        doc = DocumentVersion(
            id=uuid.uuid4(),
            doc_token=doc_token,
            title=title,
            content=content,
            content_hash=content_hash,
            version=new_version,
            embedding=embedding,
        )

        session.add(doc)
        await session.commit()

        logger.info(f"文档更新: {title} v{new_version}")
        return {"action": "updated", "version": new_version}
