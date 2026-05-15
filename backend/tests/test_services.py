"""
Unit tests for the API services lifecycle and singleton container.

Subject: api/services.py — init_services, get_services, shutdown_services
Scope:   Service initialization, singleton access, and cleanup.
"""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from api.services import (
    Services,
    get_services,
    init_services,
    shutdown_services,
)
from infrastructure.config import AppConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALL_STORE_PATCHES = [
    "api.services.validate_jwt_config",
    "api.services.validate_encryption_config",
    "api.services.create_llm",
    "api.services.create_fast_llm",
    "api.services.PostgresPool",
    "api.services.TaskRepository",
    "api.services.TaskRegistry",
    "api.services.PostgresUserStore",
    "api.services.PostgresSubscriptionPlanStore",
    "api.services.PostgresUserSubscriptionStore",
    "api.services.PostgresKnowledgeTreeStore",
    "api.services.PostgresKnowledgeChapterStore",
    "api.services.PostgresKnowledgeDocumentStore",
    "api.services.PostgresKnowledgeContentStore",
    "api.services.PostgresKnowledgeQuestionStore",
    "api.services.PostgresFlashcardStore",
    "api.services.PostgresExamSessionStore",
    "api.services.PostgresAgentRepository",
    "api.services.PostgresLLMCredentialStore",
    "api.services.EncryptionService",
]


@contextmanager
def _patches(**overrides):
    """Enter all required patches; yield a dict of named mock objects."""
    with (
        patch("api.services.validate_jwt_config") as mock_validate_jwt,
        patch("api.services.validate_encryption_config") as mock_validate_enc,
        patch("api.services.create_llm", return_value=MagicMock()) as mock_create_llm,
        patch("api.services.create_fast_llm", return_value=MagicMock()) as mock_create_fast,
        patch("api.services.PostgresPool") as mock_pool_cls,
        patch("api.services.TaskRepository") as mock_task_repo_cls,
        patch("api.services.TaskRegistry") as mock_task_registry_cls,
        patch("api.services.PostgresUserStore"),
        patch("api.services.PostgresSubscriptionPlanStore"),
        patch("api.services.PostgresUserSubscriptionStore"),
        patch("api.services.PostgresKnowledgeTreeStore"),
        patch("api.services.PostgresKnowledgeChapterStore"),
        patch("api.services.PostgresKnowledgeDocumentStore"),
        patch("api.services.PostgresKnowledgeContentStore"),
        patch("api.services.PostgresKnowledgeQuestionStore"),
        patch("api.services.PostgresFlashcardStore"),
        patch("api.services.PostgresExamSessionStore"),
        patch("api.services.PostgresAgentRepository"),
        patch("api.services.PostgresLLMCredentialStore"),
        patch("api.services.EncryptionService"),
    ):
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool
        mock_task_repo = MagicMock()
        mock_task_repo_cls.return_value = mock_task_repo
        yield {
            "validate_jwt": mock_validate_jwt,
            "validate_enc": mock_validate_enc,
            "create_llm": mock_create_llm,
            "create_fast_llm": mock_create_fast,
            "pool_cls": mock_pool_cls,
            "pool": mock_pool,
            "task_repo": mock_task_repo,
            "task_registry_cls": mock_task_registry_cls,
        }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_services():
    import api.services as svc_module

    svc_module._services = None
    yield
    svc_module._services = None


# ---------------------------------------------------------------------------
# init_services
# ---------------------------------------------------------------------------


def test_init_services_returns_services_object():
    """init_services() must return a fully populated Services dataclass."""
    with _patches() as mocks:
        config = AppConfig(llm_provider="groq")
        services = init_services(config)

    assert isinstance(services, Services)
    assert services.config is config
    assert services.llm is mocks["create_llm"].return_value
    assert services.fast_llm is mocks["create_fast_llm"].return_value
    assert services._pg_pool is mocks["pool"]
    mocks["validate_jwt"].assert_called_once()
    mocks["validate_enc"].assert_called_once()
    mocks["pool"].connect.assert_called_once()
    mocks["task_repo"].fail_orphaned.assert_called_once()


