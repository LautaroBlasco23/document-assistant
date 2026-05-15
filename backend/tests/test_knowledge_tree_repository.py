"""Unit tests for PostgreSQL knowledge tree repositories.

Scope: PostgresKnowledgeTreeStore, PostgresKnowledgeChapterStore,
       PostgresKnowledgeDocumentStore, PostgresKnowledgeContentStore,
       PostgresKnowledgeQuestionStore, PostgresFlashcardStore,
       PostgresExamSessionStore.
Out-of-scope: integration with real PostgreSQL.
Setup: Mock psycopg.Connection and PostgresConnection via unittest.mock.
"""
from datetime import datetime
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from core.model.knowledge_tree import (
    ExamSession,
    Flashcard,
    KnowledgeChapter,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeTree,
)
from core.model.question import Question
from infrastructure.db.knowledge_tree_repository import (
    PostgresExamSessionStore,
    PostgresFlashcardStore,
    PostgresKnowledgeChapterStore,
    PostgresKnowledgeContentStore,
    PostgresKnowledgeDocumentStore,
    PostgresKnowledgeQuestionStore,
    PostgresKnowledgeTreeStore,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXED_UUID = UUID("12345678-1234-5678-1234-567812345678")
FIXED_UUID_2 = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
FIXED_USER_ID = UUID("bbbbbbbb-cccc-dddd-eeee-ffffffffffff")


def _make_pool_and_cursor():
    pool = MagicMock()
    cur = MagicMock()
    conn = MagicMock()

    cur.fetchone.return_value = None
    cur.fetchall.return_value = []

    cm_cur = MagicMock()
    cm_cur.__enter__ = MagicMock(return_value=cur)
    cm_cur.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cm_cur

    cm_tx = MagicMock()
    cm_tx.__enter__ = MagicMock(return_value=None)
    cm_tx.__exit__ = MagicMock(return_value=False)
    conn.transaction.return_value = cm_tx

    conn.info.transaction_status = 0

    pool.connection.return_value = conn

    return pool, cur, conn


def _tree_row(
    tree_id=FIXED_UUID,
    user_id=FIXED_USER_ID,
    title="My Tree",
    description="A tree",
    created_at=None,
):
    return {
        "id": tree_id,
        "user_id": user_id,
        "title": title,
        "description": description,
        "created_at": created_at or datetime(2024, 1, 1),
    }


def _chapter_row(
    chapter_id=FIXED_UUID,
    tree_id=FIXED_UUID,
    number=1,
    title="Chapter 1",
    created_at=None,
):
    return {
        "id": chapter_id,
        "tree_id": tree_id,
        "number": number,
        "title": title,
        "created_at": created_at or datetime(2024, 1, 1),
    }


def _doc_row(
    doc_id=FIXED_UUID,
    tree_id=FIXED_UUID,
    chapter_id=FIXED_UUID_2,
    title="Doc",
    content="content",
    is_main=False,
    created_at=None,
    updated_at=None,
    source_file_path=None,
    source_file_name=None,
    chapter_number=1,
    page_start=None,
    page_end=None,
    original_content=None,
    source_type="file",
    source_url=None,
    file_type=None,
):
    return {
        "id": doc_id,
        "tree_id": tree_id,
        "chapter_id": chapter_id,
        "title": title,
        "content": content,
        "is_main": is_main,
        "created_at": created_at or datetime(2024, 1, 1),
        "updated_at": updated_at or datetime(2024, 1, 1),
        "source_file_path": source_file_path,
        "source_file_name": source_file_name,
        "chapter_number": chapter_number,
        "page_start": page_start,
        "page_end": page_end,
        "original_content": original_content,
        "source_type": source_type,
        "source_url": source_url,
        "file_type": file_type,
    }


def _chunk_row(
    chunk_id=FIXED_UUID,
    tree_id=FIXED_UUID,
    chapter_id=FIXED_UUID_2,
    doc_id=FIXED_UUID,
    chunk_index=0,
    text="chunk text",
    token_count=50,
):
    return {
        "id": chunk_id,
        "tree_id": tree_id,
        "chapter_id": chapter_id,
        "doc_id": doc_id,
        "chunk_index": chunk_index,
        "text": text,
        "token_count": token_count,
    }


def _question_row(
    question_id=FIXED_UUID,
    tree_id=FIXED_UUID,
    chapter_id=FIXED_UUID_2,
    question_type="multiple_choice",
    question_data=None,
    created_at=None,
):
    return {
        "id": question_id,
        "tree_id": tree_id,
        "chapter_id": chapter_id,
        "question_type": question_type,
        "question_data": question_data or {"question": "Q?", "options": ["A", "B"], "answer": "A"},
        "created_at": created_at or datetime(2024, 1, 1),
    }


def _flashcard_row(
    flashcard_id=FIXED_UUID,
    tree_id=FIXED_UUID,
    chapter_id=FIXED_UUID_2,
    doc_id=FIXED_UUID,
    front="Front",
    back="Back",
    source_text=None,
    created_at=None,
):
    return {
        "id": flashcard_id,
        "tree_id": tree_id,
        "chapter_id": chapter_id,
        "doc_id": doc_id,
        "front": front,
        "back": back,
        "source_text": source_text,
        "created_at": created_at or datetime(2024, 1, 1),
    }


def _exam_session_row(
    session_id=FIXED_UUID,
    tree_id=FIXED_UUID,
    chapter_id=FIXED_UUID_2,
    score=0.8,
    total_questions=10,
    correct_count=8,
    question_ids=None,
    results=None,
    created_at=None,
):
    return {
        "id": session_id,
        "tree_id": tree_id,
        "chapter_id": chapter_id,
        "score": score,
        "total_questions": total_questions,
        "correct_count": correct_count,
        "question_ids": question_ids or ["q1", "q2"],
        "results": results or {"q1": True, "q2": False},
        "created_at": created_at or datetime(2024, 1, 1),
    }


# ---------------------------------------------------------------------------
# PostgresKnowledgeTreeStore
# ---------------------------------------------------------------------------

def test_tree_store_list_trees_for_user():
    """list_trees_for_user must return trees ordered by created_at DESC."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchall.return_value = [
        _tree_row(title="Newer", created_at=datetime(2024, 2, 1)),
        _tree_row(title="Older", created_at=datetime(2024, 1, 1)),
    ]

    store = PostgresKnowledgeTreeStore(pool)
    trees = store.list_trees_for_user(FIXED_USER_ID)

    assert len(trees) == 2
    assert trees[0].title == "Newer"
    assert trees[1].title == "Older"


def test_tree_store_list_trees_empty():
    """list_trees_for_user must return an empty list when no trees exist."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchall.return_value = []

    store = PostgresKnowledgeTreeStore(pool)
    trees = store.list_trees_for_user(FIXED_USER_ID)

    assert trees == []


def test_tree_store_create_tree():
    """create_tree must insert a row and return a KnowledgeTree."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _tree_row(title="New Tree", description="desc")

    store = PostgresKnowledgeTreeStore(pool)
    tree = store.create_tree("New Tree", "desc", FIXED_USER_ID)

    assert isinstance(tree, KnowledgeTree)
    assert tree.title == "New Tree"
    assert tree.description == "desc"


def test_tree_store_get_tree_found():
    """get_tree must return the KnowledgeTree when it exists."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _tree_row(tree_id=FIXED_UUID, title="Found")

    store = PostgresKnowledgeTreeStore(pool)
    tree = store.get_tree(FIXED_UUID)

    assert tree is not None
    assert tree.id == FIXED_UUID
    assert tree.title == "Found"


def test_tree_store_get_tree_not_found():
    """get_tree must return None when the tree does not exist."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = None

    store = PostgresKnowledgeTreeStore(pool)
    tree = store.get_tree(FIXED_UUID)

    assert tree is None


def test_tree_store_update_tree():
    """update_tree must modify and return the updated tree."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _tree_row(title="Updated Title", description="new desc")

    store = PostgresKnowledgeTreeStore(pool)
    tree = store.update_tree(FIXED_UUID, "Updated Title", "new desc")

    assert tree.title == "Updated Title"
    assert tree.description == "new desc"


def test_tree_store_update_tree_not_found():
    """update_tree must raise ValueError when the tree does not exist."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = None

    store = PostgresKnowledgeTreeStore(pool)
    with pytest.raises(ValueError, match="Knowledge tree not found"):
        store.update_tree(FIXED_UUID, "Title", "desc")


def test_tree_store_delete_tree():
    """delete_tree must execute a DELETE statement."""
    pool, cur, _ = _make_pool_and_cursor()

    store = PostgresKnowledgeTreeStore(pool)
    store.delete_tree(FIXED_UUID)

    assert cur.execute.call_count == 1


# ---------------------------------------------------------------------------
# PostgresKnowledgeChapterStore
# ---------------------------------------------------------------------------

def test_chapter_store_list_chapters():
    """list_chapters must return chapters ordered by number."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchall.return_value = [
        _chapter_row(number=1, title="Ch 1"),
        _chapter_row(number=2, title="Ch 2"),
    ]

    store = PostgresKnowledgeChapterStore(pool)
    chapters = store.list_chapters(FIXED_UUID)

    assert len(chapters) == 2
    assert chapters[0].number == 1
    assert chapters[1].number == 2


