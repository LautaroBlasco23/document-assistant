"""Services container for API."""

import logging
from dataclasses import dataclass

from api.tasks import TaskRegistry
from core.ports.llm import LLM
from infrastructure.auth.encryption import EncryptionService
from infrastructure.auth.jwt_handler import validate_encryption_config, validate_jwt_config
from infrastructure.config import AppConfig, load_config
from infrastructure.db.agent_repository import PostgresAgentRepository
from infrastructure.db.knowledge_tree_repository import (
    PostgresExamSessionStore,
    PostgresFlashcardStore,
    PostgresKnowledgeChapterStore,
    PostgresKnowledgeContentStore,
    PostgresKnowledgeDocumentStore,
    PostgresKnowledgeQuestionStore,
    PostgresKnowledgeTreeStore,
    PostgresStudySessionStore,
)
from infrastructure.db.llm_credential_repository import PostgresLLMCredentialStore
from infrastructure.db.postgres import PostgresConnection
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
    kt_exam_store: PostgresExamSessionStore
    kt_study_store: PostgresStudySessionStore
    agent_store: PostgresAgentRepository
    llm_credential_store: PostgresLLMCredentialStore
    encryption: EncryptionService
    _pg_pool: PostgresConnection


def init_services(config: AppConfig | None = None) -> Services:
    """Initialize services and return the container."""
    if config is None:
        config = load_config()

    validate_jwt_config()
    validate_encryption_config()

    llm = create_llm(config)
    fast_llm = create_fast_llm(config, llm)

    pg_pool = PostgresConnection(config.postgres)
    pg_pool.connect()
    task_repo = TaskRepository(pg_pool)
    task_repo.fail_orphaned()
    task_registry = TaskRegistry(max_workers=2, repo=task_repo)

    user_store = PostgresUserStore(pg_pool)
    plan_store = PostgresSubscriptionPlanStore(pg_pool)
    subscription_store = PostgresUserSubscriptionStore(pg_pool)

    kt_tree_store = PostgresKnowledgeTreeStore(pg_pool)
    kt_chapter_store = PostgresKnowledgeChapterStore(pg_pool)
    kt_doc_store = PostgresKnowledgeDocumentStore(pg_pool)
    kt_content_store = PostgresKnowledgeContentStore(pg_pool)
    kt_question_store = PostgresKnowledgeQuestionStore(pg_pool)
    kt_flashcard_store = PostgresFlashcardStore(pg_pool)
    kt_exam_store = PostgresExamSessionStore(pg_pool)
    kt_study_store = PostgresStudySessionStore(pg_pool)
    agent_store = PostgresAgentRepository(pg_pool)
    llm_credential_store = PostgresLLMCredentialStore(pg_pool)
    _enc_key = config.auth.encryption_key
    encryption = EncryptionService(
        _enc_key if isinstance(_enc_key, bytes) else _enc_key.encode()
    )

    services = Services(
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
        kt_exam_store=kt_exam_store,
        kt_study_store=kt_study_store,
        agent_store=agent_store,
        llm_credential_store=llm_credential_store,
        encryption=encryption,
        _pg_pool=pg_pool,
    )

    logger.info(
        "Config: provider=%s postgres=%s:%d",
        config.llm_provider,
        config.postgres.host,
        config.postgres.port,
    )
    logger.info("Services initialized")
    return services


def shutdown_services(services: Services) -> None:
    """Clean up a services container."""
    services.task_registry.shutdown()
    services._pg_pool.close()
    logger.info("Services shut down")
