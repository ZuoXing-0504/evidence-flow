from __future__ import annotations

import json
from typing import Annotated, Any, TypeVar
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain import Evidence, Finding, ResearchPlan
from app.research.adapters.http import ExternalProviderError, post_json

PayloadT = TypeVar("PayloadT", bound=BaseModel)
CitationId = Annotated[str, Field(pattern=r"^E[1-9][0-9]*$")]


class DashScopeMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    content: str


class DashScopeChoice(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: DashScopeMessage


class DashScopeCompletion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    choices: list[DashScopeChoice] = Field(min_length=1)


class CitationFinding(BaseModel):
    claim: str = Field(min_length=1, max_length=5000)
    supporting_citations: list[CitationId] = Field(min_length=1)
    opposing_citations: list[CitationId] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class AnalysisPayload(BaseModel):
    findings: list[CitationFinding]


class ReportPayload(BaseModel):
    report: str = Field(min_length=20)


def _evidence_context(evidence: list[Evidence]) -> list[dict[str, Any]]:
    return [
        {
            "citation_id": item.citation_id,
            "title": item.title,
            "url": item.url,
            "content": item.content[:4000],
            "relevance_score": item.relevance_score,
            "credibility_score": item.credibility_score,
        }
        for item in evidence[:20]
    ]


class DashScopeResearchModel:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        api_key: str,
        base_url: str,
        reasoning_model: str,
    ) -> None:
        self.client = client
        self.api_key = api_key
        self.url = f"{base_url.rstrip('/')}/chat/completions"
        self.reasoning_model = reasoning_model

    async def _complete_json(
        self,
        *,
        system: str,
        prompt: str,
        response_type: type[PayloadT],
    ) -> PayloadT:
        raw = await post_json(
            self.client,
            self.url,
            service="DashScope",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            payload={
                "model": self.reasoning_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
            },
        )
        try:
            completion = DashScopeCompletion.model_validate(raw)
            return response_type.model_validate_json(completion.choices[0].message.content)
        except (ValidationError, ValueError, IndexError) as exc:
            raise ExternalProviderError("DashScope returned invalid structured output") from exc

    async def create_plan(self, topic: str) -> ResearchPlan:
        prompt = json.dumps(
            {
                "topic": topic,
                "required_schema": {
                    "objective": "string",
                    "sections": ["3-8 report section names"],
                    "search_queries": ["3-8 focused web search queries"],
                    "expected_evidence": ["evidence categories"],
                },
            },
            ensure_ascii=False,
        )
        return await self._complete_json(
            system=(
                "You are a research planner. Return only one JSON object matching the supplied "
                "schema. Make queries specific, diverse, and suitable for evidence gathering."
            ),
            prompt=prompt,
            response_type=ResearchPlan,
        )

    async def analyze(self, topic: str, evidence: list[Evidence]) -> list[Finding]:
        prompt = json.dumps(
            {
                "topic": topic,
                "evidence": _evidence_context(evidence),
                "required_schema": {
                    "findings": [
                        {
                            "claim": "evidence-grounded claim",
                            "supporting_citations": ["E1"],
                            "opposing_citations": [],
                            "confidence": 0.0,
                        }
                    ]
                },
            },
            ensure_ascii=False,
        )
        payload = await self._complete_json(
            system=(
                "You are an evidence analyst. Use only the supplied evidence and exact citation "
                "IDs. Return JSON only. Never invent a citation or unsupported fact."
            ),
            prompt=prompt,
            response_type=AnalysisPayload,
        )
        evidence_ids = {item.citation_id: item.id for item in evidence if item.citation_id}
        findings: list[Finding] = []
        for item in payload.findings:
            supporting = [
                evidence_ids[value] for value in item.supporting_citations if value in evidence_ids
            ]
            opposing = [
                evidence_ids[value] for value in item.opposing_citations if value in evidence_ids
            ]
            if supporting:
                findings.append(
                    Finding(
                        claim=item.claim,
                        supporting_evidence_ids=supporting,
                        opposing_evidence_ids=opposing,
                        confidence=item.confidence,
                    )
                )
        if not findings and evidence:
            raise ExternalProviderError("DashScope analysis did not reference accepted evidence")
        return findings

    async def write_report(
        self,
        topic: str,
        plan: ResearchPlan | None,
        findings: list[Finding],
        evidence: list[Evidence],
    ) -> str:
        citation_by_id: dict[UUID, str] = {
            item.id: item.citation_id for item in evidence if item.citation_id
        }
        finding_context = [
            {
                "claim": item.claim,
                "supporting_citations": [
                    citation_by_id[value]
                    for value in item.supporting_evidence_ids
                    if value in citation_by_id
                ],
                "opposing_citations": [
                    citation_by_id[value]
                    for value in item.opposing_evidence_ids
                    if value in citation_by_id
                ],
                "confidence": item.confidence,
            }
            for item in findings
        ]
        prompt = json.dumps(
            {
                "topic": topic,
                "plan": plan.model_dump(mode="json") if plan else None,
                "findings": finding_context,
                "evidence": _evidence_context(evidence),
                "required_schema": {"report": "complete Markdown report"},
            },
            ensure_ascii=False,
        )
        payload = await self._complete_json(
            system=(
                "Write a rigorous Markdown research report using only supplied findings and "
                "evidence. Cite claims inline with exact [E#] IDs and finish with a Sources "
                "section. Return JSON only with a report field."
            ),
            prompt=prompt,
            response_type=ReportPayload,
        )
        return payload.report
