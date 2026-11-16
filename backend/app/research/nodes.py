from __future__ import annotations

from typing import Any

from app.domain import (
    Evidence,
    EvidenceDecision,
    Finding,
    ResearchNode,
    ResearchState,
    ResearchStatus,
)
from app.research.citations import validate_citations
from app.research.contracts import EvidenceRetriever, ReportWriter, ResearchAnalyst, ResearchPlanner


def _tokenize(value: str) -> set[str]:
    return {token.casefold() for token in value.replace("-", " ").split() if len(token) > 1}


class ResearchNodes:
    def __init__(
        self,
        planner: ResearchPlanner,
        web_retriever: EvidenceRetriever,
        local_retriever: EvidenceRetriever,
        *,
        minimum_evidence: int = 3,
        analyst: ResearchAnalyst | None = None,
        writer: ReportWriter | None = None,
    ) -> None:
        self.planner = planner
        self.web_retriever = web_retriever
        self.local_retriever = local_retriever
        self.minimum_evidence = minimum_evidence
        self.research_analyst = analyst
        self.report_writer = writer

    async def memory_recall(self, state: ResearchState) -> dict[str, Any]:
        del state
        return {}

    async def intent_router(self, state: ResearchState) -> dict[str, Any]:
        topic = " ".join(state["topic"].split())
        if len(topic) < 3:
            return {"errors": ["Research topic must contain at least 3 characters"]}
        return {"topic": topic, "status": ResearchStatus.RUNNING}

    async def planner_node(self, state: ResearchState) -> dict[str, Any]:
        plan = await self.planner.create_plan(state["topic"])
        return {
            "plan": plan,
            "search_queries": plan.search_queries,
            "query_history": plan.search_queries,
        }

    async def dispatch_search(self, state: ResearchState) -> dict[str, Any]:
        del state
        return {}

    async def web_scout(self, state: ResearchState) -> dict[str, Any]:
        evidence = await self.web_retriever.search(state["topic"], state["search_queries"])
        return {"candidate_evidence": evidence}

    async def local_scout(self, state: ResearchState) -> dict[str, Any]:
        evidence = await self.local_retriever.search(state["topic"], state["search_queries"])
        return {"candidate_evidence": evidence}

    async def evidence_judge(self, state: ResearchState) -> dict[str, Any]:
        topic_tokens = _tokenize(state["topic"])
        accepted: list[Evidence] = []
        seen_hashes: set[str] = set()
        seen_urls: set[str] = set()

        for candidate in state["candidate_evidence"]:
            item = candidate.model_copy(deep=True)
            normalized_url = item.url.rstrip("/").casefold() if item.url else ""
            if item.content_hash in seen_hashes or (normalized_url and normalized_url in seen_urls):
                item.decision = EvidenceDecision.DUPLICATE
                continue

            content_tokens = _tokenize(f"{item.title} {item.content}")
            overlap = len(topic_tokens & content_tokens)
            item.relevance_score = min(1.0, 0.55 + overlap * 0.1)
            item.credibility_score = 0.6 if item.url else 0.7
            item.decision = EvidenceDecision.ACCEPTED
            item.citation_id = f"E{len(accepted) + 1}"
            accepted.append(item)
            seen_hashes.add(item.content_hash)
            if normalized_url:
                seen_urls.add(normalized_url)

        return {"accepted_evidence": accepted}

    async def analyst(self, state: ResearchState) -> dict[str, Any]:
        if self.research_analyst is not None:
            findings = await self.research_analyst.analyze(
                state["topic"], state["accepted_evidence"]
            )
            return {"findings": findings}
        findings = [
            Finding(
                claim=f"{item.title}: {item.content[:300]}",
                supporting_evidence_ids=[item.id],
                confidence=((item.relevance_score or 0.0) + (item.credibility_score or 0.0)) / 2,
            )
            for item in state["accepted_evidence"]
        ]
        return {"findings": findings}

    async def reflect(self, state: ResearchState) -> dict[str, Any]:
        evidence_gap = self.minimum_evidence - len(state["accepted_evidence"])
        can_retry = state["iteration"] < state["max_iterations"]
        should_continue = evidence_gap > 0 and can_retry
        if not should_continue:
            missing = [] if evidence_gap <= 0 else [f"At least {evidence_gap} more sources needed"]
            return {"should_continue": False, "missing_information": missing}

        next_iteration = state["iteration"] + 1
        supplemental_queries = [
            f"{state['topic']} additional independent source round {next_iteration}",
            f"{state['topic']} primary data round {next_iteration}",
            f"{state['topic']} contrary evidence round {next_iteration}",
        ]
        return {
            "iteration": next_iteration,
            "should_continue": True,
            "search_queries": supplemental_queries,
            "query_history": supplemental_queries,
            "missing_information": [f"Need {evidence_gap} additional sources"],
        }

    async def writer(self, state: ResearchState) -> dict[str, Any]:
        plan = state.get("plan")
        if self.report_writer is not None:
            report = await self.report_writer.write_report(
                state["topic"], plan, state["findings"], state["accepted_evidence"]
            )
            return {"report": report}
        title = f"# {state['topic']} Research Report"
        objective = f"\n\n## Objective\n\n{plan.objective}" if plan else ""
        finding_lines = [
            f"- {finding.claim} [{state['accepted_evidence'][index].citation_id}]"
            for index, finding in enumerate(state["findings"])
        ]
        findings = "\n\n## Findings\n\n" + (
            "\n".join(finding_lines) if finding_lines else "No reliable evidence was retrieved."
        )
        source_lines = [
            f"- [{item.citation_id}] {item.title} - {item.url or 'Local knowledge base'}"
            for item in state["accepted_evidence"]
        ]
        sources = "\n\n## Sources\n\n" + (
            "\n".join(source_lines) if source_lines else "No sources available."
        )
        return {"report": title + objective + findings + sources}

    async def citation_validator(self, state: ResearchState) -> dict[str, Any]:
        errors = validate_citations(state["report"], state["accepted_evidence"])
        status = ResearchStatus.COMPLETED_WITH_WARNINGS if errors else ResearchStatus.COMPLETED
        return {
            "citation_errors": errors,
            "warnings": errors,
            "status": status,
        }

    async def memory_commit(self, state: ResearchState) -> dict[str, Any]:
        del state
        return {}


def route_after_intent(state: ResearchState) -> str:
    return "failed" if state["errors"] else ResearchNode.PLANNER.value


def route_after_reflect(state: ResearchState) -> str:
    return "search" if state["should_continue"] else ResearchNode.WRITER.value


def terminal_failure(state: ResearchState) -> dict[str, Any]:
    del state
    return {"status": ResearchStatus.FAILED}
