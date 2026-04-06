"""
Integration tests for the Knowledge Tree repository layer.

Requires a running PostgreSQL instance (docker compose up -d).
Run with:  uv run pytest -m integration
"""

import pytest

from infrastructure.config import PostgresConfig
from infrastructure.db.postgres import PostgresPool
from infrastructure.db.knowledge_tree_repository import (
    PostgresKnowledgeTreeStore,
    PostgresKnowledgeChapterStore,
    PostgresKnowledgeDocumentStore,
    PostgresKnowledgeContentStore,
)
from core.model.knowledge_tree import KnowledgeChunk
from uuid import uuid4


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pool():
    """Connect to the local PostgreSQL instance and apply schema/migrations."""
    cfg = PostgresConfig()
    p = PostgresPool(cfg)
    try:
        p.connect()
    except Exception:
        pytest.skip("PostgreSQL not reachable — skipping integration tests")
    yield p
    p.close()


@pytest.fixture(scope="module")
def tree_store(pool):
    return PostgresKnowledgeTreeStore(pool)


@pytest.fixture(scope="module")
def chapter_store(pool):
    return PostgresKnowledgeChapterStore(pool)


@pytest.fixture(scope="module")
def doc_store(pool):
    return PostgresKnowledgeDocumentStore(pool)


@pytest.fixture(scope="module")
def content_store(pool):
    return PostgresKnowledgeContentStore(pool)


# ---------------------------------------------------------------------------
# Tree CRUD
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_create_and_list_tree(tree_store):
    tree = tree_store.create_tree("Integration Test Tree", "A test tree")
    try:
        assert tree.title == "Integration Test Tree"
        assert tree.description == "A test tree"
        assert tree.id is not None

        trees = tree_store.list_trees()
        ids = [t.id for t in trees]
        assert tree.id in ids
    finally:
        tree_store.delete_tree(tree.id)


@pytest.mark.integration
def test_get_tree(tree_store):
    tree = tree_store.create_tree("Get Test", None)
    try:
        fetched = tree_store.get_tree(tree.id)
        assert fetched is not None
        assert fetched.id == tree.id
        assert fetched.title == "Get Test"
        assert fetched.description is None
    finally:
        tree_store.delete_tree(tree.id)


@pytest.mark.integration
def test_get_tree_not_found(tree_store):
    result = tree_store.get_tree(uuid4())
    assert result is None


@pytest.mark.integration
def test_update_tree(tree_store):
    tree = tree_store.create_tree("Old Title", "Old desc")
    try:
        updated = tree_store.update_tree(tree.id, "New Title", "New desc")
        assert updated.title == "New Title"
        assert updated.description == "New desc"
        assert updated.id == tree.id

        fetched = tree_store.get_tree(tree.id)
        assert fetched.title == "New Title"
    finally:
        tree_store.delete_tree(tree.id)


@pytest.mark.integration
def test_delete_tree(tree_store):
    tree = tree_store.create_tree("Delete Me", None)
    tree_store.delete_tree(tree.id)
    assert tree_store.get_tree(tree.id) is None


# ---------------------------------------------------------------------------
# Chapter CRUD
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_create_and_list_chapters(tree_store, chapter_store):
    tree = tree_store.create_tree("Chapter Test Tree", None)
    try:
        ch1 = chapter_store.create_chapter(tree.id, "Intro")
        ch2 = chapter_store.create_chapter(tree.id, "Advanced")

        chapters = chapter_store.list_chapters(tree.id)
        numbers = [c.number for c in chapters]
        assert ch1.number in numbers
        assert ch2.number in numbers
        assert ch1.number < ch2.number  # sequential
    finally:
        tree_store.delete_tree(tree.id)


@pytest.mark.integration
def test_update_chapter(tree_store, chapter_store):
    tree = tree_store.create_tree("Chapter Update Tree", None)
    try:
        ch = chapter_store.create_chapter(tree.id, "Original")
        updated = chapter_store.update_chapter(tree.id, ch.number, "Renamed")
        assert updated.title == "Renamed"
        assert updated.number == ch.number

        chapters = chapter_store.list_chapters(tree.id)
        match = next((c for c in chapters if c.number == ch.number), None)
        assert match is not None
        assert match.title == "Renamed"
    finally:
        tree_store.delete_tree(tree.id)


