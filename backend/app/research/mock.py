from __future__ import annotations

from hashlib import sha256
from urllib.parse import quote

from app.domain import Evidence, EvidenceSource, ResearchPlan


def _prefers_chinese(value: str) -> bool:
    return any("\u4e00" <= character <= "\u9fff" for character in value)


class MockPlanner:
    async def create_plan(self, topic: str) -> ResearchPlan:
        normalized = " ".join(topic.split())
        if _prefers_chinese(normalized):
            return ResearchPlan(
                objective=f"围绕“{normalized}”形成一份有证据支撑的分析报告",
                sections=["行业背景", "核心驱动因素", "风险与展望"],
                search_queries=[
                    f"{normalized} 行业概览",
                    f"{normalized} 核心驱动因素",
                    f"{normalized} 风险与发展趋势",
                ],
                expected_evidence=["市场数据", "行业分析", "风险证据"],
            )
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
            if _prefers_chinese(topic):
                content = (
                    f"这是关于“{topic}”的模拟研究来源 {index}，围绕“{query}”提供可独立核验的事实。"
                )
                title = f"模拟来源 {index}：{query}"
            else:
                content = (
                    f"Mock research source {index} for {topic}. "
                    f"It addresses the query '{query}' with independently verifiable facts."
                )
                title = f"Mock source {index}: {query}"
            evidence.append(
                Evidence(
                    source_type=EvidenceSource.WEB,
                    title=title,
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
