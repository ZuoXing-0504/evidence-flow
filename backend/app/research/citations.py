import re

from app.domain import Evidence

CITATION_PATTERN = re.compile(r"\[(E[1-9][0-9]*)\]")


def extract_citations(report: str) -> list[str]:
    return list(dict.fromkeys(CITATION_PATTERN.findall(report)))


def validate_citations(report: str, evidence: list[Evidence]) -> list[str]:
    if not evidence:
        return ["No accepted evidence is available"]

    available = {item.citation_id for item in evidence if item.citation_id}
    cited = set(extract_citations(report))
    errors: list[str] = []

    for citation in sorted(cited - available):
        errors.append(f"Citation [{citation}] does not map to accepted evidence")

    if not cited:
        errors.append("The report contains no evidence citations")

    return errors
