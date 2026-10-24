from datetime import datetime

from sqlalchemy import and_, case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import TaskPriority, TaskStatus
from app.domain.status_machine import ACTIVE_STATUSES, FINAL_STATUSES
from app.models.task import Task
from app.schemas.task import TaskFilters

PRIORITY_RANK = case(
    (Task.priority == TaskPriority.HIGH, 3),
    (Task.priority == TaskPriority.MEDIUM, 2),
    else_=1,
)


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, task_id: int) -> Task | None:
        return await self.session.get(Task, task_id)

    async def get_for_update(self, task_id: int) -> Task | None:
        result = await self.session.execute(
            select(Task)
            .where(Task.id == task_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def add(self, task: Task) -> Task:
        self.session.add(task)
        await self.session.flush()
        return task

    async def delete(self, task: Task) -> None:
        await self.session.delete(task)

    @staticmethod
    def _apply_filters(stmt, f: TaskFilters):
        if f.search:
            stmt = stmt.where(
                or_(
                    Task.title.icontains(f.search, autoescape=True),
                    Task.description.icontains(f.search, autoescape=True),
                )
            )
        if f.status:
            stmt = stmt.where(Task.status == f.status)
        if f.priority:
            stmt = stmt.where(Task.priority == f.priority)
        if f.assignee_id is not None:
            stmt = stmt.where(Task.assignee_id == f.assignee_id)
        if f.deadline_from:
            stmt = stmt.where(Task.deadline >= f.deadline_from)
        if f.deadline_to:
            stmt = stmt.where(Task.deadline <= f.deadline_to)
        return stmt

    @staticmethod
    def _ordering(f: TaskFilters) -> list:
        if f.sort_by is None:
            return [PRIORITY_RANK.desc(), Task.deadline.asc().nulls_last(), Task.id]

        column = {
            "priority": PRIORITY_RANK,
            "deadline": Task.deadline,
            "created_at": Task.created_at,
        }[f.sort_by]
        expr = column.asc() if f.order == "asc" else column.desc()
        if f.sort_by == "deadline":
            expr = expr.nulls_last()
        return [expr, Task.id]

    async def list_tasks(self, f: TaskFilters) -> tuple[list[Task], int]:
        base = self._apply_filters(select(Task), f)
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        stmt = (
            base.order_by(*self._ordering(f))
            .limit(f.size)
            .offset((f.page - 1) * f.size)
        )
        items = (await self.session.scalars(stmt)).all()
        return list(items), total or 0

    async def count_active_for_assignee(
        self, user_id: int, exclude_task_id: int | None = None
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Task)
            .where(Task.assignee_id == user_id, Task.status.in_(ACTIVE_STATUSES))
        )
        if exclude_task_id is not None:
            stmt = stmt.where(Task.id != exclude_task_id)
        return await self.session.scalar(stmt) or 0

    async def list_overdue(self, now: datetime) -> list[Task]:
        stmt = (
            select(Task)
            .where(Task.deadline < now, Task.status.not_in(FINAL_STATUSES))
            .order_by(Task.deadline.asc(), Task.id)
        )
        return list((await self.session.scalars(stmt)).all())

    async def cancel_overdue(self, now: datetime) -> int:
        result = await self.session.execute(
            update(Task)
            .where(Task.deadline < now, Task.status.not_in(FINAL_STATUSES))
            .values(status=TaskStatus.CANCELLED, updated_at=func.now())
        )
        return result.rowcount

    async def stats(self, now: datetime) -> dict:
        total, active, overdue = (
            await self.session.execute(
                select(
                    func.count(Task.id),
                    func.count(Task.id).filter(Task.status.in_(ACTIVE_STATUSES)),
                    func.count(Task.id).filter(
                        and_(Task.deadline < now, Task.status.not_in(FINAL_STATUSES))
                    ),
                )
            )
        ).one()
        by_status = dict(
            (
                await self.session.execute(
                    select(Task.status, func.count()).group_by(Task.status)
                )
            ).all()
        )
        by_priority = dict(
            (
                await self.session.execute(
                    select(Task.priority, func.count()).group_by(Task.priority)
                )
            ).all()
        )
        return {
            "total": total,
            "active": active,
            "overdue": overdue,
            "by_status": by_status,
            "by_priority": by_priority,
        }