@pytest.mark.integration
def test_delete_chapter(tree_store, chapter_store):
    tree = tree_store.create_tree("Delete Chapter Tree", None)
    try:
        ch = chapter_store.create_chapter(tree.id, "To Delete")
        chapter_store.delete_chapter(tree.id, ch.number)
        chapters = chapter_store.list_chapters(tree.id)
        assert all(c.number != ch.number for c in chapters)
    finally:
        tree_store.delete_tree(tree.id)


# ---------------------------------------------------------------------------
# Document CRUD
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_create_and_list_documents(tree_store, chapter_store, doc_store):
    tree = tree_store.create_tree("Doc Test Tree", None)
    try:
        ch = chapter_store.create_chapter(tree.id, "Ch1")
        doc = doc_store.create_document(tree.id, ch.id, "My Doc", "Some content", False)

        assert doc.title == "My Doc"
        assert doc.content == "Some content"
        assert doc.chapter_id == ch.id
        assert not doc.is_main

        docs = doc_store.list_documents(tree.id, ch.id)
        ids = [d.id for d in docs]
        assert doc.id in ids
    finally:
        tree_store.delete_tree(tree.id)


@pytest.mark.integration
def test_update_document(tree_store, chapter_store, doc_store):
    tree = tree_store.create_tree("Doc Update Tree", None)
    try:
        ch = chapter_store.create_chapter(tree.id, "Ch")
        doc = doc_store.create_document(tree.id, ch.id, "Old", "Old content", False)
        updated = doc_store.update_document(doc.id, "New", "New content")
        assert updated.title == "New"
        assert updated.content == "New content"
    finally:
        tree_store.delete_tree(tree.id)


@pytest.mark.integration
def test_delete_document(tree_store, chapter_store, doc_store):
    tree = tree_store.create_tree("Doc Delete Tree", None)
    try:
        ch = chapter_store.create_chapter(tree.id, "Ch")
        doc = doc_store.create_document(tree.id, ch.id, "Del", "x", False)
        doc_store.delete_document(doc.id)
        assert doc_store.get_document(doc.id) is None
    finally:
        tree_store.delete_tree(tree.id)


# ---------------------------------------------------------------------------
# Content (chunks)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_save_and_get_chunks(tree_store, chapter_store, doc_store, content_store):
    tree = tree_store.create_tree("Chunk Test Tree", None)
    try:
        ch = chapter_store.create_chapter(tree.id, "Chunk Chapter")
        doc = doc_store.create_document(tree.id, ch.id, "Chunk Doc", "text", False)

        chunks = [
            KnowledgeChunk(
                id=uuid4(),
                tree_id=tree.id,
                chapter_id=ch.id,
                doc_id=doc.id,
                chunk_index=i,
                text=f"chunk {i}",
                token_count=10,
            )
            for i in range(3)
        ]
        content_store.save_chunks(chunks)

        retrieved = content_store.get_chunks(tree.id, ch.number)
        assert len(retrieved) == 3
        texts = {c.text for c in retrieved}
        assert "chunk 0" in texts
        assert "chunk 2" in texts
    finally:
        tree_store.delete_tree(tree.id)


# ---------------------------------------------------------------------------
# Cascade delete
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_cascade_delete_removes_chapters_and_docs(tree_store, chapter_store, doc_store, content_store):
    tree = tree_store.create_tree("Cascade Test Tree", None)
    tree_id = tree.id

    ch = chapter_store.create_chapter(tree_id, "Ch")
    doc = doc_store.create_document(tree_id, ch.id, "Doc", "content", False)
    content_store.save_chunks([
        KnowledgeChunk(
            id=uuid4(),
            tree_id=tree_id,
            chapter_id=ch.id,
            doc_id=doc.id,
            chunk_index=0,
            text="some text",
            token_count=5,
        )
    ])

    tree_store.delete_tree(tree_id)

    # Everything should be gone due to ON DELETE CASCADE
    assert tree_store.get_tree(tree_id) is None
    assert chapter_store.list_chapters(tree_id) == []
    assert doc_store.list_documents(tree_id, None) == []
    assert content_store.get_chunks(tree_id, ch.number) == []
