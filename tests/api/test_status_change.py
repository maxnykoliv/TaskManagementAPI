from tests.utils import create_task, force_deadline_past, iso_in, set_status


async def test_full_happy_path(client, alice, bob):
    t = await create_task(client, alice["headers"], assignee_id=bob["id"])
    for status in ("IN_PROGRESS", "REVIEW", "DONE"):
        r = await set_status(client, alice["headers"], t["id"], status)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == status


async def test_assignee_can_change_status(client, alice, bob):
    t = await create_task(client, alice["headers"], assignee_id=bob["id"])
    r = await set_status(client, bob["headers"], t["id"], "IN_PROGRESS")
    assert r.status_code == 200


async def test_backward_transition_fails(client, alice):
    t = await create_task(client, alice["headers"])
    await set_status(client, alice["headers"], t["id"], "IN_PROGRESS")
    r = await set_status(client, alice["headers"], t["id"], "BACKLOG")
    assert r.status_code == 409


async def test_skipping_status_fails(client, alice):
    t = await create_task(client, alice["headers"])
    r = await set_status(client, alice["headers"], t["id"], "DONE")
    assert r.status_code == 409


async def test_done_requires_assignee(client, alice):
    t = await create_task(client, alice["headers"])
    await set_status(client, alice["headers"], t["id"], "IN_PROGRESS")
    await set_status(client, alice["headers"], t["id"], "REVIEW")
    r = await set_status(client, alice["headers"], t["id"], "DONE")
    assert r.status_code == 422


async def test_done_fails_when_deadline_expired(
    client, session_maker, alice, bob
):
    t = await create_task(
        client, alice["headers"], assignee_id=bob["id"], deadline=iso_in(hours=1)
    )
    await set_status(client, alice["headers"], t["id"], "IN_PROGRESS")
    await set_status(client, alice["headers"], t["id"], "REVIEW")
    await force_deadline_past(session_maker, t["id"])

    r = await set_status(client, alice["headers"], t["id"], "DONE")
    assert r.status_code == 422


async def test_cannot_change_assignee_in_review(client, alice, bob, carol):
    t = await create_task(client, alice["headers"], assignee_id=bob["id"])
    await set_status(client, alice["headers"], t["id"], "IN_PROGRESS")
    await set_status(client, alice["headers"], t["id"], "REVIEW")

    r = await client.patch(
        f"/api/v1/tasks/{t['id']}",
        json={"assignee_id": carol["id"]},
        headers=alice["headers"],
    )
    assert r.status_code == 422


async def test_can_change_assignee_in_progress(client, alice, bob, carol):
    t = await create_task(client, alice["headers"], assignee_id=bob["id"])
    await set_status(client, alice["headers"], t["id"], "IN_PROGRESS")

    r = await client.patch(
        f"/api/v1/tasks/{t['id']}",
        json={"assignee_id": carol["id"]},
        headers=alice["headers"],
    )
    assert r.status_code == 200
    assert r.json()["assignee_id"] == carol["id"]