from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, cast
from uuid import UUID, uuid4

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.domain import ResearchEvent, ResearchEventType, ResearchNode, ResearchState, ResearchStatus
from app.research.contracts import EventSink, EvidenceRetriever, ResearchPlanner
from app.research.nodes import (
    ResearchNodes,
    route_after_intent,
    route_after_reflect,
    terminal_failure,
)

ResearchGraph = CompiledStateGraph[ResearchState, None, ResearchState, ResearchState]
NodeFunction = Callable[[ResearchState], Awaitable[dict[str, Any]]]


def _event_payload(result: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {"updated_fields": sorted(result)}
    for field in ("candidate_evidence", "accepted_evidence", "findings", "search_queries"):
        value = result.get(field)
        if isinstance(value, list):
            payload[f"{field}_count"] = len(value)
    if "iteration" in result:
        payload["iteration"] = result["iteration"]
    return payload


def _instrument(node: ResearchNode, function: NodeFunction, sink: EventSink) -> NodeFunction:
    async def instrumented(state: ResearchState) -> dict[str, Any]:
        await sink(
            ResearchEvent(
                task_id=state["task_id"],
                node=node,
                event_type=ResearchEventType.NODE_STARTED,
            )
        )
        try:
            result = await function(state)
        except Exception as exc:
            await sink(
                ResearchEvent(
                    task_id=state["task_id"],
                    node=node,
                    event_type=ResearchEventType.NODE_FAILED,
                    payload={"error": str(exc)},
                )
            )
            raise
        await sink(
            ResearchEvent(
                task_id=state["task_id"],
                node=node,
                event_type=ResearchEventType.NODE_COMPLETED,
                payload=_event_payload(result),
            )
        )
        return result

    return instrumented


def build_research_graph(
    planner: ResearchPlanner,
    web_retriever: EvidenceRetriever,
    local_retriever: EvidenceRetriever,
    *,
    minimum_evidence: int = 3,
    event_sink: EventSink | None = None,
) -> ResearchGraph:
    nodes = ResearchNodes(
        planner,
        web_retriever,
        local_retriever,
        minimum_evidence=minimum_evidence,
    )
    graph = StateGraph(ResearchState)

    def observed(node: ResearchNode, function: NodeFunction) -> NodeFunction:
        return _instrument(node, function, event_sink) if event_sink else function

    def add_observed_node(node: ResearchNode, function: NodeFunction) -> None:
        # LangGraph's overloads do not retain callable compatibility after decoration.
        graph.add_node(node.value, cast(Any, observed(node, function)))

    add_observed_node(ResearchNode.MEMORY_RECALL, nodes.memory_recall)
    add_observed_node(ResearchNode.INTENT_ROUTER, nodes.intent_router)
    add_observed_node(ResearchNode.PLANNER, nodes.planner_node)
    graph.add_node("dispatch_search", nodes.dispatch_search)
    add_observed_node(ResearchNode.WEB_SCOUT, nodes.web_scout)
    add_observed_node(ResearchNode.LOCAL_SCOUT, nodes.local_scout)
    add_observed_node(ResearchNode.EVIDENCE_JUDGE, nodes.evidence_judge)
    add_observed_node(ResearchNode.ANALYST, nodes.analyst)
    add_observed_node(ResearchNode.REFLECT, nodes.reflect)
    add_observed_node(ResearchNode.WRITER, nodes.writer)
    add_observed_node(ResearchNode.CITATION_VALIDATOR, nodes.citation_validator)
    add_observed_node(ResearchNode.MEMORY_COMMIT, nodes.memory_commit)
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


async def run_graph(graph: ResearchGraph, state: ResearchState) -> dict[str, Any]:
    return await graph.ainvoke(state, config={"recursion_limit": 50})
