import json
import logging
import os
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
    num_chapters: int = 0,
) -> Path:
    safe_title = _safe_name(doc.title)
    d = output_dir / safe_title
    d.mkdir(parents=True, exist_ok=True)
    out = d / "manifest.json"

    chapters_data = []
    for ch in doc.chapters:
        sections_data = [
            {"title": s.title, "page_start": s.page_start, "page_end": s.page_end}
            for s in ch.sections
        ]
        chapters_data.append(
            {
                "index": ch.index,
                "title": ch.title,
                "sections": sections_data,
            }
        )

    manifest = {
        "file_hash": doc.file_hash,
        "title": doc.title,
        "source_path": doc.source_path,
        "original_filename": doc.original_filename,
        "model": model,
        "collection": collection,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "chunk_count": chunk_count,
        "num_chapters": num_chapters,
        "chapters": chapters_data,
    }
    with open(out, "w") as f:
        json.dump(manifest, f, indent=2)
        f.flush()
        os.fsync(f.fileno())

    logger.info("Wrote manifest: %s", out)
    return out
