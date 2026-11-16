from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any, NotRequired, TypedDict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class ResearchStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResearchNode(StrEnum):
    MEMORY_RECALL = "memory_recall"
    INTENT_ROUTER = "intent_router"
    PLANNER = "planner"
    WEB_SCOUT = "web_scout"
    LOCAL_SCOUT = "local_scout"
    EVIDENCE_JUDGE = "evidence_judge"
    ANALYST = "analyst"
    REFLECT = "reflect"
    WRITER = "writer"
    CITATION_VALIDATOR = "citation_validator"
    MEMORY_COMMIT = "memory_commit"


class EvidenceSource(StrEnum):
    WEB = "web"
    LOCAL = "local"
    MEMORY = "memory"


class EvidenceDecision(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"


class ResearchEventType(StrEnum):
    TASK_CREATED = "task_created"
    NODE_STARTED = "node_started"
    NODE_PROGRESS = "node_progress"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"


class ResearchPlan(BaseModel):
    objective: str = Field(min_length=3, max_length=1_000)
    sections: list[str] = Field(min_length=1, max_length=12)
    search_queries: list[str] = Field(min_length=3, max_length=8)
    expected_evidence: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("sections", "search_queries", "expected_evidence")
    @classmethod
    def clean_unique_text(cls, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for raw_value in values:
            value = " ".join(raw_value.split())
            key = value.casefold()
            if value and key not in seen:
                seen.add(key)
                result.append(value)
        return result


class Evidence(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    source_type: EvidenceSource
    title: str = Field(min_length=1, max_length=500)
    url: str | None = Field(default=None, max_length=2_048)
    content: str = Field(min_length=1, max_length=50_000)
    published_at: datetime | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content_hash: str = Field(min_length=16, max_length=128)
    relevance_score: float | None = Field(default=None, ge=0, le=1)
    credibility_score: float | None = Field(default=None, ge=0, le=1)
    decision: EvidenceDecision = EvidenceDecision.PENDING
    rejection_reason: str | None = Field(default=None, max_length=1_000)
    citation_id: str | None = Field(default=None, pattern=r"^E[1-9][0-9]*$")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_source_location(self) -> Evidence:
        if self.source_type == EvidenceSource.WEB and not self.url:
            raise ValueError("Web evidence must include a URL")
        if self.decision == EvidenceDecision.REJECTED and not self.rejection_reason:
            raise ValueError("Rejected evidence must include a reason")
        return self


class Finding(BaseModel):
    claim: str = Field(min_length=1, max_length=5_000)
    supporting_evidence_ids: list[UUID] = Field(min_length=1)
    opposing_evidence_ids: list[UUID] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class ResearchEvent(BaseModel):
    id: int | None = Field(default=None, ge=1)
    task_id: UUID
    node: ResearchNode | None = None
    event_type: ResearchEventType
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(default_factory=dict)


class ResearchState(TypedDict):
    task_id: UUID
    user_id: UUID
    topic: str
    status: ResearchStatus
    plan: NotRequired[ResearchPlan]
    search_queries: Annotated[list[str], list.__add__]
    candidate_evidence: Annotated[list[Evidence], list.__add__]
    accepted_evidence: list[Evidence]
    findings: list[Finding]
    missing_information: list[str]
    iteration: int
    max_iterations: int
    report: str
    warnings: Annotated[list[str], list.__add__]
    errors: Annotated[list[str], list.__add__]
