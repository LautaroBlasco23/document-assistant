import logging

from neo4j import GraphDatabase

from core.model.chunk import Chunk
from infrastructure.config import Neo4jConfig

logger = logging.getLogger(__name__)


class Neo4jStore:
    def __init__(self, config: Neo4jConfig):
        self._driver = GraphDatabase.driver(
            config.uri, auth=(config.user, config.password)
        )

    @property
    def driver(self):
        """Access to the Neo4j driver."""
        return self._driver

    def close(self) -> None:
        self._driver.close()

    def ensure_indexes(self) -> None:
        """Create indexes if they don't exist."""
        queries = [
            "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
            "CREATE INDEX entity_label IF NOT EXISTS FOR (e:Entity) ON (e.label)",
            "CREATE INDEX doc_hash IF NOT EXISTS FOR (d:Document) ON (d.file_hash)",
        ]
        with self._driver.session() as session:
            for q in queries:
                session.run(q)
        logger.info("Neo4j indexes ensured")

    def upsert_document(self, file_hash: str, title: str, source_path: str) -> None:
        with self._driver.session() as session:
            session.run(
                "MERGE (d:Document {file_hash: $hash}) "
                "SET d.title = $title, d.source_path = $source_path",
                hash=file_hash,
                title=title,
                source_path=source_path,
            )

    def upsert_entities(self, entities: list[dict], chunk: Chunk) -> None:
        """
        MERGE each entity and create a MENTIONS relationship to the chunk.
        Batched in a single transaction.
        """
        if not entities:
            return

        meta = chunk.metadata
        with self._driver.session() as session:
            with session.begin_transaction() as tx:
                for entity in entities:
                    name = entity.get("name", "").strip()
                    label = entity.get("type", "Concept")
                    context = entity.get("context", "")
                    if not name:
                        continue
                    tx.run(
                        """
                        MERGE (e:Entity {name: $name})
                        SET e.label = $label
                        WITH e
                        MERGE (e)-[r:MENTIONS {chunk_id: $chunk_id}]->(e)
                        SET r.page = $page,
                            r.chapter = $chapter,
                            r.source_file = $source_file,
                            r.context = $context
                        """,
                        name=name,
                        label=label,
                        chunk_id=chunk.id,
                        page=meta.page_number if meta else 0,
                        chapter=meta.chapter_index if meta else 0,
                        source_file=meta.source_file if meta else "",
                        context=context,
                    )

    def query_related(self, entity_names: list[str]) -> list[str]:
        """Return chunk_ids that mention any of the given entity names."""
        if not entity_names:
            return []
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (e:Entity)-[r:MENTIONS]->()
                WHERE e.name IN $names
                RETURN DISTINCT r.chunk_id AS chunk_id
                """,
                names=entity_names,
            )
            return [row["chunk_id"] for row in result if row["chunk_id"]]

    def delete_document(self, file_hash: str) -> None:
        """Delete all entities and relationships associated with a document."""
        with self._driver.session() as session:
            # Delete relationships where the source_file matches
            session.run(
                """
                MATCH (e:Entity)-[r:MENTIONS]->()
                WHERE r.source_file = $file_hash
                DELETE r
                """,
                file_hash=file_hash,
            )
            # Delete the document node itself
            session.run(
                "MATCH (d:Document {file_hash: $hash}) DELETE d",
                hash=file_hash,
            )
        logger.info("Deleted document %s from Neo4j", file_hash)
