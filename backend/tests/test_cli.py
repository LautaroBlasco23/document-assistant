"""Unit tests for CLI commands in cli/main.py."""
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

from cli import main as cli_main
from core.model.user import User, UserLimits

FIXED_UUID = UUID("12345678-1234-5678-1234-567812345678")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(provider="groq", api_key="test-key"):
    """Return a lightweight mock config object."""
    config = MagicMock()
    config.llm_provider = provider
    config.groq.api_key = api_key
    config.groq.base_url = "https://api.groq.com/openai/v1"
    config.ollama.base_url = "http://localhost:11434"
    config.postgres.host = "localhost"
    config.postgres.port = 5432
    config.postgres.database = "docassist"
    config.postgres.user = "docassist"
    config.postgres.password = "docassist_pass"
    return config


def _make_user(email="alice@example.com", user_id=FIXED_UUID):
    return User(
        id=user_id,
        email=email,
        password_hash="hashed",
        display_name="Alice",
        is_active=True,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )


def _make_pool_and_cursor():
    """Return a mocked PostgresPool and cursor."""
    pool = MagicMock()
    cur = MagicMock()
    conn = MagicMock()

    cur.fetchone.return_value = None
    cur.fetchall.return_value = []

    cm_cur = MagicMock()
    cm_cur.__enter__ = MagicMock(return_value=cur)
    cm_cur.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cm_cur

    cm_tx = MagicMock()
    cm_tx.__enter__ = MagicMock(return_value=None)
    cm_tx.__exit__ = MagicMock(return_value=False)
    conn.transaction.return_value = cm_tx

    pool.connection.return_value = conn

    return pool, cur, conn


# ---------------------------------------------------------------------------
# run_check
# ---------------------------------------------------------------------------

@patch("cli.main.load_config")
@patch("cli.main.check_postgres")
@patch("cli.main.check_ollama")
def test_run_check_all_healthy(mock_check_ollama, mock_check_postgres, mock_load_config, capsys):
    """All services healthy → prints success, returns 0."""
    mock_load_config.return_value = _make_config(provider="groq", api_key="sk-test")
    mock_check_postgres.return_value = True
    mock_check_ollama.return_value = True  # not used for groq

    code = cli_main.run_check()
    captured = capsys.readouterr()

    assert code == 0
    assert "OK" in captured.out
    assert "FAIL" not in captured.out


@patch("cli.main.load_config")
@patch("cli.main.check_postgres")
@patch("cli.main.check_ollama")
def test_run_check_postgres_down(mock_check_ollama, mock_check_postgres, mock_load_config, capsys):
    """PostgreSQL down → reports failure, returns 1."""
    mock_load_config.return_value = _make_config(provider="groq", api_key="sk-test")
    mock_check_postgres.return_value = False
    mock_check_ollama.return_value = True

    code = cli_main.run_check()
    captured = capsys.readouterr()

    assert code == 1
    assert "FAIL" in captured.out
    assert "PostgreSQL" in captured.out


@patch("cli.main.load_config")
@patch("cli.main.check_postgres")
@patch("cli.main.check_ollama")
def test_run_check_ollama_down(mock_check_ollama, mock_check_postgres, mock_load_config, capsys):
    """Ollama down → reports failure, returns 1."""
    mock_load_config.return_value = _make_config(provider="ollama")
    mock_check_postgres.return_value = True
    mock_check_ollama.return_value = False

    code = cli_main.run_check()
    captured = capsys.readouterr()

    assert code == 1
    assert "FAIL" in captured.out
    assert "LLM" in captured.out


@patch("cli.main.load_config")
@patch("cli.main.check_postgres")
@patch("cli.main.check_ollama")
def test_run_check_groq_missing_key(
    mock_check_ollama, mock_check_postgres, mock_load_config, capsys
):
    """Groq provider with missing API key → reports failure, returns 1."""
    mock_load_config.return_value = _make_config(provider="groq", api_key="")
    mock_check_postgres.return_value = True
    mock_check_ollama.return_value = True

    code = cli_main.run_check()
    captured = capsys.readouterr()

    assert code == 1
    assert "FAIL" in captured.out
    assert "missing" in captured.out


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------

@patch("cli.main.load_config")
@patch("cli.main.PostgresPool")
@patch("cli.main.get_password_hash")
@patch("cli.main.PostgresUserStore")
@patch("cli.main.PostgresUserSubscriptionStore")
def test_create_user_success(
    mock_sub_store_cls, mock_user_store_cls, mock_hash, mock_pool_cls, mock_load_config, capsys
):
    """Successful user creation with hashed password and free plan assignment."""
    mock_load_config.return_value = _make_config()
    pool, _, _ = _make_pool_and_cursor()
    mock_pool_cls.return_value = pool

    mock_hash.return_value = "hashed_password"

    mock_user_store = MagicMock()
    mock_user_store.get_by_email.return_value = None
    mock_user_store.create.return_value = _make_user(email="bob@example.com")
    mock_user_store_cls.return_value = mock_user_store

    mock_sub_store = MagicMock()
    mock_sub_store_cls.return_value = mock_sub_store

    code = cli_main.create_user("bob@example.com", "secret123", "Bob")
    captured = capsys.readouterr()

    assert code == 0
    assert "Created user" in captured.out
    mock_hash.assert_called_once_with("secret123")
    mock_user_store.create.assert_called_once_with("bob@example.com", "hashed_password", "Bob")
    mock_sub_store.assign_plan.assert_called_once()


