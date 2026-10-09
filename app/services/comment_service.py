from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.comment import Comment
from app.models.user import User
from app.repositories.comment_repo import CommentRepository
from app.repositories.task_repo import TaskRepository
from app.schemas.comment import CommentCreate


class CommentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.comments = CommentRepository(session)
        self.tasks = TaskRepository(session)

    async def _ensure_task_exists(self, task_id: int) -> None:
        if await self.tasks.get(task_id) is None:
            raise NotFoundError("Task not found")

    async def create(self, task_id: int, data: CommentCreate, author: User) -> Comment:
        await self._ensure_task_exists(task_id)
        comment = Comment(task_id=task_id, author_id=author.id, text=data.text)
        await self.comments.add(comment)
        await self.session.commit()
        await self.session.refresh(comment)
        return comment

    async def list_for_task(
        self, task_id: int, page: int, size: int
    ) -> tuple[list[Comment], int]:
        await self._ensure_task_exists(task_id)
        return await self.comments.list_for_task(task_id, page, size)