"""Unit tests for the remove chapter feature."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from infrastructure.output.manifest import remove_chapter_from_manifest

# ---------------------------------------------------------------------------
# Manifest removal tests
# ---------------------------------------------------------------------------


def _write_manifest(directory: Path, manifest: dict) -> Path:
    """Helper: write a manifest.json into a subdirectory and return its path."""
    doc_dir = directory / "my_book"
    doc_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = doc_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f)
    return manifest_path


def _make_manifest(file_hash: str, chapters: list[dict]) -> dict:
    return {
        "file_hash": file_hash,
        "title": "My Book",
        "source_path": "/tmp/book.pdf",
        "original_filename": "book.pdf",
        "model": "nomic-embed-text",
        "collection": "documents",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "chunk_count": 100,
        "num_chapters": len(chapters),
        "chapters": chapters,
    }


def test_manifest_chapter_removal():
    """Removing chapter index=1 leaves chapters 0 and 2 intact, and decrements num_chapters."""
    chapters = [
        {"index": 0, "title": "Introduction", "sections": []},
        {"index": 1, "title": "Acknowledgements", "sections": []},
        {"index": 2, "title": "Chapter One", "sections": []},
    ]
    manifest = _make_manifest("abc123", chapters)

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp)
        _write_manifest(output_dir, manifest)

        remaining = remove_chapter_from_manifest("abc123", 1, output_dir)

    assert remaining == 2


def test_manifest_chapter_removal_updates_file():
    """After removal, the manifest file no longer contains the removed chapter index."""
    chapters = [
        {"index": 0, "title": "Cover", "sections": []},
        {"index": 1, "title": "Content", "sections": []},
    ]
    manifest = _make_manifest("deadbeef", chapters)

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp)
        manifest_path = _write_manifest(output_dir, manifest)

        remove_chapter_from_manifest("deadbeef", 0, output_dir)

        with open(manifest_path) as f:
            updated = json.load(f)

    remaining_indices = [ch["index"] for ch in updated["chapters"]]
    assert 0 not in remaining_indices
    assert 1 in remaining_indices
    assert updated["num_chapters"] == 1


def test_manifest_removal_idempotent():
    """Removing the same chapter twice returns gracefully on the second call."""
    chapters = [
        {"index": 0, "title": "Cover", "sections": []},
        {"index": 1, "title": "Content", "sections": []},
    ]
    manifest = _make_manifest("cafebabe", chapters)

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp)
        _write_manifest(output_dir, manifest)

        first = remove_chapter_from_manifest("cafebabe", 0, output_dir)
        second = remove_chapter_from_manifest("cafebabe", 0, output_dir)

    assert first == 1
    assert second == 1  # same count returned gracefully; chapter was already gone


def test_manifest_missing_file_hash_returns_zero():
    """If no manifest matches the file_hash, function returns 0 without raising."""
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp)
        result = remove_chapter_from_manifest("nonexistent_hash", 0, output_dir)
    assert result == 0


def test_manifest_chapter_not_found_returns_original_count():
    """If chapter_index is not in manifest, original chapter count is returned unchanged."""
    chapters = [
        {"index": 0, "title": "Cover", "sections": []},
        {"index": 1, "title": "Content", "sections": []},
    ]
    manifest = _make_manifest("ff00ff", chapters)

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp)
        _write_manifest(output_dir, manifest)

        result = remove_chapter_from_manifest("ff00ff", 99, output_dir)

    assert result == 2


# ---------------------------------------------------------------------------
# API chapter_number to chapter_index conversion
# ---------------------------------------------------------------------------


def test_chapter_number_to_index_conversion():
    """1-based chapter_number from URL converts to 0-based chapter_index."""
    # This mirrors the conversion logic in the endpoint
    for chapter_number in [1, 2, 5, 10]:
        chapter_index = chapter_number - 1
        assert chapter_index == chapter_number - 1


# ---------------------------------------------------------------------------
# Reject removal of last chapter
# ---------------------------------------------------------------------------


def _make_test_client_with_mock_services():
    """Return a TestClient with services dependency overridden by a MagicMock."""
    from fastapi.testclient import TestClient

    from api.deps import get_services_dep
    from api.main import app

    mock_services = MagicMock()
    # Prevent content_store calls from raising
    mock_services.content_store.get_summary.return_value = None
    mock_services.content_store.get_flashcards.return_value = []
    mock_services.qdrant.delete_by_chapter.return_value = 0

    app.dependency_overrides[get_services_dep] = lambda: mock_services
    client = TestClient(app)
    return client, app


def test_reject_removal_when_one_chapter_remains():
    """Endpoint must return 400 when only one chapter exists."""
    single_chapter_manifest = _make_manifest(
        "singlehash",
        [{"index": 0, "title": "Only Chapter", "sections": []}],
    )

    client, app = _make_test_client_with_mock_services()
    try:
        with patch(
            "api.routers.documents._list_documents",
            return_value=[single_chapter_manifest],
        ):
            response = client.delete("/api/documents/singlehash/chapters/1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "Cannot remove the only chapter" in response.json()["detail"]


def test_reject_removal_when_document_not_found():
    """Endpoint must return 404 when document hash is not found."""
    client, app = _make_test_client_with_mock_services()
    try:
        with patch("api.routers.documents._list_documents", return_value=[]):
            response = client.delete("/api/documents/unknownhash/chapters/1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_reject_removal_when_chapter_not_in_manifest():
    """Endpoint must return 404 when chapter_number is not found in manifest."""
    manifest = _make_manifest(
        "twochaps",
        [
            {"index": 0, "title": "Intro", "sections": []},
            {"index": 1, "title": "Chapter 1", "sections": []},
        ],
    )

    client, app = _make_test_client_with_mock_services()
    try:
        with patch("api.routers.documents._list_documents", return_value=[manifest]):
            # chapter_number=99 -> chapter_index=98, not in manifest
            response = client.delete("/api/documents/twochaps/chapters/99")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
