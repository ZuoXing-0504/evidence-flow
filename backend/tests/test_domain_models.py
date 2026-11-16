from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain import Evidence, EvidenceDecision, EvidenceSource, Finding, ResearchPlan


def test_plan_normalizes_and_deduplicates_queries() -> None:
    plan = ResearchPlan(
        objective="Compare the market",
        sections=["Market size"],
        search_queries=["AI market 2026", " AI   market 2026 ", "China AI policy"],
    )

    assert plan.search_queries == ["AI market 2026", "China AI policy"]


def test_web_evidence_requires_url() -> None:
    with pytest.raises(ValidationError, match="must include a URL"):
        Evidence(
            source_type=EvidenceSource.WEB,
            title="Source",
            content="Evidence content",
            content_hash="a" * 64,
        )


def test_rejected_evidence_requires_reason() -> None:
    with pytest.raises(ValidationError, match="must include a reason"):
        Evidence(
            source_type=EvidenceSource.LOCAL,
            title="Document",
            content="Evidence content",
            content_hash="b" * 64,
            decision=EvidenceDecision.REJECTED,
        )


def test_finding_requires_supporting_evidence() -> None:
    with pytest.raises(ValidationError):
        Finding(claim="A claim", supporting_evidence_ids=[], confidence=0.8)


def test_valid_finding() -> None:
    evidence_id = uuid4()
    finding = Finding(
        claim="The market is growing",
        supporting_evidence_ids=[evidence_id],
        confidence=0.82,
    )

    assert finding.supporting_evidence_ids == [evidence_id]
