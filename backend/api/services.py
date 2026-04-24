"""Singleton services container for API."""

import logging
from dataclasses import dataclass

from api.tasks import TaskRegistry
from core.ports.llm import LLM
from infrastructure.auth.jwt_handler import validate_jwt_config
from infrastructure.config import AppConfig, load_config
from infrastructure.db.knowledge_tree_repository import (
    PostgresFlashcardStore,
    PostgresKnowledgeChapterStore,
    PostgresKnowledgeContentStore,
    PostgresKnowledgeDocumentStore,
    PostgresKnowledgeQuestionStore,
    PostgresKnowledgeTreeStore,
)
from infrastructure.db.postgres import PostgresPool
from infrastructure.db.task_repository import TaskRepository
from infrastructure.db.user_repository import (
    PostgresSubscriptionPlanStore,
    PostgresUserStore,
    PostgresUserSubscriptionStore,
)
from infrastructure.llm.factory import create_fast_llm, create_llm

logger = logging.getLogger(__name__)


@dataclass
class Services:
    """Container for all infrastructure and application services."""

    config: AppConfig
    llm: LLM
    fast_llm: LLM
    task_registry: TaskRegistry
    user_store: PostgresUserStore
    subscription_store: PostgresUserSubscriptionStore
    plan_store: PostgresSubscriptionPlanStore
    kt_tree_store: PostgresKnowledgeTreeStore
    kt_chapter_store: PostgresKnowledgeChapterStore
    kt_doc_store: PostgresKnowledgeDocumentStore
    kt_content_store: PostgresKnowledgeContentStore
    kt_question_store: PostgresKnowledgeQuestionStore
    kt_flashcard_store: PostgresFlashcardStore
    _pg_pool: PostgresPool


# Global services instance
_services: Services | None = None


def init_services(config: AppConfig | None = None) -> Services:
    """Initialize or reinitialize services."""
    global _services

    if config is None:
        config = load_config()

    # Validate JWT configuration early
    validate_jwt_config()

    llm = create_llm(config)
    fast_llm = create_fast_llm(config, llm)

    pg_pool = PostgresPool(config.postgres)
    pg_pool.connect()
    task_repo = TaskRepository(pg_pool)
    task_repo.fail_orphaned()
    task_registry = TaskRegistry(max_workers=2, repo=task_repo)

    # Initialize user stores
    user_store = PostgresUserStore(pg_pool)
    plan_store = PostgresSubscriptionPlanStore(pg_pool)
    subscription_store = PostgresUserSubscriptionStore(pg_pool)

    kt_tree_store = PostgresKnowledgeTreeStore(pg_pool)
    kt_chapter_store = PostgresKnowledgeChapterStore(pg_pool)
    kt_doc_store = PostgresKnowledgeDocumentStore(pg_pool)
    kt_content_store = PostgresKnowledgeContentStore(pg_pool)
    kt_question_store = PostgresKnowledgeQuestionStore(pg_pool)
    kt_flashcard_store = PostgresFlashcardStore(pg_pool)

    _services = Services(
        config=config,
        llm=llm,
        fast_llm=fast_llm,
        task_registry=task_registry,
        user_store=user_store,
        subscription_store=subscription_store,
        plan_store=plan_store,
        kt_tree_store=kt_tree_store,
        kt_chapter_store=kt_chapter_store,
        kt_doc_store=kt_doc_store,
        kt_content_store=kt_content_store,
        kt_question_store=kt_question_store,
        kt_flashcard_store=kt_flashcard_store,
        _pg_pool=pg_pool,
    )

    logger.info(
        "Config: provider=%s postgres=%s:%d",
        config.llm_provider,
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
