from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime

from app.db.models import EvidenceRecord, FindingRecord, ResearchEventRecord, ResearchTaskRecord
from app.domain import EvidenceSource, ResearchEventType, ResearchNode
from app.research.schemas import NodeMetricResponse, ResearchMetricsResponse


def _elapsed_ms(start: datetime | None, end: datetime | None) -> int | None:
    if start is None or end is None:
        return None
    if start.tzinfo is None and end.tzinfo is not None:
        end = end.replace(tzinfo=None)
    elif start.tzinfo is not None and end.tzinfo is None:
        start = start.replace(tzinfo=None)
    return max(0, round((end - start).total_seconds() * 1000))


def build_research_metrics(
    task: ResearchTaskRecord,
    events: list[ResearchEventRecord],
    evidence: list[EvidenceRecord],
    findings: list[FindingRecord],
) -> ResearchMetricsResponse:
    starts: dict[str, deque[datetime]] = defaultdict(deque)
    durations: dict[str, int] = defaultdict(int)
    runs: dict[str, int] = defaultdict(int)

    for event in events:
        if event.node is None:
            continue
        if event.event_type == ResearchEventType.NODE_STARTED.value:
            starts[event.node].append(event.created_at)
        elif (
            event.event_type
            in {
                ResearchEventType.NODE_COMPLETED.value,
                ResearchEventType.NODE_FAILED.value,
            }
            and starts[event.node]
        ):
            started_at = starts[event.node].popleft()
            durations[event.node] += _elapsed_ms(started_at, event.created_at) or 0
            runs[event.node] += 1

    node_metrics = [
        NodeMetricResponse(
            node=node,
            run_count=runs[node.value],
            duration_ms=durations[node.value],
        )
        for node in ResearchNode
        if runs[node.value]
    ]
    source_counts = {source: 0 for source in EvidenceSource}
    for item in evidence:
        source_counts[EvidenceSource(item.source_type)] += 1

    return ResearchMetricsResponse(
        total_duration_ms=_elapsed_ms(task.started_at, task.completed_at),
        queue_duration_ms=_elapsed_ms(task.created_at, task.started_at),
        iteration_count=task.iteration,
        agent_run_count=sum(metric.run_count for metric in node_metrics),
        evidence_count=len(evidence),
        finding_count=len(findings),
        citation_count=sum(item.citation_id is not None for item in evidence),
        evidence_by_source=source_counts,
        node_metrics=node_metrics,
    )
