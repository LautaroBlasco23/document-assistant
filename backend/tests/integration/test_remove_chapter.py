"""
Integration tests for the remove chapter feature.
These tests require running Qdrant, Neo4j, and PostgreSQL.
They are skipped if those services are not reachable.
"""

import json
import tempfile
from pathlib import Path

import pytest

from core.model.chunk import Chunk, ChunkMetadata
from infrastructure.config import Neo4jConfig, QdrantConfig
from infrastructure.graph.neo4j_store import Neo4jStore
from infrastructure.output.manifest import remove_chapter_from_manifest, write_manifest
from infrastructure.vectorstore.qdrant_store import QdrantStore

VECTOR_SIZE = 4


# ---------------------------------------------------------------------------
# Service availability checks
# ---------------------------------------------------------------------------


def _qdrant_available() -> bool:
    try:
        from qdrant_client import QdrantClient

        QdrantClient(url="http://localhost:6333", timeout=2).get_collections()
        return True
    except Exception:
        return False


def _neo4j_available() -> bool:
    try:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(
            "bolt://localhost:7687", auth=("neo4j", "password")
        )
        driver.verify_connectivity()
        driver.close()
        return True
    except Exception:
        return False


skip_if_no_qdrant = pytest.mark.skipif(
    not _qdrant_available(), reason="Qdrant not reachable"
)
skip_if_no_neo4j = pytest.mark.skipif(
    not _neo4j_available(), reason="Neo4j not reachable"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(file_hash: str, chapter_index: int, page: int = 1) -> Chunk:
    meta = ChunkMetadata(
        source_file=file_hash,
        chapter_index=chapter_index,
        page_number=page,
        start_char=0,
        end_char=50,
    )
    return Chunk(
        text=f"Text for chapter {chapter_index} page {page}",
        token_count=5,
        metadata=meta,
    )


def _make_vector() -> list[float]:
    return [0.1, 0.2, 0.3, 0.4]


# ---------------------------------------------------------------------------
# Qdrant: delete_by_chapter
# ---------------------------------------------------------------------------


@pytest.mark.integration
@skip_if_no_qdrant
def test_qdrant_delete_by_chapter():
    """delete_by_chapter removes only chunks for the specified chapter."""
    config = QdrantConfig(
        url="http://localhost:6333",
        collection_name="test_remove_chapter_qdrant",
    )
    store = QdrantStore(config)
    store.ensure_collection(VECTOR_SIZE)

    file_hash = "integ_test_hash_qdrant_abc"
    chunks_ch0 = [_make_chunk(file_hash, 0, p) for p in range(1, 4)]
    chunks_ch1 = [_make_chunk(file_hash, 1, p) for p in range(1, 4)]

    all_chunks = chunks_ch0 + chunks_ch1
    vectors = [_make_vector() for _ in all_chunks]
    store.upsert(all_chunks, vectors)

    # Verify both chapters exist
    all_in_store = store.search_by_file(file_hash)
    chapters_before = {c.metadata.chapter_index for c in all_in_store if c.metadata}
    assert 0 in chapters_before
    assert 1 in chapters_before

    # Remove chapter 0
    deleted = store.delete_by_chapter(file_hash, 0)
    assert deleted == 3

    # Verify chapter 0 is gone, chapter 1 remains
    remaining = store.search_by_file(file_hash)
    chapters_after = {c.metadata.chapter_index for c in remaining if c.metadata}
    assert 0 not in chapters_after
    assert 1 in chapters_after

    # Cleanup
    store.delete_by_source_file(file_hash)


@pytest.mark.integration
@skip_if_no_qdrant
def test_qdrant_delete_by_chapter_idempotent():
    """Calling delete_by_chapter twice for the same chapter returns 0 on second call."""
    config = QdrantConfig(
        url="http://localhost:6333",
        collection_name="test_remove_chapter_qdrant",
    )
    store = QdrantStore(config)
    store.ensure_collection(VECTOR_SIZE)

    file_hash = "integ_test_hash_idempotent"
    chunks = [_make_chunk(file_hash, 2)]
    store.upsert(chunks, [_make_vector()])

    first = store.delete_by_chapter(file_hash, 2)
    assert first == 1

    second = store.delete_by_chapter(file_hash, 2)
    assert second == 0


# ---------------------------------------------------------------------------
# Neo4j: delete_chapter
# ---------------------------------------------------------------------------


@pytest.mark.integration
@skip_if_no_neo4j
def test_neo4j_delete_chapter():
    """delete_chapter removes MENTIONS relationships for the specified chapter only."""
    config = Neo4jConfig(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="password",
    )
    store = Neo4jStore(config)
    store.ensure_indexes()

    file_hash = "integ_neo4j_chapter_hash"

    # Create a chunk for chapter 0 and chapter 1
    chunk_ch0 = _make_chunk(file_hash, 0)
    chunk_ch1 = _make_chunk(file_hash, 1)

    entities_ch0 = [{"name": "AlphaEntity", "type": "Concept", "context": ""}]
    entities_ch1 = [{"name": "BetaEntity", "type": "Concept", "context": ""}]

    store.upsert_document(file_hash, "Test Book", "/tmp/test.pdf")
    store.upsert_entities(entities_ch0, chunk_ch0)
    store.upsert_entities(entities_ch1, chunk_ch1)

    # Verify both chapter entities exist
    alpha_chunks = store.query_related(["AlphaEntity"])
    beta_chunks = store.query_related(["BetaEntity"])
    assert len(alpha_chunks) > 0
    assert len(beta_chunks) > 0

    # Remove chapter 0 relationships
    store.delete_chapter(file_hash, 0)

    # Chapter 0 entity should no longer be reachable via this source_file
    # (Note: query_related returns chunk_ids; the relationships were deleted)
    alpha_after = store.query_related(["AlphaEntity"])
    beta_after = store.query_related(["BetaEntity"])

    # AlphaEntity's relationship was deleted; BetaEntity's should still exist
    assert len(alpha_after) == 0
    assert len(beta_after) > 0

    # Cleanup
    store.delete_document(file_hash)
    store.close()


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
