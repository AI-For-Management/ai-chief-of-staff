"""项目模块 Pydantic 模型"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class Milestone(BaseModel):
    date: str  # YYYY-MM-DD
    title: str
    status: str = "pending"  # pending|done|delayed


class TimelineEvent(BaseModel):
    time: str
    event: str
    author: str = ""


class ProjectMemberInput(BaseModel):
    employee_id: UUID
    role: str = ""
    responsibilities: str = ""


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    owner_id: UUID | None = None
    status: str = "planning"
    start_date: datetime | None = None
    end_date: datetime | None = None
    milestones: list[Milestone] = []
    members: list[ProjectMemberInput] = []


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    owner_id: UUID | None = None
    status: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    milestones: list[Milestone] | None = None


class TimelineAdd(BaseModel):
    event: str
    author: str = ""


class ProjectMemberOut(BaseModel):
    id: UUID
    employee_id: UUID
    employee_name: str = ""
    role: str
    responsibilities: str
    model_config = {"from_attributes": True}


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str
    owner_id: UUID | None
    owner_name: str = ""
    status: str
    start_date: datetime | None
    end_date: datetime | None
    milestones: list = []
    timeline_events: list = []
    members: list[ProjectMemberOut] = []
    created_at: datetime
    model_config = {"from_attributes": True}
