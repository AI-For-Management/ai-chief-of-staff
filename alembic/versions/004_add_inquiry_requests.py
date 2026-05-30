"""add inquiry_requests table

Revision ID: 004
Revises: 003
Create Date: 2026-05-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "inquiry_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("employee_id", UUID(as_uuid=True), nullable=False, comment="被询问的员工 employees.id"),
        sa.Column("project_id", UUID(as_uuid=True), nullable=False, comment="询问关联的项目 projects.id"),
        sa.Column("feishu_message_id", sa.String(80), nullable=True, comment="发送的飞书消息ID，用于回复匹配"),
        sa.Column("prefix_token", sa.String(40), nullable=False, comment="问询短码，如 inq-abc123，便于回复识别"),
        sa.Column("question_text", sa.Text, nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reply_text", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), server_default="sent", comment="sent|replied|expired"),
    )
    op.create_index("ix_inquiry_message_id", "inquiry_requests", ["feishu_message_id"])
    op.create_index("ix_inquiry_prefix", "inquiry_requests", ["prefix_token"], unique=True)
    op.create_index("ix_inquiry_status", "inquiry_requests", ["status"])


def downgrade():
    op.drop_index("ix_inquiry_status", table_name="inquiry_requests")
    op.drop_index("ix_inquiry_prefix", table_name="inquiry_requests")
    op.drop_index("ix_inquiry_message_id", table_name="inquiry_requests")
    op.drop_table("inquiry_requests")
