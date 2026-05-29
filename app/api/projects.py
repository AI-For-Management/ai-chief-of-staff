"""项目管理 API"""
import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Project, ProjectMember, Employee
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ProjectMemberInput, ProjectMemberOut, TimelineAdd,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/projects", tags=["projects"])


async def _enrich_project(db: AsyncSession, p: Project) -> dict:
    """填充 owner_name 和 members 列表"""
    data = {
        "id": p.id, "name": p.name, "description": p.description,
        "owner_id": p.owner_id, "owner_name": "",
        "status": p.status, "start_date": p.start_date, "end_date": p.end_date,
        "milestones": p.milestones or [], "timeline_events": p.timeline_events or [],
        "created_at": p.created_at, "members": [],
    }
    if p.owner_id:
        owner = await db.get(Employee, p.owner_id)
        if owner:
            data["owner_name"] = owner.name

    result = await db.execute(
        select(ProjectMember, Employee.name)
        .outerjoin(Employee, Employee.id == ProjectMember.employee_id)
        .where(ProjectMember.project_id == p.id)
    )
    for member, emp_name in result.all():
        data["members"].append({
            "id": member.id, "employee_id": member.employee_id,
            "employee_name": emp_name or "", "role": member.role,
            "responsibilities": member.responsibilities,
        })
    return data


@router.post("", response_model=ProjectResponse)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    p = Project(
        name=data.name, description=data.description,
        owner_id=data.owner_id, status=data.status,
        start_date=data.start_date, end_date=data.end_date,
        milestones=[m.model_dump() for m in data.milestones],
        timeline_events=[],
    )
    db.add(p)
    await db.flush()

    for m in data.members:
        db.add(ProjectMember(
            project_id=p.id, employee_id=m.employee_id,
            role=m.role, responsibilities=m.responsibilities,
        ))
    await db.commit()
    await db.refresh(p)
    return await _enrich_project(db, p)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(status: str = "", db: AsyncSession = Depends(get_db)):
    stmt = select(Project).order_by(desc(Project.created_at))
    if status:
        stmt = stmt.where(Project.status == status)
    result = await db.execute(stmt)
    projects = result.scalars().all()
    return [await _enrich_project(db, p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    return await _enrich_project(db, p)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: UUID, data: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")

    payload = data.model_dump(exclude_unset=True)
    if "milestones" in payload and payload["milestones"] is not None:
        payload["milestones"] = [m.model_dump() if hasattr(m, "model_dump") else m for m in payload["milestones"]]

    for k, v in payload.items():
        if v is not None:
            setattr(p, k, v)
    await db.commit()
    await db.refresh(p)
    return await _enrich_project(db, p)


@router.delete("/{project_id}")
async def delete_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    # 删除关联成员
    members = await db.execute(select(ProjectMember).where(ProjectMember.project_id == project_id))
    for m in members.scalars().all():
        await db.delete(m)
    await db.delete(p)
    await db.commit()
    return {"status": "deleted"}


@router.post("/{project_id}/timeline")
async def add_timeline_event(project_id: UUID, data: TimelineAdd, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "项目不存在")
    events = list(p.timeline_events or [])
    events.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "event": data.event,
        "author": data.author,
    })
    p.timeline_events = events
    await db.commit()
    return {"status": "added", "events_count": len(events)}


@router.post("/{project_id}/members", response_model=ProjectMemberOut)
async def add_member(project_id: UUID, data: ProjectMemberInput, db: AsyncSession = Depends(get_db)):
    if not await db.get(Project, project_id):
        raise HTTPException(404, "项目不存在")
    m = ProjectMember(
        project_id=project_id, employee_id=data.employee_id,
        role=data.role, responsibilities=data.responsibilities,
    )
    db.add(m)
    await db.commit()
    await db.refresh(m)
    emp = await db.get(Employee, data.employee_id)
    return {
        "id": m.id, "employee_id": m.employee_id,
        "employee_name": emp.name if emp else "",
        "role": m.role, "responsibilities": m.responsibilities,
    }


@router.delete("/{project_id}/members/{member_id}")
async def remove_member(project_id: UUID, member_id: UUID, db: AsyncSession = Depends(get_db)):
    m = await db.get(ProjectMember, member_id)
    if not m or m.project_id != project_id:
        raise HTTPException(404, "成员不存在")
    await db.delete(m)
    await db.commit()
    return {"status": "removed"}
