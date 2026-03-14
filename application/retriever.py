import json
import logging
from typing import TYPE_CHECKING

from core.model.chunk import Chunk
from core.ports.embedder import Embedder
from core.ports.llm import LLM
from infrastructure.config import AppConfig

if TYPE_CHECKING:
    from infrastructure.graph.neo4j_store import Neo4jStore
    from infrastructure.vectorstore.qdrant_store import QdrantStore

logger = logging.getLogger(__name__)

_TOKEN_BUDGET = 6000
_RERANK_SYSTEM = (
    "You are a relevance ranking assistant. "
    "Given a query and a list of text snippets (numbered from 0), "
    "return a JSON array of snippet indices sorted by relevance to the query. "
    "Most relevant first. Return ONLY the JSON array, nothing else. "
    "Example: [2, 0, 4, 1, 3]"
)


class HybridRetriever:
    def __init__(
        self,
        qdrant: "QdrantStore",
        neo4j: "Neo4jStore",
        embedder: Embedder,
        llm: LLM,
        config: AppConfig,
    ):
        self._qdrant = qdrant
        self._neo4j = neo4j
        self._embedder = embedder
        self._llm = llm
        self._config = config

    def retrieve(
        self, query: str, k: int = 20, filters: dict | None = None
    ) -> list[Chunk]:
        """
        Hybrid retrieval: vector + keyword + graph, then LLM rerank.
        Returns chunks trimmed to token budget.
        """
        candidates: dict[str, Chunk] = {}

        # 1. Vector search
        query_vec = self._embedder.embed([query])[0]
        vector_hits = self._qdrant.search_vector(query_vec, k=k, filters=filters)
        for c in vector_hits:
            candidates[c.id] = c
        logger.debug("Vector search: %d hits", len(vector_hits))

        # 2. Keyword search
        keyword_hits = self._qdrant.search_text(query, k=k, filters=filters)
        for c in keyword_hits:
            candidates[c.id] = c
        logger.debug("Keyword search: %d hits", len(keyword_hits))

        # 3. Graph: extract entities from query and fetch related chunks
        try:
            from infrastructure.graph.entity_extractor import extract_entities
            entities = extract_entities(query, self._llm)
            entity_names = [e["name"] for e in entities]
            if entity_names:
                chunk_ids = self._neo4j.query_related(entity_names)
                if chunk_ids:
                    graph_chunks = self._qdrant.fetch_by_ids(chunk_ids[:k])
                    for c in graph_chunks:
                        candidates[c.id] = c
                    logger.debug("Graph search: %d hits", len(graph_chunks))
        except Exception as exc:
            logger.warning("Graph retrieval failed: %s", exc)

        if not candidates:
            return []

        # 4. LLM rerank
        ranked = self._rerank(query, list(candidates.values()))

        # 5. Trim to token budget
        result: list[Chunk] = []
        total_tokens = 0
        for chunk in ranked:
            if total_tokens + chunk.token_count > _TOKEN_BUDGET:
                break
            result.append(chunk)
            total_tokens += chunk.token_count

        logger.info(
            "Retrieved %d chunks (%d tokens) for query: %s...",
            len(result),
            total_tokens,
            query[:60],
        )
        return result

    def _rerank(self, query: str, chunks: list[Chunk]) -> list[Chunk]:
        """Ask the LLM to reorder chunks by relevance."""
        snippets = "\n".join(
            f"[{i}] {c.text[:200]}" for i, c in enumerate(chunks)
        )
        user_msg = f"Query: {query}\n\nSnippets:\n{snippets}"

        try:
            if hasattr(self._llm, "chat"):
                raw = self._llm.chat(_RERANK_SYSTEM, user_msg)
            else:
                raw = self._llm.generate(f"{_RERANK_SYSTEM}\n\n{user_msg}")

            start = raw.find("[")
            end = raw.rfind("]")
            if start != -1 and end != -1:
                indices = json.loads(raw[start : end + 1])
                ordered = []
                seen: set[int] = set()
                for idx in indices:
                    if isinstance(idx, int) and 0 <= idx < len(chunks) and idx not in seen:
                        ordered.append(chunks[idx])
                        seen.add(idx)
                # Append any chunks the LLM didn't mention
                for i, c in enumerate(chunks):
                    if i not in seen:
                        ordered.append(c)
                return ordered
        except Exception as exc:
            logger.warning("Reranking failed: %s", exc)

        return chunks
