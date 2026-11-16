from collections.abc import Awaitable, Callable
from typing import Protocol
from uuid import UUID

from app.domain import Evidence, Finding, ResearchEvent, ResearchPlan, ResearchState

EventSink = Callable[[ResearchEvent], Awaitable[None]]


class ResearchPlanner(Protocol):
    async def create_plan(self, topic: str) -> ResearchPlan: ...


class EvidenceRetriever(Protocol):
    async def search(self, topic: str, queries: list[str]) -> list[Evidence]: ...


class ResearchAnalyst(Protocol):
    async def analyze(self, topic: str, evidence: list[Evidence]) -> list[Finding]: ...


class ReportWriter(Protocol):
    async def write_report(
        self,
        topic: str,
        plan: ResearchPlan | None,
        findings: list[Finding],
        evidence: list[Evidence],
    ) -> str: ...


class ResearchMemory(Protocol):
    async def recall(self, *, user_id: UUID, topic: str, limit: int = 3) -> list[Evidence]: ...

    async def remember(self, state: ResearchState) -> None: ...
