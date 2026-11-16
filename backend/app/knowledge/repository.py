from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DocumentRecord
from app.domain import DocumentStatus


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: UUID,
        title: str,
        source_uri: str | None,
        content_hash: str,
    ) -> DocumentRecord:
        document = DocumentRecord(
            user_id=user_id,
            title=title,
            source_uri=source_uri,
            content_hash=content_hash,
        )
        self.session.add(document)
        await self.session.flush()
        return document

    async def get(self, document_id: UUID) -> DocumentRecord | None:
        return await self.session.get(DocumentRecord, document_id)

    async def get_by_hash(self, user_id: UUID, content_hash: str) -> DocumentRecord | None:
        return await self.session.scalar(
            select(DocumentRecord).where(
                DocumentRecord.user_id == user_id,
                DocumentRecord.content_hash == content_hash,
            )
        )

    async def list(self, user_id: UUID) -> list[DocumentRecord]:
        result = await self.session.scalars(
            select(DocumentRecord)
            .where(DocumentRecord.user_id == user_id)
            .order_by(DocumentRecord.created_at.desc())
        )
        return list(result)

    async def mark_indexed(self, document: DocumentRecord, chunk_count: int) -> None:
        document.status = DocumentStatus.INDEXED.value
        document.chunk_count = chunk_count
        document.error = None
        document.updated_at = datetime.now(UTC)
        await self.session.flush()

    async def mark_failed(self, document: DocumentRecord, message: str) -> None:
        document.status = DocumentStatus.FAILED.value
        document.error = message[:1000]
        document.updated_at = datetime.now(UTC)
        await self.session.flush()

    async def delete(self, document: DocumentRecord) -> None:
        await self.session.delete(document)
        await self.session.flush()
