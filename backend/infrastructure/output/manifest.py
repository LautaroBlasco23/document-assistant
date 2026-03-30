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
    stored_chapter_indices: list[int] | None = None,
) -> Path:
    safe_title = _safe_name(doc.title)
    d = output_dir / safe_title
    d.mkdir(parents=True, exist_ok=True)
    out = d / "manifest.json"

    is_partial = stored_chapter_indices is not None and len(stored_chapter_indices) < len(
        doc.chapters
    )
    stored_set = set(stored_chapter_indices) if stored_chapter_indices else None

    chapters_data = []
    for ch in doc.chapters:
        if ch.sections:
            sections_data = [
                {"title": s.title, "page_start": s.page_start, "page_end": s.page_end}
                for s in ch.sections
            ]
        elif ch.pages:
            page_start = ch.pages[0].number
            page_end = ch.pages[-1].number
            sections_data = [{"title": ch.title, "page_start": page_start, "page_end": page_end}]
        else:
            sections_data = []
        entry: dict = {
            "index": ch.index,
            "title": ch.title,
            "sections": sections_data,
            "stored": stored_set is None or ch.index in stored_set,
        }
        if ch.toc_href:
            entry["toc_href"] = ch.toc_href
        chapters_data.append(entry)

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

    if is_partial:
        manifest["partial"] = True
        manifest["stored_chapter_indices"] = sorted(stored_chapter_indices or [])
        manifest["total_detected_chapters"] = len(doc.chapters)

    with open(out, "w") as f:
        json.dump(manifest, f, indent=2)
        f.flush()
        os.fsync(f.fileno())

    logger.info("Wrote manifest: %s (partial=%s)", out, is_partial)
    return out


def remove_chapter_from_manifest(file_hash: str, chapter_index: int, output_dir: Path) -> int:
    """Remove a chapter entry from the manifest JSON. Returns count of remaining chapters.

    Idempotent: if the chapter is already absent or the manifest is missing, logs a warning
    and returns gracefully.
    """
    # Find the manifest file for this document
    manifest_path: Path | None = None
    if output_dir.exists():
        for doc_dir in output_dir.iterdir():
            if not doc_dir.is_dir():
                continue
            candidate = doc_dir / "manifest.json"
            if candidate.exists():
                try:
                    with open(candidate) as f:
                        data = json.load(f)
                    if data.get("file_hash") == file_hash:
                        manifest_path = candidate
                        break
                except Exception as e:
                    logger.warning("Failed to read manifest %s: %s", candidate, e)

    if manifest_path is None:
        logger.warning("Manifest not found for file_hash=%s, skipping manifest update", file_hash)
        return 0

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except Exception as e:
        logger.warning("Failed to load manifest %s: %s", manifest_path, e)
        return 0

    chapters = manifest.get("chapters", [])
    original_count = len(chapters)
    chapters_remaining = [ch for ch in chapters if ch.get("index") != chapter_index]

    if len(chapters_remaining) == original_count:
        logger.warning(
            "Chapter index=%d not found in manifest for file_hash=%s, nothing to remove",
            chapter_index,
            file_hash,
        )
        return original_count

    manifest["chapters"] = chapters_remaining
    manifest["num_chapters"] = len(chapters_remaining)

    try:
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        logger.error("Failed to write updated manifest %s: %s", manifest_path, e)
        raise

    logger.info(
        "Removed chapter index=%d from manifest %s (%d chapters remaining)",
        chapter_index,
        manifest_path,
        len(chapters_remaining),
    )
    return len(chapters_remaining)
