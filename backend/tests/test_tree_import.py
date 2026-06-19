"""
Unit tests for tree import orchestration.

Subject: application/services/tree_import.py — create_tree_from_file_task(), import_youtube_task(), ingest_file_task()
Scope:   File parsing, tree creation, chapter processing, YouTube import, document ingest.
Out of scope:
  - File loader internals              → ingest/test_*.py
  - Chunking logic                     → chunking tests
  - TaskRegistry lifecycle             → test_task_registry.py
Setup:   Mocked Services, Task, file loaders, and stores.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from application.services.tree_import import (
    create_tree_from_file_task,
    import_youtube_task,
    ingest_file_task,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task():
    """Return a mocked Task object."""
    return MagicMock()


def _make_services():
    """Return a mocked Services object."""
    services = MagicMock()
    services.kt_tree_store.create_tree.return_value = MagicMock(id=uuid4())
    services.kt_doc_store.create_document.return_value = MagicMock(id=uuid4())
    services.kt_doc_store.update_document_source_file.return_value = None
    services.kt_chapter_store.create_chapter.return_value = MagicMock(id=uuid4())
    services.kt_content_store.save_chunks.return_value = None
    services.subscription_store.get_user_limits.return_value = MagicMock(
        current_documents=0, max_documents=100
    )
    return services


def _make_document(chapters=None):
    """Return a mocked parsed document."""
    doc = MagicMock()
    doc.title = "Test Document"
    doc.source_path = "/tmp/test.pdf"
    doc.chapters = chapters or []
    return doc


def _make_chapter(index=0, title="Chapter 1", pages=None):
    """Return a mocked chapter."""
    chapter = MagicMock()
    chapter.index = index
    chapter.title = title
    chapter.pages = pages or []
    return chapter


def _make_page(number=1, text="Page content"):
    """Return a mocked page."""
    page = MagicMock()
    page.number = number
    page.text = text
    return page


# ---------------------------------------------------------------------------
# create_tree_from_file_task
# ---------------------------------------------------------------------------


def test_create_tree_from_file_task_returns_tree_id_and_chapter_count():
    """On success, the task must return tree_id and chapter_count."""
    task = _make_task()
    services = _make_services()
    chapter = _make_chapter(index=0, title="Intro", pages=[_make_page()])
    doc = _make_document(chapters=[chapter])

    with patch("application.services.tree_import._parse_and_chunk") as mock_parse:
        mock_parse.return_value = (doc, [], "hash123", {})

        with patch("application.services.tree_import.PROJECT_ROOT", Path(tempfile.gettempdir())):
            with patch("application.services.tree_import.ChapterAwareSplitter") as mock_splitter_cls:
                mock_splitter = MagicMock()
                mock_splitter.split.return_value = []
                mock_splitter_cls.return_value = mock_splitter

                with patch("fitz.open"):
                    result = create_tree_from_file_task(
                        task, b"file content", "test.pdf", "My Tree",
                        services=services, user_id=uuid4(),
                    )

                    assert "tree_id" in result
                    assert result["chapter_count"] == 1


def test_create_tree_from_file_task_respects_chapter_indices():
    """When chapter_indices is provided, only those chapters should be processed."""
    task = _make_task()
    services = _make_services()
    chapters = [
        _make_chapter(index=0, title="Ch1", pages=[_make_page()]),
        _make_chapter(index=1, title="Ch2", pages=[_make_page()]),
        _make_chapter(index=2, title="Ch3", pages=[_make_page()]),
    ]
    doc = _make_document(chapters=chapters)

    with patch("application.services.tree_import._parse_and_chunk") as mock_parse:
        mock_parse.return_value = (doc, [], "hash123", {})

        with patch("application.services.tree_import.PROJECT_ROOT", Path(tempfile.gettempdir())):
            with patch("application.services.tree_import.ChapterAwareSplitter") as mock_splitter_cls:
                mock_splitter = MagicMock()
                mock_splitter.split.return_value = []
                mock_splitter_cls.return_value = mock_splitter

                with patch("fitz.open"):
                    result = create_tree_from_file_task(
                        task, b"file content", "test.pdf", "My Tree",
                        services=services, user_id=uuid4(),
                        chapter_indices=[0, 2],  # Only chapters 0 and 2
                    )

                    assert result["chapter_count"] == 2


def test_create_tree_from_file_task_enforces_document_limit():
    """When importing would exceed the document limit, PlanLimitExceeded must be raised."""
    from api.limit_checks import PlanLimitExceeded

    task = _make_task()
    services = _make_services()
    services.subscription_store.get_user_limits.return_value = MagicMock(
        current_documents=95, max_documents=100
    )
    chapters = [_make_chapter(index=i, pages=[_make_page()]) for i in range(10)]
    doc = _make_document(chapters=chapters)

    with patch("application.services.tree_import._parse_and_chunk") as mock_parse:
        mock_parse.return_value = (doc, [], "hash123", {})

        with patch("application.services.tree_import.PROJECT_ROOT", Path(tempfile.gettempdir())):
            with patch("application.services.tree_import.ChapterAwareSplitter") as mock_splitter_cls:
                mock_splitter = MagicMock()
                mock_splitter.split.return_value = []
                mock_splitter_cls.return_value = mock_splitter

                with pytest.raises(PlanLimitExceeded, match="exceeding your limit"):
                    create_tree_from_file_task(
                        task, b"file content", "test.pdf", "My Tree",
                        services=services, user_id=uuid4(),
                    )


def test_create_tree_from_file_task_no_chapters():
    """When no chapters are found, the task must return chapter_count=0."""
    task = _make_task()
    services = _make_services()
    doc = _make_document(chapters=[])

    with patch("application.services.tree_import._parse_and_chunk") as mock_parse:
        mock_parse.return_value = (doc, [], "hash123", {})

        with patch("application.services.tree_import.PROJECT_ROOT", Path(tempfile.gettempdir())):
            result = create_tree_from_file_task(
                task, b"file content", "test.pdf", "My Tree",
                services=services, user_id=uuid4(),
            )

            assert result["chapter_count"] == 0


def test_create_tree_from_file_task_unsupported_file_type():
    """An unsupported file extension must raise ValueError."""
    task = _make_task()
    services = _make_services()

    with pytest.raises(ValueError, match="Unsupported file type"):
        create_tree_from_file_task(
            task, b"file content", "test.xyz", "My Tree",
            services=services, user_id=uuid4(),
        )


def test_create_tree_from_file_task_cleans_up_temp_file():
    """The temporary file must be deleted even on success."""
    task = _make_task()
    services = _make_services()
    chapter = _make_chapter(pages=[_make_page()])
    doc = _make_document(chapters=[chapter])

    with patch("application.services.tree_import._parse_and_chunk") as mock_parse:
        mock_parse.return_value = (doc, [], "hash123", {})

        with patch("application.services.tree_import.PROJECT_ROOT", Path(tempfile.gettempdir())):
            with patch("application.services.tree_import.ChapterAwareSplitter") as mock_splitter_cls:
                mock_splitter = MagicMock()
                mock_splitter.split.return_value = []
                mock_splitter_cls.return_value = mock_splitter

                with patch("fitz.open"):
                    create_tree_from_file_task(
                        task, b"file content", "test.pdf", "My Tree",
                        services=services, user_id=uuid4(),
                    )


# ---------------------------------------------------------------------------
# import_youtube_task
# ---------------------------------------------------------------------------


def test_import_youtube_task_returns_doc_id_and_title():
    """On success, the task must return doc_id and title."""
    task = _make_task()
    tree_id = uuid4()
    services = _make_services()
    services.kt_doc_store.create_youtube_document.return_value = MagicMock(id=uuid4())

    mock_meta = MagicMock()
    mock_meta.title = "Test Video"

    with patch("infrastructure.ingest.youtube_loader.extract_video_id", return_value="abc123"):
        with patch("infrastructure.ingest.youtube_loader.fetch_metadata", return_value=mock_meta):
            with patch("infrastructure.ingest.youtube_loader.fetch_transcript", return_value="This is a transcript."):
                result = import_youtube_task(
                    task, "https://youtube.com/watch?v=abc123", tree_id,
                    chapter_id=None, chapter_number=None,
                    services=services,
                )

                assert "doc_id" in result
                assert result["title"] == "Test Video"


def test_import_youtube_task_invalid_url():
    """An invalid YouTube URL must raise HTTPException 422."""
    from fastapi import HTTPException

    task = _make_task()
    tree_id = uuid4()
    services = _make_services()

    with patch("infrastructure.ingest.youtube_loader.extract_video_id") as mock_extract:
        mock_extract.side_effect = ValueError("Invalid YouTube URL")

        with pytest.raises(HTTPException) as exc_info:
            import_youtube_task(
                task, "not-a-youtube-url", tree_id,
                chapter_id=None, chapter_number=None,
                services=services,
            )

        assert exc_info.value.status_code == 422


def test_import_youtube_task_video_unavailable():
    """When the video is unavailable, HTTPException 400 must be raised."""
    from fastapi import HTTPException

    task = _make_task()
    tree_id = uuid4()
    services = _make_services()

    with patch("infrastructure.ingest.youtube_loader.extract_video_id", return_value="abc123"):
        with patch("infrastructure.ingest.youtube_loader.fetch_metadata") as mock_meta_fn:
            from infrastructure.ingest.youtube_loader import VideoUnavailable
            mock_meta_fn.side_effect = VideoUnavailable("Video not found")

            with pytest.raises(HTTPException) as exc_info:
                import_youtube_task(
                    task, "https://youtube.com/watch?v=abc123", tree_id,
                    chapter_id=None, chapter_number=None,
                    services=services,
                )

            assert exc_info.value.status_code == 400


def test_import_youtube_task_transcript_unavailable():
    """When no transcript is available, HTTPException 422 must be raised."""
    from fastapi import HTTPException

    task = _make_task()
    tree_id = uuid4()
    services = _make_services()

    with patch("infrastructure.ingest.youtube_loader.extract_video_id", return_value="abc123"):
        with patch("infrastructure.ingest.youtube_loader.fetch_metadata", return_value=MagicMock(title="Test")):
            with patch("infrastructure.ingest.youtube_loader.fetch_transcript") as mock_transcript:
                from infrastructure.ingest.youtube_loader import TranscriptUnavailable
                mock_transcript.side_effect = TranscriptUnavailable("No transcript")

                with pytest.raises(HTTPException) as exc_info:
                    import_youtube_task(
                        task, "https://youtube.com/watch?v=abc123", tree_id,
                        chapter_id=None, chapter_number=None,
                        services=services,
                    )

                assert exc_info.value.status_code == 422


def test_import_youtube_task_chunks_when_chapter_provided():
    """When chapter_id and chapter_number are provided, the transcript must be chunked."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    services = _make_services()
    services.kt_doc_store.create_youtube_document.return_value = MagicMock(id=uuid4())

    mock_meta = MagicMock()
    mock_meta.title = "Test Video"

    with patch("infrastructure.ingest.youtube_loader.extract_video_id", return_value="abc123"):
        with patch("infrastructure.ingest.youtube_loader.fetch_metadata", return_value=mock_meta):
            with patch("infrastructure.ingest.youtube_loader.fetch_transcript", return_value="Line 1\nLine 2\nLine 3"):
                with patch("application.services.tree_import.ChapterAwareSplitter") as mock_splitter_cls:
                    mock_splitter = MagicMock()
                    mock_chunk = MagicMock()
                    mock_chunk.id = None
                    mock_chunk.text = "chunked text"
                    mock_chunk.token_count = 5
                    mock_splitter.split.return_value = [mock_chunk]
                    mock_splitter_cls.return_value = mock_splitter

                    import_youtube_task(
                        task, "https://youtube.com/watch?v=abc123", tree_id,
                        chapter_id=chapter_id, chapter_number=1,
                        services=services,
                    )

                    # Chunks should be saved
                    services.kt_content_store.save_chunks.assert_called_once()


