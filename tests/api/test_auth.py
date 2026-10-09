async def test_register_and_duplicate(client):
    payload = {"email": "a@example.com", "username": "aaa", "password": "password123"}
    r = await client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 201
    assert "hashed_password" not in r.json()

    r = await client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 409


async def test_login_wrong_password(client, alice):
    r = await client.post(
        "/api/v1/auth/login",
        data={"username": "alice@example.com", "password": "wrong-password"},
    )
    assert r.status_code == 401


async def test_me_requires_token(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


async def test_me_returns_current_user(client, alice):
    r = await client.get("/api/v1/auth/me", headers=alice["headers"])
    assert r.status_code == 200
    assert r.json()["email"] == "alice@example.com"


async def test_tasks_require_auth(client):
    r = await client.get("/api/v1/tasks")
    assert r.status_code == 401