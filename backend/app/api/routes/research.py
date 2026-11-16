from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser
from app.core.config import get_settings
from app.db import Database, get_database
from app.db.models import ResearchEventRecord, ResearchTaskRecord
from app.db.session import get_session
from app.domain import ResearchEvent, ResearchEventType, ResearchStatus
from app.jobs import JobDispatcher, get_job_dispatcher
from app.research.repository import ResearchRepository
from app.research.schemas import (
    CreateResearchRequest,
    EvidenceResponse,
    FindingResponse,
    ReportResponse,
    ResearchTaskListResponse,
    ResearchTaskResponse,
)
from app.research.workflow import create_initial_state

router = APIRouter(prefix="/api/research", tags=["research"])
Session = Annotated[AsyncSession, Depends(get_session)]
Dispatcher = Annotated[JobDispatcher, Depends(get_job_dispatcher)]
DatabaseDependency = Annotated[Database, Depends(get_database)]

TERMINAL_STATUSES = {
    ResearchStatus.COMPLETED.value,
    ResearchStatus.COMPLETED_WITH_WARNINGS.value,
    ResearchStatus.FAILED.value,
    ResearchStatus.CANCELLED.value,
}


async def _owned_task(
    repository: ResearchRepository, task_id: UUID, user_id: UUID
) -> ResearchTaskRecord:
    task = await repository.get_task(task_id)
    if task is None or task.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research task not found")
    return task


@router.post("", response_model=ResearchTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_research(
    body: CreateResearchRequest,
    session: Session,
    dispatcher: Dispatcher,
    user: CurrentUser,
) -> ResearchTaskRecord:
    settings = get_settings()
    state = create_initial_state(
        body.topic,
        user_id=user.id,
        max_iterations=(
            body.max_iterations
            if body.max_iterations is not None
            else settings.max_research_iterations
        ),
    )
    repository = ResearchRepository(session)
    task = await repository.create_task(
        task_id=state["task_id"],
        user_id=user.id,
        topic=state["topic"],
        max_iterations=state["max_iterations"],
    )
    await repository.add_event(
        ResearchEvent(
            task_id=task.id,
            event_type=ResearchEventType.TASK_CREATED,
            payload={"topic": task.topic},
        )
    )
    await session.commit()

    try:
        await dispatcher.enqueue_research(task.id)
    except Exception as exc:
        await repository.mark_failed(task, "Research worker is unavailable")
        await repository.add_event(
            ResearchEvent(
                task_id=task.id,
                event_type=ResearchEventType.TASK_FAILED,
                payload={"error": "Research worker is unavailable"},
            )
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Research worker is unavailable",
        ) from exc
    return task


@router.get("", response_model=ResearchTaskListResponse)
async def list_research(
    session: Session,
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ResearchTaskListResponse:
    items = await ResearchRepository(session).list_tasks(user.id, limit=limit, offset=offset)
    return ResearchTaskListResponse(
        items=[ResearchTaskResponse.model_validate(item) for item in items]
    )


@router.get("/{task_id}", response_model=ResearchTaskResponse)
async def get_research(task_id: UUID, session: Session, user: CurrentUser) -> ResearchTaskRecord:
    return await _owned_task(ResearchRepository(session), task_id, user.id)


@router.post("/{task_id}/cancel", response_model=ResearchTaskResponse)
async def cancel_research(task_id: UUID, session: Session, user: CurrentUser) -> ResearchTaskRecord:
    repository = ResearchRepository(session)
    task = await _owned_task(repository, task_id, user.id)
    changed = await repository.request_cancellation(task)
    if not changed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task is already terminal")
    if task.status == ResearchStatus.CANCELLED.value:
        await repository.add_event(
            ResearchEvent(task_id=task.id, event_type=ResearchEventType.TASK_CANCELLED)
        )
    await session.commit()
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_research(task_id: UUID, session: Session, user: CurrentUser) -> Response:
    repository = ResearchRepository(session)
    task = await _owned_task(repository, task_id, user.id)
    if task.status not in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Active research task cannot be deleted",
        )
    await repository.delete_task(task)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{task_id}/report", response_model=ReportResponse)
async def get_report(task_id: UUID, session: Session, user: CurrentUser) -> object:
    repository = ResearchRepository(session)
    task = await _owned_task(repository, task_id, user.id)
    report = await repository.get_report(task.id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Report is not ready")
    return report


@router.get("/{task_id}/evidence", response_model=list[EvidenceResponse])
async def get_evidence(task_id: UUID, session: Session, user: CurrentUser) -> list[object]:
    repository = ResearchRepository(session)
    task = await _owned_task(repository, task_id, user.id)
    return list(await repository.get_evidence(task.id))


@router.get("/{task_id}/findings", response_model=list[FindingResponse])
async def get_findings(task_id: UUID, session: Session, user: CurrentUser) -> list[object]:
    repository = ResearchRepository(session)
    task = await _owned_task(repository, task_id, user.id)
    return list(await repository.get_findings(task.id))


def _encode_sse(record: ResearchEventRecord) -> str:
    data = json.dumps(
        {
            "task_id": str(record.task_id),
            "node": record.node,
            "type": record.event_type,
            "payload": record.payload,
            "created_at": record.created_at.isoformat(),
        },
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return f"id: {record.id}\nevent: {record.event_type}\ndata: {data}\n\n"


async def _event_stream(
    request: Request,
    database: Database,
    task_id: UUID,
    after_id: int,
) -> AsyncIterator[str]:
    cursor = after_id
    while not await request.is_disconnected():
        async with database.sessions() as session:
            repository = ResearchRepository(session)
            events = await repository.list_events(task_id, after_id=cursor)
            task = await repository.get_task(task_id)

        for event in events:
            cursor = event.id
            yield _encode_sse(event)

        if task is None or (task.status in TERMINAL_STATUSES and not events):
            break
        if not events:
            yield ": keep-alive\n\n"
        await asyncio.sleep(0.5)


@router.get("/{task_id}/events")
async def stream_events(
    task_id: UUID,
    request: Request,
    session: Session,
    database: DatabaseDependency,
    user: CurrentUser,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> Response:
    await _owned_task(ResearchRepository(session), task_id, user.id)
    try:
        after_id = int(last_event_id) if last_event_id else 0
        if after_id < 0:
            raise ValueError
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Last-Event-ID must be a non-negative integer",
        ) from exc

    return StreamingResponse(
        _event_stream(request, database, task_id, after_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
