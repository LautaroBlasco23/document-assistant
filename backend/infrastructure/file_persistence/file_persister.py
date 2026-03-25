import logging
from pathlib import Path

from infrastructure.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

UPLOADS_DIR = PROJECT_ROOT / "data" / "uploads"


def ensure_uploads_dir() -> Path:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOADS_DIR


def persist_file(file_hash: str, extension: str, content: bytes) -> Path:
    """Persist a file to the uploads directory.

    Args:
        file_hash: SHA-256 hash of the file
        extension: File extension including dot (e.g., '.pdf', '.epub')
        content: File bytes

    Returns:
        Path to the persisted file
    """
    ensure_uploads_dir()
    safe_ext = extension.lstrip(".").lower()
    file_path = UPLOADS_DIR / f"{file_hash}.{safe_ext}"
    file_path.write_bytes(content)
    logger.info("Persisted file: %s", file_path.name)
    return file_path


def get_persisted_file(file_hash: str, extension: str) -> Path | None:
    """Get path to a persisted file.

    Args:
        file_hash: SHA-256 hash of the file
        extension: File extension including dot (e.g., '.pdf', '.epub')

    Returns:
        Path to the file if it exists, None otherwise
    """
    safe_ext = extension.lstrip(".").lower()
    file_path = UPLOADS_DIR / f"{file_hash}.{safe_ext}"
    if file_path.exists():
        return file_path
    return None


def delete_persisted_file(file_hash: str, extension: str) -> bool:
    """Delete a persisted file.

    Args:
        file_hash: SHA-256 hash of the file
        extension: File extension including dot (e.g., '.pdf', '.epub')

    Returns:
        True if deleted, False if not found
    """
    safe_ext = extension.lstrip(".").lower()
    file_path = UPLOADS_DIR / f"{file_hash}.{safe_ext}"
    if file_path.exists():
        file_path.unlink()
        logger.info("Deleted persisted file: %s", file_path.name)
        return True
    return False
