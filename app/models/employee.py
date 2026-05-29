"""员工信息表"""
import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    employee_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="工号")
    department: Mapped[str] = mapped_column(String(100), default="")
    position: Mapped[str] = mapped_column(String(100), default="")
    feishu_open_id: Mapped[str] = mapped_column(String(200), default="", comment="飞书open_id")
    skills: Mapped[dict] = mapped_column(JSONB, default=dict, comment="技能标签及熟练度 {skill: level}")
    profile_data: Mapped[dict] = mapped_column(JSONB, default=dict, comment="员工多维图谱 JSON")
    is_active: Mapped[bool] = mapped_column(default=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EmployeeMetrics(Base):
    __tablename__ = "employee_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, comment="关联employees.id")
    period_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="daily|weekly|monthly|yearly")
    period_date: Mapped[str] = mapped_column(String(20), nullable=False, comment="2026-05-28 / 2026-W22 / 2026-05 / 2026")
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0, comment="完成任务数")
    tasks_assigned: Mapped[int] = mapped_column(Integer, default=0, comment="分配任务数")
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0, comment="完成率 0-1")
    contribution_score: Mapped[float] = mapped_column(Float, default=0.0, comment="贡献指数 0-100")
    workload_score: Mapped[float] = mapped_column(Float, default=0.0, comment="工作负荷 0-100")
    quality_score: Mapped[float] = mapped_column(Float, default=0.0, comment="质量评分 0-100")
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict, comment="扩展指标")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
