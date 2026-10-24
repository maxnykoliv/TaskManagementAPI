from tests.utils import create_task, iso_in, set_status


async def test_create_task_defaults(client, alice):
    t = await create_task(client, alice["headers"], title="Write report")
    assert t["status"] == "BACKLOG"
    assert t["priority"] == "MEDIUM"
    assert t["author_id"] == alice["id"]
    assert t["assignee_id"] is None


async def test_create_with_past_deadline_fails(client, alice):
    r = await client.post(
        "/api/v1/tasks",
        json={"title": "Old", "deadline": iso_in(hours=-1)},
        headers=alice["headers"],
    )
    assert r.status_code == 422


async def test_update_task(client, alice):
    t = await create_task(client, alice["headers"], title="Old title")
    r = await client.patch(
        f"/api/v1/tasks/{t['id']}",
        json={"title": "New title", "priority": "HIGH"},
        headers=alice["headers"],
    )
    assert r.status_code == 200
    assert r.json()["title"] == "New title"
    assert r.json()["priority"] == "HIGH"


async def test_update_with_past_deadline_fails(client, alice):
    t = await create_task(client, alice["headers"])
    r = await client.patch(
        f"/api/v1/tasks/{t['id']}",
        json={"deadline": iso_in(hours=-1)},
        headers=alice["headers"],
    )
    assert r.status_code == 422


async def test_status_cannot_be_changed_via_patch(client, alice):
    t = await create_task(client, alice["headers"])
    r = await client.patch(
        f"/api/v1/tasks/{t['id']}",
        json={"status": "DONE"},
        headers=alice["headers"],
    )
    assert r.status_code == 422
    r = await client.get(f"/api/v1/tasks/{t['id']}", headers=alice["headers"])
    assert r.json()["status"] == "BACKLOG"


async def test_final_status_task_is_not_editable(client, alice):
    t = await create_task(client, alice["headers"])
    await set_status(client, alice["headers"], t["id"], "CANCELLED")
    r = await client.patch(
        f"/api/v1/tasks/{t['id']}", json={"title": "x"}, headers=alice["headers"]
    )
    assert r.status_code == 409


async def test_delete_backlog_task(client, alice):
    t = await create_task(client, alice["headers"])
    r = await client.delete(f"/api/v1/tasks/{t['id']}", headers=alice["headers"])
    assert r.status_code == 204
    r = await client.get(f"/api/v1/tasks/{t['id']}", headers=alice["headers"])
    assert r.status_code == 404


async def test_cannot_delete_in_progress_task(client, alice):
    t = await create_task(client, alice["headers"])
    await set_status(client, alice["headers"], t["id"], "IN_PROGRESS")
    r = await client.delete(f"/api/v1/tasks/{t['id']}", headers=alice["headers"])
    assert r.status_code == 409
    await set_status(client, alice["headers"], t["id"], "CANCELLED")
    r = await client.delete(f"/api/v1/tasks/{t['id']}", headers=alice["headers"])
    assert r.status_code == 204


async def test_unrelated_user_cannot_modify(client, alice, bob):
    t = await create_task(client, alice["headers"])
    r = await client.patch(
        f"/api/v1/tasks/{t['id']}", json={"title": "hack"}, headers=bob["headers"]
    )
    assert r.status_code == 403


async def test_get_missing_task_returns_404(client, alice):
    r = await client.get("/api/v1/tasks/99999", headers=alice["headers"])
    assert r.status_code == 404


async def test_active_tasks_limit_is_ten(client, alice, bob):
    ids = []
    for i in range(10):
        t = await create_task(
            client, alice["headers"], title=f"T{i}", assignee_id=bob["id"]
        )
        ids.append(t["id"])

    r = await client.post(
        "/api/v1/tasks",
        json={"title": "T11", "assignee_id": bob["id"]},
        headers=alice["headers"],
    )
    assert r.status_code == 409

    await set_status(client, alice["headers"], ids[0], "CANCELLED")
    r = await client.post(
        "/api/v1/tasks",
        json={"title": "T11", "assignee_id": bob["id"]},
        headers=alice["headers"],
    )
    assert r.status_code == 201


async def test_default_sorting_priority_then_deadline(client, alice):
    h = alice["headers"]
    await create_task(client, h, title="A", priority="LOW", deadline=iso_in(days=1))
    await create_task(client, h, title="B", priority="HIGH", deadline=iso_in(days=3))
    await create_task(client, h, title="C", priority="HIGH", deadline=iso_in(days=2))
    await create_task(client, h, title="D", priority="MEDIUM")

    r = await client.get("/api/v1/tasks", headers=h)
    assert [t["title"] for t in r.json()["items"]] == ["C", "B", "D", "A"]


async def test_sort_by_deadline_desc(client, alice):
    h = alice["headers"]
    await create_task(client, h, title="A", deadline=iso_in(days=1))
    await create_task(client, h, title="B", deadline=iso_in(days=2))
    r = await client.get("/api/v1/tasks?sort_by=deadline&order=desc", headers=h)
    assert [t["title"] for t in r.json()["items"]] == ["B", "A"]


async def test_search_and_filters(client, alice, bob):
    h = alice["headers"]
    await create_task(client, h, title="Quarterly report", priority="HIGH")
    await create_task(client, h, title="Other", description="contains REPORT text")
    await create_task(client, h, title="Unrelated", assignee_id=bob["id"])

    r = await client.get("/api/v1/tasks?search=report", headers=h)
    assert r.json()["total"] == 2

    r = await client.get("/api/v1/tasks?priority=HIGH", headers=h)
    assert r.json()["total"] == 1

    r = await client.get(f"/api/v1/tasks?assignee_id={bob['id']}", headers=h)
    assert [t["title"] for t in r.json()["items"]] == ["Unrelated"]

    r = await client.get("/api/v1/tasks?status=DONE", headers=h)
    assert r.json()["total"] == 0


async def test_deadline_range_filter(client, alice):
    h = alice["headers"]
    await create_task(client, h, title="soon", deadline=iso_in(days=1))
    await create_task(client, h, title="later", deadline=iso_in(days=10))
    await create_task(client, h, title="no deadline")

    r = await client.get(
        "/api/v1/tasks",
        params={"deadline_from": iso_in(days=5), "deadline_to": iso_in(days=20)},
        headers=h,
    )
    assert [t["title"] for t in r.json()["items"]] == ["later"]


async def test_unknown_query_param_rejected(client, alice):
    r = await client.get("/api/v1/tasks?colour=red", headers=alice["headers"])
    assert r.status_code == 422


async def test_pagination(client, alice):
    h = alice["headers"]
    for i in range(5):
        await create_task(client, h, title=f"T{i}")

    r = await client.get("/api/v1/tasks?page=2&size=2", headers=h)
    body = r.json()
    assert body["total"] == 5
    assert body["pages"] == 3
    assert body["page"] == 2
    assert len(body["items"]) == 2
