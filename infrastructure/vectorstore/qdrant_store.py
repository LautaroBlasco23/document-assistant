import logging

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from core.model.chunk import Chunk, ChunkMetadata
from infrastructure.config import QdrantConfig

logger = logging.getLogger(__name__)

_UPSERT_BATCH = 512


class QdrantStore:
    def __init__(self, config: QdrantConfig):
        self._client = QdrantClient(url=config.url)
        self._collection = config.collection_name

    def ensure_collection(self, vector_size: int) -> None:
        """Create collection if it doesn't exist; add payload indexes."""
        existing = {c.name for c in self._client.get_collections().collections}
        if self._collection not in existing:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=qmodels.VectorParams(
                    size=vector_size,
                    distance=qmodels.Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection '%s' (dim=%d)", self._collection, vector_size)

            # Payload indexes for filtering
            for field in ("book", "chapter", "page", "file_hash"):
                self._client.create_payload_index(
                    collection_name=self._collection,
                    field_name=field,
                    field_schema=qmodels.PayloadSchemaType.KEYWORD,
                )
            # Full-text index on the text field
            self._client.create_payload_index(
                collection_name=self._collection,
                field_name="text",
                field_schema=qmodels.TextIndexParams(
                    type=qmodels.TextIndexType.TEXT,
                    tokenizer=qmodels.TokenizerType.WORD,
                    min_token_len=2,
                    max_token_len=15,
                    lowercase=True,
                ),
            )
        else:
            logger.debug("Collection '%s' already exists", self._collection)

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Upsert chunks with their vectors, batched."""
        points = []
        for chunk, vec in zip(chunks, vectors):
            meta = chunk.metadata
            payload = {
                "text": chunk.text,
                "file_hash": _meta_attr(meta, "source_file", ""),
                "source_file": _meta_attr(meta, "source_file", ""),
                "chapter": _meta_attr(meta, "chapter_index", 0),
                "page": _meta_attr(meta, "page_number", 0),
                "chunk_hash": chunk.id,
            }
            points.append(qmodels.PointStruct(id=chunk.id, vector=vec, payload=payload))

        for i in range(0, len(points), _UPSERT_BATCH):
            batch = points[i : i + _UPSERT_BATCH]
            self._client.upsert(collection_name=self._collection, points=batch)
        logger.info("Upserted %d points into '%s'", len(points), self._collection)

    def search_vector(
        self, query_vec: list[float], k: int = 20, filters: dict | None = None
    ) -> list[Chunk]:
        query_filter = _build_filter(filters) if filters else None
        results = self._client.search(
            collection_name=self._collection,
            query_vector=query_vec,
            limit=k,
            query_filter=query_filter,
            with_payload=True,
        )
        return [_point_to_chunk(r) for r in results]

    def search_text(
        self, query_str: str, k: int = 20, filters: dict | None = None
    ) -> list[Chunk]:
        must_conditions = [
            qmodels.FieldCondition(
                key="text",
                match=qmodels.MatchText(text=query_str),
            )
        ]
        if filters:
            for key, val in filters.items():
                must_conditions.append(
                    qmodels.FieldCondition(key=key, match=qmodels.MatchValue(value=val))
                )

        results = self._client.scroll(
            collection_name=self._collection,
            scroll_filter=qmodels.Filter(must=must_conditions),
            limit=k,
            with_payload=True,
            with_vectors=False,
        )
        return [_point_to_chunk(r) for r in results[0]]

    def has_file(self, file_hash: str) -> bool:
        """Return True if any chunk with this file_hash exists."""
        try:
            results = self._client.scroll(
                collection_name=self._collection,
                scroll_filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="file_hash",
                            match=qmodels.MatchValue(value=file_hash),
                        )
                    ]
                ),
                limit=1,
                with_payload=False,
                with_vectors=False,
            )
            return len(results[0]) > 0
        except Exception:
            return False

    def fetch_by_ids(self, ids: list[str]) -> list[Chunk]:
        """Fetch chunks by their IDs."""
        results = self._client.retrieve(
            collection_name=self._collection,
            ids=ids,
            with_payload=True,
        )
        return [_point_to_chunk(r) for r in results]


def _meta_attr(meta: ChunkMetadata | None, attr: str, default):
    if meta is None:
        return default
    return getattr(meta, attr, default)


def _build_filter(filters: dict) -> qmodels.Filter:
    conditions = [
        qmodels.FieldCondition(key=k, match=qmodels.MatchValue(value=v))
        for k, v in filters.items()
    ]
    return qmodels.Filter(must=conditions)


def _point_to_chunk(point) -> Chunk:
    payload = point.payload or {}
    meta = ChunkMetadata(
        source_file=payload.get("source_file", ""),
        chapter_index=payload.get("chapter", 0),
        page_number=payload.get("page", 0),
        start_char=0,
        end_char=0,
    )
    return Chunk(
        id=str(point.id),
        text=payload.get("text", ""),
        token_count=len(payload.get("text", "").split()),
        metadata=meta,
    )
