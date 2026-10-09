from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CommentServiceDep, CurrentUser
from app.schemas.comment import CommentCreate, CommentOut
from app.schemas.common import Page, PaginationParams

router = APIRouter(prefix="/tasks/{task_id}/comments", tags=["comments"])


@router.post("", response_model=CommentOut, status_code=201)
async def create_comment(
    task_id: int,
    data: CommentCreate,
    service: CommentServiceDep,
    current_user: CurrentUser,
):
    return await service.create(task_id, data, current_user)


@router.get("", response_model=Page[CommentOut])
async def list_comments(
    task_id: int,
    pagination: Annotated[PaginationParams, Query()],
    service: CommentServiceDep,
    current_user: CurrentUser,
):
    items, total = await service.list_for_task(
        task_id, pagination.page, pagination.size
    )
    return Page[CommentOut].create(
        items=[CommentOut.model_validate(c) for c in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )