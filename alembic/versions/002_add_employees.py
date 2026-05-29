"""add employees and employee_metrics tables

Revision ID: 002
Revises: 001
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "employees",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("employee_id", sa.String(50), unique=True, nullable=False),
        sa.Column("department", sa.String(100), server_default=""),
        sa.Column("position", sa.String(100), server_default=""),
        sa.Column("feishu_open_id", sa.String(200), server_default=""),
        sa.Column("skills", JSONB, server_default="{}"),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "employee_metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("employee_id", UUID(as_uuid=True), nullable=False),
        sa.Column("period_type", sa.String(20), nullable=False),
        sa.Column("period_date", sa.String(20), nullable=False),
        sa.Column("tasks_completed", sa.Integer, server_default="0"),
        sa.Column("tasks_assigned", sa.Integer, server_default="0"),
        sa.Column("completion_rate", sa.Float, server_default="0"),
        sa.Column("contribution_score", sa.Float, server_default="0"),
        sa.Column("workload_score", sa.Float, server_default="0"),
        sa.Column("quality_score", sa.Float, server_default="0"),
        sa.Column("extra_data", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 索引：按员工+周期快速查询
    op.create_index("ix_metrics_employee_period", "employee_metrics", ["employee_id", "period_type", "period_date"])


def downgrade():
    op.drop_index("ix_metrics_employee_period")
    op.drop_table("employee_metrics")
    op.drop_table("employees")
