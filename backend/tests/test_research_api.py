from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Database, get_database
from app.db.models import Base
from app.db.session import get_session
from app.domain import ResearchStatus
from app.jobs import JobDispatcher, get_job_dispatcher
from app.main import app
from app.research.service import execute_research_task


class InlineDispatcher:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def enqueue_research(self, task_id: UUID) -> None:
        await execute_research_task(task_id, self.database)


class RecordingDispatcher:
    def __init__(self) -> None:
        self.task_ids: list[UUID] = []

    async def enqueue_research(self, task_id: UUID) -> None:
        self.task_ids.append(task_id)


class FailingDispatcher:
    async def enqueue_research(self, task_id: UUID) -> None:
        del task_id
        raise ConnectionError("Redis unavailable")


async def _database(path: Path) -> AsyncIterator[Database]:
    database = Database(f"sqlite+aiosqlite:///{path.as_posix()}")
    async with database.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield database
    finally:
        await database.dispose()


async def _client(database: Database, dispatcher: JobDispatcher) -> AsyncIterator[AsyncClient]:
    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.sessions() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_database] = lambda: database
    app.dependency_overrides[get_job_dispatcher] = lambda: dispatcher
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_research_api_runs_and_replays_events(tmp_path: Path) -> None:
    async for database in _database(tmp_path / "complete.db"):
        async for client in _client(database, InlineDispatcher(database)):
            created = await client.post(
                "/api/research", json={"topic": "AI agent market", "max_iterations": 1}
            )
            assert created.status_code == 202
            task_id = created.json()["id"]

            detail = await client.get(f"/api/research/{task_id}")
            assert detail.json()["status"] == ResearchStatus.COMPLETED

            listing = await client.get("/api/research")
            assert [item["id"] for item in listing.json()["items"]] == [task_id]

            evidence = await client.get(f"/api/research/{task_id}/evidence")
            assert len(evidence.json()) == 3
            assert evidence.json()[0]["citation_id"] == "E1"

            report = await client.get(f"/api/research/{task_id}/report")
            assert report.status_code == 200
            assert "[E1]" in report.json()["content"]
            assert report.json()["citation_errors"] == []

            events = await client.get(f"/api/research/{task_id}/events")
            assert events.status_code == 200
            assert "event: task_created" in events.text
            assert "event: node_started" in events.text
            assert "event: task_completed" in events.text

            event_ids = [
                int(line.removeprefix("id: "))
                for line in events.text.splitlines()
                if line.startswith("id: ")
            ]
            replay = await client.get(
                f"/api/research/{task_id}/events",
                headers={"Last-Event-ID": str(event_ids[-2])},
            )
            assert f"id: {event_ids[-1]}" in replay.text
            assert f"id: {event_ids[-2]}\n" not in replay.text


@pytest.mark.asyncio
async def test_queued_task_can_be_cancelled(tmp_path: Path) -> None:
    async for database in _database(tmp_path / "cancel.db"):
        dispatcher = RecordingDispatcher()
        async for client in _client(database, dispatcher):
            created = await client.post("/api/research", json={"topic": "Queued research"})
            task_id = created.json()["id"]
            assert dispatcher.task_ids == [UUID(task_id)]

            cancelled = await client.post(f"/api/research/{task_id}/cancel")
            assert cancelled.status_code == 200
            assert cancelled.json()["status"] == ResearchStatus.CANCELLED
            assert cancelled.json()["cancel_requested"] is True

            second_cancel = await client.post(f"/api/research/{task_id}/cancel")
            assert second_cancel.status_code == 409

            events = await client.get(f"/api/research/{task_id}/events")
            assert "event: task_cancelled" in events.text


@pytest.mark.asyncio
async def test_pending_report_and_invalid_event_cursor_are_rejected(tmp_path: Path) -> None:
    async for database in _database(tmp_path / "errors.db"):
        async for client in _client(database, RecordingDispatcher()):
            created = await client.post("/api/research", json={"topic": "Pending research"})
            task_id = created.json()["id"]

            report = await client.get(f"/api/research/{task_id}/report")
            assert report.status_code == 409

            events = await client.get(
                f"/api/research/{task_id}/events", headers={"Last-Event-ID": "invalid"}
            )
            assert events.status_code == 400


@pytest.mark.asyncio
async def test_worker_unavailability_is_persisted_as_failure(tmp_path: Path) -> None:
    async for database in _database(tmp_path / "worker-failure.db"):
        async for client in _client(database, FailingDispatcher()):
            response = await client.post("/api/research", json={"topic": "Worker failure"})
            assert response.status_code == 503

            listing = await client.get("/api/research")
            task = listing.json()["items"][0]
            assert task["status"] == ResearchStatus.FAILED
            assert task["errors"] == ["Research worker is unavailable"]

            missing = await client.get(f"/api/research/{UUID(int=0)}")
            assert missing.status_code == 404
