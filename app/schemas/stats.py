from pydantic import BaseModel

from app.domain.enums import TaskPriority, TaskStatus


class StatsOut(BaseModel):
    total: int
    by_status: dict[TaskStatus, int]
    by_priority: dict[TaskPriority, int]
    overdue: int
    active: int