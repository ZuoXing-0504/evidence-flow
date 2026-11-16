from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Database
from app.db.models import Base
from app.db.session import get_session
from app.knowledge import get_knowledge_store
from app.knowledge.embeddings import DeterministicEmbedder
from app.knowledge.semantic import SemanticKnowledgeStore
from app.knowledge.vector import InMemoryVectorBackend
from app.main import app


class FailingKnowledgeStore:
    async def index_document(self, **kwargs: object) -> int:
        del kwargs
        raise ConnectionError("Vector store unavailable")


async def _client(path: Path, store_override: object | None = None) -> AsyncIterator[AsyncClient]:
    database = Database(f"sqlite+aiosqlite:///{path.as_posix()}")
    async with database.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    store = SemanticKnowledgeStore(
        DeterministicEmbedder(64), InMemoryVectorBackend(), collection_prefix="api_test"
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.sessions() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_knowledge_store] = lambda: store_override or store
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        await database.dispose()


async def _register(client: AsyncClient, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "strong-password-123",
            "display_name": "Knowledge User",
        },
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_document_lifecycle_and_user_isolation(tmp_path: Path) -> None:
    async for client in _client(tmp_path / "documents.db"):
        owner = await _register(client, "owner@example.com")
        other = await _register(client, "other@example.com")
        body = {
            "title": "Internal market memo",
            "content": "The enterprise AI agent market is expanding across regulated industries.",
            "source_uri": "https://example.com/memo",
        }
        created = await client.post("/api/documents", json=body, headers=owner)
        assert created.status_code == 201
        document_id = created.json()["id"]
        assert created.json()["status"] == "indexed"
        assert created.json()["chunk_count"] == 1

        duplicate = await client.post("/api/documents", json=body, headers=owner)
        assert duplicate.status_code == 409
        assert len((await client.get("/api/documents", headers=owner)).json()["items"]) == 1
        assert (await client.get("/api/documents", headers=other)).json()["items"] == []
        assert (
            await client.delete(f"/api/documents/{document_id}", headers=other)
        ).status_code == 404

        deleted = await client.delete(f"/api/documents/{document_id}", headers=owner)
        assert deleted.status_code == 204
        assert (await client.get("/api/documents", headers=owner)).json()["items"] == []


@pytest.mark.asyncio
async def test_documents_require_authentication(tmp_path: Path) -> None:
    async for client in _client(tmp_path / "documents-auth.db"):
        assert (await client.get("/api/documents")).status_code == 401

        headers = await _register(client, "blank@example.com")
        blank = await client.post(
            "/api/documents",
            json={"title": "Blank", "content": " " * 20},
            headers=headers,
        )
        assert blank.status_code == 422


@pytest.mark.asyncio
async def test_indexing_failure_is_persisted(tmp_path: Path) -> None:
    async for client in _client(tmp_path / "documents-failure.db", FailingKnowledgeStore()):
        headers = await _register(client, "failure@example.com")
        response = await client.post(
            "/api/documents",
            json={
                "title": "Unavailable index",
                "content": "This content is long enough to pass document input validation.",
            },
            headers=headers,
        )
        assert response.status_code == 502

        documents = (await client.get("/api/documents", headers=headers)).json()["items"]
        assert documents[0]["status"] == "failed"
        assert documents[0]["error"] == "Vector indexing failed"
