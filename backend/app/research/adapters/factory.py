from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import httpx

from app.core.config import Settings
from app.knowledge.retrieval import KnowledgeRetriever
from app.knowledge.store import KnowledgeStore
from app.research.adapters.bocha import BochaWebRetriever
from app.research.adapters.dashscope import DashScopeResearchModel
from app.research.contracts import (
    EvidenceRetriever,
    ReportWriter,
    ResearchAnalyst,
    ResearchMemory,
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
    memory: ResearchMemory | None = None


def build_research_runtime(
    settings: Settings,
    client: httpx.AsyncClient,
    *,
    user_id: UUID | None = None,
    knowledge_store: KnowledgeStore | None = None,
) -> ResearchRuntime:
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

    local_retriever: EvidenceRetriever
    memory: ResearchMemory | None
    if user_id is not None and knowledge_store is not None:
        local_retriever = KnowledgeRetriever(knowledge_store, user_id)
        memory = knowledge_store
    else:
        local_retriever = StaticRetriever()
        memory = None

    return ResearchRuntime(
        planner=planner,
        web_retriever=web_retriever,
        local_retriever=local_retriever,
        analyst=analyst,
        writer=writer,
        memory=memory,
    )
