from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from typing import Any, Protocol

from pymilvus import DataType, MilvusClient  # type: ignore[import-untyped]


@dataclass(frozen=True, slots=True)
class VectorEntry:
    id: str
    user_id: str
    document_id: str
    title: str
    content: str
    content_hash: str
    source_uri: str
    vector: list[float]


@dataclass(frozen=True, slots=True)
class VectorHit:
    entry: VectorEntry
    score: float


class VectorBackend(Protocol):
    async def upsert(self, namespace: str, entries: list[VectorEntry]) -> None: ...

    async def search(
        self,
        namespace: str,
        *,
        user_id: str,
        vector: list[float],
        limit: int,
    ) -> list[VectorHit]: ...

    async def delete(self, namespace: str, *, user_id: str, document_id: str) -> None: ...


def _cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


class InMemoryVectorBackend:
    def __init__(self) -> None:
        self._entries: dict[str, dict[str, VectorEntry]] = {}
        self._lock = asyncio.Lock()

    async def upsert(self, namespace: str, entries: list[VectorEntry]) -> None:
        async with self._lock:
            collection = self._entries.setdefault(namespace, {})
            collection.update({entry.id: entry for entry in entries})

    async def search(
        self,
        namespace: str,
        *,
        user_id: str,
        vector: list[float],
        limit: int,
    ) -> list[VectorHit]:
        async with self._lock:
            entries = list(self._entries.get(namespace, {}).values())
        hits = [
            VectorHit(entry=entry, score=_cosine(vector, entry.vector))
            for entry in entries
            if entry.user_id == user_id
        ]
        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:limit]

    async def delete(self, namespace: str, *, user_id: str, document_id: str) -> None:
        async with self._lock:
            collection = self._entries.get(namespace, {})
            matching = [
                entry_id
                for entry_id, entry in collection.items()
                if entry.user_id == user_id and entry.document_id == document_id
            ]
            for entry_id in matching:
                del collection[entry_id]


class MilvusVectorBackend:
    def __init__(self, *, uri: str, dimension: int, client: Any | None = None) -> None:
        self.client: Any = client or MilvusClient(uri=uri)
        self.dimension = dimension
        self._initialized: set[str] = set()
        self._init_lock = asyncio.Lock()

    async def _ensure_collection(self, namespace: str) -> None:
        if namespace in self._initialized:
            return
        async with self._init_lock:
            if namespace in self._initialized:
                return
            await asyncio.to_thread(self._ensure_collection_sync, namespace)
            self._initialized.add(namespace)

    def _ensure_collection_sync(self, namespace: str) -> None:
        if not self.client.has_collection(collection_name=namespace):
            schema = self.client.create_schema(auto_id=False, enable_dynamic_field=False)
            schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=100)
            schema.add_field("user_id", DataType.VARCHAR, max_length=36)
            schema.add_field("document_id", DataType.VARCHAR, max_length=36)
            schema.add_field("title", DataType.VARCHAR, max_length=500)
            schema.add_field("content", DataType.VARCHAR, max_length=65535)
            schema.add_field("content_hash", DataType.VARCHAR, max_length=128)
            schema.add_field("source_uri", DataType.VARCHAR, max_length=2048)
            schema.add_field("vector", DataType.FLOAT_VECTOR, dim=self.dimension)
            indexes = self.client.prepare_index_params()
            indexes.add_index(field_name="vector", index_type="AUTOINDEX", metric_type="COSINE")
            try:
                self.client.create_collection(
                    collection_name=namespace,
                    schema=schema,
                    index_params=indexes,
                )
            except Exception:
                if not self.client.has_collection(collection_name=namespace):
                    raise
        self.client.load_collection(collection_name=namespace)

    async def upsert(self, namespace: str, entries: list[VectorEntry]) -> None:
        if not entries:
            return
        await self._ensure_collection(namespace)
        data = [
            {
                "id": entry.id,
                "user_id": entry.user_id,
                "document_id": entry.document_id,
                "title": entry.title,
                "content": entry.content,
                "content_hash": entry.content_hash,
                "source_uri": entry.source_uri,
                "vector": entry.vector,
            }
            for entry in entries
        ]
        await asyncio.to_thread(self.client.upsert, collection_name=namespace, data=data)

    async def search(
        self,
        namespace: str,
        *,
        user_id: str,
        vector: list[float],
        limit: int,
    ) -> list[VectorHit]:
        await self._ensure_collection(namespace)
        raw = await asyncio.to_thread(
            self.client.search,
            collection_name=namespace,
            data=[vector],
            filter=f'user_id == "{user_id}"',
            limit=limit,
            output_fields=[
                "user_id",
                "document_id",
                "title",
                "content",
                "content_hash",
                "source_uri",
            ],
            search_params={"metric_type": "COSINE", "params": {}},
        )
        hits: list[VectorHit] = []
        for item in raw[0] if raw else []:
            entity = item.get("entity", {})
            entry = VectorEntry(
                id=str(item.get("id", "")),
                user_id=str(entity.get("user_id", "")),
                document_id=str(entity.get("document_id", "")),
                title=str(entity.get("title", "")),
                content=str(entity.get("content", "")),
                content_hash=str(entity.get("content_hash", "")),
                source_uri=str(entity.get("source_uri", "")),
                vector=[],
            )
            hits.append(VectorHit(entry=entry, score=float(item.get("distance", 0.0))))
        return hits

    async def delete(self, namespace: str, *, user_id: str, document_id: str) -> None:
        await self._ensure_collection(namespace)
        expression = f'user_id == "{user_id}" and document_id == "{document_id}"'
        await asyncio.to_thread(
            self.client.delete,
            collection_name=namespace,
            filter=expression,
        )
