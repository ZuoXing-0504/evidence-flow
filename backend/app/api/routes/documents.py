from __future__ import annotations

from hashlib import sha256
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser
from app.db.models import DocumentRecord
from app.db.session import get_session
from app.knowledge import KnowledgeStore, get_knowledge_store
from app.knowledge.repository import DocumentRepository
from app.knowledge.schemas import (
    CreateDocumentRequest,
    DocumentListResponse,
    DocumentResponse,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])
Session = Annotated[AsyncSession, Depends(get_session)]
Store = Annotated[KnowledgeStore, Depends(get_knowledge_store)]


async def _owned_document(
    repository: DocumentRepository, document_id: UUID, user_id: UUID
) -> DocumentRecord:
    document = await repository.get(document_id)
    if document is None or document.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    body: CreateDocumentRequest,
    session: Session,
    user: CurrentUser,
    store: Store,
) -> DocumentRecord:
    content_hash = sha256(body.content.encode()).hexdigest()
    repository = DocumentRepository(session)
    if await repository.get_by_hash(user.id, content_hash) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This document content is already registered",
        )
    try:
        document = await repository.create(
            user_id=user.id,
            title=body.title,
            source_uri=body.source_uri,
            content_hash=content_hash,
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This document content is already registered",
        ) from exc

    try:
        chunk_count = await store.index_document(
            user_id=user.id,
            document_id=document.id,
            title=document.title,
            content=body.content,
            source_uri=document.source_uri,
        )
        await repository.mark_indexed(document, chunk_count)
        await session.commit()
    except Exception as exc:
        await repository.mark_failed(document, "Vector indexing failed")
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Document vector indexing failed",
        ) from exc
    return document


@router.get("", response_model=DocumentListResponse)
async def list_documents(session: Session, user: CurrentUser) -> DocumentListResponse:
    items = await DocumentRepository(session).list(user.id)
    return DocumentListResponse(items=[DocumentResponse.model_validate(item) for item in items])


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    session: Session,
    user: CurrentUser,
    store: Store,
) -> Response:
    repository = DocumentRepository(session)
    document = await _owned_document(repository, document_id, user.id)
    try:
        await store.delete_document(user_id=user.id, document_id=document.id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Document vectors could not be deleted",
        ) from exc
    await repository.delete(document)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
