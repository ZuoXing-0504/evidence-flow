from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain import DocumentStatus


class CreateDocumentRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=20, max_length=1_000_000)
    source_uri: str | None = Field(default=None, max_length=2048)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Title cannot be blank")
        return cleaned

    @field_validator("content")
    @classmethod
    def reject_blank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Document content cannot be blank")
        return value.strip()


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    source_uri: str | None
    content_hash: str
    status: DocumentStatus
    chunk_count: int
    error: str | None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
