from collections.abc import Awaitable, Callable
from typing import Protocol

from app.domain import Evidence, Finding, ResearchEvent, ResearchPlan

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