def test_chapter_store_create_chapter_auto_number():
    """create_chapter must auto-assign the next number."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.side_effect = [
        {"next_number": 3},
        _chapter_row(number=3, title="Ch 3"),
    ]

    store = PostgresKnowledgeChapterStore(pool)
    chapter = store.create_chapter(FIXED_UUID, "Ch 3")

    assert chapter.number == 3
    assert chapter.title == "Ch 3"


def test_chapter_store_create_chapter_first():
    """create_chapter must assign number 1 when no chapters exist."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.side_effect = [
        {"next_number": 1},
        _chapter_row(number=1, title="First"),
    ]

    store = PostgresKnowledgeChapterStore(pool)
    chapter = store.create_chapter(FIXED_UUID, "First")

    assert chapter.number == 1


def test_chapter_store_update_chapter():
    """update_chapter must modify the title and return the updated chapter."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _chapter_row(title="Renamed")

    store = PostgresKnowledgeChapterStore(pool)
    chapter = store.update_chapter(FIXED_UUID, 1, "Renamed")

    assert chapter.title == "Renamed"


def test_chapter_store_update_chapter_not_found():
    """update_chapter must raise ValueError when the chapter does not exist."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = None

    store = PostgresKnowledgeChapterStore(pool)
    with pytest.raises(ValueError, match="Knowledge chapter not found"):
        store.update_chapter(FIXED_UUID, 99, "Nope")


