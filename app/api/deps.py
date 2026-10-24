from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.auth_service import AuthService
from app.services.comment_service import CommentService
from app.services.task_service import TaskService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_comment_service(db: DbSession) -> CommentService:
    return CommentService(db)


CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]


def get_task_service(db: DbSession) -> TaskService:
    return TaskService(db)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: DbSession
) -> User:
    user_id = decode_access_token(token)
    if user_id is None:
        raise UnauthorizedError()
    user = await UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(db)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
