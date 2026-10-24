import asyncio

import pytest

from app.background import overdue_worker
from app.background.overdue_worker import cancel_overdue_once
from tests.utils import create_task, force_deadline_past, iso_in, set_status


async def _setup_tasks(client, session_maker, headers):
    t1 = await create_task(client, headers, title="plain", priority="HIGH")
    t2 = await create_task(client, headers, title="cancelled", priority="LOW")
    t3 = await create_task(
        client, headers, title="overdue", priority="MEDIUM", deadline=iso_in(days=1)
    )
    await set_status(client, headers, t2["id"], "CANCELLED")
    await force_deadline_past(session_maker, t2["id"])
    await force_deadline_past(session_maker, t3["id"])
    return t1, t2, t3


async def test_overdue_endpoint(client, session_maker, alice):
    _, _, t3 = await _setup_tasks(client, session_maker, alice["headers"])
    r = await client.get("/api/v1/tasks/overdue", headers=alice["headers"])
    assert r.status_code == 200
    assert [t["id"] for t in r.json()] == [t3["id"]]


async def test_stats_endpoint(client, session_maker, alice):
    await _setup_tasks(client, session_maker, alice["headers"])
    r = await client.get("/api/v1/tasks/stats", headers=alice["headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert body["active"] == 2
    assert body["overdue"] == 1
    assert body["by_status"] == {
        "BACKLOG": 2,
        "IN_PROGRESS": 0,
        "REVIEW": 0,
        "DONE": 0,
        "CANCELLED": 1,
    }
    assert body["by_priority"] == {"LOW": 1, "MEDIUM": 1, "HIGH": 1}


async def test_background_worker_cancels_overdue(client, session_maker, alice):
    t1, _, t3 = await _setup_tasks(client, session_maker, alice["headers"])

    assert await cancel_overdue_once(session_maker) == 1

    r = await client.get(f"/api/v1/tasks/{t3['id']}", headers=alice["headers"])
    assert r.json()["status"] == "CANCELLED"
    r = await client.get(f"/api/v1/tasks/{t1['id']}", headers=alice["headers"])
    assert r.json()["status"] == "BACKLOG"

    # a second run is a no-op
    assert await cancel_overdue_once(session_maker) == 0


async def test_worker_survives_failed_iteration(monkeypatch):
    calls = 0

    async def flaky_iteration():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("database unavailable")
        if calls == 3:
            raise asyncio.CancelledError
        return 0

    monkeypatch.setattr(overdue_worker, "cancel_overdue_once", flaky_iteration)

    with pytest.raises(asyncio.CancelledError):
        await overdue_worker.run(interval=0)
    assert calls == 3
