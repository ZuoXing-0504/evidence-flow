from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain import EvidenceDecision, EvidenceSource, ResearchEventType, ResearchStatus


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    display_name: Mapped[str] = mapped_column(String(120), default="Guest researcher")
    preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    tasks: Mapped[list[ResearchTaskRecord]] = relationship(back_populates="user")


class ResearchTaskRecord(Base):
    __tablename__ = "research_tasks"
    __table_args__ = (Index("ix_research_tasks_user_created", "user_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    topic: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(40), default=ResearchStatus.QUEUED.value, index=True)
    iteration: Mapped[int] = mapped_column(Integer, default=0)
    max_iterations: Mapped[int] = mapped_column(Integer, default=2)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    errors: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[UserRecord] = relationship(back_populates="tasks")
    evidence: Mapped[list[EvidenceRecord]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    findings: Mapped[list[FindingRecord]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    events: Mapped[list[ResearchEventRecord]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    report: Mapped[ReportRecord | None] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class EvidenceRecord(Base):
    __tablename__ = "evidence"
    __table_args__ = (
        UniqueConstraint("task_id", "domain_id", name="uq_evidence_task_domain_id"),
        Index("ix_evidence_task_citation", "task_id", "citation_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    domain_id: Mapped[UUID] = mapped_column(Uuid)
    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_tasks.id", ondelete="CASCADE"), index=True
    )
    source_type: Mapped[str] = mapped_column(String(20), default=EvidenceSource.WEB.value)
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str | None] = mapped_column(String(2048))
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(128), index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    relevance_score: Mapped[float | None] = mapped_column(Float)
    credibility_score: Mapped[float | None] = mapped_column(Float)
    decision: Mapped[str] = mapped_column(String(20), default=EvidenceDecision.PENDING.value)
    rejection_reason: Mapped[str | None] = mapped_column(String(1000))
    citation_id: Mapped[str | None] = mapped_column(String(20))
    extra: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    task: Mapped[ResearchTaskRecord] = relationship(back_populates="evidence")


class FindingRecord(Base):
    __tablename__ = "findings"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_tasks.id", ondelete="CASCADE"), index=True
    )
    claim: Mapped[str] = mapped_column(Text)
    supporting_evidence_ids: Mapped[list[str]] = mapped_column(JSON)
    opposing_evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float)

    task: Mapped[ResearchTaskRecord] = relationship(back_populates="findings")


class ResearchEventRecord(Base):
    __tablename__ = "research_events"
    __table_args__ = (Index("ix_research_events_task_id_id", "task_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_tasks.id", ondelete="CASCADE"), index=True
    )
    node: Mapped[str | None] = mapped_column(String(60))
    event_type: Mapped[str] = mapped_column(
        String(40), default=ResearchEventType.NODE_PROGRESS.value
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    task: Mapped[ResearchTaskRecord] = relationship(back_populates="events")


class ReportRecord(Base):
    __tablename__ = "reports"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_tasks.id", ondelete="CASCADE"), unique=True, index=True
    )
    content: Mapped[str] = mapped_column(Text)
    citation_errors: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    task: Mapped[ResearchTaskRecord] = relationship(back_populates="report")