def test_init_services_creates_all_stores():
    """init_services() must instantiate every store class exactly once."""
    with (
        patch("api.services.validate_jwt_config"),
        patch("api.services.validate_encryption_config"),
        patch("api.services.create_llm", return_value=MagicMock()),
        patch("api.services.create_fast_llm", return_value=MagicMock()),
        patch("api.services.PostgresPool") as mock_pool_cls,
        patch("api.services.TaskRepository"),
        patch("api.services.TaskRegistry"),
        patch("api.services.PostgresUserStore") as mock_user_store_cls,
        patch("api.services.PostgresSubscriptionPlanStore") as mock_plan_store_cls,
        patch("api.services.PostgresUserSubscriptionStore") as mock_sub_store_cls,
        patch("api.services.PostgresKnowledgeTreeStore") as mock_kt_tree_cls,
        patch("api.services.PostgresKnowledgeChapterStore") as mock_kt_chapter_cls,
        patch("api.services.PostgresKnowledgeDocumentStore") as mock_kt_doc_cls,
        patch("api.services.PostgresKnowledgeContentStore") as mock_kt_content_cls,
        patch("api.services.PostgresKnowledgeQuestionStore") as mock_kt_q_cls,
        patch("api.services.PostgresFlashcardStore") as mock_kt_flash_cls,
        patch("api.services.PostgresExamSessionStore") as mock_exam_cls,
        patch("api.services.PostgresAgentRepository") as mock_agent_cls,
        patch("api.services.PostgresLLMCredentialStore") as mock_cred_cls,
        patch("api.services.EncryptionService"),
    ):
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool

        init_services(AppConfig())

    mock_user_store_cls.assert_called_once_with(mock_pool)
    mock_plan_store_cls.assert_called_once_with(mock_pool)
    mock_sub_store_cls.assert_called_once_with(mock_pool)
    mock_kt_tree_cls.assert_called_once_with(mock_pool)
    mock_kt_chapter_cls.assert_called_once_with(mock_pool)
    mock_kt_doc_cls.assert_called_once_with(mock_pool)
    mock_kt_content_cls.assert_called_once_with(mock_pool)
    mock_kt_q_cls.assert_called_once_with(mock_pool)
    mock_kt_flash_cls.assert_called_once_with(mock_pool)
    mock_exam_cls.assert_called_once_with(mock_pool)
    mock_agent_cls.assert_called_once_with(mock_pool)
    mock_cred_cls.assert_called_once_with(mock_pool)


def test_init_services_uses_load_config_when_none_provided():
    """When no config argument is passed, init_services() must call load_config()."""
    with _patches() as _:
        with patch(
            "api.services.load_config", return_value=AppConfig(llm_provider="ollama")
        ) as mock_load:
            services = init_services()

    mock_load.assert_called_once()
    assert services.config.llm_provider == "ollama"


# ---------------------------------------------------------------------------
# get_services (singleton)
# ---------------------------------------------------------------------------


def test_get_services_returns_singleton():
    """get_services() must return the same object created by init_services()."""
    with _patches() as _:
        init_services(AppConfig())
        services = get_services()

    assert services is get_services()


def test_get_services_raises_when_not_initialized():
    """get_services() must raise RuntimeError if called before init_services()."""
    with pytest.raises(RuntimeError, match="Services not initialized"):
        get_services()


# ---------------------------------------------------------------------------
# shutdown_services
# ---------------------------------------------------------------------------


def test_shutdown_services_cleans_up():
    """shutdown_services() must call task_registry.shutdown() and pg_pool.close()."""
    with _patches() as mocks:
        mock_registry_instance = MagicMock()
        mocks["task_registry_cls"].return_value = mock_registry_instance

        init_services(AppConfig())
        get_services()
        shutdown_services()

    mock_registry_instance.shutdown.assert_called_once()
    mocks["pool"].close.assert_called_once()


def test_shutdown_services_idempotent():
    """Calling shutdown_services() twice must not raise an error."""
    with _patches() as _:
        init_services(AppConfig())
        shutdown_services()
        shutdown_services()


def test_get_services_after_shutdown_raises():
    """After shutdown_services(), get_services() must raise RuntimeError again."""
    with _patches() as _:
        init_services(AppConfig())
        shutdown_services()

    with pytest.raises(RuntimeError, match="Services not initialized"):
        get_services()
