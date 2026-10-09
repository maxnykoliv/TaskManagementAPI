import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import comment, task, user  # noqa: F401


@pytest_asyncio.fixture
async def engine():
    url = settings.TEST_DATABASE_URL
    if not url or url == settings.DATABASE_URL:
        pytest.exit(
            "TEST_DATABASE_URL must be set and differ from DATABASE_URL", returncode=1
        )
    eng = create_async_engine(url, poolclass=NullPool)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def session_maker(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def client(session_maker):
    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _make_user(client: AsyncClient, name: str) -> dict:
    email = f"{name}@example.com"
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": name, "password": "password123"},
    )
    assert r.status_code == 201, r.text
    user_id = r.json()["id"]
    r = await client.post(
        "/api/v1/auth/login", data={"username": email, "password": "password123"}
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"id": user_id, "headers": {"Authorization": f"Bearer {token}"}}


@pytest_asyncio.fixture
async def alice(client):
    return await _make_user(client, "alice")


@pytest_asyncio.fixture
async def bob(client):
    return await _make_user(client, "bob")


@pytest_asyncio.fixture
async def carol(client):
    return await _make_user(client, "carol")