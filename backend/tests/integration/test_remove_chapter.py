"""
Integration tests for the remove chapter feature.
"""

import json
import tempfile
from pathlib import Path

import pytest

from infrastructure.output.manifest import remove_chapter_from_manifest, write_manifest


# ---------------------------------------------------------------------------
# Manifest: remove_chapter_from_manifest (file I/O)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_manifest_round_trip():
    """write_manifest then remove_chapter_from_manifest leaves a consistent manifest."""
    from core.model.document import Chapter, Document

    file_hash = "round_trip_hash"
    chapters = [
        Chapter(index=0, title="Cover"),
        Chapter(index=1, title="Preface"),
        Chapter(index=2, title="Chapter 1"),
    ]
    doc = Document(
        source_path="/tmp/book.pdf",
        title="round_trip",
        file_hash=file_hash,
        chapters=chapters,
        original_filename="book.pdf",
    )

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp)
        write_manifest(
            doc,
            chunk_count=30,
            collection="documents",
            model="nomic-embed-text",
            output_dir=output_dir,
            num_chapters=3,
        )

        remaining = remove_chapter_from_manifest(file_hash, 1, output_dir)
        assert remaining == 2

        # Read back the manifest and verify
        manifest_path = output_dir / "round_trip" / "manifest.json"
        with open(manifest_path) as f:
            manifest = json.load(f)

        indices = [ch["index"] for ch in manifest["chapters"]]
        assert 1 not in indices
        assert 0 in indices
        assert 2 in indices
        assert manifest["num_chapters"] == 2
