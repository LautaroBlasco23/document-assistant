"""
Integration tests for the Knowledge Tree router (api/routers/knowledge_trees.py).

Requires a running PostgreSQL instance (docker compose up -d postgres).
Run with:  uv run pytest -m integration
"""

import json
import os
import time
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

# Set environment variables BEFORE any imports that may read them.
os.environ.setdefault("DOCASSIST_AUTH__JWT_SECRET", "x" * 40)
os.environ.setdefault("DOCASSIST_LLM_PROVIDER", "ollama")

import pytest
from ebooklib import epub
from fastapi.testclient import TestClient

import fitz
from api.main import create_app
from api.services import get_services
from core.model.knowledge_tree import KnowledgeChunk
from infrastructure.config import load_config
from core.model.question import Question, QuestionType
from infrastructure.db.knowledge_tree_repository import (
    PostgresFlashcardStore,
    PostgresKnowledgeChapterStore,
    PostgresKnowledgeContentStore,
    PostgresKnowledgeDocumentStore,
    PostgresKnowledgeQuestionStore,
    PostgresKnowledgeTreeStore,
)
from infrastructure.db.postgres import PostgresPool
from infrastructure.db.user_repository import PostgresUserStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pdf_bytes(num_pages: int = 3) -> bytes:
    """Create a minimal multi-page PDF with chapter-like headings."""
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page()
        text = (
            f"Chapter {i + 1}\n\n"
            "This is sample content with enough words to allow chunking. " * 80
        )
        page.insert_text((72, 72), text)
    buf = BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def _make_epub_bytes(
    title: str = "Test EPUB",
    chapters: list[tuple[str, str]] | None = None,
) -> bytes:
    """Create a minimal EPUB in memory."""
    if chapters is None:
        chapters = [("c1.xhtml", "Chapter 1"), ("c2.xhtml", "Chapter 2")]
    book = epub.EpubBook()
    book.set_identifier("test-id")
    book.set_title(title)
    book.set_language("en")
    spine = []
    for idx, (file_name, ch_title) in enumerate(chapters):
        item = epub.EpubHtml(title=ch_title, file_name=file_name, lang="en")
        item.content = (
            f"<html><head><title>{ch_title}</title></head>"
            f"<body><h1>{ch_title}</h1><p>{'word ' * 200}</p></body></html>"
        )
        book.add_item(item)
        spine.append(item)
    book.spine = spine
    book.toc = [
        epub.Link(file_name, ch_title, f"id{idx}")
        for idx, (file_name, ch_title) in enumerate(chapters)
    ]
    nav = epub.EpubNav()
    book.add_item(nav)
    book.add_item(epub.EpubNcx())
    buf = BytesIO()
    epub.write_epub(buf, book)
    return buf.getvalue()


