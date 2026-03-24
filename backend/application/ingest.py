import hashlib
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from core.model.document import Document

logger = logging.getLogger(__name__)

# Type aliases for injected loader functions
LoadFn = Callable[[Path, str, str], Document | None]
PreviewFn = Callable[[Path, str], tuple[Document | None, list]]


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


def ingest_file(
    path: Path,
    loaders: dict[str, LoadFn],
    exists_fn: Callable[[str], bool] | None = None,
    original_filename: str = "",
) -> Document | None:
    """
    Ingest a single PDF or EPUB file.

    loaders: maps file extension (e.g. ".pdf") to a load function.
    exists_fn: optional callable to check if a file hash is already ingested;
               if provided and returns True, the file is skipped.
    original_filename: stored on the Document so the UI can display the
                       user-facing name instead of a temp path.
    """
    path = Path(path)
    if not path.exists():
        logger.error("File not found: %s", path)
        return None

    suffix = path.suffix.lower()
    loader = loaders.get(suffix)
    if loader is None:
        logger.error("Unsupported file type: %s", suffix)
        return None

    file_hash = _hash_file(path)
    logger.info("Hashed %s -> %s", path.name, file_hash[:12])

    if exists_fn is not None and exists_fn(file_hash):
        logger.info("Skipping %s — already ingested (hash %s)", path.name, file_hash[:12])
        return None

    return loader(path, file_hash, original_filename)


def preview_file(
    path: Path,
    previewers: dict[str, PreviewFn],
) -> DocumentPreview | None:
    """Extract chapter structure from a file without loading full page text.

    previewers: maps file extension to a preview function.
    Returns DocumentPreview with chapter list, or None if file is unsupported.
    """
    path = Path(path)
    if not path.exists():
        logger.error("File not found: %s", path)
        return None

    suffix = path.suffix.lower()
    previewer = previewers.get(suffix)
    if previewer is None:
        logger.error("Unsupported file type for preview: %s", suffix)
        return None

    file_hash = _hash_file(path)
    logger.info("Preview: hashing %s -> %s", path.name, file_hash[:12])

    doc, chapter_previews = previewer(path, file_hash)

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
