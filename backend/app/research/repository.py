from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    EvidenceRecord,
    FindingRecord,
    ReportRecord,
    ResearchEventRecord,
    ResearchTaskRecord,
)
from app.domain import Evidence, Finding, ResearchEvent, ResearchState, ResearchStatus


class ResearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_task(
        self,
        *,
        task_id: UUID,
        user_id: UUID,
        topic: str,
        max_iterations: int,
    ) -> ResearchTaskRecord:
        task = ResearchTaskRecord(
            id=task_id,
            user_id=user_id,
            topic=topic,
            max_iterations=max_iterations,
        )
        self.session.add(task)
        await self.session.flush()
        return task

    async def get_task(self, task_id: UUID) -> ResearchTaskRecord | None:
        return await self.session.get(ResearchTaskRecord, task_id)

    async def list_tasks(
        self, user_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> list[ResearchTaskRecord]:
        result = await self.session.scalars(
            select(ResearchTaskRecord)
            .where(ResearchTaskRecord.user_id == user_id)
            .order_by(ResearchTaskRecord.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result)

    async def delete_task(self, task: ResearchTaskRecord) -> None:
        await self.session.delete(task)
        await self.session.flush()

    async def mark_running(self, task: ResearchTaskRecord) -> None:
        task.status = ResearchStatus.RUNNING.value
        task.started_at = datetime.now(UTC)
        task.updated_at = datetime.now(UTC)
        await self.session.flush()

    async def request_cancellation(self, task: ResearchTaskRecord) -> bool:
        terminal = {
            ResearchStatus.COMPLETED.value,
            ResearchStatus.COMPLETED_WITH_WARNINGS.value,
            ResearchStatus.FAILED.value,
            ResearchStatus.CANCELLED.value,
        }
        if task.status in terminal:
            return False
        task.cancel_requested = True
        if task.status == ResearchStatus.QUEUED.value:
            task.status = ResearchStatus.CANCELLED.value
            task.completed_at = datetime.now(UTC)
        task.updated_at = datetime.now(UTC)
        await self.session.flush()
        return True

    async def is_cancellation_requested(self, task_id: UUID) -> bool:
        return bool(
            await self.session.scalar(
                select(ResearchTaskRecord.cancel_requested).where(ResearchTaskRecord.id == task_id)
            )
        )

    async def add_event(self, event: ResearchEvent) -> ResearchEventRecord:
        record = ResearchEventRecord(
            task_id=event.task_id,
            node=event.node.value if event.node else None,
            event_type=event.event_type.value,
            payload=event.payload,
            created_at=event.created_at,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def list_events(
        self, task_id: UUID, *, after_id: int = 0, limit: int = 200
    ) -> list[ResearchEventRecord]:
        result = await self.session.scalars(
            select(ResearchEventRecord)
            .where(
                ResearchEventRecord.task_id == task_id,
                ResearchEventRecord.id > after_id,
            )
            .order_by(ResearchEventRecord.id)
            .limit(limit)
        )
        return list(result)

    async def persist_result(self, task: ResearchTaskRecord, state: ResearchState) -> None:
        await self.session.execute(delete(EvidenceRecord).where(EvidenceRecord.task_id == task.id))
        await self.session.execute(delete(FindingRecord).where(FindingRecord.task_id == task.id))

        self.session.add_all(
            [self._evidence_record(task.id, item) for item in state["accepted_evidence"]]
        )
        self.session.add_all([self._finding_record(task.id, item) for item in state["findings"]])

        report = await self.session.scalar(
            select(ReportRecord).where(ReportRecord.task_id == task.id)
        )
        if report is None:
            report = ReportRecord(task_id=task.id, content=state["report"])
            self.session.add(report)
        report.content = state["report"]
        report.citation_errors = state["citation_errors"]

        task.status = state["status"].value
        task.iteration = state["iteration"]
        task.warnings = state["warnings"]
        task.errors = state["errors"]
        task.completed_at = datetime.now(UTC)
        task.updated_at = datetime.now(UTC)
        await self.session.flush()

    async def mark_cancelled(self, task: ResearchTaskRecord) -> None:
        task.status = ResearchStatus.CANCELLED.value
        task.cancel_requested = True
        task.completed_at = datetime.now(UTC)
        task.updated_at = datetime.now(UTC)
        await self.session.flush()

    async def mark_failed(self, task: ResearchTaskRecord, message: str) -> None:
        task.status = ResearchStatus.FAILED.value
        task.errors = [message]
        task.completed_at = datetime.now(UTC)
        task.updated_at = datetime.now(UTC)
        await self.session.flush()

    async def get_report(self, task_id: UUID) -> ReportRecord | None:
        return await self.session.scalar(
            select(ReportRecord).where(ReportRecord.task_id == task_id)
        )

    async def get_evidence(self, task_id: UUID) -> list[EvidenceRecord]:
        result = await self.session.scalars(
            select(EvidenceRecord)
            .where(EvidenceRecord.task_id == task_id)
            .order_by(EvidenceRecord.citation_id)
        )
        return list(result)

    @staticmethod
    def _evidence_record(task_id: UUID, item: Evidence) -> EvidenceRecord:
        return EvidenceRecord(
            task_id=task_id,
            domain_id=item.id,
            source_type=item.source_type.value,
            title=item.title,
            url=item.url,
            content=item.content,
            published_at=item.published_at,
            retrieved_at=item.retrieved_at,
            content_hash=item.content_hash,
            relevance_score=item.relevance_score,
            credibility_score=item.credibility_score,
            decision=item.decision.value,
            rejection_reason=item.rejection_reason,
            citation_id=item.citation_id,
            extra=item.metadata,
        )

    @staticmethod
    def _finding_record(task_id: UUID, item: Finding) -> FindingRecord:
        return FindingRecord(
            task_id=task_id,
            claim=item.claim,
            supporting_evidence_ids=[str(value) for value in item.supporting_evidence_ids],
            opposing_evidence_ids=[str(value) for value in item.opposing_evidence_ids],
            confidence=item.confidence,
        )
