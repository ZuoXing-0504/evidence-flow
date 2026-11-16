from __future__ import annotations

from collections.abc import AsyncIterator
from io import BytesIO
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Database
from app.db.models import Base
from app.db.session import get_session
from app.knowledge import get_knowledge_store
from app.knowledge.embeddings import DeterministicEmbedder
from app.knowledge.extraction import DocumentExtractionError, extract_document_text
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


@pytest.mark.asyncio
async def test_text_document_upload_is_indexed(tmp_path: Path) -> None:
    async for client in _client(tmp_path / "document-upload.db"):
        headers = await _register(client, "upload@example.com")
        content = "金融机构正在评估多 Agent 工作流的审计、权限和模型风险。"

        response = await client.post(
            "/api/documents/upload",
            files={"file": ("行业备忘录.md", content.encode(), "text/markdown")},
            headers=headers,
        )

        assert response.status_code == 201
        assert response.json()["title"] == "行业备忘录"
        assert response.json()["status"] == "indexed"
        assert response.json()["chunk_count"] == 1


@pytest.mark.asyncio
async def test_document_upload_rejects_unsupported_and_invalid_text(tmp_path: Path) -> None:
    async for client in _client(tmp_path / "document-upload-errors.db"):
        headers = await _register(client, "upload-errors@example.com")

        unsupported = await client.post(
            "/api/documents/upload",
            files={"file": ("notes.csv", b"a,b,c", "text/csv")},
            headers=headers,
        )
        invalid_text = await client.post(
            "/api/documents/upload",
            files={"file": ("notes.txt", b"\xff" * 30, "text/plain")},
            headers=headers,
        )

        assert unsupported.status_code == 415
        assert unsupported.json()["detail"] == "Unsupported document type"
        assert invalid_text.status_code == 422
        assert invalid_text.json()["detail"] == "Document is not valid UTF-8 text"


def test_document_extraction_rejects_empty_text_and_unknown_suffix() -> None:
    with pytest.raises(DocumentExtractionError, match="no extractable text"):
        extract_document_text("empty.md", b"short")
    with pytest.raises(DocumentExtractionError, match="Unsupported document type"):
        extract_document_text("data.json", b'{"content": "long enough to parse"}')


def test_pdf_document_text_is_extracted() -> None:
    output = BytesIO()
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 72 720 Td (Evidence grounded research report) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.write(output)

    extracted = extract_document_text("report.pdf", output.getvalue())

    assert extracted == "Evidence grounded research report"
