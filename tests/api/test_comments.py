from tests.utils import create_task, set_status


async def test_add_and_list_comments(client, alice, bob):
    t = await create_task(client, alice["headers"])
    url = f"/api/v1/tasks/{t['id']}/comments"

    r = await client.post(url, json={"text": "First"}, headers=alice["headers"])
    assert r.status_code == 201
    assert r.json()["author_id"] == alice["id"]
    await client.post(url, json={"text": "Second"}, headers=bob["headers"])

    r = await client.get(url, headers=alice["headers"])
    body = r.json()
    assert body["total"] == 2
    assert [c["text"] for c in body["items"]] == ["First", "Second"]

    r = await client.get(url + "?page=2&size=1", headers=alice["headers"])
    assert [c["text"] for c in r.json()["items"]] == ["Second"]


async def test_comment_on_missing_task_returns_404(client, alice):
    r = await client.post(
        "/api/v1/tasks/99999/comments", json={"text": "x"}, headers=alice["headers"]
    )
    assert r.status_code == 404


async def test_empty_comment_rejected(client, alice):
    t = await create_task(client, alice["headers"])
    r = await client.post(
        f"/api/v1/tasks/{t['id']}/comments", json={"text": ""}, headers=alice["headers"]
    )
    assert r.status_code == 422


async def test_can_comment_on_cancelled_task(client, alice):
    t = await create_task(client, alice["headers"])
    await set_status(client, alice["headers"], t["id"], "CANCELLED")
    r = await client.post(
        f"/api/v1/tasks/{t['id']}/comments",
        json={"text": "post-mortem"},
        headers=alice["headers"],
    )
    assert r.status_code == 201