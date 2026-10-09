from datetime import datetime, timedelta, timezone

from sqlalchemy import update

from app.models.task import Task


def iso_in(**delta) -> str:
    return (datetime.now(timezone.utc) + timedelta(**delta)).isoformat()


async def create_task(client, headers: dict, **overrides) -> dict:
    payload = {"title": "Task"} | overrides
    r = await client.post("/api/v1/tasks", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


async def set_status(client, headers: dict, task_id: int, status: str):
    return await client.patch(
        f"/api/v1/tasks/{task_id}/status", json={"status": status}, headers=headers
    )


async def force_deadline_past(session_maker, task_id: int) -> None:
    async with session_maker() as session:
        await session.execute(
            update(Task)
            .where(Task.id == task_id)
            .values(deadline=datetime.now(timezone.utc) - timedelta(hours=1))
        )
        await session.commit()