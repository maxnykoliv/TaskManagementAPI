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


async def test_duplicate_username_rejected(client, alice):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "username": "alice", "password": "x" * 8},
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "Username already taken"


async def test_email_is_case_insensitive(client, alice):
    r = await client.post(
        "/api/v1/auth/login",
        data={"username": "ALICE@Example.com", "password": "password123"},
    )
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"


async def test_unknown_email_is_indistinguishable_from_wrong_password(client, alice):
    wrong_password = await client.post(
        "/api/v1/auth/login",
        data={"username": "alice@example.com", "password": "wrong-password"},
    )
    unknown_email = await client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@example.com", "password": "wrong-password"},
    )
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


async def test_invalid_token_rejected(client):
    r = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


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