@patch("cli.main.load_config")
@patch("cli.main.PostgresPool")
@patch("cli.main.PostgresUserStore")
def test_create_user_duplicate_email(
    mock_user_store_cls, mock_pool_cls, mock_load_config, capsys
):
    """Duplicate email → prints error and returns 1."""
    mock_load_config.return_value = _make_config()
    pool, _, _ = _make_pool_and_cursor()
    mock_pool_cls.return_value = pool

    mock_user_store = MagicMock()
    mock_user_store.get_by_email.return_value = _make_user(email="bob@example.com")
    mock_user_store_cls.return_value = mock_user_store

    code = cli_main.create_user("bob@example.com", "secret123", "Bob")
    captured = capsys.readouterr()

    assert code == 1
    assert "already exists" in captured.out
    mock_user_store.create.assert_not_called()


# ---------------------------------------------------------------------------
# set_user_plan
# ---------------------------------------------------------------------------

@patch("cli.main.load_config")
@patch("cli.main.PostgresPool")
@patch("cli.main.PostgresUserStore")
@patch("cli.main.PostgresUserSubscriptionStore")
def test_set_user_plan_success(
    mock_sub_store_cls, mock_user_store_cls, mock_pool_cls, mock_load_config, capsys
):
    """Valid plan name → subscription updated, returns 0."""
    mock_load_config.return_value = _make_config()
    pool, _, _ = _make_pool_and_cursor()
    mock_pool_cls.return_value = pool

    mock_user_store = MagicMock()
    mock_user_store.get_by_email.return_value = _make_user(email="alice@example.com")
    mock_user_store_cls.return_value = mock_user_store

    mock_sub_store = MagicMock()
    mock_sub_store_cls.return_value = mock_sub_store

    code = cli_main.set_user_plan("alice@example.com", "pro")
    captured = capsys.readouterr()

    assert code == 0
    assert "Assigned plan 'pro'" in captured.out
    mock_sub_store.assign_plan.assert_called_once_with(FIXED_UUID, "pro")


@patch("cli.main.load_config")
@patch("cli.main.PostgresPool")
@patch("cli.main.PostgresUserStore")
@patch("cli.main.PostgresUserSubscriptionStore")
def test_set_user_plan_user_not_found(
    mock_sub_store_cls, mock_user_store_cls, mock_pool_cls, mock_load_config, capsys
):
    """User not found → prints error and returns 1."""
    mock_load_config.return_value = _make_config()
    pool, _, _ = _make_pool_and_cursor()
    mock_pool_cls.return_value = pool

    mock_user_store = MagicMock()
    mock_user_store.get_by_email.return_value = None
    mock_user_store_cls.return_value = mock_user_store

    code = cli_main.set_user_plan("missing@example.com", "pro")
    captured = capsys.readouterr()

    assert code == 1
    assert "User not found" in captured.out


@patch("cli.main.load_config")
@patch("cli.main.PostgresPool")
@patch("cli.main.PostgresUserStore")
@patch("cli.main.PostgresUserSubscriptionStore")
def test_set_user_plan_invalid_plan(
    mock_sub_store_cls, mock_user_store_cls, mock_pool_cls, mock_load_config, capsys
):
    """Invalid plan name → assign_plan raises, prints error, returns 1."""
    mock_load_config.return_value = _make_config()
    pool, _, _ = _make_pool_and_cursor()
    mock_pool_cls.return_value = pool

    mock_user_store = MagicMock()
    mock_user_store.get_by_email.return_value = _make_user(email="alice@example.com")
    mock_user_store_cls.return_value = mock_user_store

    mock_sub_store = MagicMock()
    mock_sub_store.assign_plan.side_effect = ValueError("Plan not found: enterprise")
    mock_sub_store_cls.return_value = mock_sub_store

    code = cli_main.set_user_plan("alice@example.com", "enterprise")
    captured = capsys.readouterr()

    assert code == 1
    assert "Plan not found" in captured.out


# ---------------------------------------------------------------------------
# show_user_limits
# ---------------------------------------------------------------------------

