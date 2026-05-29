"""知识库 API — 文档上传、列表"""
import logging
import hashlib
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class UploadResponse(BaseModel):
    doc_token: str
    title: str
    version: int
    chars: int


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    doc_token: str = Form(""),
    title: str = Form(""),
):
    """
    上传文档到知识库（自动入库 + KB管理员浓缩 + embedding）。

    支持的文件类型：.txt / .md
    （PDF 等暂未支持，需要后续加 PyPDF2 解析）

    Args:
        file: 文件
        doc_token: 自定义doc_token（如 resume-{employee_id}），为空则用文件名
        title: 文档标题，为空则用文件名
    """
    from app.services.rag import upsert_document

    raw = await file.read()

    # 简单文本提取（先支持纯文本/markdown）
    fname = file.filename or "untitled"
    if fname.lower().endswith((".txt", ".md")):
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content = raw.decode("gbk")
            except Exception:
                raise HTTPException(400, "文件编码无法识别（请用UTF-8或GBK）")
    else:
        raise HTTPException(400, f"暂不支持 {fname} 这种文件类型，请上传 .txt 或 .md")

    if not content.strip():
        raise HTTPException(400, "文件内容为空")

    # 自动生成 doc_token / title
    safe_title = title or fname
    safe_token = doc_token or f"upload-{datetime.now().strftime('%Y%m%d%H%M%S')}-{fname}"
    content_hash = hashlib.md5(content.encode()).hexdigest()

    result = await upsert_document(safe_token, safe_title, content, content_hash)

    return UploadResponse(
        doc_token=safe_token,
        title=safe_title,
        version=result.get("version", 1),
        chars=len(content),
    )


@router.get("/documents")
async def list_documents(category: str = "", limit: int = 50):
    """列出知识库中所有文档（可按分类筛选）"""
    from sqlalchemy import select, desc
    from app.database import async_session
    from app.models.document_version import DocumentVersion

    async with async_session() as session:
        stmt = select(DocumentVersion).order_by(desc(DocumentVersion.last_updated)).limit(limit)
        result = await session.execute(stmt)
        docs = result.scalars().all()

    items = []
    for d in docs:
        meta = d.doc_metadata or {}
        if category and meta.get("category") != category:
            continue
        items.append({
            "id": str(d.id),
            "doc_token": d.doc_token,
            "title": d.title,
            "version": d.version,
            "category": meta.get("category", "未分类"),
            "char_count": len(d.content) if d.content else 0,
            "last_updated": d.last_updated.isoformat() if d.last_updated else "",
        })

    return {"items": items, "count": len(items)}


@router.delete("/documents/{doc_token}")
async def delete_document(doc_token: str):
    """删除某个文档（按 doc_token，所有版本都删）"""
    from sqlalchemy import select, delete
    from app.database import async_session
    from app.models.document_version import DocumentVersion

    async with async_session() as session:
        result = await session.execute(
            delete(DocumentVersion).where(DocumentVersion.doc_token == doc_token)
        )
        await session.commit()
        return {"deleted": result.rowcount}