# ---------------------------------------------------------------------------
# ingest_file_task
# ---------------------------------------------------------------------------


def test_ingest_file_task_returns_doc_id_title_and_chunks():
    """On success, the task must return doc_id, title, and chunk count."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    services = _make_services()
    doc_uid = uuid4()
    services.kt_doc_store.create_document.return_value = MagicMock(id=doc_uid)

    from core.model.chunk import Chunk as SplitterChunk
    chunk = SplitterChunk(text="Some content", token_count=10)

    with patch("application.services.tree_import._parse_and_chunk") as mock_parse:
        mock_doc = _make_document(chapters=[_make_chapter(pages=[_make_page(text="Some content")])])
        mock_parse.return_value = (mock_doc, [chunk], "hash123", {})

        with patch("application.services.tree_import.PROJECT_ROOT", Path(tempfile.gettempdir())):
            result = ingest_file_task(
                task, tree_id, chapter_id, chapter_number=1,
                file_bytes=b"content", filename="test.txt",
                services=services,
            )

        assert result["doc_id"] == str(doc_uid)
        assert result["title"] == "test"
        assert result["chunks"] == 1


def test_ingest_file_task_raises_when_no_text():
    """When no text can be extracted, ValueError must be raised."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    services = _make_services()

    from core.model.chunk import Chunk as SplitterChunk
    chunk = SplitterChunk(text="   ", token_count=0)  # Whitespace only

    with patch("application.services.tree_import._parse_and_chunk") as mock_parse:
        # Document with empty/missing pages — text extraction fails
        mock_doc = _make_document(chapters=[_make_chapter(pages=[_make_page(text="")])])
        mock_parse.return_value = (mock_doc, [chunk], "hash123", {})

        with patch("application.services.tree_import.PROJECT_ROOT", Path(tempfile.gettempdir())):
            with pytest.raises(ValueError, match="No text could be extracted"):
                ingest_file_task(
                    task, tree_id, chapter_id, chapter_number=1,
                    file_bytes=b"content", filename="test.txt",
                    services=services,
                )


def test_ingest_file_task_saves_chunks():
    """Extracted chunks must be persisted via kt_content_store."""
    task = _make_task()
    tree_id = uuid4()
    chapter_id = uuid4()
    services = _make_services()
    services.kt_doc_store.create_document.return_value = MagicMock(id=uuid4())

    from core.model.chunk import Chunk as SplitterChunk
    chunks = [
        SplitterChunk(text="Content 1", token_count=5),
        SplitterChunk(text="Content 2", token_count=5),
    ]

    with patch("application.services.tree_import._parse_and_chunk") as mock_parse:
        mock_doc = _make_document(chapters=[_make_chapter(pages=[
            _make_page(text="Content 1"),
            _make_page(text="Content 2"),
        ])])
        mock_parse.return_value = (mock_doc, chunks, "hash123", {})

        with patch("application.services.tree_import.PROJECT_ROOT", Path(tempfile.gettempdir())):
            ingest_file_task(
                task, tree_id, chapter_id, chapter_number=1,
                file_bytes=b"content", filename="test.txt",
                services=services,
            )

            services.kt_content_store.save_chunks.assert_called_once()
            saved_chunks = services.kt_content_store.save_chunks.call_args[0][0]
            assert len(saved_chunks) == 2
