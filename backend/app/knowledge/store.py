from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain import Evidence, ResearchState


class KnowledgeStore(Protocol):
    async def index_document(
        self,
        *,
        user_id: UUID,
        document_id: UUID,
        title: str,
        content: str,
        source_uri: str | None,
    ) -> int: ...

    async def delete_document(self, *, user_id: UUID, document_id: UUID) -> None: ...

    async def search_documents(
        self, *, user_id: UUID, query: str, limit: int = 5
    ) -> list[Evidence]: ...

    async def recall(self, *, user_id: UUID, topic: str, limit: int = 3) -> list[Evidence]: ...

    async def remember(self, state: ResearchState) -> None: ...
