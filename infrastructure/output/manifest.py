import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from core.model.document import Document
from infrastructure.output.markdown_writer import _safe_name

logger = logging.getLogger(__name__)


def write_manifest(
    doc: Document,
    chunk_count: int,
    collection: str,
    model: str,
    output_dir: Path,
) -> Path:
    safe_title = _safe_name(doc.title)
    d = output_dir / safe_title
    d.mkdir(parents=True, exist_ok=True)
    out = d / "manifest.json"

    manifest = {
        "file_hash": doc.file_hash,
        "title": doc.title,
        "source_path": doc.source_path,
        "model": model,
        "collection": collection,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "chunk_count": chunk_count,
    }
    with open(out, "w") as f:
        json.dump(manifest, f, indent=2)

    logger.info("Wrote manifest: %s", out)
    return out
