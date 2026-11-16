from __future__ import annotations

import asyncio
from datetime import datetime
from hashlib import sha256

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain import Evidence, EvidenceSource
from app.research.adapters.http import ExternalProviderError, post_json


class BochaSearchItem(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    name: str = Field(min_length=1)
    url: str = Field(min_length=1)
    snippet: str = ""
    summary: str | None = None
    site_name: str | None = Field(default=None, alias="siteName")
    date_published: str | None = Field(default=None, alias="datePublished")


class BochaWebPages(BaseModel):
    model_config = ConfigDict(extra="ignore")

    value: list[BochaSearchItem] = Field(default_factory=list)


class BochaData(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    web_pages: BochaWebPages | None = Field(default=None, alias="webPages")


class BochaResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    code: int
    msg: str | None = None
    data: BochaData | None = None


def _published_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class BochaWebRetriever:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        api_key: str,
        base_url: str,
        results_per_query: int = 5,
    ) -> None:
        self.client = client
        self.api_key = api_key
        self.url = f"{base_url.rstrip('/')}/web-search"
        self.results_per_query = results_per_query

    async def search(self, topic: str, queries: list[str]) -> list[Evidence]:
        del topic
        batches = await asyncio.gather(*(self._search_query(query) for query in queries))
        return [item for batch in batches for item in batch]

    async def _search_query(self, query: str) -> list[Evidence]:
        raw = await post_json(
            self.client,
            self.url,
            service="Bocha Web Search",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            payload={
                "query": query,
                "freshness": "noLimit",
                "summary": True,
                "count": self.results_per_query,
            },
        )
        try:
            response = BochaResponse.model_validate(raw)
        except ValidationError as exc:
            raise ExternalProviderError("Bocha Web Search returned invalid data") from exc
        if response.code != 200 or response.data is None:
            raise ExternalProviderError(
                f"Bocha Web Search rejected the request with code {response.code}"
            )

        items = response.data.web_pages.value if response.data.web_pages else []
        evidence: list[Evidence] = []
        for item in items:
            content = (item.summary or item.snippet).strip()
            if not content:
                continue
            evidence.append(
                Evidence(
                    source_type=EvidenceSource.WEB,
                    title=item.name,
                    url=item.url,
                    content=content,
                    published_at=_published_at(item.date_published),
                    content_hash=sha256(content.encode()).hexdigest(),
                    metadata={
                        "provider": "bocha",
                        "query": query,
                        "site_name": item.site_name,
                    },
                )
            )
        return evidence