def test_chapter_store_delete_chapter():
    """delete_chapter must execute a DELETE statement."""
    pool, cur, _ = _make_pool_and_cursor()

    store = PostgresKnowledgeChapterStore(pool)
    store.delete_chapter(FIXED_UUID, 1)

    assert cur.execute.call_count == 1


# ---------------------------------------------------------------------------
# PostgresKnowledgeDocumentStore
# ---------------------------------------------------------------------------

def test_doc_store_list_documents_without_chapter_filter():
    """list_documents must return all documents for a tree when chapter_id is None."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchall.return_value = [
        _doc_row(title="Doc 1"),
        _doc_row(title="Doc 2"),
    ]

    store = PostgresKnowledgeDocumentStore(pool)
    docs = store.list_documents(FIXED_UUID, None)

    assert len(docs) == 2
    assert docs[0].title == "Doc 1"


def test_doc_store_list_documents_with_chapter_filter():
    """list_documents must filter by chapter_id when provided."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchall.return_value = [_doc_row(title="Ch Doc")]

    store = PostgresKnowledgeDocumentStore(pool)
    docs = store.list_documents(FIXED_UUID, FIXED_UUID_2)

    assert len(docs) == 1
    assert docs[0].title == "Ch Doc"


def test_doc_store_create_document():
    """create_document must insert and return a KnowledgeDocument."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _doc_row(title="New Doc", file_type="pdf")

    store = PostgresKnowledgeDocumentStore(pool)
    doc = store.create_document(
        tree_id=FIXED_UUID,
        chapter_id=FIXED_UUID_2,
        title="New Doc",
        content="content",
        is_main=True,
        file_type="pdf",
    )

    assert isinstance(doc, KnowledgeDocument)
    assert doc.title == "New Doc"
    assert doc.file_type == "pdf"


def test_doc_store_create_document_auto_file_type():
    """create_document must auto-detect file_type from source_file_name."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _doc_row(file_type="pdf")

    store = PostgresKnowledgeDocumentStore(pool)
    doc = store.create_document(
        tree_id=FIXED_UUID,
        chapter_id=None,
        title="PDF Doc",
        content="content",
        is_main=False,
        source_file_name="report.pdf",
    )

    assert doc.file_type == "pdf"


