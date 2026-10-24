from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.domain.enums import TaskPriority, TaskStatus
from app.domain.status_machine import FINAL_STATUSES, can_transition
from app.models.task import Task
from app.models.user import User
from app.repositories.task_repo import TaskRepository
from app.repositories.user_repo import UserRepository
from app.schemas.stats import StatsOut
from app.schemas.task import TaskCreate, TaskFilters, TaskUpdate

MAX_ACTIVE_TASKS = 10
NON_NULLABLE_FIELDS = {"title", "priority"}


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


class TaskService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.tasks = TaskRepository(session)
        self.users = UserRepository(session)

    @staticmethod
    def _ensure_participant(task: Task, user: User) -> None:
        if user.id not in (task.author_id, task.assignee_id):
            raise ForbiddenError("Only the author or the assignee can modify this task")

    @staticmethod
    def _validate_deadline(deadline: datetime) -> datetime:
        deadline = _aware(deadline)
        if deadline < _now():
            raise BusinessRuleError("Deadline cannot be in the past")
        return deadline

    async def _ensure_can_assign(
        self, assignee_id: int, exclude_task_id: int | None = None
    ) -> None:
        user = await self.users.get_for_update(assignee_id)
        if user is None or not user.is_active:
            raise NotFoundError("Assignee not found")
        active = await self.tasks.count_active_for_assignee(
            assignee_id, exclude_task_id
        )
        if active >= MAX_ACTIVE_TASKS:
            raise ConflictError(f"User already has {MAX_ACTIVE_TASKS} active tasks")

    async def _get_locked(self, task_id: int) -> Task:
        task = await self.tasks.get_for_update(task_id)
        if task is None:
            raise NotFoundError("Task not found")
        return task

    async def create(self, data: TaskCreate, author: User) -> Task:
        deadline = self._validate_deadline(data.deadline) if data.deadline else None
        if data.assignee_id is not None:
            await self._ensure_can_assign(data.assignee_id)

        task = Task(
            title=data.title,
            description=data.description,
            priority=data.priority,
            status=TaskStatus.BACKLOG,
            assignee_id=data.assignee_id,
            author_id=author.id,
            deadline=deadline,
        )
        await self.tasks.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get(self, task_id: int) -> Task:
        task = await self.tasks.get(task_id)
        if task is None:
            raise NotFoundError("Task not found")
        return task

    async def list_tasks(self, filters: TaskFilters) -> tuple[list[Task], int]:
        return await self.tasks.list_tasks(filters)

    async def update(self, task_id: int, data: TaskUpdate, user: User) -> Task:
        task = await self._get_locked(task_id)
        self._ensure_participant(task, user)

        if task.status in FINAL_STATUSES:
            raise ConflictError(f"Task in status {task.status.value} cannot be edited")

        fields = data.model_dump(exclude_unset=True)
        for name in NON_NULLABLE_FIELDS:
            if name in fields and fields[name] is None:
                raise BusinessRuleError(f"Field '{name}' cannot be null")

        if fields.get("deadline") is not None:
            new_deadline = _aware(fields["deadline"])
            if task.deadline is None or new_deadline != task.deadline:
                fields["deadline"] = self._validate_deadline(new_deadline)
            else:
                fields.pop("deadline")

        if "assignee_id" in fields and fields["assignee_id"] != task.assignee_id:
            if task.status == TaskStatus.REVIEW:
                raise BusinessRuleError(
                    "Assignee cannot be changed after the task reached Review"
                )
            if fields["assignee_id"] is not None:
                await self._ensure_can_assign(fields["assignee_id"], task.id)

        for name, value in fields.items():
            setattr(task, name, value)

        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def change_status(
        self, task_id: int, new_status: TaskStatus, user: User
    ) -> Task:
        task = await self._get_locked(task_id)
        self._ensure_participant(task, user)

        if not can_transition(task.status, new_status):
            raise ConflictError(
                f"Transition {task.status.value} -> {new_status.value} is not allowed"
            )

        if new_status == TaskStatus.DONE:
            if task.assignee_id is None:
                raise BusinessRuleError("Task without an assignee cannot be Done")
            if task.deadline is not None and task.deadline < _now():
                raise BusinessRuleError("Task with an expired deadline cannot be Done")

        task.status = new_status
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def delete(self, task_id: int, user: User) -> None:
        task = await self._get_locked(task_id)
        self._ensure_participant(task, user)

        if task.status in (TaskStatus.IN_PROGRESS, TaskStatus.REVIEW):
            raise ConflictError(
                "Task in progress or review cannot be deleted. "
                "Cancel or complete it first"
            )
        await self.tasks.delete(task)
        await self.session.commit()

    async def overdue(self) -> list[Task]:
        return await self.tasks.list_overdue(_now())

    async def stats(self) -> StatsOut:
        raw = await self.tasks.stats(_now())
        by_status = {s: raw["by_status"].get(s, 0) for s in TaskStatus}
        by_priority = {p: raw["by_priority"].get(p, 0) for p in TaskPriority}
        return StatsOut(
            total=raw["total"],
            by_status=by_status,
            by_priority=by_priority,
            overdue=raw["overdue"],
            active=raw["active"],
        )
