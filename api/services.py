"""Singleton services container for API."""

import logging
from dataclasses import dataclass

from api.tasks import TaskRegistry
from application.retriever import HybridRetriever
from core.ports.content_store import ContentStore
from core.ports.llm import LLM
from infrastructure.config import AppConfig, load_config
from infrastructure.db.content_repository import PostgresContentStore
from infrastructure.db.postgres import PostgresPool
from infrastructure.db.task_repository import TaskRepository
from infrastructure.graph.neo4j_store import Neo4jStore
from infrastructure.llm.embedding_cache import EmbeddingCache
from infrastructure.llm.factory import create_fast_llm, create_llm
from infrastructure.llm.ollama import OllamaEmbedder
from infrastructure.vectorstore.qdrant_store import QdrantStore

logger = logging.getLogger(__name__)


@dataclass
class Services:
    """Container for all infrastructure and application services."""

    config: AppConfig
    embedder: OllamaEmbedder
    llm: LLM
    fast_llm: LLM
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

    llm = create_llm(config)
    fast_llm = create_fast_llm(config, llm)

    qdrant = QdrantStore(config.qdrant)
    neo4j = Neo4jStore(config.neo4j)
    retriever = HybridRetriever(qdrant, neo4j, embedder, llm, config)
    pg_pool = PostgresPool(config.postgres)
    pg_pool.connect()
    content_store = PostgresContentStore(pg_pool)
    task_repo = TaskRepository(pg_pool)
    task_registry = TaskRegistry(max_workers=2, repo=task_repo)

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
        "Config: provider=%s embed=%s qdrant=%s neo4j=%s postgres=%s:%d",
        config.llm_provider,
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
