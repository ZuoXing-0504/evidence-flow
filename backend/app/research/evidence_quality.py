from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.domain import Evidence, EvidenceSource

_WORD_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+#]*|[\u4e00-\u9fff]+")
_TRACKING_PARAMETERS = {
    "from",
    "ref",
    "source",
    "spm",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}
_MULTIPART_SUFFIXES = {
    "ac.uk",
    "co.jp",
    "co.uk",
    "com.au",
    "com.cn",
    "edu.cn",
    "gov.cn",
    "net.cn",
    "org.cn",
    "org.uk",
}
_LOW_QUALITY_HOSTS = {
    "360doc.com",
    "book118.com",
    "doc88.com",
    "docin.com",
    "mianfeiwendang.com",
    "renrendoc.com",
    "sgpjbg.com",
    "taodocs.com",
    "wenku.baidu.com",
    "wenkub.com",
}
_USER_GENERATED_HOSTS = {
    "baijiahao.baidu.com",
    "blog.csdn.net",
    "guba.eastmoney.com",
    "guba.sina.cn",
    "mp.weixin.qq.com",
    "toutiao.com",
    "zhuanlan.zhihu.com",
}
_AUTHORITATIVE_HOSTS = {
    "europa.eu",
    "imf.org",
    "oecd.org",
    "un.org",
    "who.int",
    "worldbank.org",
}
_TRUSTED_RESEARCH_HOSTS = {
    "arxiv.org",
    "brookings.edu",
    "cset.georgetown.edu",
    "cnki.net",
    "gartner.com",
    "mckinsey.com",
    "nature.com",
    "rand.org",
    "sciencedirect.com",
    "ssrn.com",
}
_TRUSTED_NEWS_HOSTS = {
    "bloomberg.com",
    "caixin.com",
    "cnstock.com",
    "eastmoney.com",
    "ft.com",
    "jrj.com.cn",
    "people.com.cn",
    "reuters.com",
    "sina.cn",
    "sina.com.cn",
    "sohu.com",
    "stcn.com",
    "thepaper.cn",
    "wsj.com",
    "xinhuanet.com",
}


@dataclass(frozen=True, slots=True)
class EvidenceQuality:
    relevance: float
    credibility: float
    normalized_url: str
    domain: str
    tier: str

    @property
    def rank(self) -> float:
        return self.relevance * 0.45 + self.credibility * 0.55


def tokenize(value: str) -> set[str]:
    tokens: set[str] = set()
    for match in _WORD_PATTERN.findall(value.casefold()):
        if "\u4e00" <= match[0] <= "\u9fff":
            if len(match) == 1:
                tokens.add(match)
            else:
                tokens.update(match[index : index + 2] for index in range(len(match) - 1))
        elif len(match) > 1:
            tokens.add(match)
    return tokens


def normalize_url(value: str | None) -> str:
    if not value:
        return ""
    try:
        parsed = urlsplit(value.strip())
    except ValueError:
        return value.strip().casefold()
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
        return value.strip().casefold()

    scheme = parsed.scheme.casefold()
    host = parsed.hostname.casefold().removeprefix("www.")
    try:
        port = parsed.port
    except ValueError:
        return value.strip().casefold()
    default_port = port is None or (scheme, port) in {("http", 80), ("https", 443)}
    netloc = host if default_port else f"{host}:{port}"
    path = re.sub(r"/{2,}", "/", parsed.path).rstrip("/")
    query = urlencode(
        sorted(
            (key, item)
            for key, item in parse_qsl(parsed.query, keep_blank_values=True)
            if key.casefold() not in _TRACKING_PARAMETERS
        )
    )
    return urlunsplit((scheme, netloc, path, query, ""))


def domain_key(value: str | None) -> str:
    if not value:
        return ""
    try:
        host = (urlsplit(value).hostname or "").casefold().removeprefix("www.")
    except ValueError:
        return ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    suffix = ".".join(parts[-2:])
    return ".".join(parts[-3:]) if suffix in _MULTIPART_SUFFIXES else suffix


def _matches_host(host: str, candidates: set[str]) -> bool:
    return any(host == candidate or host.endswith(f".{candidate}") for candidate in candidates)


def _web_credibility(item: Evidence) -> tuple[float, str]:
    try:
        parsed = urlsplit(item.url or "")
        host = (parsed.hostname or "").casefold().removeprefix("www.")
    except ValueError:
        return 0.2, "invalid"
    if parsed.scheme.casefold() not in {"http", "https"} or not host:
        return 0.2, "invalid"
    if _matches_host(host, _LOW_QUALITY_HOSTS):
        return 0.32, "aggregator"
    if _matches_host(host, _USER_GENERATED_HOSTS):
        return 0.42, "user_generated"
    if host.endswith((".gov", ".gov.cn", ".edu", ".edu.cn")) or _matches_host(
        host, _AUTHORITATIVE_HOSTS
    ):
        score, tier = 0.92, "authority"
    elif _matches_host(host, _TRUSTED_RESEARCH_HOSTS):
        score, tier = 0.84, "research"
    elif _matches_host(host, _TRUSTED_NEWS_HOSTS):
        score, tier = 0.76, "publisher"
    else:
        score, tier = 0.6, "standard"

    if parsed.scheme.casefold() == "https":
        score += 0.02
    if item.published_at is not None:
        score += 0.02
    if item.metadata.get("site_name"):
        score += 0.01
    if len(item.content) >= 300:
        score += 0.01
    elif len(item.content) < 80:
        score -= 0.05
    return min(1.0, max(0.0, score)), tier


def assess_evidence(topic: str, item: Evidence) -> EvidenceQuality:
    topic_tokens = tokenize(topic)
    query_tokens = tokenize(str(item.metadata.get("query", "")))
    content_tokens = tokenize(f"{item.title} {item.content}")

    def coverage(expected: set[str]) -> float:
        return len(expected & content_tokens) / len(expected) if expected else 0.0

    lexical_score = min(1.0, 0.25 + max(coverage(topic_tokens), coverage(query_tokens)) * 0.75)
    relevance = (
        lexical_score
        if item.relevance_score is None
        else item.relevance_score * 0.7 + lexical_score * 0.3
    )

    if item.source_type == EvidenceSource.LOCAL:
        credibility, tier = 0.82, "local"
    elif item.source_type == EvidenceSource.MEMORY:
        credibility, tier = 0.72, "memory"
    elif item.metadata.get("provider") == "mock":
        credibility, tier = 0.65, "mock"
    else:
        credibility, tier = _web_credibility(item)
    if item.credibility_score is not None:
        credibility = item.credibility_score * 0.7 + credibility * 0.3

    return EvidenceQuality(
        relevance=min(1.0, max(0.0, relevance)),
        credibility=min(1.0, max(0.0, credibility)),
        normalized_url=normalize_url(item.url),
        domain=domain_key(item.url),
        tier=tier,
    )
