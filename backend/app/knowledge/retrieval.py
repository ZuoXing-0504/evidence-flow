from __future__ import annotations

import asyncio
from uuid import UUID

from app.domain import Evidence
from app.knowledge.store import KnowledgeStore


class KnowledgeRetriever:
    def __init__(self, store: KnowledgeStore, user_id: UUID, *, results_per_query: int = 3) -> None:
        self.store = store
        self.user_id = user_id
        self.results_per_query = results_per_query

    async def search(self, topic: str, queries: list[str]) -> list[Evidence]:
        search_queries = queries or [topic]
        batches = await asyncio.gather(
            *(
                self.store.search_documents(
                    user_id=self.user_id,
                    query=query,
                    limit=self.results_per_query,
                )
                for query in search_queries
            )
        )
        return [item for batch in batches for item in batch]
