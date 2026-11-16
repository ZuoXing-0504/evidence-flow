from hashlib import sha256

import pytest

from app.domain import Evidence, EvidenceSource, ResearchStatus
from app.research import (
    MockPlanner,
    MockWebRetriever,
    StaticRetriever,
    build_research_graph,
    create_initial_state,
)


class FailingRetriever:
    async def search(self, topic: str, queries: list[str]) -> list[Evidence]:
        del topic, queries
        raise ConnectionError("Vector store unavailable")


class FailingMemory:
    async def recall(self, **kwargs: object) -> list[Evidence]:
        del kwargs
        raise ConnectionError("Memory unavailable")

    async def remember(self, state: object) -> None:
        del state
        raise ConnectionError("Memory unavailable")


@pytest.mark.asyncio
async def test_offline_workflow_completes_with_valid_citations() -> None:
    graph = build_research_graph(MockPlanner(), MockWebRetriever(), StaticRetriever())

    result = await graph.ainvoke(create_initial_state("AI agent market"))

    assert result["status"] == ResearchStatus.COMPLETED
    assert len(result["accepted_evidence"]) == 3
    assert len(result["findings"]) == 3
    assert result["citation_errors"] == []
    assert "[E1]" in result["report"]
    assert result["iteration"] == 0


@pytest.mark.asyncio
async def test_offline_workflow_follows_chinese_topic_language() -> None:
    graph = build_research_graph(MockPlanner(), MockWebRetriever(), StaticRetriever())

    result = await graph.ainvoke(create_initial_state("金融行业多 Agent 应用"))

    assert result["status"] == ResearchStatus.COMPLETED
    assert result["plan"].objective.startswith("围绕")
    assert result["accepted_evidence"][0].title.startswith("模拟来源")
    assert result["report"].startswith("# 金融行业多 Agent 应用研究报告")
    assert "## 研究目标" in result["report"]
    assert "## 核心发现" in result["report"]
    assert "## 参考来源" in result["report"]


@pytest.mark.asyncio
async def test_parallel_retrieval_combines_web_and_local_evidence() -> None:
    content = "Local evidence about the AI agent market"
    local = Evidence(
        source_type=EvidenceSource.LOCAL,
        title="Internal market memo",
        content=content,
        content_hash=sha256(content.encode()).hexdigest(),
    )
    graph = build_research_graph(
        MockPlanner(),
        MockWebRetriever(),
        StaticRetriever([local]),
        minimum_evidence=4,
    )

    result = await graph.ainvoke(create_initial_state("AI agent market"))

    assert result["status"] == ResearchStatus.COMPLETED
    assert {item.source_type for item in result["accepted_evidence"]} == {
        EvidenceSource.WEB,
        EvidenceSource.LOCAL,
    }


@pytest.mark.asyncio
async def test_reflection_stops_at_iteration_limit() -> None:
    graph = build_research_graph(
        MockPlanner(),
        StaticRetriever(),
        StaticRetriever(),
        minimum_evidence=3,
    )

    result = await graph.ainvoke(create_initial_state("Sparse topic", max_iterations=2))

    assert result["iteration"] == 2
    assert result["status"] == ResearchStatus.COMPLETED_WITH_WARNINGS
    assert len(result["query_history"]) == 9
    assert result["missing_information"] == ["At least 3 more sources needed"]
    assert result["citation_errors"] == ["No accepted evidence is available"]
    assert "No reliable evidence" in result["report"]


@pytest.mark.asyncio
async def test_invalid_topic_fails_before_planning() -> None:
    graph = build_research_graph(MockPlanner(), MockWebRetriever(), StaticRetriever())

    result = await graph.ainvoke(create_initial_state("  a "))

    assert result["status"] == ResearchStatus.FAILED
    assert result["errors"] == ["Research topic must contain at least 3 characters"]


@pytest.mark.asyncio
async def test_local_retrieval_and_memory_failures_degrade_to_warnings() -> None:
    graph = build_research_graph(
        MockPlanner(),
        MockWebRetriever(),
        FailingRetriever(),
        memory=FailingMemory(),
    )

    result = await graph.ainvoke(create_initial_state("AI agent market"))

    assert result["status"] == ResearchStatus.COMPLETED
    assert "Local knowledge retrieval is unavailable" in result["warnings"]
    assert "Semantic memory recall is unavailable" in result["warnings"]
    assert "Semantic memory commit is unavailable" in result["warnings"]
