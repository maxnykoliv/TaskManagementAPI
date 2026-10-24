from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import AuthServiceDep, CurrentUser
from app.schemas.auth import RegisterIn, TokenOut
from app.schemas.user import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(data: RegisterIn, service: AuthServiceDep):
    return await service.register(data)


@router.post("/login", response_model=TokenOut)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], service: AuthServiceDep
):
    token = await service.login(form.username, form.password)
    return TokenOut(access_token=token)


@router.get("/me", response_model=UserOut)
async def me(current_user: CurrentUser):
    return current_user
