"""Delete a document from all stores."""
import logging
import shutil
from pathlib import Path

from core.ports.content_store import ContentStore
from infrastructure.file_persistence import delete_persisted_file
from infrastructure.graph.neo4j_store import Neo4jStore
from infrastructure.output.markdown_writer import _safe_name
from infrastructure.vectorstore.qdrant_store import QdrantStore

logger = logging.getLogger(__name__)


def delete_document(
    file_hash: str,
    doc_manifest: dict,
    qdrant: QdrantStore,
    neo4j: Neo4jStore,
    content_store: ContentStore,
    output_dir: Path,
) -> list[str]:
    """Delete a document from all stores. Returns list of error strings (empty = success)."""
    errors: list[str] = []

    # Fetch metadata before deleting from content_store (delete_by_document wipes document_metadata)
    file_extension: str | None = None
    try:
        meta = content_store.get_metadata(file_hash)
        if meta:
            file_extension = meta.file_extension or None
    except Exception as e:
        logger.warning("Could not fetch metadata for %s before deletion: %s", file_hash, e)

    try:
        qdrant.delete_by_source_file(file_hash)
    except Exception as e:
        logger.error("Failed to delete %s from Qdrant: %s", file_hash, e)
        errors.append(f"Qdrant: {e}")

    try:
        neo4j.delete_document(file_hash)
    except Exception as e:
        logger.error("Failed to delete %s from Neo4j: %s", file_hash, e)
        errors.append(f"Neo4j: {e}")

    try:
        content_store.delete_by_document(file_hash)
    except Exception as e:
        logger.error("Failed to delete content for %s from PostgreSQL: %s", file_hash, e)
        errors.append(f"PostgreSQL: {e}")

    try:
        doc_dir = output_dir / _safe_name(doc_manifest["title"])
        if doc_dir.exists():
            shutil.rmtree(doc_dir)
        else:
            logger.warning("Manifest directory not found for %s: %s", file_hash, doc_dir)
    except Exception as e:
        logger.error("Failed to delete manifest directory for %s: %s", file_hash, e)
        errors.append(f"Manifest: {e}")

    try:
        if file_extension:
            delete_persisted_file(file_hash, file_extension)
    except Exception as e:
        logger.error("Failed to delete persisted file for %s: %s", file_hash, e)
        errors.append(f"Persisted file: {e}")

    return errors
