"""initial schema - 4 core tables + pgvector extension

Revision ID: 001
Revises:
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

EMBEDDING_DIM = 1024


def upgrade():
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # lark_configs
    op.create_table(
        "lark_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("app_id", sa.String(200), nullable=False),
        sa.Column("app_secret", sa.Text, nullable=False),
        sa.Column("encrypt_key", sa.String(200), server_default=""),
        sa.Column("verification_token", sa.String(200), server_default=""),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # lark_assets
    op.create_table(
        "lark_assets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("config_id", UUID(as_uuid=True), nullable=False),
        sa.Column("asset_type", sa.String(50), nullable=False),
        sa.Column("asset_token", sa.String(200), nullable=False),
        sa.Column("asset_name", sa.String(300), server_default=""),
        sa.Column("table_id", sa.String(200), server_default=""),
        sa.Column("field_mapping", JSONB, server_default="{}"),
        sa.Column("cron_expression", sa.String(100), server_default="0 */6 * * *"),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # document_versions
    op.create_table(
        "document_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("doc_token", sa.String(200), nullable=False, index=True),
        sa.Column("title", sa.String(500), server_default=""),
        sa.Column("content", sa.Text, server_default=""),
        sa.Column("content_hash", sa.String(64), server_default=""),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("last_updated", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # agent_sessions
    op.create_table(
        "agent_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("thread_id", sa.String(200), unique=True, nullable=False),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), server_default="running"),
        sa.Column("user_input", sa.Text, server_default=""),
        sa.Column("result_summary", sa.Text, server_default=""),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("agent_sessions")
    op.drop_table("document_versions")
    op.drop_table("lark_assets")
    op.drop_table("lark_configs")
    op.execute("DROP EXTENSION IF EXISTS vector")
