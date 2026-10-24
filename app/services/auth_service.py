from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import RegisterIn


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)

    async def register(self, data: RegisterIn) -> User:
        email = data.email.lower()
        if await self.users.get_by_email(email):
            raise ConflictError("Email already registered")
        if await self.users.get_by_username(data.username):
            raise ConflictError("Username already taken")

        user = User(
            email=email,
            username=data.username,
            # Argon2 is CPU-bound by design; keep it off the event loop.
            hashed_password=await run_in_threadpool(hash_password, data.password),
        )
        try:
            await self.users.add(user)
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError(
                "User with this email or username already exists"
            ) from None
        return user

    async def login(self, email: str, password: str) -> str:
        user = await self.users.get_by_email(email.lower())
        hashed = user.hashed_password if user else DUMMY_PASSWORD_HASH
        password_ok = await run_in_threadpool(verify_password, password, hashed)
        if user is None or not password_ok:
            raise UnauthorizedError("Incorrect email or password")
        if not user.is_active:
            raise UnauthorizedError("User is inactive")
        return create_access_token(user.id)
