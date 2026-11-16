from __future__ import annotations

import asyncio
from typing import cast
from uuid import UUID

import httpx

from app.core.config import get_settings
from app.db import Database, get_database
from app.domain import ResearchEvent, ResearchEventType, ResearchState, ResearchStatus
from app.research.adapters import build_research_runtime
from app.research.repository import ResearchRepository
from app.research.workflow import build_research_graph, create_initial_state


class ResearchCancelledError(Exception):
    pass


class DatabaseEventSink:
    def __init__(self, database: Database) -> None:
        self.database = database
        self._write_lock = asyncio.Lock()

    async def __call__(self, event: ResearchEvent) -> None:
        async with self._write_lock, self.database.sessions() as session:
            repository = ResearchRepository(session)
            if await repository.is_cancellation_requested(event.task_id):
                raise ResearchCancelledError
            await repository.add_event(event)
            await session.commit()


async def execute_research_task(task_id: UUID, database: Database | None = None) -> None:
    database = database or get_database()
    async with database.sessions() as session:
        repository = ResearchRepository(session)
        task = await repository.get_task(task_id)
        if task is None:
            raise ValueError(f"Research task {task_id} does not exist")
        if task.status == ResearchStatus.CANCELLED.value or task.cancel_requested:
            return
        await repository.mark_running(task)
        topic = task.topic
        user_id = task.user_id
        max_iterations = task.max_iterations
        await session.commit()

    initial_state = create_initial_state(
        topic,
        user_id=user_id,
        task_id=task_id,
        max_iterations=max_iterations,
    )

    try:
        settings = get_settings()
        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
            runtime = build_research_runtime(settings, client)
            graph = build_research_graph(
                runtime.planner,
                runtime.web_retriever,
                runtime.local_retriever,
                event_sink=DatabaseEventSink(database),
                analyst=runtime.analyst,
                writer=runtime.writer,
            )
            result = cast(ResearchState, await graph.ainvoke(initial_state))
        async with database.sessions() as session:
            repository = ResearchRepository(session)
            task = await repository.get_task(task_id)
            if task is None:
                raise ValueError(f"Research task {task_id} disappeared")
            await repository.persist_result(task, result)
            await repository.add_event(
                ResearchEvent(
                    task_id=task_id,
                    event_type=ResearchEventType.TASK_COMPLETED,
                    payload={
                        "status": result["status"].value,
                        "evidence_count": len(result["accepted_evidence"]),
                        "finding_count": len(result["findings"]),
                    },
                )
            )
            await session.commit()
    except ResearchCancelledError:
        async with database.sessions() as session:
            repository = ResearchRepository(session)
            task = await repository.get_task(task_id)
            if task is not None:
                await repository.mark_cancelled(task)
                await repository.add_event(
                    ResearchEvent(task_id=task_id, event_type=ResearchEventType.TASK_CANCELLED)
                )
                await session.commit()
    except Exception as exc:
        async with database.sessions() as session:
            repository = ResearchRepository(session)
            task = await repository.get_task(task_id)
            if task is not None:
                await repository.mark_failed(task, str(exc))
                await repository.add_event(
                    ResearchEvent(
                        task_id=task_id,
                        event_type=ResearchEventType.TASK_FAILED,
                        payload={"error": str(exc)},
                    )
                )
                await session.commit()
        raise
