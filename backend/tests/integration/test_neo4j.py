"""
Integration tests for Neo4jStore.
Skipped if Neo4j is not reachable.
"""
import pytest

from core.model.chunk import Chunk, ChunkMetadata
from infrastructure.config import Neo4jConfig
from infrastructure.graph.neo4j_store import Neo4jStore


def _neo4j_available() -> bool:
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            "bolt://localhost:7687", auth=("neo4j", "document_assistant_pass")
        )
        driver.verify_connectivity()
        driver.close()
        return True
    except Exception:
        return False


skip_if_no_neo4j = pytest.mark.skipif(
    not _neo4j_available(), reason="Neo4j not reachable"
)


@pytest.fixture()
def store() -> Neo4jStore:
    config = Neo4jConfig()
    s = Neo4jStore(config)
    s.ensure_indexes()
    yield s
    # Cleanup test data
    with s._driver.session() as session:
        session.run("MATCH (n:Entity) WHERE n.name STARTS WITH 'TestEntity' DETACH DELETE n")
    s.close()


@skip_if_no_neo4j
def test_upsert_entities_and_query(store):
    chunk = Chunk(
        id="neo4j-test-chunk-1",
        text="TestEntity Alpha appeared at the event.",
        token_count=7,
        metadata=ChunkMetadata("test.pdf", 0, 1, 0, 40),
    )
    entities = [{"name": "TestEntity Alpha", "type": "Person", "context": "appeared"}]
    store.upsert_entities(entities, chunk)

    result = store.query_related(["TestEntity Alpha"])
    assert "neo4j-test-chunk-1" in result


@skip_if_no_neo4j
def test_query_related_unknown_entity(store):
    result = store.query_related(["NonExistentXYZ999"])
    assert result == []
