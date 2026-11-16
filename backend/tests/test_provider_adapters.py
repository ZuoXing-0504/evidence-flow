from __future__ import annotations

import json
from hashlib import sha256

import httpx
import pytest

from app.core.config import Settings
from app.domain import Evidence, EvidenceDecision, EvidenceSource
from app.research.adapters.bocha import BochaWebRetriever
from app.research.adapters.dashscope import DashScopeResearchModel
from app.research.adapters.factory import build_research_runtime
from app.research.adapters.http import ExternalProviderError, post_json
from app.research.mock import MockPlanner, MockWebRetriever


@pytest.mark.asyncio
async def test_bocha_results_are_converted_to_evidence() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-key"
        assert json.loads(request.content)["count"] == 5
        return httpx.Response(
            200,
            json={
                "code": 200,
                "data": {
                    "webPages": {
                        "value": [
                            {
                                "name": "Agent market report",
                                "url": "https://example.com/report",
                                "snippet": "Fallback snippet",
                                "summary": "Independent AI agent market evidence.",
                                "siteName": "Example Research",
                                "datePublished": "2026-01-02T03:04:05Z",
                            }
                        ]
                    }
                },
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        retriever = BochaWebRetriever(
            client,
            api_key="test-key",
            base_url="https://bocha.test/v1/",
        )
        result = await retriever.search("AI agents", ["AI agent market"])

    assert len(result) == 1
    assert result[0].source_type == EvidenceSource.WEB
    assert result[0].content == "Independent AI agent market evidence."
    assert result[0].published_at is not None
    assert result[0].metadata == {
        "provider": "bocha",
        "query": "AI agent market",
        "site_name": "Example Research",
    }


@pytest.mark.asyncio
async def test_bocha_provider_rejects_api_errors() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 400, "msg": "bad request", "data": None})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        retriever = BochaWebRetriever(client, api_key="test-key", base_url="https://bocha.test/v1")
        with pytest.raises(ExternalProviderError, match="code 400"):
            await retriever.search("topic", ["query"])


@pytest.mark.asyncio
async def test_bocha_spaces_multiple_queries(monkeypatch: pytest.MonkeyPatch) -> None:
    queries: list[str] = []
    delays: list[float] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        queries.append(json.loads(request.content)["query"])
        return httpx.Response(200, json={"code": 200, "data": {"webPages": {"value": []}}})

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr("app.research.adapters.bocha.asyncio.sleep", record_sleep)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        retriever = BochaWebRetriever(
            client,
            api_key="test-key",
            base_url="https://bocha.test/v1",
            query_interval_seconds=0.5,
        )
        result = await retriever.search("topic", ["first", "second", "third"])

    assert result == []
    assert queries == ["first", "second", "third"]
    assert delays == [0.5, 0.5]


def _completion(content: dict[str, object]) -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": json.dumps(content)}}]},
    )


@pytest.mark.asyncio
async def test_dashscope_plans_analyzes_and_writes_with_citations() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer dashscope-key"
        body = json.loads(request.content)
        system = body["messages"][0]["content"]
        if "research planner" in system:
            return _completion(
                {
                    "objective": "Analyze the AI agent market",
                    "sections": ["Market", "Drivers", "Risks"],
                    "search_queries": ["agent market", "agent drivers", "agent risks"],
                    "expected_evidence": ["market data"],
                }
            )
        if "evidence analyst" in system:
            return _completion(
                {
                    "findings": [
                        {
                            "claim": "The market is expanding.",
                            "supporting_citations": ["E1"],
                            "opposing_citations": [],
                            "confidence": 0.82,
                        }
                    ]
                }
            )
        return _completion(
            {
                "report": (
                    "# AI agent market\n\nThe market is expanding [E1]."
                    "\n\n## Sources\n\n[E1] Source"
                )
            }
        )

    content = "Independent evidence about the AI agent market."
    evidence = Evidence(
        source_type=EvidenceSource.WEB,
        title="Source",
        url="https://example.com/source",
        content=content,
        content_hash=sha256(content.encode()).hexdigest(),
        decision=EvidenceDecision.ACCEPTED,
        citation_id="E1",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = DashScopeResearchModel(
            client,
            api_key="dashscope-key",
            base_url="https://dashscope.test/v1/",
            reasoning_model="qwen-plus",
        )
        plan = await model.create_plan("AI agent market")
        findings = await model.analyze("AI agent market", [evidence])
        report = await model.write_report("AI agent market", plan, findings, [evidence])

    assert plan.search_queries == ["agent market", "agent drivers", "agent risks"]
    assert findings[0].supporting_evidence_ids == [evidence.id]
    assert findings[0].confidence == 0.82
    assert "[E1]" in report


@pytest.mark.asyncio
async def test_dashscope_rejects_unmapped_citations() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return _completion(
            {
                "findings": [
                    {
                        "claim": "Unsupported",
                        "supporting_citations": ["E2"],
                        "opposing_citations": [],
                        "confidence": 0.5,
                    }
                ]
            }
        )

    content = "Evidence"
    evidence = Evidence(
        source_type=EvidenceSource.WEB,
        title="Source",
        url="https://example.com",
        content=content,
        content_hash=sha256(content.encode()).hexdigest(),
        decision=EvidenceDecision.ACCEPTED,
        citation_id="E1",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = DashScopeResearchModel(
            client,
            api_key="key",
            base_url="https://dashscope.test/v1",
            reasoning_model="qwen-plus",
        )
        with pytest.raises(ExternalProviderError, match="did not reference"):
            await model.analyze("topic", [evidence])


@pytest.mark.asyncio
async def test_runtime_factory_keeps_offline_defaults() -> None:
    async with httpx.AsyncClient() as client:
        runtime = build_research_runtime(Settings(_env_file=None), client)

    assert isinstance(runtime.planner, MockPlanner)
    assert isinstance(runtime.web_retriever, MockWebRetriever)
    assert runtime.analyst is None
    assert runtime.writer is None


@pytest.mark.asyncio
async def test_runtime_factory_selects_real_providers() -> None:
    settings = Settings(
        llm_provider="dashscope",
        dashscope_api_key="dashscope-key",
        web_search_provider="bocha",
        bocha_api_key="bocha-key",
        _env_file=None,
    )
    async with httpx.AsyncClient() as client:
        runtime = build_research_runtime(settings, client)

    assert isinstance(runtime.planner, DashScopeResearchModel)
    assert isinstance(runtime.web_retriever, BochaWebRetriever)
    assert runtime.analyst is runtime.planner
    assert runtime.writer is runtime.planner


@pytest.mark.asyncio
async def test_provider_http_retries_transient_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("app.research.adapters.http.asyncio.sleep", no_sleep)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await post_json(
            client,
            "https://provider.test/resource",
            service="Test Provider",
            headers={},
            payload={},
        )

    assert result == {"ok": True}
    assert calls == 2


@pytest.mark.asyncio
async def test_provider_http_honors_retry_after(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    delays: list[float] = []

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "1.5"})
        return httpx.Response(200, json={"ok": True})

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr("app.research.adapters.http.asyncio.sleep", record_sleep)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await post_json(
            client,
            "https://provider.test/resource",
            service="Test Provider",
            headers={},
            payload={},
        )

    assert result == {"ok": True}
    assert delays == [1.5]
