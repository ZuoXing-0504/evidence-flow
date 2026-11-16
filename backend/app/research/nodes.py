from __future__ import annotations

from typing import Any

from app.domain import (
    Evidence,
    EvidenceDecision,
    EvidenceSource,
    Finding,
    ResearchNode,
    ResearchState,
    ResearchStatus,
)
from app.research.citations import validate_citations
from app.research.contracts import (
    EvidenceRetriever,
    ReportWriter,
    ResearchAnalyst,
    ResearchMemory,
    ResearchPlanner,
)
from app.research.evidence_quality import assess_evidence


def _prefers_chinese(value: str) -> bool:
    return any("\u4e00" <= character <= "\u9fff" for character in value)


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
        memory: ResearchMemory | None = None,
    ) -> None:
        self.planner = planner
        self.web_retriever = web_retriever
        self.local_retriever = local_retriever
        self.minimum_evidence = minimum_evidence
        self.research_analyst = analyst
        self.report_writer = writer
        self.memory = memory

    async def memory_recall(self, state: ResearchState) -> dict[str, Any]:
        if self.memory is None:
            return {}
        try:
            evidence = await self.memory.recall(
                user_id=state["user_id"], topic=state["topic"], limit=3
            )
        except Exception:
            return {"warnings": ["Semantic memory recall is unavailable"]}
        return {"candidate_evidence": evidence}

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
        try:
            evidence = await self.local_retriever.search(state["topic"], state["search_queries"])
        except Exception:
            return {
                "candidate_evidence": [],
                "warnings": ["Local knowledge retrieval is unavailable"],
            }
        return {"candidate_evidence": evidence}

    async def evidence_judge(self, state: ResearchState) -> dict[str, Any]:
        accepted: list[Evidence] = []
        seen_hashes: set[str] = set()
        seen_urls: set[str] = set()
        seen_titles: set[str] = set()
        domain_counts: dict[str, int] = {}

        ranked: list[tuple[float, Evidence]] = []
        for candidate in state["candidate_evidence"]:
            item = candidate.model_copy(deep=True)
            quality = assess_evidence(state["topic"], item)
            item.relevance_score = quality.relevance
            item.credibility_score = quality.credibility
            item.metadata.update(
                {
                    "quality_rank": round(quality.rank, 4),
                    "quality_tier": quality.tier,
                    "source_domain": quality.domain,
                    "normalized_url": quality.normalized_url,
                }
            )
            ranked.append((quality.rank, item))

        for _, item in sorted(ranked, key=lambda value: value[0], reverse=True):
            normalized_url = str(item.metadata["normalized_url"])
            normalized_title = " ".join(item.title.casefold().split())
            domain = str(item.metadata["source_domain"])
            if (
                item.content_hash in seen_hashes
                or normalized_title in seen_titles
                or (normalized_url and normalized_url in seen_urls)
            ):
                item.decision = EvidenceDecision.DUPLICATE
                continue
            if (item.relevance_score or 0) < 0.3:
                item.decision = EvidenceDecision.REJECTED
                item.rejection_reason = "Evidence has insufficient topic overlap"
                continue
            if (item.credibility_score or 0) < 0.45:
                item.decision = EvidenceDecision.REJECTED
                item.rejection_reason = "Source credibility is below the acceptance threshold"
                continue
            domain_quota_reached = domain and domain_counts.get(domain, 0) >= 3
            if item.source_type == EvidenceSource.WEB and domain_quota_reached:
                item.decision = EvidenceDecision.REJECTED
                item.rejection_reason = "Source domain quota exceeded"
                continue
            item.decision = EvidenceDecision.ACCEPTED
            item.citation_id = f"E{len(accepted) + 1}"
            accepted.append(item)
            seen_hashes.add(item.content_hash)
            seen_titles.add(normalized_title)
            if normalized_url:
                seen_urls.add(normalized_url)
            if item.source_type == EvidenceSource.WEB and domain:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1

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
        chinese = _prefers_chinese(state["topic"])
        if not should_continue:
            if evidence_gap <= 0:
                missing = []
            elif chinese:
                missing = [f"至少还需要 {evidence_gap} 个信息来源"]
            else:
                missing = [f"At least {evidence_gap} more sources needed"]
            return {"should_continue": False, "missing_information": missing}

        next_iteration = state["iteration"] + 1
        if chinese:
            supplemental_queries = [
                f"{state['topic']} 补充独立来源 第 {next_iteration} 轮",
                f"{state['topic']} 一手数据 第 {next_iteration} 轮",
                f"{state['topic']} 反方证据 第 {next_iteration} 轮",
            ]
            missing_information = [f"还需要 {evidence_gap} 个补充来源"]
        else:
            supplemental_queries = [
                f"{state['topic']} additional independent source round {next_iteration}",
                f"{state['topic']} primary data round {next_iteration}",
                f"{state['topic']} contrary evidence round {next_iteration}",
            ]
            missing_information = [f"Need {evidence_gap} additional sources"]
        return {
            "iteration": next_iteration,
            "should_continue": True,
            "search_queries": supplemental_queries,
            "query_history": supplemental_queries,
            "missing_information": missing_information,
        }

    async def writer(self, state: ResearchState) -> dict[str, Any]:
        plan = state.get("plan")
        if self.report_writer is not None:
            report = await self.report_writer.write_report(
                state["topic"], plan, state["findings"], state["accepted_evidence"]
            )
            return {"report": report}
        chinese = _prefers_chinese(state["topic"])
        title = f"# {state['topic']}研究报告" if chinese else f"# {state['topic']} Research Report"
        objective_heading = "研究目标" if chinese else "Objective"
        objective = f"\n\n## {objective_heading}\n\n{plan.objective}" if plan else ""
        finding_lines = [
            f"- {finding.claim} [{state['accepted_evidence'][index].citation_id}]"
            for index, finding in enumerate(state["findings"])
        ]
        findings_heading = "核心发现" if chinese else "Findings"
        no_findings = "未检索到可靠证据。" if chinese else "No reliable evidence was retrieved."
        findings = f"\n\n## {findings_heading}\n\n" + (
            "\n".join(finding_lines) if finding_lines else no_findings
        )
        source_lines = [
            f"- [{item.citation_id}] {item.title} - "
            f"{item.url or ('本地知识库' if chinese else 'Local knowledge base')}"
            for item in state["accepted_evidence"]
        ]
        sources_heading = "参考来源" if chinese else "Sources"
        no_sources = "暂无可用来源。" if chinese else "No sources available."
        sources = f"\n\n## {sources_heading}\n\n" + (
            "\n".join(source_lines) if source_lines else no_sources
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
        if self.memory is None:
            return {}
        try:
            await self.memory.remember(state)
        except Exception:
            return {"warnings": ["Semantic memory commit is unavailable"]}
        return {}


def route_after_intent(state: ResearchState) -> str:
    return "failed" if state["errors"] else ResearchNode.PLANNER.value


def route_after_reflect(state: ResearchState) -> str:
    return "search" if state["should_continue"] else ResearchNode.WRITER.value


def terminal_failure(state: ResearchState) -> dict[str, Any]:
    del state
    return {"status": ResearchStatus.FAILED}
