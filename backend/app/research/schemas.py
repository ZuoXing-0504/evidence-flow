from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain import EvidenceDecision, EvidenceSource, ResearchStatus


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