@patch("cli.main.load_config")
@patch("cli.main.PostgresPool")
@patch("cli.main.PostgresUserStore")
@patch("cli.main.PostgresUserSubscriptionStore")
def test_show_user_limits_with_plan(
    mock_sub_store_cls, mock_user_store_cls, mock_pool_cls, mock_load_config, capsys
):
    """User with plan → shows tree limit, document limit, usage."""
    mock_load_config.return_value = _make_config()
    pool, _, _ = _make_pool_and_cursor()
    mock_pool_cls.return_value = pool

    mock_user_store = MagicMock()
    mock_user_store.get_by_email.return_value = _make_user(email="alice@example.com")
    mock_user_store_cls.return_value = mock_user_store

    limits = UserLimits(
        max_documents=10,
        max_knowledge_trees=5,
        current_documents=3,
        current_knowledge_trees=2,
        can_create_document=True,
        can_create_tree=True,
    )
    mock_sub_store = MagicMock()
    mock_sub_store.get_user_limits.return_value = limits
    mock_sub_store_cls.return_value = mock_sub_store

    code = cli_main.show_user_limits("alice@example.com")
    captured = capsys.readouterr()

    assert code == 0
    assert "Knowledge Trees: 2 / 5" in captured.out
    assert "Documents: 3 / 10" in captured.out
    assert "Can create tree: True" in captured.out
    assert "Can create document: True" in captured.out


@patch("cli.main.load_config")
@patch("cli.main.PostgresPool")
@patch("cli.main.PostgresUserStore")
@patch("cli.main.PostgresUserSubscriptionStore")
def test_show_user_limits_without_plan(
    mock_sub_store_cls, mock_user_store_cls, mock_pool_cls, mock_load_config, capsys
):
    """User without plan → shows zeroed defaults."""
    mock_load_config.return_value = _make_config()
    pool, _, _ = _make_pool_and_cursor()
    mock_pool_cls.return_value = pool

    mock_user_store = MagicMock()
    mock_user_store.get_by_email.return_value = _make_user(email="alice@example.com")
    mock_user_store_cls.return_value = mock_user_store

    limits = UserLimits(
        max_documents=0,
        max_knowledge_trees=0,
        current_documents=0,
        current_knowledge_trees=0,
        can_create_document=False,
        can_create_tree=False,
    )
    mock_sub_store = MagicMock()
    mock_sub_store.get_user_limits.return_value = limits
    mock_sub_store_cls.return_value = mock_sub_store

    code = cli_main.show_user_limits("alice@example.com")
    captured = capsys.readouterr()

    assert code == 0
    assert "Knowledge Trees: 0 / 0" in captured.out
    assert "Can create tree: False" in captured.out


@patch("cli.main.load_config")
@patch("cli.main.PostgresPool")
@patch("cli.main.PostgresUserStore")
def test_show_user_limits_user_not_found(
    mock_user_store_cls, mock_pool_cls, mock_load_config, capsys
):
    """User not found → prints error and returns 1."""
    mock_load_config.return_value = _make_config()
    pool, _, _ = _make_pool_and_cursor()
    mock_pool_cls.return_value = pool

    mock_user_store = MagicMock()
    mock_user_store.get_by_email.return_value = None
    mock_user_store_cls.return_value = mock_user_store

    code = cli_main.show_user_limits("missing@example.com")
    captured = capsys.readouterr()

    assert code == 1
    assert "User not found" in captured.out


# ---------------------------------------------------------------------------
# list_users
# ---------------------------------------------------------------------------

@patch("cli.main.load_config")
@patch("cli.main.PostgresPool")
def test_list_users_empty(mock_pool_cls, mock_load_config, capsys):
    """Empty database → prints 'No users found.' and returns 0."""
    mock_load_config.return_value = _make_config()
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchall.return_value = []
    mock_pool_cls.return_value = pool

    code = cli_main.list_users()
    captured = capsys.readouterr()

    assert code == 0
    assert "No users found." in captured.out


@patch("cli.main.load_config")
@patch("cli.main.PostgresPool")
def test_list_users_populated(mock_pool_cls, mock_load_config, capsys):
    """Populated database → lists users with emails and plans."""
    mock_load_config.return_value = _make_config()
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchall.return_value = [
        {
            "id": FIXED_UUID,
            "email": "alice@example.com",
            "display_name": "Alice",
            "is_active": True,
            "created_at": datetime(2024, 6, 15),
            "plan_slug": "pro",
            "max_documents": 100,
            "max_knowledge_trees": 50,
        },
        {
            "id": UUID("87654321-4321-8765-4321-876543218765"),
            "email": "bob@example.com",
            "display_name": "Bob",
            "is_active": False,
            "created_at": datetime(2024, 3, 10),
            "plan_slug": None,
            "max_documents": 5,
            "max_knowledge_trees": 3,
        },
    ]
    mock_pool_cls.return_value = pool

    code = cli_main.list_users()
    captured = capsys.readouterr()

    assert code == 0
    assert "alice@example.com" in captured.out
    assert "pro" in captured.out
    assert "bob@example.com" in captured.out
    assert "none" in captured.out
    assert "yes" in captured.out
    assert "no" in captured.out
    assert "2024-06-15" in captured.out
    assert "2024-03-10" in captured.out


@patch("cli.main.load_config")
@patch("cli.main.PostgresPool")
def test_list_users_exception(mock_pool_cls, mock_load_config, capsys):
    """Database exception → prints error and returns 1."""
    mock_load_config.return_value = _make_config()
    pool, _, _ = _make_pool_and_cursor()
    pool.connection.side_effect = Exception("connection refused")
    mock_pool_cls.return_value = pool

    code = cli_main.list_users()
    captured = capsys.readouterr()

    assert code == 1
    assert "Error listing users" in captured.out