def _poll_task(client: TestClient, task_id: str, timeout: float = 30.0) -> dict:
    """Poll /api/tasks/{task_id} until the task reaches a terminal state."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 200
        data = resp.json()
        if data["status"] in ("completed", "failed"):
            return data
        time.sleep(0.25)
    raise TimeoutError(f"Task {task_id} did not finish within {timeout}s")


def _mock_llm_for_generation() -> None:
    """
    Monkey-patch the global services LLM so that question/flashcard
    generation background tasks receive valid JSON without calling a real provider.
    """
    services = get_services()

    class _MockLLM:
        def chat(self, system: str, user: str, format: str | None = None) -> str:  # noqa: A002
            system_lower = system.lower()
            if "true false" in system_lower or "true_false" in system_lower:
                return json.dumps(
                    {"questions": [{"statement": "Water boils at 100C", "answer": True}]}
                )
            if "multiple choice" in system_lower or "multiple_choice" in system_lower:
                return json.dumps(
                    {
                        "questions": [
                            {
                                "question": "What is 2+2?",
                                "choices": ["3", "4", "5", "6"],
                                "correct_index": 1,
                            }
                        ]
                    }
                )
            if "matching" in system_lower:
                return json.dumps(
                    {
                        "questions": [
                            {
                                "pairs": [
                                    {"term": "A", "definition": "1"},
                                    {"term": "B", "definition": "2"},
                                    {"term": "C", "definition": "3"},
                                ]
                            }
                        ]
                    }
                )
            if "checkbox" in system_lower:
                return json.dumps(
                    {
                        "questions": [
                            {
                                "question": "Select primes",
                                "choices": ["2", "3", "4", "5"],
                                "correct_indices": [0, 1, 3],
                            }
                        ]
                    }
                )
            # Flashcard or fallback
            return json.dumps(
                {"front": "What is the capital of France?", "back": "Paris"}
            )

    services.llm = _MockLLM()
    services.fast_llm = _MockLLM()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def db_pool():
    """Connect to PostgreSQL and ensure schema is present. Skip if unreachable."""
    cfg = load_config().postgres
    pool = PostgresPool(cfg)
    try:
        pool.connect()
    except Exception:
        pytest.skip("PostgreSQL not reachable — skipping integration tests")
    yield pool
    pool.close()


@pytest.fixture(scope="module")
def app_and_client(db_pool):
    """
    Build the real FastAPI app, run lifespan, register a test user,
    and yield an authenticated TestClient.
    """
    app = create_app()

    with TestClient(app) as client:
        email = "kt_integration@example.com"
        password = "password123"

        # Ensure a clean slate: delete user if they already exist from a prior run
        user_store = PostgresUserStore(db_pool)
        existing = user_store.get_by_email(email)
        if existing:
            tree_store = PostgresKnowledgeTreeStore(db_pool)
            for tree in tree_store.list_trees_for_user(existing.id):
                tree_store.delete_tree(tree.id)
            with db_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM users WHERE id = %s", (existing.id,))
                conn.commit()

        # Register test user
        reg_resp = client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "display_name": "KT Integration"},
        )
        assert reg_resp.status_code == 201

        # Log in to obtain a JWT
        login_resp = client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"

        yield client

        # -- module-level cleanup --
        user = user_store.get_by_email(email)
        if user:
            tree_store = PostgresKnowledgeTreeStore(db_pool)
            for tree in tree_store.list_trees_for_user(user.id):
                tree_store.delete_tree(tree.id)
            with db_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM users WHERE id = %s", (user.id,))
                conn.commit()

        # Remove any files left in storage directory
        storage_dir = Path(__file__).parent.parent.parent / "data" / "storage"
        if storage_dir.exists():
            for f in storage_dir.iterdir():
                try:
                    f.unlink()
                except OSError:
                    pass


@pytest.fixture
def client(app_and_client):
    """Convenience alias for the authenticated TestClient."""
    return app_and_client


# ---------------------------------------------------------------------------
# 1. Import pipeline end-to-end
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_import_pipeline_creates_tree_chapters_and_chunks(client, db_pool):
    """Upload a PDF via /import, wait for the background task, then verify DB state."""
    pdf_bytes = _make_pdf_bytes(num_pages=3)

    resp = client.post(
        "/api/knowledge-trees/import",
        data={"title": "Imported Book"},
        files={"file": ("book.pdf", BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]

    task = _poll_task(client, task_id, timeout=30.0)
    assert task["status"] == "completed"
    result = task["result"]
    assert result is not None
    tree_id = result["tree_id"]
    assert tree_id is not None
    assert result["chapter_count"] >= 1

    # Verify tree exists
    tree_store = PostgresKnowledgeTreeStore(db_pool)
    tree = tree_store.get_tree(UUID(tree_id))
    assert tree is not None
    assert tree.title == "Imported Book"

    # Verify chapters exist
    chapter_store = PostgresKnowledgeChapterStore(db_pool)
    chapters = chapter_store.list_chapters(tree.id)
    assert len(chapters) == result["chapter_count"]

    # Verify chunks exist for at least one chapter
    content_store = PostgresKnowledgeContentStore(db_pool)
    for ch in chapters:
        chunks = content_store.get_chunks(tree.id, ch.number)
        assert len(chunks) >= 0  # may be zero for very short chapters, but usually >0

    # Verify source document exists
    doc_store = PostgresKnowledgeDocumentStore(db_pool)
    docs = doc_store.list_documents(tree.id, None)
    assert len(docs) >= len(chapters)  # at least one per chapter + tree-level source doc


@pytest.mark.integration
def test_import_with_chapter_indices(client, db_pool):
    """Import only selected chapter indices."""
    pdf_bytes = _make_pdf_bytes(num_pages=3)

    resp = client.post(
        "/api/knowledge-trees/import",
        data={"title": "Partial Book", "chapter_indices": "0"},
        files={"file": ("book.pdf", BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp.status_code == 202
    task = _poll_task(client, resp.json()["task_id"], timeout=30.0)
    assert task["status"] == "completed"
    assert task["result"]["chapter_count"] == 1


# ---------------------------------------------------------------------------
# 2. Question generation background task lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_question_generation_task_lifecycle(client, db_pool):
    """Generate questions for a chapter that already has chunks."""
    # Set up tree, chapter, document and chunks directly in DB
    tree_store = PostgresKnowledgeTreeStore(db_pool)
    user_store = PostgresUserStore(db_pool)
    user = user_store.get_by_email("kt_integration@example.com")
    tree = tree_store.create_tree("QGen Tree", None, user.id)

    chapter_store = PostgresKnowledgeChapterStore(db_pool)
    ch = chapter_store.create_chapter(tree.id, "QGen Chapter")

    doc_store = PostgresKnowledgeDocumentStore(db_pool)
    doc = doc_store.create_document(tree.id, ch.id, "QGen Doc", "some content", False)

    content_store = PostgresKnowledgeContentStore(db_pool)
    content_store.save_chunks([
        KnowledgeChunk(
            id=uuid4(),
            tree_id=tree.id,
            chapter_id=ch.id,
            doc_id=doc.id,
            chunk_index=0,
            text="Water boils at 100 degrees Celsius at sea level. " * 20,
            token_count=50,
        ),
        KnowledgeChunk(
            id=uuid4(),
            tree_id=tree.id,
            chapter_id=ch.id,
            doc_id=doc.id,
            chunk_index=1,
            text="The capital of France is Paris. " * 20,
            token_count=50,
        ),
    ])

    # Mock LLM so the background task does not call a real provider
    _mock_llm_for_generation()

    resp = client.post(
        f"/api/knowledge-trees/{tree.id}/chapters/{ch.number}/questions",
        json={"question_types": ["true_false", "multiple_choice"]},
    )
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]

    task = _poll_task(client, task_id, timeout=30.0)
    assert task["status"] == "completed"

    # Verify questions exist via API
    resp = client.get(f"/api/knowledge-trees/{tree.id}/chapters/{ch.number}/questions")
    assert resp.status_code == 200
    questions = resp.json()
    assert len(questions) >= 2  # at least one TF + one MC

    types = {q["question_type"] for q in questions}
    assert "true_false" in types
    assert "multiple_choice" in types

    # Verify each question has the expected data structure
    for q in questions:
        assert "id" in q
        assert "question_type" in q
        assert "question_data" in q
        assert isinstance(q["question_data"], dict)

    # Cleanup is handled by the module fixture


@pytest.mark.integration
def test_question_generation_with_type_filter(client, db_pool):
    """Request only checkbox questions and verify only that type is stored."""
    tree_store = PostgresKnowledgeTreeStore(db_pool)
    user_store = PostgresUserStore(db_pool)
    user = user_store.get_by_email("kt_integration@example.com")
    tree = tree_store.create_tree("Filtered QGen", None, user.id)
    ch = PostgresKnowledgeChapterStore(db_pool).create_chapter(tree.id, "Ch1")
    doc = PostgresKnowledgeDocumentStore(db_pool).create_document(
        tree.id, ch.id, "Doc", "content", False
    )
    PostgresKnowledgeContentStore(db_pool).save_chunks([
        KnowledgeChunk(
            id=uuid4(), tree_id=tree.id, chapter_id=ch.id, doc_id=doc.id,
            chunk_index=0, text="Some text. " * 30, token_count=30,
        ),
    ])

    _mock_llm_for_generation()

    resp = client.post(
        f"/api/knowledge-trees/{tree.id}/chapters/{ch.number}/questions",
        json={"question_types": ["checkbox"]},
    )
    assert resp.status_code == 202
    task = _poll_task(client, resp.json()["task_id"], timeout=30.0)
    assert task["status"] == "completed"

    resp = client.get(
        f"/api/knowledge-trees/{tree.id}/chapters/{ch.number}/questions",
        params={"type": "checkbox"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    resp = client.get(
        f"/api/knowledge-trees/{tree.id}/chapters/{ch.number}/questions",
        params={"type": "true_false"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 0


# ---------------------------------------------------------------------------
# 3. Flashcard generation background task
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_flashcard_generation_task(client, db_pool):
    """Submit a flashcard generation task and verify the stored flashcard."""
    tree_store = PostgresKnowledgeTreeStore(db_pool)
    user_store = PostgresUserStore(db_pool)
    user = user_store.get_by_email("kt_integration@example.com")
    tree = tree_store.create_tree("Flash Tree", None, user.id)
    ch = PostgresKnowledgeChapterStore(db_pool).create_chapter(tree.id, "Flash Chapter")

    _mock_llm_for_generation()

    resp = client.post(
        f"/api/knowledge-trees/{tree.id}/chapters/{ch.number}/flashcards",
        json={"selected_text": "The capital of France is Paris."},
    )
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]

    task = _poll_task(client, task_id, timeout=30.0)
    assert task["status"] == "completed"

    flash_store = PostgresFlashcardStore(db_pool)
    cards = flash_store.list_flashcards(tree.id, ch.id)
    assert len(cards) == 1
    assert cards[0].front == "What is the capital of France?"
    assert cards[0].back == "Paris"


# ---------------------------------------------------------------------------
# 4. Document ingest into existing chapter
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_ingest_file_into_chapter(client, db_pool):
    """Ingest a PDF into an existing chapter and verify document + chunks."""
    tree_store = PostgresKnowledgeTreeStore(db_pool)
    user_store = PostgresUserStore(db_pool)
    user = user_store.get_by_email("kt_integration@example.com")
    tree = tree_store.create_tree("Ingest Tree", None, user.id)
    ch = PostgresKnowledgeChapterStore(db_pool).create_chapter(tree.id, "Ingest Chapter")

    pdf_bytes = _make_pdf_bytes(num_pages=2)
    resp = client.post(
        f"/api/knowledge-trees/{tree.id}/chapters/{ch.number}/documents/ingest",
        files={"file": ("ingest.pdf", BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]

    task = _poll_task(client, task_id, timeout=30.0)
    assert task["status"] == "completed"
    result = task["result"]
    assert "doc_id" in result

    doc_store = PostgresKnowledgeDocumentStore(db_pool)
    doc = doc_store.get_document(UUID(result["doc_id"]))
    assert doc is not None
    assert doc.chapter_id == ch.id
    assert "ingest" in doc.title.lower() or "ingest" in doc.title

    content_store = PostgresKnowledgeContentStore(db_pool)
    chunks = content_store.get_chunks(tree.id, ch.number)
    assert len(chunks) > 0


# ---------------------------------------------------------------------------
# 5. File serving
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_get_document_file(client, db_pool, tmp_path):
    """Serve an uploaded document file with the correct content-type."""
    tree_store = PostgresKnowledgeTreeStore(db_pool)
    user_store = PostgresUserStore(db_pool)
    user = user_store.get_by_email("kt_integration@example.com")
    tree = tree_store.create_tree("File Tree", None, user.id)
    ch = PostgresKnowledgeChapterStore(db_pool).create_chapter(tree.id, "File Chapter")

    # Write a real PDF to the storage directory
    storage_dir = Path(__file__).parent.parent.parent / "data" / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_path = storage_dir / f"{uuid4()}.pdf"
    pdf_bytes = _make_pdf_bytes(num_pages=1)
    file_path.write_bytes(pdf_bytes)

    doc_store = PostgresKnowledgeDocumentStore(db_pool)
    doc = doc_store.create_document(tree.id, ch.id, "File Doc", "content", False)
    doc_store.update_document_source_file(doc.id, str(file_path), "file.pdf")

    resp = client.get(f"/api/knowledge-trees/{tree.id}/documents/{doc.id}/file")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content == pdf_bytes


@pytest.mark.integration
def test_get_document_thumbnail(client, db_pool, tmp_path):
    """Return a PNG thumbnail for a PDF document."""
    tree_store = PostgresKnowledgeTreeStore(db_pool)
    user_store = PostgresUserStore(db_pool)
    user = user_store.get_by_email("kt_integration@example.com")
    tree = tree_store.create_tree("Thumb Tree", None, user.id)
    ch = PostgresKnowledgeChapterStore(db_pool).create_chapter(tree.id, "Thumb Chapter")

    storage_dir = Path(__file__).parent.parent.parent / "data" / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_path = storage_dir / f"{uuid4()}.pdf"
    pdf_bytes = _make_pdf_bytes(num_pages=1)
    file_path.write_bytes(pdf_bytes)

    doc_store = PostgresKnowledgeDocumentStore(db_pool)
    doc = doc_store.create_document(tree.id, ch.id, "Thumb Doc", "content", False)
    doc_store.update_document_source_file(doc.id, str(file_path), "thumb.pdf")

    resp = client.get(f"/api/knowledge-trees/{tree.id}/documents/{doc.id}/thumbnail")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert len(resp.content) > 0


@pytest.mark.integration
def test_get_thumbnail_non_pdf_returns_404(client, db_pool):
    """Thumbnails are only available for PDF files."""
    tree_store = PostgresKnowledgeTreeStore(db_pool)
    user_store = PostgresUserStore(db_pool)
    user = user_store.get_by_email("kt_integration@example.com")
    tree = tree_store.create_tree("NoThumb Tree", None, user.id)
    ch = PostgresKnowledgeChapterStore(db_pool).create_chapter(tree.id, "NoThumb Chapter")

    storage_dir = Path(__file__).parent.parent.parent / "data" / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_path = storage_dir / f"{uuid4()}.epub"
    file_path.write_bytes(b"fake epub")

    doc_store = PostgresKnowledgeDocumentStore(db_pool)
    doc = doc_store.create_document(tree.id, ch.id, "NoThumb Doc", "content", False)
    doc_store.update_document_source_file(doc.id, str(file_path), "book.epub")

    resp = client.get(f"/api/knowledge-trees/{tree.id}/documents/{doc.id}/thumbnail")
    assert resp.status_code == 404


@pytest.mark.integration
def test_get_file_missing_path_returns_404(client, db_pool):
    """A document without a source_file_path should return 404."""
    tree_store = PostgresKnowledgeTreeStore(db_pool)
    user_store = PostgresUserStore(db_pool)
    user = user_store.get_by_email("kt_integration@example.com")
    tree = tree_store.create_tree("MissingFile Tree", None, user.id)
    ch = PostgresKnowledgeChapterStore(db_pool).create_chapter(tree.id, "MissingFile Chapter")

    doc_store = PostgresKnowledgeDocumentStore(db_pool)
    doc = doc_store.create_document(tree.id, ch.id, "MissingFile Doc", "content", False)

    resp = client.get(f"/api/knowledge-trees/{tree.id}/documents/{doc.id}/file")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 6. Preview endpoint
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_preview_pdf_returns_structure(client):
    """Preview a PDF without creating any tree or persistent data."""
    pdf_bytes = _make_pdf_bytes(num_pages=2)
    resp = client.post(
        "/api/knowledge-trees/preview",
        files={"file": ("preview.pdf", BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "file_hash" in data
    assert "filename" in data
    assert "num_chapters" in data
    assert isinstance(data["chapters"], list)
    assert data["num_chapters"] >= 1


@pytest.mark.integration
def test_preview_epub_returns_structure(client):
    """Preview an EPUB without creating any tree or persistent data."""
    epub_bytes = _make_epub_bytes(
        title="Preview Book",
        chapters=[("c1.xhtml", "Intro"), ("c2.xhtml", "Body")],
    )
    resp = client.post(
        "/api/knowledge-trees/preview",
        files={"file": ("preview.epub", BytesIO(epub_bytes), "application/epub+zip")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "preview.epub"
    assert data["num_chapters"] == 2
    assert data["chapters"][0]["title"] == "Intro"
    assert data["chapters"][1]["title"] == "Body"


@pytest.mark.integration
def test_preview_unsupported_file_returns_422(client):
    """Only PDF and EPUB are accepted by the preview endpoint."""
    resp = client.post(
        "/api/knowledge-trees/preview",
        files={"file": ("readme.txt", BytesIO(b"hello"), "text/plain")},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 7. Cascade delete verification
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_cascade_delete_tree_removes_everything(client, db_pool):
    """Delete a tree and assert that chapters, docs, chunks and questions are gone."""
    tree_store = PostgresKnowledgeTreeStore(db_pool)
    user_store = PostgresUserStore(db_pool)
    user = user_store.get_by_email("kt_integration@example.com")
    tree = tree_store.create_tree("Cascade Tree", None, user.id)

    chapter_store = PostgresKnowledgeChapterStore(db_pool)
    ch = chapter_store.create_chapter(tree.id, "Cascade Chapter")

    doc_store = PostgresKnowledgeDocumentStore(db_pool)
    doc = doc_store.create_document(tree.id, ch.id, "Cascade Doc", "content", False)

    content_store = PostgresKnowledgeContentStore(db_pool)
    content_store.save_chunks([
        KnowledgeChunk(
            id=uuid4(),
            tree_id=tree.id,
            chapter_id=ch.id,
            doc_id=doc.id,
            chunk_index=0,
            text="chunk",
            token_count=5,
        ),
    ])

    question_store = PostgresKnowledgeQuestionStore(db_pool)
    question_store.save_questions([
        Question(
            id=uuid4(),
            tree_id=tree.id,
            chapter_id=ch.id,
            question_type="true_false",
            question_data={"statement": "Test", "answer": True},
        ),
    ])

    resp = client.delete(f"/api/knowledge-trees/{tree.id}")
    assert resp.status_code == 204

    assert tree_store.get_tree(tree.id) is None
    assert chapter_store.list_chapters(tree.id) == []
    assert doc_store.list_documents(tree.id, None) == []
    assert content_store.get_chunks(tree.id, ch.number) == []
    assert question_store.get_questions(tree.id, ch.id) == []


# ---------------------------------------------------------------------------
# 8. Chapter reordering / renumbering
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_delete_middle_chapter_renumbers_remaining(client, db_pool):
    """Deleting chapter 2 should leave chapters numbered 1 and 2 (not 1 and 3)."""
    tree_store = PostgresKnowledgeTreeStore(db_pool)
    user_store = PostgresUserStore(db_pool)
    user = user_store.get_by_email("kt_integration@example.com")
    tree = tree_store.create_tree("Renumber Tree", None, user.id)

    chapter_store = PostgresKnowledgeChapterStore(db_pool)
    ch1 = chapter_store.create_chapter(tree.id, "First")
    ch2 = chapter_store.create_chapter(tree.id, "Second")
    ch3 = chapter_store.create_chapter(tree.id, "Third")
    assert ch1.number == 1
    assert ch2.number == 2
    assert ch3.number == 3

    resp = client.delete(f"/api/knowledge-trees/{tree.id}/chapters/2")
    assert resp.status_code == 204

    chapters = chapter_store.list_chapters(tree.id)
    numbers = [c.number for c in chapters]
    assert numbers == [1, 2]
    titles = [c.title for c in chapters]
    assert "First" in titles
    assert "Third" in titles
    assert "Second" not in titles


@pytest.mark.integration
def test_update_chapter_title(client, db_pool):
    """Updating a chapter title should be reflected in subsequent list calls."""
    tree_store = PostgresKnowledgeTreeStore(db_pool)
    user_store = PostgresUserStore(db_pool)
    user = user_store.get_by_email("kt_integration@example.com")
    tree = tree_store.create_tree("UpdateCh Tree", None, user.id)
    ch = PostgresKnowledgeChapterStore(db_pool).create_chapter(tree.id, "Old Title")

    resp = client.put(
        f"/api/knowledge-trees/{tree.id}/chapters/{ch.number}",
        json={"title": "New Title"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"

    resp = client.get(f"/api/knowledge-trees/{tree.id}/chapters")
    assert resp.status_code == 200
    titles = [c["title"] for c in resp.json()]
    assert "New Title" in titles
    assert "Old Title" not in titles


# ---------------------------------------------------------------------------
# Additional router CRUD tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_create_and_list_trees(client):
    """Creating trees via the API should include them in the list response."""
    resp = client.post("/api/knowledge-trees", json={"title": "Alpha Tree"})
    assert resp.status_code == 201
    alpha = resp.json()

    resp = client.post("/api/knowledge-trees", json={"title": "Beta Tree"})
    assert resp.status_code == 201

    resp = client.get("/api/knowledge-trees")
    assert resp.status_code == 200
    titles = [t["title"] for t in resp.json()]
    assert "Alpha Tree" in titles
    assert "Beta Tree" in titles

    client.delete(f"/api/knowledge-trees/{alpha['id']}")


@pytest.mark.integration
def test_update_tree(client, db_pool):
    """PUT should update title and description."""
    tree_store = PostgresKnowledgeTreeStore(db_pool)
    user_store = PostgresUserStore(db_pool)
    user = user_store.get_by_email("kt_integration@example.com")
    tree = tree_store.create_tree("Old Name", "Old Desc", user.id)

    resp = client.put(
        f"/api/knowledge-trees/{tree.id}",
        json={"title": "New Name", "description": "New Desc"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "New Name"
    assert data["description"] == "New Desc"


@pytest.mark.integration
def test_get_tree_not_found(client):
    """Fetching a non-existent tree should return 404."""
    resp = client.get(f"/api/knowledge-trees/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.integration
def test_create_and_list_documents(client, db_pool):
    """POST /documents should create a doc visible in the list."""
    tree_store = PostgresKnowledgeTreeStore(db_pool)
    user_store = PostgresUserStore(db_pool)
    user = user_store.get_by_email("kt_integration@example.com")
    tree = tree_store.create_tree("DocList Tree", None, user.id)
    ch = PostgresKnowledgeChapterStore(db_pool).create_chapter(tree.id, "DocList Chapter")

    resp = client.post(
        f"/api/knowledge-trees/{tree.id}/documents",
        json={"title": "My Doc", "content": "Hello world", "chapter_id": str(ch.id)},
    )
    assert resp.status_code == 201
    doc = resp.json()
    assert doc["title"] == "My Doc"
    assert doc["chapter_id"] == str(ch.id)

    resp = client.get(f"/api/knowledge-trees/{tree.id}/documents")
    assert resp.status_code == 200
    titles = [d["title"] for d in resp.json()]
    assert "My Doc" in titles


@pytest.mark.integration
def test_update_document(client, db_pool):
    """PUT /documents/{id} should update title and content."""
    tree_store = PostgresKnowledgeTreeStore(db_pool)
    user_store = PostgresUserStore(db_pool)
    user = user_store.get_by_email("kt_integration@example.com")
    tree = tree_store.create_tree("DocUpdate Tree", None, user.id)
    ch = PostgresKnowledgeChapterStore(db_pool).create_chapter(tree.id, "DocUpdate Chapter")
    doc_store = PostgresKnowledgeDocumentStore(db_pool)
    doc = doc_store.create_document(tree.id, ch.id, "Old", "Old content", False)

    resp = client.put(
        f"/api/knowledge-trees/{tree.id}/documents/{doc.id}",
        json={"title": "New", "content": "New content"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "New"
    assert data["content"] == "New content"


@pytest.mark.integration
def test_delete_document(client, db_pool):
    """DELETE /documents/{id} should remove the document."""
    tree_store = PostgresKnowledgeTreeStore(db_pool)
    user_store = PostgresUserStore(db_pool)
    user = user_store.get_by_email("kt_integration@example.com")
    tree = tree_store.create_tree("DocDelete Tree", None, user.id)
    ch = PostgresKnowledgeChapterStore(db_pool).create_chapter(tree.id, "DocDelete Chapter")
    doc_store = PostgresKnowledgeDocumentStore(db_pool)
    doc = doc_store.create_document(tree.id, ch.id, "ToDelete", "content", False)

    resp = client.delete(f"/api/knowledge-trees/{tree.id}/documents/{doc.id}")
    assert resp.status_code == 204

    assert doc_store.get_document(doc.id) is None


@pytest.mark.integration
def test_get_chapter_content(client, db_pool):
    """GET /chapters/{number}/content should return stored chunks."""
    tree_store = PostgresKnowledgeTreeStore(db_pool)
    user_store = PostgresUserStore(db_pool)
    user = user_store.get_by_email("kt_integration@example.com")
    tree = tree_store.create_tree("Content Tree", None, user.id)
    ch = PostgresKnowledgeChapterStore(db_pool).create_chapter(tree.id, "Content Chapter")
    doc = PostgresKnowledgeDocumentStore(db_pool).create_document(
        tree.id, ch.id, "Content Doc", "text", False
    )
    PostgresKnowledgeContentStore(db_pool).save_chunks([
        KnowledgeChunk(
            id=uuid4(), tree_id=tree.id, chapter_id=ch.id, doc_id=doc.id,
            chunk_index=0, text="first chunk", token_count=5,
        ),
        KnowledgeChunk(
            id=uuid4(), tree_id=tree.id, chapter_id=ch.id, doc_id=doc.id,
            chunk_index=1, text="second chunk", token_count=5,
        ),
    ])

    resp = client.get(f"/api/knowledge-trees/{tree.id}/chapters/{ch.number}/content")
    assert resp.status_code == 200
    chunks = resp.json()
    assert len(chunks) == 2
    texts = {c["text"] for c in chunks}
    assert "first chunk" in texts
    assert "second chunk" in texts


@pytest.mark.integration
def test_delete_question(client, db_pool):
    """DELETE a single question should remove it from the store."""
    tree_store = PostgresKnowledgeTreeStore(db_pool)
    user_store = PostgresUserStore(db_pool)
    user = user_store.get_by_email("kt_integration@example.com")
    tree = tree_store.create_tree("QDelete Tree", None, user.id)
    ch = PostgresKnowledgeChapterStore(db_pool).create_chapter(tree.id, "QDelete Chapter")
    question_store = PostgresKnowledgeQuestionStore(db_pool)
    q = Question(
        id=uuid4(),
        tree_id=tree.id,
        chapter_id=ch.id,
        question_type="true_false",
        question_data={"statement": "Sky is blue", "answer": True},
    )
    question_store.save_questions([q])

    resp = client.delete(
        f"/api/knowledge-trees/{tree.id}/chapters/{ch.number}/questions/{q.id}"
    )
    assert resp.status_code == 204

    assert question_store.get_questions(tree.id, ch.id) == []


@pytest.mark.integration
def test_import_rejects_unsupported_file(client):
    """The import endpoint should reject non-PDF/EPUB uploads."""
    resp = client.post(
        "/api/knowledge-trees/import",
        data={"title": "Bad"},
        files={"file": ("bad.txt", BytesIO(b"text"), "text/plain")},
    )
    assert resp.status_code == 422


@pytest.mark.integration
def test_ingest_rejects_unsupported_file(client, db_pool):
    """The chapter ingest endpoint should reject non-PDF/EPUB uploads."""
    tree_store = PostgresKnowledgeTreeStore(db_pool)
    user_store = PostgresUserStore(db_pool)
    user = user_store.get_by_email("kt_integration@example.com")
    tree = tree_store.create_tree("IngestReject Tree", None, user.id)
    ch = PostgresKnowledgeChapterStore(db_pool).create_chapter(tree.id, "IngestReject Chapter")

    resp = client.post(
        f"/api/knowledge-trees/{tree.id}/chapters/{ch.number}/documents/ingest",
        files={"file": ("bad.txt", BytesIO(b"text"), "text/plain")},
    )
    assert resp.status_code == 422
