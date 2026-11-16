from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain import EvidenceDecision, EvidenceSource, ResearchNode, ResearchStatus


class CreateResearchRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=1000)
    max_iterations: int | None = Field(default=None, ge=0, le=5)


class ResearchTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    topic: str
    status: ResearchStatus
    iteration: int
    max_iterations: int
    cancel_requested: bool
    warnings: list[str]
    errors: list[str]
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class ResearchTaskListResponse(BaseModel):
    items: list[ResearchTaskResponse]


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    domain_id: UUID
    source_type: EvidenceSource
    title: str
    url: str | None
    content: str
    relevance_score: float | None
    credibility_score: float | None
    decision: EvidenceDecision
    citation_id: str | None
    published_at: datetime | None
    retrieved_at: datetime


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: UUID
    content: str
    citation_errors: list[str]
    created_at: datetime
    updated_at: datetime


class FindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    claim: str
    supporting_evidence_ids: list[UUID]
    opposing_evidence_ids: list[UUID]
    confidence: float


class NodeMetricResponse(BaseModel):
    node: ResearchNode
    run_count: int = Field(ge=1)
    duration_ms: int = Field(ge=0)


class ResearchMetricsResponse(BaseModel):
    total_duration_ms: int | None
    queue_duration_ms: int | None
    iteration_count: int = Field(ge=0)
    agent_run_count: int = Field(ge=0)
    evidence_count: int = Field(ge=0)
    finding_count: int = Field(ge=0)
    citation_count: int = Field(ge=0)
    evidence_by_source: dict[EvidenceSource, int]
    node_metrics: list[NodeMetricResponse]
