from __future__ import annotations

from hashlib import sha256
from urllib.parse import quote

from app.domain import Evidence, EvidenceSource, ResearchPlan


class MockPlanner:
    async def create_plan(self, topic: str) -> ResearchPlan:
        normalized = " ".join(topic.split())
        return ResearchPlan(
            objective=f"Produce an evidence-grounded analysis of {normalized}",
            sections=["Market context", "Key drivers", "Risks and outlook"],
            search_queries=[
                f"{normalized} market overview",
                f"{normalized} key drivers",
                f"{normalized} risks outlook",
            ],
            expected_evidence=["Market data", "Industry analysis", "Risk evidence"],
        )


class MockWebRetriever:
    async def search(self, topic: str, queries: list[str]) -> list[Evidence]:
        evidence: list[Evidence] = []
        for index, query in enumerate(queries[:3], start=1):
            content = (
                f"Mock research source {index} for {topic}. "
                f"It addresses the query '{query}' with independently verifiable facts."
            )
            evidence.append(
                Evidence(
                    source_type=EvidenceSource.WEB,
                    title=f"Mock source {index}: {query}",
                    url=f"https://example.com/research/{quote(query, safe='')}",
                    content=content,
                    content_hash=sha256(content.encode()).hexdigest(),
                    metadata={"provider": "mock", "query": query},
                )
            )
        return evidence


class StaticRetriever:
    def __init__(self, evidence: list[Evidence] | None = None) -> None:
        self._evidence = evidence or []

    async def search(self, topic: str, queries: list[str]) -> list[Evidence]:
        del topic, queries
        return [item.model_copy(deep=True) for item in self._evidence]
