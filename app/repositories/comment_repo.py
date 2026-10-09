from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment


class CommentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, comment: Comment) -> Comment:
        self.session.add(comment)
        await self.session.flush()
        return comment

    async def list_for_task(
        self, task_id: int, page: int, size: int
    ) -> tuple[list[Comment], int]:
        total = await self.session.scalar(
            select(func.count()).select_from(Comment).where(Comment.task_id == task_id)
        )
        stmt = (
            select(Comment)
            .where(Comment.task_id == task_id)
            .order_by(Comment.created_at.asc(), Comment.id)
            .limit(size)
            .offset((page - 1) * size)
        )
        items = (await self.session.scalars(stmt)).all()
        return list(items), total or 0