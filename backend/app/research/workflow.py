from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.domain import ResearchNode, ResearchState, ResearchStatus
from app.research.contracts import EvidenceRetriever, ResearchPlanner
from app.research.nodes import (
    ResearchNodes,
    route_after_intent,
    route_after_reflect,
    terminal_failure,
)


def build_research_graph(
    planner: ResearchPlanner,
    web_retriever: EvidenceRetriever,
    local_retriever: EvidenceRetriever,
    *,
    minimum_evidence: int = 3,
) -> CompiledStateGraph:
    nodes = ResearchNodes(
        planner,
        web_retriever,
        local_retriever,
        minimum_evidence=minimum_evidence,
    )
    graph = StateGraph(ResearchState)

    graph.add_node(ResearchNode.MEMORY_RECALL.value, nodes.memory_recall)
    graph.add_node(ResearchNode.INTENT_ROUTER.value, nodes.intent_router)
    graph.add_node(ResearchNode.PLANNER.value, nodes.planner_node)
    graph.add_node("dispatch_search", nodes.dispatch_search)
    graph.add_node(ResearchNode.WEB_SCOUT.value, nodes.web_scout)
    graph.add_node(ResearchNode.LOCAL_SCOUT.value, nodes.local_scout)
    graph.add_node(ResearchNode.EVIDENCE_JUDGE.value, nodes.evidence_judge)
    graph.add_node(ResearchNode.ANALYST.value, nodes.analyst)
    graph.add_node(ResearchNode.REFLECT.value, nodes.reflect)
    graph.add_node(ResearchNode.WRITER.value, nodes.writer)
    graph.add_node(ResearchNode.CITATION_VALIDATOR.value, nodes.citation_validator)
    graph.add_node(ResearchNode.MEMORY_COMMIT.value, nodes.memory_commit)
    graph.add_node("failed", terminal_failure)

    graph.add_edge(START, ResearchNode.MEMORY_RECALL.value)
    graph.add_edge(ResearchNode.MEMORY_RECALL.value, ResearchNode.INTENT_ROUTER.value)
    graph.add_conditional_edges(
        ResearchNode.INTENT_ROUTER.value,
        route_after_intent,
        {ResearchNode.PLANNER.value: ResearchNode.PLANNER.value, "failed": "failed"},
    )
    graph.add_edge("failed", END)
    graph.add_edge(ResearchNode.PLANNER.value, "dispatch_search")
    graph.add_edge("dispatch_search", ResearchNode.WEB_SCOUT.value)
    graph.add_edge("dispatch_search", ResearchNode.LOCAL_SCOUT.value)
    graph.add_edge(
        [ResearchNode.WEB_SCOUT.value, ResearchNode.LOCAL_SCOUT.value],
        ResearchNode.EVIDENCE_JUDGE.value,
    )
    graph.add_edge(ResearchNode.EVIDENCE_JUDGE.value, ResearchNode.ANALYST.value)
    graph.add_edge(ResearchNode.ANALYST.value, ResearchNode.REFLECT.value)
    graph.add_conditional_edges(
        ResearchNode.REFLECT.value,
        route_after_reflect,
        {"search": "dispatch_search", ResearchNode.WRITER.value: ResearchNode.WRITER.value},
    )
    graph.add_edge(ResearchNode.WRITER.value, ResearchNode.CITATION_VALIDATOR.value)
    graph.add_edge(ResearchNode.CITATION_VALIDATOR.value, ResearchNode.MEMORY_COMMIT.value)
    graph.add_edge(ResearchNode.MEMORY_COMMIT.value, END)

    return graph.compile()


def create_initial_state(
    topic: str,
    *,
    user_id: UUID | None = None,
    task_id: UUID | None = None,
    max_iterations: int = 2,
) -> ResearchState:
    return ResearchState(
        task_id=task_id or uuid4(),
        user_id=user_id or uuid4(),
        topic=topic,
        status=ResearchStatus.QUEUED,
        search_queries=[],
        query_history=[],
        candidate_evidence=[],
        accepted_evidence=[],
        findings=[],
        missing_information=[],
        iteration=0,
        max_iterations=max_iterations,
        should_continue=False,
        report="",
        citation_errors=[],
        warnings=[],
        errors=[],
    )


async def run_graph(graph: CompiledStateGraph, state: ResearchState) -> dict[str, Any]:
    return await graph.ainvoke(state, config={"recursion_limit": 50})
