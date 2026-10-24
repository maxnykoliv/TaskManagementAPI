import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.background import overdue_worker
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = None
    if settings.OVERDUE_WORKER_ENABLED:
        worker = asyncio.create_task(
            overdue_worker.run(settings.OVERDUE_CHECK_INTERVAL)
        )
    yield
    if worker:
        worker.cancel()
        with suppress(asyncio.CancelledError):
            await worker
    await engine.dispose()


app = FastAPI(title="Task Management API", lifespan=lifespan)

register_exception_handlers(app)
app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
