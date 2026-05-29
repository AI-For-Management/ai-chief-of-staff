"""文档版本控制 + 向量存储"""
import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.database import Base

EMBEDDING_DIM = 1024  # BGE-large-zh-v1.5


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_token: Mapped[str] = mapped_column(String(200), nullable=False, index=True, comment="飞书文档唯一标识")
    title: Mapped[str] = mapped_column(String(500), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(64), default="", comment="内容MD5，用于变更检测")
    version: Mapped[int] = mapped_column(Integer, default=1)
    embedding: Mapped[list] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    doc_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, comment="知识库标签/分类")
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
