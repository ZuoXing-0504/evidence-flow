from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.research.service import execute_research_task


class JobDispatcher(Protocol):
    async def enqueue_research(self, task_id: UUID) -> None: ...


class RedisJobDispatcher:
    def __init__(self, redis_url: str) -> None:
        self.redis_settings = RedisSettings.from_dsn(redis_url)

    async def enqueue_research(self, task_id: UUID) -> None:
        redis = await create_pool(self.redis_settings)
        try:
            await redis.enqueue_job("run_research_task_job", str(task_id), _job_id=str(task_id))
        finally:
            await redis.aclose()


async def run_research_task_job(_: dict[str, Any], task_id: str) -> None:
    await execute_research_task(UUID(task_id))


class WorkerSettings:
    functions = [run_research_task_job]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 4
    job_timeout = 60 * 30


def get_job_dispatcher() -> JobDispatcher:
    return RedisJobDispatcher(get_settings().redis_url)
