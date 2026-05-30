"""询问记录 — 机器人主动私聊员工后的回执跟踪"""
import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InquiryRequest(Base):
    __tablename__ = "inquiry_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    feishu_message_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True,
                                                          comment="发送的飞书消息ID")
    prefix_token: Mapped[str] = mapped_column(String(40), nullable=False, unique=True,
                                              comment="问询短码 inq-xxxx")
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reply_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="sent",
                                        comment="sent|replied|expired")
