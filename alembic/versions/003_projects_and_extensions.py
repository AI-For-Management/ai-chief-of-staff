"""add projects, project_members, employee.profile_data, doc_versions.metadata

Revision ID: 003
Revises: 002
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    # === 项目表 ===
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("owner_id", UUID(as_uuid=True), nullable=True, comment="负责人 employees.id"),
        sa.Column("status", sa.String(30), server_default="planning", comment="planning|in_progress|done|paused"),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("milestones", JSONB, server_default="[]", comment="[{date,title,status}]"),
        sa.Column("timeline_events", JSONB, server_default="[]", comment="[{time,event,author}]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_projects_status", "projects", ["status"])

    # === 项目成员表 ===
    op.create_table(
        "project_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(100), server_default=""),
        sa.Column("responsibilities", sa.Text, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_project_members_project", "project_members", ["project_id"])
    op.create_index("ix_project_members_employee", "project_members", ["employee_id"])

    # === employees 增加 profile_data ===
    op.add_column(
        "employees",
        sa.Column("profile_data", JSONB, server_default="{}", comment="员工多维图谱 JSON"),
    )

    # === document_versions 增加 metadata ===
    op.add_column(
        "document_versions",
        sa.Column("metadata", JSONB, server_default="{}", comment="知识库标签/分类"),
    )


def downgrade():
    op.drop_column("document_versions", "metadata")
    op.drop_column("employees", "profile_data")
    op.drop_index("ix_project_members_employee")
    op.drop_index("ix_project_members_project")
    op.drop_table("project_members")
    op.drop_index("ix_projects_status")
    op.drop_table("projects")