def test_doc_store_create_youtube_document():
    """create_youtube_document must set source_type='youtube'."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _doc_row(source_type="youtube", source_url="https://youtube.com/watch")

    store = PostgresKnowledgeDocumentStore(pool)
    doc = store.create_youtube_document(
        tree_id=FIXED_UUID,
        chapter_id=None,
        title="Video",
        content="transcript",
        source_url="https://youtube.com/watch",
    )

    assert doc.source_type == "youtube"


def test_doc_store_get_document_found():
    """get_document must return the KnowledgeDocument when it exists."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _doc_row(doc_id=FIXED_UUID, title="Found Doc")

    store = PostgresKnowledgeDocumentStore(pool)
    doc = store.get_document(FIXED_UUID)

    assert doc is not None
    assert doc.id == FIXED_UUID
    assert doc.title == "Found Doc"


def test_doc_store_get_document_not_found():
    """get_document must return None when the document does not exist."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = None

    store = PostgresKnowledgeDocumentStore(pool)
    doc = store.get_document(FIXED_UUID)

    assert doc is None


def test_doc_store_update_document():
    """update_document must modify and return the updated document."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _doc_row(title="Updated", content="new content")

    store = PostgresKnowledgeDocumentStore(pool)
    doc = store.update_document(FIXED_UUID, "Updated", "new content")

    assert doc.title == "Updated"


def test_doc_store_update_document_not_found():
    """update_document must raise ValueError when the document does not exist."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = None

    store = PostgresKnowledgeDocumentStore(pool)
    with pytest.raises(ValueError, match="Knowledge document not found"):
        store.update_document(FIXED_UUID, "Title", "content")


def test_doc_store_save_improvement_preserves_original():
    """save_improvement must preserve original_content when it is null."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _doc_row(
        content="improved", original_content="original"
    )

    store = PostgresKnowledgeDocumentStore(pool)
    doc = store.save_improvement(FIXED_UUID, "improved")

    assert doc.content == "improved"
    assert doc.original_content == "original"


def test_doc_store_save_improvement_not_found():
    """save_improvement must raise ValueError when the document does not exist."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = None

    store = PostgresKnowledgeDocumentStore(pool)
    with pytest.raises(ValueError, match="Knowledge document not found"):
        store.save_improvement(FIXED_UUID, "improved")


def test_doc_store_revert_improvement():
    """revert_improvement must swap content and original_content."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _doc_row(content="original", original_content=None)

    store = PostgresKnowledgeDocumentStore(pool)
    doc = store.revert_improvement(FIXED_UUID)

    assert doc.content == "original"


