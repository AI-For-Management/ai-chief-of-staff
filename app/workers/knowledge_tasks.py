"""知识管理Celery定时任务 — 文档扫描 + 增量版本 + re-embed"""
import hashlib
import logging
import asyncio

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.knowledge_tasks.scan_documents")
def scan_documents():
    """定时扫描飞书文档，检测变更并更新向量库"""
    logger.info("开始文档扫描任务")
    try:
        result = asyncio.run(_scan_all_docs())
        logger.info(f"文档扫描完成: {result}")
        return result
    except Exception as e:
        logger.error(f"文档扫描失败: {e}")
        return {"error": str(e)}


async def _scan_all_docs() -> dict:
    """扫描所有绑定的飞书文档/Wiki"""
    from sqlalchemy import select
    from app.database import async_session
    from app.models import LarkAsset
    from app.services.feishu.docs import get_doc_blocks, blocks_to_markdown
    from app.services.rag import upsert_document

    stats = {"scanned": 0, "updated": 0, "unchanged": 0, "errors": 0}

    async with async_session() as session:
        result = await session.execute(
            select(LarkAsset).where(
                LarkAsset.asset_type.in_(["doc", "wiki"]),
                LarkAsset.is_active == True,
            )
        )
        assets = result.scalars().all()

    for asset in assets:
        try:
            stats["scanned"] += 1

            # 获取文档内容
            blocks = await get_doc_blocks(asset.asset_token)
            markdown = blocks_to_markdown(blocks)

            if not markdown.strip():
                continue

            # 计算内容hash
            content_hash = hashlib.md5(markdown.encode()).hexdigest()

            # 更新向量库
            result = await upsert_document(
                doc_token=asset.asset_token,
                title=asset.asset_name or asset.asset_token,
                content=markdown,
                content_hash=content_hash,
            )

            if result["action"] == "updated":
                stats["updated"] += 1
            else:
                stats["unchanged"] += 1

        except Exception as e:
            logger.error(f"扫描文档 {asset.asset_token} 失败: {e}")
            stats["errors"] += 1

    return stats


@celery_app.task(name="app.workers.knowledge_tasks.reembed_document")
def reembed_document(doc_token: str):
    """手动触发单个文档的re-embed"""
    logger.info(f"手动re-embed: {doc_token}")
    try:
        result = asyncio.run(_reembed_single(doc_token))
        return result
    except Exception as e:
        logger.error(f"re-embed失败: {e}")
        return {"error": str(e)}


async def _reembed_single(doc_token: str) -> dict:
    """重新向量化单个文档"""
    from sqlalchemy import select
    from app.database import async_session
    from app.models.document_version import DocumentVersion
    from app.services.embedding import embed_text

    async with async_session() as session:
        result = await session.execute(
            select(DocumentVersion)
            .where(DocumentVersion.doc_token == doc_token)
            .order_by(DocumentVersion.version.desc())
            .limit(1)
        )
        doc = result.scalar_one_or_none()

        if not doc:
            return {"error": "文档不存在"}

        embedding = await embed_text(doc.content[:8000])
        doc.embedding = embedding
        await session.commit()

    return {"doc_token": doc_token, "version": doc.version, "action": "reembedded"}
