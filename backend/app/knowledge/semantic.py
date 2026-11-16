from __future__ import annotations

from hashlib import sha256
from uuid import UUID

from app.domain import Evidence, EvidenceDecision, EvidenceSource, ResearchState
from app.knowledge.chunking import chunk_text
from app.knowledge.embeddings import Embedder
from app.knowledge.vector import VectorBackend, VectorEntry, VectorHit


class SemanticKnowledgeStore:
    def __init__(
        self,
        embedder: Embedder,
        backend: VectorBackend,
        *,
        collection_prefix: str,
        minimum_score: float = 0.05,
    ) -> None:
        self.embedder = embedder
        self.backend = backend
        self.documents_namespace = f"{collection_prefix}_documents"
        self.memories_namespace = f"{collection_prefix}_memories"
        self.minimum_score = minimum_score

    async def index_document(
        self,
        *,
        user_id: UUID,
        document_id: UUID,
        title: str,
        content: str,
        source_uri: str | None,
    ) -> int:
        chunks = chunk_text(content)
        vectors = await self.embedder.embed(chunks)
        entries = self._entries(
            user_id=user_id,
            document_id=document_id,
            title=title,
            source_uri=source_uri,
            chunks=chunks,
            vectors=vectors,
        )
        await self.backend.upsert(self.documents_namespace, entries)
        return len(entries)

    async def delete_document(self, *, user_id: UUID, document_id: UUID) -> None:
        await self.backend.delete(
            self.documents_namespace,
            user_id=str(user_id),
            document_id=str(document_id),
        )

    async def search_documents(
        self, *, user_id: UUID, query: str, limit: int = 5
    ) -> list[Evidence]:
        return await self._search(
            self.documents_namespace,
            user_id=user_id,
            query=query,
            limit=limit,
            source_type=EvidenceSource.LOCAL,
        )

    async def recall(self, *, user_id: UUID, topic: str, limit: int = 3) -> list[Evidence]:
        return await self._search(
            self.memories_namespace,
            user_id=user_id,
            query=topic,
            limit=limit,
            source_type=EvidenceSource.MEMORY,
        )

    async def remember(self, state: ResearchState) -> None:
        if not state["report"]:
            return
        chunks = chunk_text(state["report"])
        vectors = await self.embedder.embed(chunks)
        entries = self._entries(
            user_id=state["user_id"],
            document_id=state["task_id"],
            title=state["topic"],
            source_uri=None,
            chunks=chunks,
            vectors=vectors,
        )
        await self.backend.delete(
            self.memories_namespace,
            user_id=str(state["user_id"]),
            document_id=str(state["task_id"]),
        )
        await self.backend.upsert(self.memories_namespace, entries)

    async def _search(
        self,
        namespace: str,
        *,
        user_id: UUID,
        query: str,
        limit: int,
        source_type: EvidenceSource,
    ) -> list[Evidence]:
        vectors = await self.embedder.embed([query])
        if not vectors:
            return []
        hits = await self.backend.search(
            namespace,
            user_id=str(user_id),
            vector=vectors[0],
            limit=limit,
        )
        return [self._evidence(hit, source_type) for hit in hits if hit.score >= self.minimum_score]

    @staticmethod
    def _entries(
        *,
        user_id: UUID,
        document_id: UUID,
        title: str,
        source_uri: str | None,
        chunks: list[str],
        vectors: list[list[float]],
    ) -> list[VectorEntry]:
        if len(chunks) != len(vectors):
            raise ValueError("Embedding provider returned an unexpected vector count")
        return [
            VectorEntry(
                id=f"{document_id}:{index}",
                user_id=str(user_id),
                document_id=str(document_id),
                title=title,
                content=chunk,
                content_hash=sha256(chunk.encode()).hexdigest(),
                source_uri=source_uri or "",
                vector=vector,
            )
            for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
        ]

    @staticmethod
    def _evidence(hit: VectorHit, source_type: EvidenceSource) -> Evidence:
        return Evidence(
            source_type=source_type,
            title=hit.entry.title,
            url=hit.entry.source_uri or None,
            content=hit.entry.content,
            content_hash=hit.entry.content_hash,
            relevance_score=max(0.0, min(1.0, hit.score)),
            credibility_score=0.7 if source_type == EvidenceSource.LOCAL else 0.65,
            decision=EvidenceDecision.PENDING,
            metadata={
                "provider": "semantic_knowledge",
                "document_id": hit.entry.document_id,
                "vector_score": hit.score,
            },
        )
