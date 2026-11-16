from hashlib import sha256
from typing import cast

import pytest

from app.domain import Evidence, EvidenceSource, ResearchState
from app.research.evidence_quality import assess_evidence, domain_key, normalize_url, tokenize
from app.research.mock import MockPlanner, StaticRetriever
from app.research.nodes import ResearchNodes


def _evidence(url: str, title: str, content: str) -> Evidence:
    return Evidence(
        source_type=EvidenceSource.WEB,
        title=title,
        url=url,
        content=content,
        content_hash=sha256(content.encode()).hexdigest(),
        metadata={"provider": "bocha", "query": "金融行业 Agent 应用"},
    )


def test_chinese_tokenization_and_url_normalization() -> None:
    assert {"金融", "行业", "agent"} <= tokenize("金融行业 Agent 应用")
    assert (
        normalize_url("HTTPS://WWW.Example.com/report/?utm_source=test&b=2&a=1#summary")
        == "https://example.com/report?a=1&b=2"
    )
    assert domain_key("https://finance.sina.com.cn/article") == "sina.com.cn"
    assert normalize_url("https://example.com:invalid/report") == (
        "https://example.com:invalid/report"
    )


def test_authoritative_sources_score_above_document_aggregators() -> None:
    content = "金融行业正在评估 Agent 在风险管理和客户服务中的应用。" * 3
    authority = _evidence("https://www.pbc.gov.cn/report", "金融科技报告", content)
    aggregator = _evidence("https://www.wenkub.com/document", "金融行业资料", content)

    authority_quality = assess_evidence("金融行业 Agent 应用", authority)
    aggregator_quality = assess_evidence("金融行业 Agent 应用", aggregator)

    assert authority_quality.tier == "authority"
    assert authority_quality.credibility > 0.9
    assert aggregator_quality.tier == "aggregator"
    assert aggregator_quality.credibility < 0.45


def test_user_generated_subdomains_do_not_inherit_publisher_trust() -> None:
    content = "金融行业正在评估 Agent 在风险管理和客户服务中的应用。" * 3
    item = _evidence("https://guba.sina.cn/article", "个人观点", content)

    quality = assess_evidence("金融行业 Agent 应用", item)

    assert quality.tier == "user_generated"
    assert quality.credibility < 0.45


@pytest.mark.asyncio
async def test_evidence_judge_filters_low_quality_and_limits_each_domain() -> None:
    topic = "金融行业 Agent 应用"
    content = "金融行业正在评估 Agent 在风险管理和客户服务中的应用。" * 3
    candidates = [
        _evidence("https://www.pbc.gov.cn/report", "金融科技监管报告", content + "监管"),
        _evidence("https://www.wenkub.com/document", "聚合文档", content + "聚合"),
        *[
            _evidence(
                f"https://www.reuters.com/technology/article-{index}",
                f"Financial agents report {index}",
                content + str(index),
            )
            for index in range(4)
        ],
    ]
    nodes = ResearchNodes(MockPlanner(), StaticRetriever(), StaticRetriever())

    state = cast(ResearchState, {"topic": topic, "candidate_evidence": candidates})
    result = await nodes.evidence_judge(state)
    accepted = result["accepted_evidence"]

    assert len(accepted) == 4
    assert accepted[0].url == "https://www.pbc.gov.cn/report"
    assert all("wenkub.com" not in (item.url or "") for item in accepted)
    assert sum("reuters.com" in (item.url or "") for item in accepted) == 3
    assert [item.citation_id for item in accepted] == ["E1", "E2", "E3", "E4"]
