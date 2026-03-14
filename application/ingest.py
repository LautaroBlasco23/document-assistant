import hashlib
import logging
from pathlib import Path

from core.model.document import Document
from infrastructure.config import AppConfig

logger = logging.getLogger(__name__)


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def ingest_file(path: Path, config: AppConfig) -> Document | None:
    """
    Ingest a single PDF or EPUB file.

    Returns None if the file was already ingested (same hash already in Qdrant).
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
        return load_pdf(path, file_hash)
    else:
        from infrastructure.ingest.epub_loader import load_epub
        return load_epub(path, file_hash)


def _already_ingested(file_hash: str, config: AppConfig) -> bool:
    """Return True if a document with this hash already exists in Qdrant."""
    try:
        from infrastructure.vectorstore.qdrant_store import QdrantStore
        store = QdrantStore(config.qdrant)
        return store.has_file(file_hash)
    except Exception as exc:
        logger.warning("Could not check Qdrant for existing hash: %s", exc)
        return False
