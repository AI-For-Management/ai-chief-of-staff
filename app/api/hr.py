"""人事管理API — 员工CRUD + 指标查询 + 排行榜"""
import logging
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.employee import Employee, EmployeeMetrics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/hr", tags=["hr"])


# ===== Schemas =====

class EmployeeCreate(BaseModel):
    name: str
    employee_id: str
    department: str = ""
    position: str = ""
    feishu_open_id: str = ""
    skills: dict = {}


class EmployeeResponse(BaseModel):
    id: UUID
    name: str
    employee_id: str
    department: str
    position: str
    skills: dict
    is_active: bool
    model_config = {"from_attributes": True}


class MetricsResponse(BaseModel):
    employee_id: UUID
    period_type: str
    period_date: str
    tasks_completed: int
    tasks_assigned: int
    completion_rate: float
    contribution_score: float
    workload_score: float
    quality_score: float
    model_config = {"from_attributes": True}


class LeaderboardEntry(BaseModel):
    rank: int
    name: str
    department: str
    contribution_score: float
    tasks_completed: int
    completion_rate: float


# ===== 员工CRUD =====

@router.post("/employees", response_model=EmployeeResponse)
async def create_employee(data: EmployeeCreate, db: AsyncSession = Depends(get_db)):
    emp = Employee(**data.model_dump())
    db.add(emp)
    await db.commit()
    await db.refresh(emp)
    return emp


@router.get("/employees", response_model=list[EmployeeResponse])
async def list_employees(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Employee).where(Employee.is_active == True).order_by(Employee.name))
    return result.scalars().all()


@router.get("/employees/{emp_id}")
async def get_employee_detail(emp_id: UUID, db: AsyncSession = Depends(get_db)):
    emp = await db.get(Employee, emp_id)
    if not emp:
        raise HTTPException(404, "员工不存在")

    # 获取最新各周期指标
    metrics = {}
    for period in ["daily", "weekly", "monthly", "yearly"]:
        result = await db.execute(
            select(EmployeeMetrics)
            .where(EmployeeMetrics.employee_id == emp_id, EmployeeMetrics.period_type == period)
            .order_by(desc(EmployeeMetrics.period_date))
            .limit(1)
        )
        m = result.scalar_one_or_none()
        if m:
            metrics[period] = {
                "period_date": m.period_date,
                "tasks_completed": m.tasks_completed,
                "tasks_assigned": m.tasks_assigned,
                "completion_rate": m.completion_rate,
                "contribution_score": m.contribution_score,
                "workload_score": m.workload_score,
                "quality_score": m.quality_score,
            }

    return {
        "employee": EmployeeResponse.model_validate(emp).model_dump(),
        "metrics": metrics,
    }


@router.delete("/employees/{emp_id}")
async def delete_employee(emp_id: UUID, db: AsyncSession = Depends(get_db)):
    emp = await db.get(Employee, emp_id)
    if not emp:
        raise HTTPException(404, "员工不存在")
    emp.is_active = False
    await db.commit()
    return {"status": "deactivated"}


# ===== 排行榜 =====

@router.get("/leaderboard/{period_type}", response_model=list[LeaderboardEntry])
async def get_leaderboard(period_type: str, period_date: str = "", db: AsyncSession = Depends(get_db)):
    """
    获取贡献排行榜
    period_type: daily | weekly | monthly | yearly
    period_date: 可选，默认取最新一期
    """
    if period_type not in ("daily", "weekly", "monthly", "yearly"):
        raise HTTPException(400, "period_type 必须是 daily/weekly/monthly/yearly")

    # 如果没指定日期，取最新一期
    if not period_date:
        result = await db.execute(
            select(EmployeeMetrics.period_date)
            .where(EmployeeMetrics.period_type == period_type)
            .order_by(desc(EmployeeMetrics.period_date))
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if not row:
            return []
        period_date = row

    # 查询该期所有员工指标，按贡献分排序
    result = await db.execute(
        select(EmployeeMetrics, Employee)
        .join(Employee, Employee.id == EmployeeMetrics.employee_id)
        .where(
            EmployeeMetrics.period_type == period_type,
            EmployeeMetrics.period_date == period_date,
            Employee.is_active == True,
        )
        .order_by(desc(EmployeeMetrics.contribution_score))
    )

    entries = []
    for i, (m, emp) in enumerate(result.all(), 1):
        entries.append(LeaderboardEntry(
            rank=i,
            name=emp.name,
            department=emp.department,
            contribution_score=m.contribution_score,
            tasks_completed=m.tasks_completed,
            completion_rate=m.completion_rate,
        ))

    return entries


# ===== 指标概览（侧边栏用） =====

@router.get("/summary")
async def hr_summary(db: AsyncSession = Depends(get_db)):
    """人事概览数据"""
    # 员工总数
    result = await db.execute(select(Employee).where(Employee.is_active == True))
    employees = result.scalars().all()
    total = len(employees)

    # 最新月度平均贡献分
    from sqlalchemy import func as sqlfunc
    result = await db.execute(
        select(
            sqlfunc.avg(EmployeeMetrics.contribution_score),
            sqlfunc.avg(EmployeeMetrics.completion_rate),
            sqlfunc.avg(EmployeeMetrics.workload_score),
        )
        .where(EmployeeMetrics.period_type == "monthly")
    )
    row = result.one_or_none()
    avg_contribution = round(row[0] or 0, 1)
    avg_completion = round((row[1] or 0) * 100, 1)
    avg_workload = round(row[2] or 0, 1)

    return {
        "total_employees": total,
        "avg_contribution": avg_contribution,
        "avg_completion_pct": avg_completion,
        "avg_workload": avg_workload,
    }


@router.post("/metrics/refresh")
async def refresh_metrics():
    """手动触发员工指标更新"""
    from app.workers.hr_tasks import update_employee_metrics
    task = update_employee_metrics.delay()
    return {"task_id": task.id, "status": "submitted"}


# ===== 员工图谱 =====

class ProfileGenerateRequest(BaseModel):
    resume_text: str = ""


@router.post("/employees/{emp_id}/profile/generate")
async def generate_employee_profile(emp_id: UUID, req: ProfileGenerateRequest):
    """为员工生成多维能力图谱"""
    from app.agents.profile_graph import generate_profile
    profile = await generate_profile(str(emp_id), req.resume_text)
    return {"employee_id": str(emp_id), "profile": profile}


@router.get("/employees/{emp_id}/profile")
async def get_employee_profile(emp_id: UUID, db: AsyncSession = Depends(get_db)):
    """获取员工图谱"""
    from app.models import Employee
    emp = await db.get(Employee, emp_id)
    if not emp:
        raise HTTPException(404, "员工不存在")
    return {"employee_id": str(emp_id), "name": emp.name, "profile": emp.profile_data or {}}
