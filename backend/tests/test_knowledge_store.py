from __future__ import annotations

import json
from uuid import uuid4

import httpx
import pytest

from app.domain import EvidenceSource
from app.knowledge.chunking import chunk_text
from app.knowledge.embeddings import DashScopeEmbedder, DeterministicEmbedder
from app.knowledge.retrieval import KnowledgeRetriever
from app.knowledge.semantic import SemanticKnowledgeStore
from app.knowledge.vector import InMemoryVectorBackend, MilvusVectorBackend, VectorEntry
from app.research import MockPlanner, StaticRetriever, build_research_graph
from app.research.workflow import create_initial_state


def _store() -> SemanticKnowledgeStore:
    return SemanticKnowledgeStore(
        DeterministicEmbedder(64),
        InMemoryVectorBackend(),
        collection_prefix="test",
    )


def test_chunk_text_is_bounded_and_overlapping() -> None:
    text = " ".join(f"word-{index}" for index in range(300))
    chunks = chunk_text(text, chunk_size=200, overlap=30)

    assert len(chunks) > 2
    assert all(len(chunk) <= 200 for chunk in chunks)
    assert chunk_text("  \n ") == []
    with pytest.raises(ValueError, match="chunk_size"):
        chunk_text(text, chunk_size=50)
    with pytest.raises(ValueError, match="overlap"):
        chunk_text(text, chunk_size=200, overlap=200)


@pytest.mark.asyncio
async def test_document_search_and_memory_are_user_isolated() -> None:
    store = _store()
    owner_id = uuid4()
    other_id = uuid4()
    document_id = uuid4()
    count = await store.index_document(
        user_id=owner_id,
        document_id=document_id,
        title="Semiconductor supply report",
        content="Semiconductor supply chains face advanced packaging capacity constraints.",
        source_uri="https://example.com/chips",
    )

    assert count == 1
    owner_results = await store.search_documents(
        user_id=owner_id, query="semiconductor packaging capacity"
    )
    other_results = await store.search_documents(
        user_id=other_id, query="semiconductor packaging capacity"
    )
    assert len(owner_results) == 1
    assert owner_results[0].source_type == EvidenceSource.LOCAL
    assert owner_results[0].metadata["document_id"] == str(document_id)
    assert other_results == []

    state = create_initial_state("Semiconductor outlook", user_id=owner_id)
    state["report"] = "Semiconductor packaging capacity remains constrained [E1]."
    await store.remember(state)
    recalled = await store.recall(user_id=owner_id, topic="semiconductor packaging")
    assert len(recalled) == 1
    assert recalled[0].source_type == EvidenceSource.MEMORY
    assert await store.recall(user_id=other_id, topic="semiconductor packaging") == []

    await store.delete_document(user_id=owner_id, document_id=document_id)
    assert (
        await store.search_documents(user_id=owner_id, query="semiconductor packaging capacity")
        == []
    )


@pytest.mark.asyncio
async def test_deterministic_embeddings_support_chinese_retrieval() -> None:
    store = _store()
    user_id = uuid4()
    await store.index_document(
        user_id=user_id,
        document_id=uuid4(),
        title="人工智能行业报告",
        content="人工智能智能体正在企业客户服务场景中加速落地。",
        source_uri=None,
    )

    results = await store.search_documents(user_id=user_id, query="智能体客户服务")

    assert results
    assert results[0].title == "人工智能行业报告"


@pytest.mark.asyncio
async def test_local_knowledge_and_memory_flow_through_graph() -> None:
    store = _store()
    user_id = uuid4()
    await store.index_document(
        user_id=user_id,
        document_id=uuid4(),
        title="Internal agent adoption memo",
        content="Enterprise AI agent adoption is strongest in customer support operations.",
        source_uri=None,
    )
    graph = build_research_graph(
        MockPlanner(),
        StaticRetriever(),
        KnowledgeRetriever(store, user_id),
        minimum_evidence=1,
        memory=store,
    )

    result = await graph.ainvoke(
        create_initial_state("Enterprise AI agent adoption", user_id=user_id)
    )

    assert result["status"] == "completed"
    assert any(item.source_type == EvidenceSource.LOCAL for item in result["accepted_evidence"])
    recalled = await store.recall(user_id=user_id, topic="enterprise agent adoption")
    assert recalled


@pytest.mark.asyncio
async def test_dashscope_embedding_response_is_validated() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["dimensions"] == 3
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": index, "embedding": [float(index), 0.5, 1.0]}
                    for index, _ in enumerate(body["input"])
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        embedder = DashScopeEmbedder(
            api_key="key",
            base_url="https://dashscope.test/v1",
            model="text-embedding-v3",
            dimension=3,
            timeout=10,
            client=client,
        )
        vectors = await embedder.embed(["first", "second"])

    assert vectors == [[0.0, 0.5, 1.0], [1.0, 0.5, 1.0]]


class FakeMilvusClient:
    def __init__(self) -> None:
        self.loaded: list[str] = []
        self.upserts: list[dict[str, object]] = []
        self.search_filter = ""
        self.delete_filter = ""

    def has_collection(self, *, collection_name: str) -> bool:
        return True

    def load_collection(self, *, collection_name: str) -> None:
        self.loaded.append(collection_name)

    def upsert(self, **kwargs: object) -> None:
        self.upserts.append(kwargs)

    def search(self, **kwargs: object) -> list[list[dict[str, object]]]:
        self.search_filter = str(kwargs["filter"])
        return [
            [
                {
                    "id": "doc:0",
                    "distance": 0.88,
                    "entity": {
                        "user_id": "user-1",
                        "document_id": "doc",
                        "title": "Title",
                        "content": "Content",
                        "content_hash": "a" * 64,
                        "source_uri": "",
                    },
                }
            ]
        ]

    def delete(self, **kwargs: object) -> None:
        self.delete_filter = str(kwargs["filter"])


@pytest.mark.asyncio
async def test_milvus_backend_reuses_collection_and_filters_by_user() -> None:
    client = FakeMilvusClient()
    backend = MilvusVectorBackend(uri="http://milvus:19530", dimension=3, client=client)
    entry = VectorEntry(
        id="doc:0",
        user_id="user-1",
        document_id="doc",
        title="Title",
        content="Content",
        content_hash="a" * 64,
        source_uri="",
        vector=[1.0, 0.0, 0.0],
    )

    await backend.upsert("documents", [entry])
    hits = await backend.search("documents", user_id="user-1", vector=[1.0, 0.0, 0.0], limit=3)
    await backend.delete("documents", user_id="user-1", document_id="doc")

    assert client.loaded == ["documents"]
    assert len(client.upserts) == 1
    assert hits[0].score == 0.88
    assert client.search_filter == 'user_id == "user-1"'
    assert client.delete_filter == 'user_id == "user-1" and document_id == "doc"'
