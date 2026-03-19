"""Singleton services container for API."""

import logging
from dataclasses import dataclass

from application.retriever import HybridRetriever
from infrastructure.config import AppConfig, load_config
from infrastructure.graph.neo4j_store import Neo4jStore
from infrastructure.llm.embedding_cache import EmbeddingCache
from infrastructure.llm.ollama import OllamaEmbedder, OllamaLLM
from infrastructure.vectorstore.qdrant_store import QdrantStore
from api.tasks import TaskRegistry

logger = logging.getLogger(__name__)


@dataclass
class Services:
    """Container for all infrastructure and application services."""

    config: AppConfig
    embedder: OllamaEmbedder
    llm: OllamaLLM
    qdrant: QdrantStore
    neo4j: Neo4jStore
    retriever: HybridRetriever
    task_registry: TaskRegistry


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
    qdrant = QdrantStore(config.qdrant)
    neo4j = Neo4jStore(config.neo4j)
    retriever = HybridRetriever(qdrant, neo4j, embedder, llm, config)
    task_registry = TaskRegistry(max_workers=2)

    _services = Services(
        config=config,
        embedder=embedder,
        llm=llm,
        qdrant=qdrant,
        neo4j=neo4j,
        retriever=retriever,
        task_registry=task_registry,
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
        _services = None
        logger.info("Services shut down")
