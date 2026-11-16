from collections.abc import Awaitable, Callable
from typing import Protocol

from app.domain import Evidence, ResearchEvent, ResearchPlan

EventSink = Callable[[ResearchEvent], Awaitable[None]]


class ResearchPlanner(Protocol):
    async def create_plan(self, topic: str) -> ResearchPlan: ...


class EvidenceRetriever(Protocol):
    async def search(self, topic: str, queries: list[str]) -> list[Evidence]: ...
