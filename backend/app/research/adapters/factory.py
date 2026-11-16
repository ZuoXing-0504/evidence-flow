from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import Settings
from app.research.adapters.bocha import BochaWebRetriever
from app.research.adapters.dashscope import DashScopeResearchModel
from app.research.contracts import (
    EvidenceRetriever,
    ReportWriter,
    ResearchAnalyst,
    ResearchPlanner,
)
from app.research.mock import MockPlanner, MockWebRetriever, StaticRetriever


@dataclass(frozen=True, slots=True)
class ResearchRuntime:
    planner: ResearchPlanner
    web_retriever: EvidenceRetriever
    local_retriever: EvidenceRetriever
    analyst: ResearchAnalyst | None = None
    writer: ReportWriter | None = None


def build_research_runtime(settings: Settings, client: httpx.AsyncClient) -> ResearchRuntime:
    if settings.llm_provider == "dashscope":
        model = DashScopeResearchModel(
            client,
            api_key=settings.dashscope_api_key.get_secret_value(),
            base_url=settings.dashscope_base_url,
            reasoning_model=settings.llm_reasoning_model,
        )
        planner: ResearchPlanner = model
        analyst: ResearchAnalyst | None = model
        writer: ReportWriter | None = model
    else:
        planner = MockPlanner()
        analyst = None
        writer = None

    if settings.web_search_provider == "bocha":
        web_retriever: EvidenceRetriever = BochaWebRetriever(
            client,
            api_key=settings.bocha_api_key.get_secret_value(),
            base_url=settings.bocha_base_url,
            results_per_query=settings.bocha_results_per_query,
        )
    else:
        web_retriever = MockWebRetriever()

    return ResearchRuntime(
        planner=planner,
        web_retriever=web_retriever,
        local_retriever=StaticRetriever(),
        analyst=analyst,
        writer=writer,
    )
