from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: int | None = None
    deadline: datetime | None = None


class TaskUpdate(BaseModel):
    # status is deliberately absent: it only changes via PATCH /tasks/{id}/status
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    priority: TaskPriority | None = None
    assignee_id: int | None = None
    deadline: datetime | None = None


class StatusChangeIn(BaseModel):
    status: TaskStatus


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assignee_id: int | None
    author_id: int
    deadline: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    search: str | None = Field(default=None, min_length=1, max_length=100)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: int | None = None
    deadline_from: datetime | None = None
    deadline_to: datetime | None = None
    sort_by: Literal["created_at", "deadline", "priority"] | None = None
    order: Literal["asc", "desc"] = "asc"
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
