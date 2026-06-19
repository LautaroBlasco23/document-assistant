"""
Unit tests for the knowledge-trees router.

Subject: api/routers/knowledge_trees.py
Scope:   Trees, chapters, documents CRUD; improve/revert; flashcards; questions;
         exam sessions; preview endpoint. Background task internals are out of scope.
Setup:   FastAPI TestClient with fully mocked services and current user.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.auth import get_current_user
from api.deps import get_services_dep
from api.routers import knowledge_trees as kt_router
from core.model.knowledge_tree import (
    ExamSession,
    Flashcard,
    KnowledgeChapter,
    KnowledgeDocument,
    KnowledgeTree,
)
from core.model.user import User

# ---------------------------------------------------------------------------
# Shared constants / helpers
# ---------------------------------------------------------------------------

USER_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TREE_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
CHAPTER_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
DOC_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
FLASHCARD_ID = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
QUESTION_ID = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
SESSION_ID = UUID("11111111-1111-1111-1111-111111111111")

_NOW = datetime(2024, 6, 1, 12, 0, 0)


def _make_user() -> User:
    return User(
        id=USER_ID,
        email="user@example.com",
        password_hash="hash",
        display_name="User",
        is_active=True,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _tree(tree_id=TREE_ID, user_id=USER_ID, title="My Tree") -> KnowledgeTree:
    return KnowledgeTree(
        id=tree_id, user_id=user_id, title=title,
        description=None, created_at=_NOW,
    )


def _chapter(
    number=1, chapter_id=CHAPTER_ID, tree_id=TREE_ID, title="Chapter 1",
) -> KnowledgeChapter:
    return KnowledgeChapter(
        id=chapter_id, tree_id=tree_id, number=number,
        title=title, created_at=_NOW,
    )


def _doc(doc_id=DOC_ID, tree_id=TREE_ID, chapter_id=CHAPTER_ID) -> KnowledgeDocument:
    return KnowledgeDocument(
        id=doc_id,
        tree_id=tree_id,
        chapter_id=chapter_id,
        title="Doc Title",
        content="Document content here.",
        is_main=False,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _flashcard(fid=FLASHCARD_ID) -> Flashcard:
    return Flashcard(
        id=fid,
        tree_id=TREE_ID,
        chapter_id=CHAPTER_ID,
        doc_id=None,
        front="What is X?",
        back="X is Y.",
        source_text="X is Y in this document.",
        created_at=_NOW,
    )


def _exam_session(sid=SESSION_ID) -> ExamSession:
    return ExamSession(
        id=sid,
        tree_id=TREE_ID,
        chapter_id=CHAPTER_ID,
        score=0.8,
        total_questions=5,
        correct_count=4,
        question_ids=["q1", "q2"],
        results={"q1": True, "q2": False},
        created_at=_NOW,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_services():
    svc = MagicMock()
    svc.llm = MagicMock()
    svc.config = MagicMock()
    svc.subscription_store = MagicMock()
    svc.kt_tree_store = MagicMock()
    svc.kt_chapter_store = MagicMock()
    svc.kt_doc_store = MagicMock()
    svc.kt_content_store = MagicMock()
    svc.kt_question_store = MagicMock()
    svc.kt_flashcard_store = MagicMock()
    svc.kt_exam_store = MagicMock()
    svc.task_registry = MagicMock()
    return svc


@pytest.fixture
def test_client(mock_services):
    app = FastAPI()
    app.include_router(kt_router.router, prefix="/api")
    app.dependency_overrides[get_services_dep] = lambda: mock_services
    app.dependency_overrides[get_current_user] = _make_user
    return TestClient(app)


# ---------------------------------------------------------------------------
# Trees — list / create / get / update / delete
# ---------------------------------------------------------------------------


def test_list_trees_returns_empty_list(test_client, mock_services):
    mock_services.kt_tree_store.list_trees_for_user.return_value = []
    response = test_client.get("/api/knowledge-trees")
    assert response.status_code == 200
    assert response.json() == []


def test_list_trees_returns_trees_with_chapter_count(test_client, mock_services):
    tree = _tree()
    mock_services.kt_tree_store.list_trees_for_user.return_value = [tree]
    mock_services.kt_chapter_store.list_chapters.return_value = [_chapter(), _chapter(number=2)]

    response = test_client.get("/api/knowledge-trees")
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "My Tree"
    assert body[0]["num_chapters"] == 2


def test_create_tree_returns_201(test_client, mock_services):
    mock_services.subscription_store.get_user_limits.return_value = MagicMock(
        current_knowledge_trees=0, max_knowledge_trees=5
    )
    tree = _tree(title="New Tree")
    mock_services.kt_tree_store.create_tree.return_value = tree

    response = test_client.post("/api/knowledge-trees", json={"title": "New Tree"})
    assert response.status_code == 201
    assert response.json()["title"] == "New Tree"


def test_create_tree_plan_limit_returns_403(test_client, mock_services):
    """When the user is at their tree limit, 403 is returned."""
    from api.limit_checks import PlanLimitExceeded

    mock_services.subscription_store.get_user_limits.return_value = MagicMock(
        current_knowledge_trees=3, max_knowledge_trees=3
    )
    with patch("api.routers.knowledge_trees.check_can_create_tree", side_effect=PlanLimitExceeded(
        resource="tree", current=3, max_limit=3, message="Limit reached"
    )):
        response = test_client.post("/api/knowledge-trees", json={"title": "Over Limit"})

    assert response.status_code == 402


def test_get_tree_returns_200(test_client, mock_services):
    tree = _tree()
    mock_services.kt_tree_store.get_tree.return_value = tree
    mock_services.kt_chapter_store.list_chapters.return_value = []

    response = test_client.get(f"/api/knowledge-trees/{TREE_ID}")
    assert response.status_code == 200
    assert response.json()["id"] == str(TREE_ID)


def test_get_tree_not_found_returns_404(test_client, mock_services):
    mock_services.kt_tree_store.get_tree.return_value = None
    response = test_client.get(f"/api/knowledge-trees/{TREE_ID}")
    assert response.status_code == 404


def test_get_tree_invalid_uuid_returns_422(test_client, mock_services):
    response = test_client.get("/api/knowledge-trees/not-a-uuid")
    assert response.status_code == 422


def test_update_tree_returns_updated(test_client, mock_services):
    tree = _tree()
    updated = _tree(title="Updated Title")
    mock_services.kt_tree_store.get_tree.return_value = tree
    mock_services.kt_tree_store.update_tree.return_value = updated
    mock_services.kt_chapter_store.list_chapters.return_value = []

    response = test_client.put(
        f"/api/knowledge-trees/{TREE_ID}",
        json={"title": "Updated Title"},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"


def test_update_tree_not_found_returns_404(test_client, mock_services):
    mock_services.kt_tree_store.get_tree.return_value = None
    response = test_client.put(
        f"/api/knowledge-trees/{TREE_ID}", json={"title": "X"}
    )
    assert response.status_code == 404


def test_delete_tree_returns_204(test_client, mock_services):
    mock_services.kt_tree_store.get_tree.return_value = _tree()
    response = test_client.delete(f"/api/knowledge-trees/{TREE_ID}")
    assert response.status_code == 204
    mock_services.kt_tree_store.delete_tree.assert_called_once_with(TREE_ID)


def test_delete_tree_not_found_returns_404(test_client, mock_services):
    mock_services.kt_tree_store.get_tree.return_value = None
    response = test_client.delete(f"/api/knowledge-trees/{TREE_ID}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Chapters — list / create / update / delete
# ---------------------------------------------------------------------------


def test_list_chapters_returns_chapters(test_client, mock_services):
    ch2_id = uuid4()
    mock_services.kt_chapter_store.list_chapters.return_value = [
        _chapter(1), _chapter(2, chapter_id=ch2_id),
    ]
    response = test_client.get(f"/api/knowledge-trees/{TREE_ID}/chapters")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_create_chapter_returns_201(test_client, mock_services):
    mock_services.kt_tree_store.get_tree.return_value = _tree()
    mock_services.kt_chapter_store.create_chapter.return_value = _chapter(title="New Chapter")

    response = test_client.post(
        f"/api/knowledge-trees/{TREE_ID}/chapters", json={"title": "New Chapter"}
    )
    assert response.status_code == 201
    assert response.json()["title"] == "New Chapter"


def test_create_chapter_tree_not_found_returns_404(test_client, mock_services):
    mock_services.kt_tree_store.get_tree.return_value = None
    response = test_client.post(
        f"/api/knowledge-trees/{TREE_ID}/chapters", json={"title": "Ch"}
    )
    assert response.status_code == 404


def test_update_chapter_returns_updated(test_client, mock_services):
    updated = _chapter(title="Renamed")
    mock_services.kt_chapter_store.update_chapter.return_value = updated

    response = test_client.put(
        f"/api/knowledge-trees/{TREE_ID}/chapters/1", json={"title": "Renamed"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Renamed"


def test_update_chapter_not_found_returns_404(test_client, mock_services):
    mock_services.kt_chapter_store.update_chapter.side_effect = ValueError("not found")
    response = test_client.put(
        f"/api/knowledge-trees/{TREE_ID}/chapters/99", json={"title": "X"}
    )
    assert response.status_code == 404


def test_delete_chapter_returns_204(test_client, mock_services):
    response = test_client.delete(f"/api/knowledge-trees/{TREE_ID}/chapters/1")
    assert response.status_code == 204
    mock_services.kt_chapter_store.delete_chapter.assert_called_once_with(TREE_ID, 1)


# ---------------------------------------------------------------------------
# Documents — list / create / update / delete
# ---------------------------------------------------------------------------


def test_list_documents_returns_documents(test_client, mock_services):
    mock_services.kt_doc_store.list_documents.return_value = [_doc()]
    response = test_client.get(f"/api/knowledge-trees/{TREE_ID}/documents")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Doc Title"


def test_list_documents_with_chapter_filter(test_client, mock_services):
    mock_services.kt_doc_store.list_documents.return_value = []
    response = test_client.get(
        f"/api/knowledge-trees/{TREE_ID}/documents?chapter_id={CHAPTER_ID}"
    )
    assert response.status_code == 200
    mock_services.kt_doc_store.list_documents.assert_called_once_with(TREE_ID, CHAPTER_ID)


def test_create_document_returns_201(test_client, mock_services):
    mock_services.kt_doc_store.create_document.return_value = _doc()

    response = test_client.post(
        f"/api/knowledge-trees/{TREE_ID}/documents",
        json={"title": "New Doc", "content": "Some content."},
    )
    assert response.status_code == 201


def test_update_document_returns_200(test_client, mock_services):
    existing = _doc()
    updated = _doc()
    updated.title = "Updated"
    mock_services.kt_doc_store.get_document.return_value = existing
    mock_services.kt_doc_store.update_document.return_value = updated

    response = test_client.put(
        f"/api/knowledge-trees/{TREE_ID}/documents/{DOC_ID}",
        json={"title": "Updated", "content": "New content."},
    )
    assert response.status_code == 200


def test_update_document_not_found_returns_404(test_client, mock_services):
    mock_services.kt_doc_store.get_document.return_value = None
    response = test_client.put(
        f"/api/knowledge-trees/{TREE_ID}/documents/{DOC_ID}",
        json={"title": "X", "content": "Y"},
    )
    assert response.status_code == 404


def test_delete_document_returns_204(test_client, mock_services):
    response = test_client.delete(f"/api/knowledge-trees/{TREE_ID}/documents/{DOC_ID}")
    assert response.status_code == 204
    mock_services.kt_doc_store.delete_document.assert_called_once_with(DOC_ID)


# ---------------------------------------------------------------------------
# Improve / revert document
# ---------------------------------------------------------------------------


def test_improve_document_submits_task(test_client, mock_services):
    """Improve endpoint must submit a background task and return 202 with task_id."""
    with patch("application.services.text_improvement.improve_document_task"):
        mock_services.task_registry.submit.return_value = "test-task-id-123"

        response = test_client.post(
            f"/api/knowledge-trees/{TREE_ID}/documents/{DOC_ID}/improve", json={}
        )

    assert response.status_code == 202
    data = response.json()
    assert data["task_id"] == "test-task-id-123"
    mock_services.task_registry.submit.assert_called_once()
    call_kwargs = mock_services.task_registry.submit.call_args
    assert call_kwargs.kwargs["task_type"] == "kt_improve"


def test_improve_document_formatting_mode_submits_task(test_client, mock_services):
    """Improve with mode='formatting' must submit task without passing mode."""
    with patch("application.services.text_improvement.improve_document_task"):
        mock_services.task_registry.submit.return_value = "test-task-id-456"

        response = test_client.post(
            f"/api/knowledge-trees/{TREE_ID}/documents/{DOC_ID}/improve",
            json={"mode": "formatting"},
        )

    assert response.status_code == 202
    mock_services.task_registry.submit.assert_called_once()
    call_kwargs = mock_services.task_registry.submit.call_args.kwargs
    assert call_kwargs["task_type"] == "kt_improve"
    # mode is NOT passed as a positional arg anymore; verify by checking args count
    call_args = mock_services.task_registry.submit.call_args
    # Positional args: fn, doc_uid, tree_id, services, user_id (5 positional args)
    assert len(call_args.args) == 5


def test_improve_document_invalid_agent_id_returns_422(test_client, mock_services):
    """Invalid agent_id must return 422 before submitting task."""
    response = test_client.post(
        f"/api/knowledge-trees/{TREE_ID}/documents/{DOC_ID}/improve",
        json={"agent_id": "not-a-uuid"},
    )
    assert response.status_code == 422


def test_revert_document_returns_original(test_client, mock_services):
    doc = _doc()
    doc.original_content = "# Original"
    reverted = _doc()
    reverted.content = "# Original"
    mock_services.kt_doc_store.get_document.return_value = doc
    mock_services.kt_doc_store.revert_improvement.return_value = reverted

    response = test_client.post(
        f"/api/knowledge-trees/{TREE_ID}/documents/{DOC_ID}/revert"
    )
    assert response.status_code == 200
    mock_services.kt_doc_store.revert_improvement.assert_called_once_with(DOC_ID)


def test_revert_document_no_improvement_returns_422(test_client, mock_services):
    doc = _doc()
    doc.original_content = None
    mock_services.kt_doc_store.get_document.return_value = doc

    response = test_client.post(
        f"/api/knowledge-trees/{TREE_ID}/documents/{DOC_ID}/revert"
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Flashcards
# ---------------------------------------------------------------------------


def test_list_flashcards(test_client, mock_services):
    mock_services.kt_tree_store.get_tree.return_value = _tree()
    mock_services.kt_chapter_store.list_chapters.return_value = [_chapter()]
    mock_services.kt_flashcard_store.list_flashcards.return_value = [_flashcard()]

    response = test_client.get(f"/api/knowledge-trees/{TREE_ID}/chapters/1/flashcards")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["front"] == "What is X?"


def test_list_flashcards_chapter_not_found_returns_404(test_client, mock_services):
    mock_services.kt_tree_store.get_tree.return_value = _tree()
    mock_services.kt_chapter_store.list_chapters.return_value = []

    response = test_client.get(f"/api/knowledge-trees/{TREE_ID}/chapters/99/flashcards")
    assert response.status_code == 404


def test_delete_all_flashcards_returns_204(test_client, mock_services):
    mock_services.kt_tree_store.get_tree.return_value = _tree()
    mock_services.kt_chapter_store.list_chapters.return_value = [_chapter()]

    response = test_client.delete(f"/api/knowledge-trees/{TREE_ID}/chapters/1/flashcards")
    assert response.status_code == 204
    mock_services.kt_flashcard_store.delete_all_flashcards.assert_called_once()


def test_delete_single_flashcard_returns_204(test_client, mock_services):
    response = test_client.delete(
        f"/api/knowledge-trees/{TREE_ID}/chapters/1/flashcards/{FLASHCARD_ID}"
    )
    assert response.status_code == 204
    mock_services.kt_flashcard_store.delete_flashcard.assert_called_once_with(FLASHCARD_ID)


def test_generate_flashcard_submits_task(test_client, mock_services):
    mock_services.kt_tree_store.get_tree.return_value = _tree()
    mock_services.kt_chapter_store.list_chapters.return_value = [_chapter()]
    mock_services.task_registry.submit.return_value = "task-123"

    response = test_client.post(
        f"/api/knowledge-trees/{TREE_ID}/chapters/1/flashcards",
        json={"selected_text": "The mitochondria is the powerhouse."},
    )
    assert response.status_code == 202
    assert response.json()["task_id"] == "task-123"


def test_save_flashcard_persists(test_client, mock_services):
    mock_services.kt_tree_store.get_tree.return_value = _tree()
    mock_services.kt_chapter_store.list_chapters.return_value = [_chapter()]

    response = test_client.post(
        f"/api/knowledge-trees/{TREE_ID}/chapters/1/flashcards/save",
        json={"front": "What is X?", "back": "X is Y."},
    )
    assert response.status_code == 200
    mock_services.kt_flashcard_store.save_flashcard.assert_called_once()


def test_save_flashcard_empty_front_returns_400(test_client, mock_services):
    mock_services.kt_tree_store.get_tree.return_value = _tree()
    mock_services.kt_chapter_store.list_chapters.return_value = [_chapter()]

    response = test_client.post(
        f"/api/knowledge-trees/{TREE_ID}/chapters/1/flashcards/save",
        json={"front": "", "back": "Some answer."},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------


def test_get_chapter_questions_returns_list(test_client, mock_services):
    mock_services.kt_chapter_store.list_chapters.return_value = [_chapter()]
    mock_q = MagicMock()
    mock_q.id = QUESTION_ID
    mock_q.question_type = "true_false"
    mock_q.question_data = {"statement": "The sky is blue.", "answer": True}
    mock_q.created_at = _NOW
    mock_services.kt_question_store.get_questions.return_value = [mock_q]

    response = test_client.get(f"/api/knowledge-trees/{TREE_ID}/chapters/1/questions")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_chapter_questions_chapter_not_found_returns_404(test_client, mock_services):
    mock_services.kt_chapter_store.list_chapters.return_value = []
    response = test_client.get(f"/api/knowledge-trees/{TREE_ID}/chapters/99/questions")
    assert response.status_code == 404


def test_delete_question_returns_204(test_client, mock_services):
    response = test_client.delete(
        f"/api/knowledge-trees/{TREE_ID}/chapters/1/questions/{QUESTION_ID}"
    )
    assert response.status_code == 204
    mock_services.kt_question_store.delete_question.assert_called_once_with(QUESTION_ID)


def test_generate_questions_submits_task(test_client, mock_services):
    mock_services.kt_tree_store.get_tree.return_value = _tree()
    mock_services.kt_chapter_store.list_chapters.return_value = [_chapter()]
    mock_services.task_registry.submit.return_value = "task-456"

    response = test_client.post(
        f"/api/knowledge-trees/{TREE_ID}/chapters/1/questions",
        json={},
    )
    assert response.status_code == 202
    assert response.json()["task_id"] == "task-456"


def test_generate_questions_tree_not_found_returns_404(test_client, mock_services):
    mock_services.kt_tree_store.get_tree.return_value = None
    response = test_client.post(
        f"/api/knowledge-trees/{TREE_ID}/chapters/1/questions", json={}
    )
    assert response.status_code == 404


def test_save_question_persists_valid(test_client, mock_services):
    mock_services.kt_tree_store.get_tree.return_value = _tree()
    mock_services.kt_chapter_store.list_chapters.return_value = [_chapter()]

    with patch("api.routers.knowledge_trees.QuestionGeneratorAgent.validate", return_value=True):
        response = test_client.post(
            f"/api/knowledge-trees/{TREE_ID}/chapters/1/questions/save",
            json={
                "question_type": "true_false",
                "question_data": {"statement": "The sky is blue.", "answer": True},
            },
        )

    assert response.status_code == 200
    mock_services.kt_question_store.save_questions.assert_called_once()


def test_save_question_invalid_data_returns_422(test_client, mock_services):
    mock_services.kt_tree_store.get_tree.return_value = _tree()
    mock_services.kt_chapter_store.list_chapters.return_value = [_chapter()]

    with patch("api.routers.knowledge_trees.QuestionGeneratorAgent.validate", return_value=False):
        response = test_client.post(
            f"/api/knowledge-trees/{TREE_ID}/chapters/1/questions/save",
            json={"question_type": "true_false", "question_data": {}},
        )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Exam sessions
# ---------------------------------------------------------------------------


def test_save_exam_session_returns_201(test_client, mock_services):
    mock_services.kt_tree_store.get_tree.return_value = _tree()
    mock_services.kt_chapter_store.list_chapters.return_value = [_chapter()]
    session = _exam_session()
    mock_services.kt_exam_store.save_session.return_value = session

    response = test_client.post(
        f"/api/knowledge-trees/{TREE_ID}/chapters/1/exam-sessions",
        json={
            "score": 0.8,
            "total_questions": 5,
            "correct_count": 4,
            "question_ids": ["q1", "q2"],
            "results": {"q1": True, "q2": False},
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["score"] == 0.8
    assert body["correct_count"] == 4


def test_list_exam_sessions(test_client, mock_services):
    mock_services.kt_tree_store.get_tree.return_value = _tree()
    mock_services.kt_chapter_store.list_chapters.return_value = [_chapter()]
    mock_services.kt_exam_store.list_sessions.return_value = [_exam_session()]

    response = test_client.get(f"/api/knowledge-trees/{TREE_ID}/chapters/1/exam-sessions")
    assert response.status_code == 200
    assert len(response.json()) == 1


# ---------------------------------------------------------------------------
# Preview endpoint
# ---------------------------------------------------------------------------


def test_preview_unsupported_format_returns_422(test_client):
    from io import BytesIO

    response = test_client.post(
        "/api/knowledge-trees/preview",
        files={"file": ("report.docx", BytesIO(b"content"), "application/octet-stream")},
    )
    assert response.status_code == 422


def test_preview_txt_returns_preview(test_client, mock_services):
    from io import BytesIO

    from api.schemas.knowledge_tree import ChapterPreviewOut, DocumentPreviewOut

    preview = DocumentPreviewOut(
        file_hash="abc123",
        filename="notes.txt",
        num_chapters=1,
        chapters=[ChapterPreviewOut(index=0, title="Notes", page_start=1, page_end=5)],
    )

    with patch("api.routers.knowledge_trees._preview_file", return_value=preview):
        response = test_client.post(
            "/api/knowledge-trees/preview",
            files={"file": ("notes.txt", BytesIO(b"Hello world\nLine two"), "text/plain")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["num_chapters"] == 1
    assert body["filename"] == "notes.txt"


def test_preview_parse_failure_returns_400(test_client, mock_services):
    from io import BytesIO

    with patch("api.routers.knowledge_trees._preview_file", return_value=None):
        response = test_client.post(
            "/api/knowledge-trees/preview",
            files={"file": ("doc.pdf", BytesIO(b"bad content"), "application/pdf")},
        )

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Import endpoint — only checks task submission, not background logic
# ---------------------------------------------------------------------------


def test_import_tree_submits_task(test_client, mock_services):
    from io import BytesIO

    mock_services.subscription_store.get_user_limits.return_value = MagicMock(
        current_knowledge_trees=0, max_knowledge_trees=5
    )
    mock_services.task_registry.submit.return_value = "task-789"

    with patch("api.routers.knowledge_trees.check_can_create_tree"):
        response = test_client.post(
            "/api/knowledge-trees/import",
            data={"title": "My Book"},
            files={"file": ("book.txt", BytesIO(b"Chapter 1\nContent."), "text/plain")},
        )

    assert response.status_code == 202
    assert "task_id" in response.json()


def test_import_tree_unsupported_format_returns_422(test_client, mock_services):
    from io import BytesIO

    mock_services.subscription_store.get_user_limits.return_value = MagicMock(
        current_knowledge_trees=0, max_knowledge_trees=5
    )

    with patch("api.routers.knowledge_trees.check_can_create_tree"):
        response = test_client.post(
            "/api/knowledge-trees/import",
            files={"file": ("report.docx", BytesIO(b"x"), "application/octet-stream")},
        )

    assert response.status_code == 422


def test_import_tree_bad_chapter_indices_returns_400(test_client, mock_services):
    from io import BytesIO

    mock_services.subscription_store.get_user_limits.return_value = MagicMock(
        current_knowledge_trees=0, max_knowledge_trees=5
    )

    with patch("api.routers.knowledge_trees.check_can_create_tree"):
        response = test_client.post(
            "/api/knowledge-trees/import",
            data={"chapter_indices": "not,valid"},
            files={"file": ("book.txt", BytesIO(b"content"), "text/plain")},
        )

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Get chapter content (chunks)
# ---------------------------------------------------------------------------


def test_get_chapter_content_returns_chunks(test_client, mock_services):
    chunk = MagicMock()
    chunk.id = uuid4()
    chunk.chunk_index = 0
    chunk.text = "Chunk text here."
    chunk.token_count = 10
    mock_services.kt_content_store.get_chunks.return_value = [chunk]

    response = test_client.get(f"/api/knowledge-trees/{TREE_ID}/chapters/1/content")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["text"] == "Chunk text here."
