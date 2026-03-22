"""Singleton services container for API."""

import logging
from dataclasses import dataclass

from api.tasks import TaskRegistry
from application.retriever import HybridRetriever
from core.ports.content_store import ContentStore
from infrastructure.config import AppConfig, load_config
from infrastructure.db.content_repository import PostgresContentStore
from infrastructure.db.postgres import PostgresPool
from infrastructure.graph.neo4j_store import Neo4jStore
from infrastructure.llm.embedding_cache import EmbeddingCache
from infrastructure.llm.ollama import OllamaEmbedder, OllamaLLM
from infrastructure.vectorstore.qdrant_store import QdrantStore

logger = logging.getLogger(__name__)


@dataclass
class Services:
    """Container for all infrastructure and application services."""

    config: AppConfig
    embedder: OllamaEmbedder
    llm: OllamaLLM
    fast_llm: OllamaLLM
    qdrant: QdrantStore
    neo4j: Neo4jStore
    retriever: HybridRetriever
    task_registry: TaskRegistry
    content_store: ContentStore
    _pg_pool: PostgresPool


# Global services instance
_services: Services | None = None


def init_services(config: AppConfig | None = None) -> Services:
    """Initialize or reinitialize services."""
    global _services

    if config is None:
        config = load_config()

    cache = EmbeddingCache()
    embedder = OllamaEmbedder(config.ollama, cache=cache)
    llm = OllamaLLM(config.ollama)

    if config.ollama.fast_model:
        fast_config = config.ollama.model_copy(
            update={"generation_model": config.ollama.fast_model}
        )
        fast_llm = OllamaLLM(fast_config)
    else:
        fast_llm = llm  # Fallback: reuse the same instance

    qdrant = QdrantStore(config.qdrant)
    neo4j = Neo4jStore(config.neo4j)
    retriever = HybridRetriever(qdrant, neo4j, embedder, llm, config)
    task_registry = TaskRegistry(max_workers=2)

    pg_pool = PostgresPool(config.postgres)
    pg_pool.connect()
    content_store = PostgresContentStore(pg_pool)

    _services = Services(
        config=config,
        embedder=embedder,
        llm=llm,
        fast_llm=fast_llm,
        qdrant=qdrant,
        neo4j=neo4j,
        retriever=retriever,
        task_registry=task_registry,
        content_store=content_store,
        _pg_pool=pg_pool,
    )

    logger.info(
        "Config: ollama=%s model=%s embed=%s qdrant=%s neo4j=%s postgres=%s:%d",
        config.ollama.base_url,
        config.ollama.generation_model,
        config.ollama.embedding_model,
        config.qdrant.url,
        config.neo4j.uri,
        config.postgres.host,
        config.postgres.port,
    )
    logger.info("Services initialized")
    return _services


def get_services() -> Services:
    """Get the global services instance."""
    if _services is None:
        raise RuntimeError("Services not initialized. Call init_services() first.")
    return _services


def shutdown_services() -> None:
    """Clean up services on shutdown."""
    global _services
    if _services:
        _services.task_registry.shutdown()
        _services._pg_pool.close()
        _services = None
        logger.info("Services shut down")
