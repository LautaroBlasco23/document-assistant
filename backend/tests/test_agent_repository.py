"""Unit tests for PostgreSQL agent repository.

Scope: PostgresAgentRepository — CRUD operations for agents table.
Out-of-scope: integration with real PostgreSQL, LLM provider behavior.
Setup: Mock psycopg.Connection and PostgresConnection via unittest.mock.
"""
from datetime import datetime
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from core.model.agent import Agent
from infrastructure.db.agent_repository import PostgresAgentRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXED_UUID = UUID("12345678-1234-5678-1234-567812345678")
FIXED_USER_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def _make_pool_and_cursor():
    """Return a mocked PostgresConnection and cursor that records executed SQL."""
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

    conn.info.transaction_status = 0  # IDLE

    pool.connection.return_value = conn

    return pool, cur, conn


def _agent_row(
    agent_id=FIXED_UUID,
    user_id=FIXED_USER_ID,
    name="Default",
    prompt="You are helpful",
    model="llama-3.3-70b",
    provider="groq",
    temperature=0.7,
    top_p=1.0,
    max_tokens=1024,
    is_default=True,
    created_at=None,
    updated_at=None,
):
    return {
        "id": agent_id,
        "user_id": user_id,
        "name": name,
        "prompt": prompt,
        "model": model,
        "provider": provider,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "is_default": is_default,
        "created_at": created_at or datetime(2024, 1, 1),
        "updated_at": updated_at or datetime(2024, 1, 1),
    }


def _make_agent(**overrides):
    defaults = {
        "id": FIXED_UUID,
        "user_id": FIXED_USER_ID,
        "name": "Test Agent",
        "prompt": "Be helpful",
        "model": "llama-3.3-70b",
        "provider": "groq",
        "temperature": 0.7,
        "top_p": 1.0,
        "max_tokens": 1024,
        "is_default": False,
    }
    defaults.update(overrides)
    return Agent(**defaults)


# ---------------------------------------------------------------------------
# list_by_user
# ---------------------------------------------------------------------------

def test_list_by_user_returns_agents_ordered():
    """list_by_user must return all agents for a user ordered by is_default DESC, created_at ASC."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchall.return_value = [
        _agent_row(name="Default", is_default=True, created_at=datetime(2024, 1, 1)),
        _agent_row(name="Custom", is_default=False, created_at=datetime(2024, 2, 1)),
    ]

    repo = PostgresAgentRepository(pool)
    agents = repo.list_by_user(FIXED_USER_ID)

    assert len(agents) == 2
    assert agents[0].name == "Default"
    assert agents[0].is_default is True
    assert agents[1].name == "Custom"
    assert agents[1].is_default is False


def test_list_by_user_empty():
    """list_by_user must return an empty list when the user has no agents."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchall.return_value = []

    repo = PostgresAgentRepository(pool)
    agents = repo.list_by_user(FIXED_USER_ID)

    assert agents == []


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------

def test_get_by_id_found():
    """get_by_id must return the Agent when a matching row exists."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _agent_row(agent_id=FIXED_UUID, name="My Agent")

    repo = PostgresAgentRepository(pool)
    agent = repo.get_by_id(FIXED_UUID)

    assert agent is not None
    assert agent.id == FIXED_UUID
    assert agent.name == "My Agent"


def test_get_by_id_not_found():
    """get_by_id must return None when the UUID does not exist."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = None

    repo = PostgresAgentRepository(pool)
    agent = repo.get_by_id(FIXED_UUID)

    assert agent is None


# ---------------------------------------------------------------------------
# get_default
# ---------------------------------------------------------------------------

def test_get_default_found():
    """get_default must return the default agent for a user."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _agent_row(is_default=True, name="Default")

    repo = PostgresAgentRepository(pool)
    agent = repo.get_default(FIXED_USER_ID)

    assert agent is not None
    assert agent.is_default is True
    assert agent.name == "Default"


def test_get_default_not_found():
    """get_default must return None when the user has no default agent."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = None

    repo = PostgresAgentRepository(pool)
    agent = repo.get_default(FIXED_USER_ID)

    assert agent is None


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

def test_create_returns_agent():
    """create must insert a row and return a fully populated Agent object."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _agent_row(name="New Agent", is_default=False)

    repo = PostgresAgentRepository(pool)
    agent = repo.create(_make_agent(name="New Agent", is_default=False))

    assert isinstance(agent, Agent)
    assert agent.name == "New Agent"
    assert agent.is_default is False


def test_create_duplicate_name_raises():
    """create must raise ValueError when an agent with the same name already exists."""
    import psycopg.errors

    pool, cur, _ = _make_pool_and_cursor()
    cur.execute.side_effect = psycopg.errors.UniqueViolation()

    repo = PostgresAgentRepository(pool)
    with pytest.raises(ValueError, match="Agent with name 'Dup' already exists"):
        repo.create(_make_agent(name="Dup"))


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

def test_update_returns_updated_agent():
    """update must modify the agent and return the updated object."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _agent_row(name="Updated Name", temperature=0.9)

    repo = PostgresAgentRepository(pool)
    agent = repo.update(_make_agent(name="Updated Name", temperature=0.9))

    assert agent.name == "Updated Name"
    assert agent.temperature == 0.9


def test_update_duplicate_name_raises():
    """update must raise ValueError when renaming to an existing agent name."""
    import psycopg.errors

    pool, cur, _ = _make_pool_and_cursor()
    cur.execute.side_effect = psycopg.errors.UniqueViolation()

    repo = PostgresAgentRepository(pool)
    with pytest.raises(ValueError, match="Agent with name 'Taken' already exists"):
        repo.update(_make_agent(name="Taken"))


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

def test_delete_non_default_agent():
    """delete must remove a non-default agent."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _agent_row(is_default=False)

    repo = PostgresAgentRepository(pool)
    repo.delete(FIXED_UUID)

    assert cur.execute.call_count == 2  # SELECT for lookup + DELETE


def test_delete_default_agent_raises():
    """delete must raise ValueError when attempting to delete the default agent."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _agent_row(is_default=True)

    repo = PostgresAgentRepository(pool)
    with pytest.raises(ValueError, match="Cannot delete the default agent"):
        repo.delete(FIXED_UUID)


def test_delete_nonexistent_agent_raises():
    """delete must raise ValueError when the agent does not exist."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = None

    repo = PostgresAgentRepository(pool)
    with pytest.raises(ValueError, match="Agent not found"):
        repo.delete(FIXED_UUID)


# ---------------------------------------------------------------------------
# ensure_default
# ---------------------------------------------------------------------------

def test_ensure_default_returns_existing():
    """ensure_default must return the existing default agent without creating a new one."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _agent_row(is_default=True, name="Existing Default")

    repo = PostgresAgentRepository(pool)
    agent = repo.ensure_default(FIXED_USER_ID, "llama-3.3-70b")

    assert agent is not None
    assert agent.name == "Existing Default"
    # Only one execute call (the get_default SELECT), no INSERT
    assert cur.execute.call_count == 1


def test_ensure_default_creates_when_missing():
    """ensure_default must create a default agent when none exists."""
    pool, cur, _ = _make_pool_and_cursor()
    # First call: get_default returns None
    # Second call: create INSERT returns new agent
    cur.fetchone.side_effect = [
        None,
        _agent_row(name="Default", is_default=True, model="llama-3.3-70b"),
    ]

    repo = PostgresAgentRepository(pool)
    agent = repo.ensure_default(FIXED_USER_ID, "llama-3.3-70b")

    assert agent is not None
    assert agent.name == "Default"
    assert agent.model == "llama-3.3-70b"
    assert agent.is_default is True
