import asyncio
import logging
from datetime import UTC, datetime

from app.db.session import SessionLocal
from app.repositories.task_repo import TaskRepository

logger = logging.getLogger(__name__)


async def cancel_overdue_once(session_factory=SessionLocal) -> int:
    async with session_factory() as session:
        count = await TaskRepository(session).cancel_overdue(datetime.now(UTC))
        await session.commit()
    if count:
        logger.info("Auto-cancelled %d overdue task(s)", count)
    return count


async def run(interval: int) -> None:
    logger.info("Overdue worker started (interval=%ss)", interval)
    while True:
        try:
            await cancel_overdue_once()
        except Exception:
            logger.exception("Overdue worker iteration failed")
        await asyncio.sleep(interval)