def test_doc_store_revert_improvement_not_found():
    """revert_improvement must raise ValueError when no improvement exists."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = None

    store = PostgresKnowledgeDocumentStore(pool)
    with pytest.raises(ValueError, match="Document not found or has no improvement"):
        store.revert_improvement(FIXED_UUID)


def test_doc_store_delete_document():
    """delete_document must execute a DELETE statement."""
    pool, cur, _ = _make_pool_and_cursor()

    store = PostgresKnowledgeDocumentStore(pool)
    store.delete_document(FIXED_UUID)

    assert cur.execute.call_count == 1


# ---------------------------------------------------------------------------
# PostgresKnowledgeContentStore
# ---------------------------------------------------------------------------

def test_content_store_save_chunks_empty():
    """save_chunks must be a no-op when given an empty list."""
    pool, cur, _ = _make_pool_and_cursor()

    store = PostgresKnowledgeContentStore(pool)
    store.save_chunks([])

    cur.execute.assert_not_called()


def test_content_store_save_chunks():
    """save_chunks must insert all chunks."""
    pool, cur, _ = _make_pool_and_cursor()
    chunks = [
        KnowledgeChunk(
            id=FIXED_UUID, tree_id=FIXED_UUID, chapter_id=FIXED_UUID_2,
            doc_id=FIXED_UUID, chunk_index=0, text="chunk 1", token_count=50,
        ),
        KnowledgeChunk(
            id=FIXED_UUID_2, tree_id=FIXED_UUID, chapter_id=FIXED_UUID_2,
            doc_id=FIXED_UUID, chunk_index=1, text="chunk 2", token_count=60,
        ),
    ]

    store = PostgresKnowledgeContentStore(pool)
    store.save_chunks(chunks)

    cur.executemany.assert_called_once()


def test_content_store_get_chunks():
    """get_chunks must return chunks for a tree chapter."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchall.return_value = [
        _chunk_row(chunk_index=0, text="first"),
        _chunk_row(chunk_index=1, text="second"),
    ]

    store = PostgresKnowledgeContentStore(pool)
    chunks = store.get_chunks(FIXED_UUID, chapter_number=1)

    assert len(chunks) == 2
    assert chunks[0].text == "first"
    assert chunks[1].text == "second"


# ---------------------------------------------------------------------------
# PostgresKnowledgeQuestionStore
# ---------------------------------------------------------------------------

def test_question_store_save_questions_empty():
    """save_questions must be a no-op when given an empty list."""
    pool, cur, _ = _make_pool_and_cursor()

    store = PostgresKnowledgeQuestionStore(pool)
    store.save_questions([])

    cur.execute.assert_not_called()


def test_question_store_save_questions():
    """save_questions must insert each question."""
    pool, cur, _ = _make_pool_and_cursor()
    questions = [
        Question(
            tree_id=FIXED_UUID, chapter_id=FIXED_UUID_2,
            question_type="multiple_choice",
            question_data={"question": "Q?", "options": ["A", "B"], "answer": "A"},
        ),
    ]

    store = PostgresKnowledgeQuestionStore(pool)
    store.save_questions(questions)

    assert cur.execute.call_count == 1


def test_question_store_get_questions_all_types():
    """get_questions must return all questions when question_type is None."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchall.return_value = [
        _question_row(question_type="multiple_choice"),
        _question_row(question_type="true_false"),
    ]

    store = PostgresKnowledgeQuestionStore(pool)
    questions = store.get_questions(FIXED_UUID, FIXED_UUID_2)

    assert len(questions) == 2


def test_question_store_get_questions_filtered():
    """get_questions must filter by question_type when provided."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchall.return_value = [
        _question_row(question_type="true_false"),
    ]

    store = PostgresKnowledgeQuestionStore(pool)
    questions = store.get_questions(FIXED_UUID, FIXED_UUID_2, question_type="true_false")

    assert len(questions) == 1
    assert questions[0].question_type == "true_false"


def test_question_store_delete_question():
    """delete_question must execute a DELETE statement."""
    pool, cur, _ = _make_pool_and_cursor()

    store = PostgresKnowledgeQuestionStore(pool)
    store.delete_question(FIXED_UUID)

    assert cur.execute.call_count == 1


