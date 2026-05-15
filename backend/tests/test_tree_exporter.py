"""Unit tests for application/export/tree_exporter.py."""


from datetime import datetime
from uuid import uuid4

from application.export.tree_exporter import (
    _dedup,
    format_document,
    format_flashcards,
    format_questions,
    slugify,
)
from core.model.knowledge_tree import Flashcard, KnowledgeDocument
from core.model.question import Question

# ── slugify ────────────────────────────────────────────────────────────────────

def test_slugify_basic():
    assert slugify("Hello World") == "hello_world"


def test_slugify_unsafe_chars():
    assert slugify('foo/bar:baz*"qux') == "foo_bar_baz_qux"


def test_slugify_collapses_repeated_underscores():
    assert slugify("a  b   c") == "a_b_c"


def test_slugify_empty_string():
    assert slugify("") == "untitled"


def test_slugify_only_unsafe():
    assert slugify("///") == "untitled"


def test_slugify_truncates():
    assert len(slugify("x" * 200)) == 80


# ── _dedup ─────────────────────────────────────────────────────────────────────

def test_dedup_no_collision():
    seen: set[str] = set()
    assert _dedup("foo.txt", seen) == "foo.txt"
    assert "foo.txt" in seen


def test_dedup_collision():
    seen = {"foo.txt"}
    assert _dedup("foo.txt", seen) == "foo_2.txt"


def test_dedup_multiple_collisions():
    seen = {"foo.txt", "foo_2.txt"}
    assert _dedup("foo.txt", seen) == "foo_3.txt"


def test_dedup_no_extension():
    seen = {"foo"}
    assert _dedup("foo", seen) == "foo_2"


# ── format_document ────────────────────────────────────────────────────────────

def _make_doc(**kwargs):
    defaults = dict(
        id=uuid4(), tree_id=uuid4(), chapter_id=uuid4(),
        title="Test Doc", content="body text", is_main=False,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        original_content=None,
    )
    defaults.update(kwargs)
    return KnowledgeDocument(**defaults)


def test_format_document_no_original():
    doc = _make_doc(content="hello")
    result = format_document(doc)
    assert "# Test Doc" in result
    assert "hello" in result
    assert "Original Version" not in result


def test_format_document_with_original():
    doc = _make_doc(content="improved", original_content="raw")
    result = format_document(doc)
    assert "AI-improved" in result
    assert "improved" in result
    assert "Original Version" in result
    assert "raw" in result


# ── format_flashcards ──────────────────────────────────────────────────────────

def _make_card(front, back):
    return Flashcard(
        id=uuid4(), tree_id=uuid4(), chapter_id=uuid4(), doc_id=None,
        front=front, back=back, source_text=None, created_at=datetime.utcnow(),
    )


def test_format_flashcards_empty():
    assert format_flashcards([]) == "(no flashcards)"


def test_format_flashcards_single():
    result = format_flashcards([_make_card("Q", "A")])
    assert "Q: Q" in result
    assert "A: A" in result


def test_format_flashcards_multiple_separator():
    result = format_flashcards([_make_card("Q1", "A1"), _make_card("Q2", "A2")])
    assert "---" in result


# ── format_questions ───────────────────────────────────────────────────────────

def _make_q(qtype, data):
    return Question(tree_id=uuid4(), chapter_id=uuid4(), question_type=qtype, question_data=data)


def test_format_questions_empty():
    result = format_questions([], "true_false")
    assert "no true false questions" in result


def test_format_questions_true_false():
    q = _make_q("true_false", {"statement": "Sky is blue", "answer": True, "explanation": "It is."})
    result = format_questions([q], "true_false")
    assert "Sky is blue" in result
    assert "True" in result
    assert "It is." in result


def test_format_questions_true_false_false_answer():
    q = _make_q("true_false", {"statement": "Sky is green", "answer": False})
    result = format_questions([q], "true_false")
    assert "False" in result


def test_format_questions_multiple_choice():
    q = _make_q("multiple_choice", {
        "question": "What is 2+2?",
        "options": [
            {"label": "A", "text": "3", "is_correct": False},
            {"label": "B", "text": "4", "is_correct": True},
        ],
    })
    result = format_questions([q], "multiple_choice")
    assert "2+2" in result
    assert "> B: 4" in result
    assert "  A: 3" in result


def test_format_questions_matching():
    q = _make_q("matching", {
        "question": "Match capitals",
        "pairs": [{"left": "France", "right": "Paris"}],
    })
    result = format_questions([q], "matching")
    assert "France → Paris" in result


def test_format_questions_checkbox():
    q = _make_q("checkbox", {
        "question": "Select primes",
        "options": [
            {"text": "2", "is_correct": True},
            {"text": "4", "is_correct": False},
        ],
    })
    result = format_questions([q], "checkbox")
    assert "[x] 2" in result
    assert "[ ] 4" in result


def test_format_questions_filters_by_type():
    q1 = _make_q("true_false", {"statement": "A", "answer": True})
    q2 = _make_q("multiple_choice", {"question": "B", "options": []})
    result = format_questions([q1, q2], "true_false")
    assert "A" in result
    assert "B" not in result
