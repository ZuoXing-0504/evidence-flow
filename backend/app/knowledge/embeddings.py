from __future__ import annotations

import math
import re
from collections.abc import Sequence
from hashlib import sha256
from typing import Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.research.adapters.http import ExternalProviderError, post_json

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", re.UNICODE)


def _tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for match in TOKEN_PATTERN.findall(text.casefold()):
        if "\u4e00" <= match[0] <= "\u9fff" and len(match) > 1:
            tokens.extend(match[index : index + 2] for index in range(len(match) - 1))
        else:
            tokens.append(match)
    return tokens


class Embedder(Protocol):
    @property
    def dimension(self) -> int: ...

    async def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class DeterministicEmbedder:
    def __init__(self, dimension: int = 64) -> None:
        if dimension < 8:
            raise ValueError("Embedding dimension must be at least 8")
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in _tokens(text):
            digest = sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector


class EmbeddingItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    index: int
    embedding: list[float] = Field(min_length=1)


class EmbeddingResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    data: list[EmbeddingItem]


class DashScopeEmbedder:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        dimension: int,
        timeout: float,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key
        self.url = f"{base_url.rstrip('/')}/embeddings"
        self.model = model
        self._dimension = dimension
        self.timeout = timeout
        self.client = client

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        values = list(texts)
        if self.client is not None:
            return await self._embed_all(self.client, values)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            return await self._embed_all(client, values)

    async def _embed_all(self, client: httpx.AsyncClient, values: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(values), 10):
            vectors.extend(await self._embed_batch(client, values[start : start + 10]))
        return vectors

    async def _embed_batch(self, client: httpx.AsyncClient, texts: list[str]) -> list[list[float]]:
        raw = await post_json(
            client,
            self.url,
            service="DashScope Embeddings",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            payload={
                "model": self.model,
                "input": texts,
                "dimensions": self.dimension,
                "encoding_format": "float",
            },
        )
        try:
            response = EmbeddingResponse.model_validate(raw)
        except ValidationError as exc:
            raise ExternalProviderError("DashScope Embeddings returned invalid data") from exc
        ordered = sorted(response.data, key=lambda item: item.index)
        if len(ordered) != len(texts) or any(
            len(item.embedding) != self.dimension for item in ordered
        ):
            raise ExternalProviderError("DashScope Embeddings returned unexpected dimensions")
        return [item.embedding for item in ordered]