def test_question_store_delete_all_questions():
    """delete_all_questions must delete all questions for a tree/chapter."""
    pool, cur, _ = _make_pool_and_cursor()

    store = PostgresKnowledgeQuestionStore(pool)
    store.delete_all_questions(FIXED_UUID, FIXED_UUID_2)

    assert cur.execute.call_count == 1


def test_question_store_delete_all_questions_by_type():
    """delete_all_questions must filter by question_type when provided."""
    pool, cur, _ = _make_pool_and_cursor()

    store = PostgresKnowledgeQuestionStore(pool)
    store.delete_all_questions(FIXED_UUID, FIXED_UUID_2, question_type="true_false")

    assert cur.execute.call_count == 1


# ---------------------------------------------------------------------------
# PostgresFlashcardStore
# ---------------------------------------------------------------------------

def test_flashcard_store_save_flashcard():
    """save_flashcard must insert a flashcard."""
    pool, cur, _ = _make_pool_and_cursor()
    flashcard = Flashcard(
        id=FIXED_UUID, tree_id=FIXED_UUID, chapter_id=FIXED_UUID_2,
        doc_id=FIXED_UUID, front="Q?", back="A!", source_text="src",
        created_at=datetime(2024, 1, 1),
    )

    store = PostgresFlashcardStore(pool)
    store.save_flashcard(flashcard)

    assert cur.execute.call_count == 1


def test_flashcard_store_list_flashcards():
    """list_flashcards must return flashcards for a tree/chapter."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchall.return_value = [
        _flashcard_row(front="Q1", back="A1"),
        _flashcard_row(front="Q2", back="A2"),
    ]

    store = PostgresFlashcardStore(pool)
    cards = store.list_flashcards(FIXED_UUID, FIXED_UUID_2)

    assert len(cards) == 2
    assert cards[0].front == "Q1"


def test_flashcard_store_delete_flashcard():
    """delete_flashcard must execute a DELETE statement."""
    pool, cur, _ = _make_pool_and_cursor()

    store = PostgresFlashcardStore(pool)
    store.delete_flashcard(FIXED_UUID)

    assert cur.execute.call_count == 1


def test_flashcard_store_delete_all_flashcards():
    """delete_all_flashcards must delete all flashcards for a tree/chapter."""
    pool, cur, _ = _make_pool_and_cursor()

    store = PostgresFlashcardStore(pool)
    store.delete_all_flashcards(FIXED_UUID, FIXED_UUID_2)

    assert cur.execute.call_count == 1


# ---------------------------------------------------------------------------
# PostgresExamSessionStore
# ---------------------------------------------------------------------------

def test_exam_store_save_session():
    """save_session must insert and return an ExamSession."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _exam_session_row(score=0.9, total_questions=10, correct_count=9)

    session = ExamSession(
        id=FIXED_UUID, tree_id=FIXED_UUID, chapter_id=FIXED_UUID_2,
        score=0.9, total_questions=10, correct_count=9,
        question_ids=["q1"], results={"q1": True},
        created_at=datetime(2024, 1, 1),
    )

    store = PostgresExamSessionStore(pool)
    result = store.save_session(session)

    assert isinstance(result, ExamSession)
    assert result.score == 0.9
    assert result.correct_count == 9


def test_exam_store_list_sessions():
    """list_sessions must return sessions for a tree/chapter."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchall.return_value = [
        _exam_session_row(score=0.8),
        _exam_session_row(score=0.9),
    ]

    store = PostgresExamSessionStore(pool)
    sessions = store.list_sessions(FIXED_UUID, FIXED_UUID_2)

    assert len(sessions) == 2


def test_exam_store_get_session_found():
    """get_session must return the ExamSession when it exists."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _exam_session_row(session_id=FIXED_UUID, score=0.75)

    store = PostgresExamSessionStore(pool)
    session = store.get_session(FIXED_UUID)

    assert session is not None
    assert session.id == FIXED_UUID
    assert session.score == 0.75


def test_exam_store_get_session_not_found():
    """get_session must return None when the session does not exist."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = None

    store = PostgresExamSessionStore(pool)
    session = store.get_session(FIXED_UUID)

    assert session is None
