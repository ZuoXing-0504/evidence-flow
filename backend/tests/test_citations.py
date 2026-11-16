from hashlib import sha256

from app.domain import Evidence, EvidenceDecision, EvidenceSource
from app.research.citations import extract_citations, validate_citations


def make_evidence(citation_id: str = "E1") -> Evidence:
    content = "Source content"
    return Evidence(
        source_type=EvidenceSource.WEB,
        title="Source",
        url="https://example.com/source",
        content=content,
        content_hash=sha256(content.encode()).hexdigest(),
        decision=EvidenceDecision.ACCEPTED,
        citation_id=citation_id,
    )


def test_extract_citations_preserves_first_occurrence_order() -> None:
    assert extract_citations("Claim [E2], another [E1], repeated [E2]") == ["E2", "E1"]


def test_validator_rejects_unknown_citation() -> None:
    errors = validate_citations("A supported claim [E2]", [make_evidence()])

    assert errors == ["Citation [E2] does not map to accepted evidence"]


def test_validator_requires_citation_when_evidence_exists() -> None:
    assert validate_citations("No citation", [make_evidence()]) == [
        "The report contains no evidence citations"
    ]


def test_validator_warns_when_no_evidence_exists() -> None:
    assert validate_citations("No evidence available", []) == ["No accepted evidence is available"]
