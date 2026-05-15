"""
Unit tests for the API services lifecycle container.

Subject: api/services.py — init_services, shutdown_services
Scope:   Service initialization and cleanup.
"""

from unittest.mock import MagicMock, patch

from api.services import (
    Services,
    init_services,
    shutdown_services,
)
from infrastructure.config import AppConfig

_PATCH_TARGETS = [
    "api.services.validate_jwt_config",
    "api.services.validate_encryption_config",
    "api.services.create_llm",
    "api.services.create_fast_llm",
    "api.services.PostgresConnection",
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


def _patched():
    """Return a chain of patch context managers for all service dependencies."""
    patches = [patch(t) for t in _PATCH_TARGETS]
    # Enter all patches
    exits = [p.__enter__() for p in patches]
    mocks = dict(zip(_PATCH_TARGETS, exits))

    # Configure common mocks
    pool = MagicMock()
    mocks["api.services.PostgresConnection"].return_value = pool
    mocks["api.services.create_llm"].return_value = MagicMock()
    mocks["api.services.create_fast_llm"].return_value = MagicMock()
    task_repo = MagicMock()
    mocks["api.services.TaskRepository"].return_value = task_repo

    return mocks, pool, task_repo, patches


def _cleanup(patches):
    for p in reversed(patches):
        p.__exit__(None, None, None)


def test_init_services_returns_services_object():
    """init_services() must return a fully populated Services dataclass."""
    mocks, pool, task_repo, patches = _patched()
    try:
        config = AppConfig(llm_provider="groq")
        services = init_services(config)

        assert isinstance(services, Services)
        assert services.config is config
        assert services.llm is mocks["api.services.create_llm"].return_value
        assert services.fast_llm is mocks["api.services.create_fast_llm"].return_value
        assert services._pg_pool is pool
        pool.connect.assert_called_once()
        task_repo.fail_orphaned.assert_called_once()
    finally:
        _cleanup(patches)


def test_init_services_creates_all_stores():
    """init_services() must instantiate every store class exactly once."""
    mocks, pool, _task_repo, patches = _patched()
    try:
        init_services(AppConfig())

        for target in _PATCH_TARGETS[7:19]:  # all store classes
            mocks[target].assert_called_once_with(pool)
    finally:
        _cleanup(patches)


def test_init_services_uses_load_config_when_none_provided():
    """When no config argument is passed, init_services() must call load_config()."""
    mocks, _pool, _task_repo, patches = _patched()
    try:
        with patch(
            "api.services.load_config",
            return_value=AppConfig(llm_provider="ollama"),
        ) as mock_load:
            services = init_services()

        mock_load.assert_called_once()
        assert services.config.llm_provider == "ollama"
    finally:
        _cleanup(patches)


def test_shutdown_services_cleans_up():
    """shutdown_services() must call task_registry.shutdown() and pg_pool.close()."""
    mocks, pool, _task_repo, patches = _patched()
    try:
        mock_registry = MagicMock()
        mocks["api.services.TaskRegistry"].return_value = mock_registry

        services = init_services(AppConfig())
        shutdown_services(services)

        mock_registry.shutdown.assert_called_once()
        pool.close.assert_called_once()
    finally:
        _cleanup(patches)


def test_shutdown_services_idempotent():
    """Calling shutdown_services() twice must not raise an error."""
    _mocks, _pool, _task_repo, patches = _patched()
    try:
        services = init_services(AppConfig())
        shutdown_services(services)
        shutdown_services(services)
    finally:
        _cleanup(patches)
