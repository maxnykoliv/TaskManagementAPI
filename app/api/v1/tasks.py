from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.api.deps import CurrentUser, TaskServiceDep
from app.schemas.common import Page
from app.schemas.stats import StatsOut
from app.schemas.task import (
    StatusChangeIn,
    TaskCreate,
    TaskFilters,
    TaskOut,
    TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskOut, status_code=201)
async def create_task(
    data: TaskCreate, service: TaskServiceDep, current_user: CurrentUser
):
    return await service.create(data, current_user)


@router.get("", response_model=Page[TaskOut])
async def list_tasks(
    filters: Annotated[TaskFilters, Query()],
    service: TaskServiceDep,
    current_user: CurrentUser,
):
    items, total = await service.list_tasks(filters)
    return Page[TaskOut].create(
        items=[TaskOut.model_validate(t) for t in items],
        total=total,
        page=filters.page,
        size=filters.size,
    )


# Static paths must be registered before "/{task_id}"
@router.get("/overdue", response_model=list[TaskOut])
async def overdue_tasks(service: TaskServiceDep, current_user: CurrentUser):
    return await service.overdue()


@router.get("/stats", response_model=StatsOut)
async def tasks_stats(service: TaskServiceDep, current_user: CurrentUser):
    return await service.stats()


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, service: TaskServiceDep, current_user: CurrentUser):
    return await service.get(task_id)


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    service: TaskServiceDep,
    current_user: CurrentUser,
):
    return await service.update(task_id, data, current_user)


@router.patch("/{task_id}/status", response_model=TaskOut)
async def change_task_status(
    task_id: int,
    data: StatusChangeIn,
    service: TaskServiceDep,
    current_user: CurrentUser,
):
    return await service.change_status(task_id, data.status, current_user)


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int, service: TaskServiceDep, current_user: CurrentUser):
    await service.delete(task_id, current_user)
    return Response(status_code=204)
