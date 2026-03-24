import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

from core.model.document import Document
from infrastructure.config import AppConfig

logger = logging.getLogger(__name__)


@dataclass
class ChapterPreview:
    """Lightweight chapter metadata for preview/selection UI."""

    index: int
    title: str
    page_start: int  # 1-based
    page_end: int


@dataclass
class DocumentPreview:
    """Result of preview_file - chapter structure without full text."""

    document: Document
    chapters: list[ChapterPreview]
    file_hash: str
    filename: str


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def ingest_file(path: Path, config: AppConfig, original_filename: str = "") -> Document | None:
    """
    Ingest a single PDF or EPUB file.

    Returns None if the file was already ingested (same hash already in Qdrant).
    original_filename, if provided, is stored on the Document so the UI can
    display the user-facing name instead of a temp path.
    """
    path = Path(path)
    if not path.exists():
        logger.error("File not found: %s", path)
        return None

    suffix = path.suffix.lower()
    if suffix not in (".pdf", ".epub"):
        logger.error("Unsupported file type: %s", suffix)
        return None

    file_hash = _hash_file(path)
    logger.info("Hashed %s -> %s", path.name, file_hash[:12])

    # Idempotency check: skip if already in Qdrant
    if _already_ingested(file_hash, config):
        logger.info("Skipping %s — already ingested (hash %s)", path.name, file_hash[:12])
        return None

    if suffix == ".pdf":
        from infrastructure.ingest.pdf_loader import load_pdf

        return load_pdf(path, file_hash, original_filename=original_filename)
    else:
        from infrastructure.ingest.epub_loader import load_epub

        return load_epub(path, file_hash, original_filename=original_filename)


def _already_ingested(file_hash: str, config: AppConfig) -> bool:
    """Return True if a document with this hash already exists in Qdrant."""
    try:
        from infrastructure.vectorstore.qdrant_store import QdrantStore

        store = QdrantStore(config.qdrant)
        return store.has_file(file_hash)
    except Exception as exc:
        logger.warning("Could not check Qdrant for existing hash: %s", exc)
        return False


def preview_file(path: Path, config: AppConfig) -> DocumentPreview | None:
    """Extract chapter structure from a file without loading full page text.

    This is a lightweight operation for the preview/selection UI.
    Returns DocumentPreview with chapter list, or None if file is unsupported.
    """
    path = Path(path)
    if not path.exists():
        logger.error("File not found: %s", path)
        return None

    suffix = path.suffix.lower()
    if suffix not in (".pdf", ".epub"):
        logger.error("Unsupported file type for preview: %s", suffix)
        return None

    file_hash = _hash_file(path)
    logger.info("Preview: hashing %s -> %s", path.name, file_hash[:12])

    if suffix == ".pdf":
        from infrastructure.ingest.pdf_loader import preview_pdf

        doc, chapter_previews = preview_pdf(path, file_hash)
    else:
        from infrastructure.ingest.epub_loader import preview_epub

        doc, chapter_previews = preview_epub(path, file_hash)

    if doc is None:
        return None

    return DocumentPreview(
        document=doc,
        chapters=[
            ChapterPreview(
                index=c.index,
                title=c.title,
                page_start=c.page_start,
                page_end=c.page_end,
            )
            for c in chapter_previews
        ],
        file_hash=file_hash,
        filename=path.name,
    )
