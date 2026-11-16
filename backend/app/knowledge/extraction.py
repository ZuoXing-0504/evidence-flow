from __future__ import annotations

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_DOCUMENT_CHARACTERS = 1_000_000
SUPPORTED_DOCUMENT_SUFFIXES = {".md", ".markdown", ".pdf", ".txt"}


class DocumentExtractionError(ValueError):
    pass


def extract_document_text(
    filename: str | None,
    content: bytes,
    *,
    max_characters: int = MAX_DOCUMENT_CHARACTERS,
) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in SUPPORTED_DOCUMENT_SUFFIXES:
        raise DocumentExtractionError("Unsupported document type")

    if suffix == ".pdf":
        text = _extract_pdf(content)
    else:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DocumentExtractionError("Document is not valid UTF-8 text") from exc

    normalized = text.strip()
    if len(normalized) < 20:
        raise DocumentExtractionError("Document has no extractable text")
    if len(normalized) > max_characters:
        raise DocumentExtractionError("Extracted document text is too large")
    return normalized


def document_title_from_filename(filename: str | None) -> str:
    title = Path(filename or "document").stem.strip() or "document"
    return title[:500]


def _extract_pdf(content: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted and reader.decrypt("") == 0:
            raise DocumentExtractionError("Encrypted PDF is not supported")
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except DocumentExtractionError:
        raise
    except (PdfReadError, OSError, ValueError) as exc:
        raise DocumentExtractionError("PDF could not be read") from exc
