"""飞书资产绑定 — 多维表格、云文档、Wiki空间的动态绑定"""
import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LarkAsset(Base):
    __tablename__ = "lark_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, comment="关联的lark_config")
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="bitable|doc|wiki|chat")
    asset_token: Mapped[str] = mapped_column(String(200), nullable=False, comment="飞书资源唯一标识")
    asset_name: Mapped[str] = mapped_column(String(300), default="", comment="资源名称")
    table_id: Mapped[str] = mapped_column(String(200), default="", comment="Bitable表ID")
    field_mapping: Mapped[dict] = mapped_column(JSONB, default=dict, comment="字段映射JSON")
    cron_expression: Mapped[str] = mapped_column(String(100), default="0 */6 * * *", comment="同步Cron表达式")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
