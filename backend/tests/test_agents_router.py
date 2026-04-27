"""
Unit tests for the agents router (/api/agents/*).

Subject: api/routers/agents.py
Scope:   List, create, update, delete, and get-default agent endpoints.
         Covers happy paths, validation errors (422), not-found (404),
         conflict (409), and unauthorized access (401).
Out of scope:
  - Agent domain logic              → test_agent.py (if present)
  - Agent repository SQL internals  → integration tests
  - Agent in chat resolution        → test_chat_router.py
Setup:   FastAPI TestClient with mocked Services (agent_store) + current user.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.auth import get_current_user
from api.deps import get_services_dep
from api.routers import agents as agents_router
from core.model.agent import Agent
from core.model.user import User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXED_USER_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
FIXED_AGENT_ID = UUID("11111111-1111-1111-1111-111111111111")


def _make_user() -> User:
    return User(
        id=FIXED_USER_ID,
        email="test@example.com",
        password_hash="hash",
        display_name="Test",
        is_active=True,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _make_agent(**overrides) -> Agent:
    """Factory for a test Agent domain object."""
    defaults = dict(
        id=FIXED_AGENT_ID,
        user_id=FIXED_USER_ID,
        name="Test Agent",
        prompt="You are helpful.",
        model="test-model",
        temperature=0.7,
        top_p=1.0,
        max_tokens=1024,
        is_default=False,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return Agent(**defaults)


@pytest.fixture
def mock_services():
    """Return a Services-like object with mocked agent_store and config."""
    services = MagicMock()
    services.agent_store = MagicMock()
    services.config = MagicMock()
    services.config.llm_provider = "groq"
    services.config.groq = MagicMock()
    services.config.groq.model = "groq-model"
    return services


@pytest.fixture
def test_client(mock_services):
    """Build a FastAPI test app with the agents router and dependency overrides."""
    app = FastAPI()
    app.include_router(agents_router.router, prefix="/api")

    app.dependency_overrides[get_services_dep] = lambda: mock_services
    app.dependency_overrides[get_current_user] = _make_user

    return TestClient(app)


# Helper to build an app without the user override, so the real auth dep runs.
def _build_unauth_client(mock_services_):
    app = FastAPI()
    app.include_router(agents_router.router, prefix="/api")
    app.dependency_overrides[get_services_dep] = lambda: mock_services_
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/agents — list agents
# ---------------------------------------------------------------------------

def test_list_agents_returns_empty_list(test_client, mock_services):
    """When the user has no agents, the default is auto-created and the list
    should not be empty (ensure_default is called), but if the store returns
    an empty list, the endpoint returns an empty array."""
    mock_services.agent_store.ensure_default = MagicMock()
    mock_services.agent_store.list_by_user.return_value = []

    response = test_client.get("/api/agents")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body == []


def test_list_agents_returns_existing_agents(test_client, mock_services):
    """When agents exist for the user, they are returned as AgentOut items."""
    agent = _make_agent()
    mock_services.agent_store.ensure_default = MagicMock()
    mock_services.agent_store.list_by_user.return_value = [agent]

    response = test_client.get("/api/agents")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(FIXED_AGENT_ID)
    assert body[0]["name"] == "Test Agent"
    assert body[0]["model"] == "test-model"


# ---------------------------------------------------------------------------
# POST /api/agents — create agent
# ---------------------------------------------------------------------------

def test_create_agent_success(test_client, mock_services):
    """A valid CreateAgentRequest returns 201 and the created AgentOut."""
    agent = _make_agent(name="New Agent", model="custom-model")
    mock_services.agent_store.create.return_value = agent

    response = test_client.post("/api/agents", json={
        "name": "New Agent",
        "model": "custom-model",
    })

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "New Agent"
    assert body["model"] == "custom-model"
    assert body["id"] == str(FIXED_AGENT_ID)
    mock_services.agent_store.create.assert_called_once()


def test_create_agent_with_duplicate_name_returns_409(test_client, mock_services):
    """When the store raises ValueError (e.g. duplicate name), a 409 is returned."""
    mock_services.agent_store.create.side_effect = ValueError("Name already exists")

    response = test_client.post("/api/agents", json={
        "name": "Duplicate",
        "model": "some-model",
    })

    assert response.status_code == 409
    assert "Name already exists" in response.json()["detail"]


def test_create_agent_missing_fields_returns_422(test_client):
    """Omitting required fields (model) triggers Pydantic validation (422)."""
    response = test_client.post("/api/agents", json={
        "name": "Incomplete",
    })

    assert response.status_code == 422


def test_create_agent_invalid_temperature_returns_422(test_client):
    """A temperature outside [0, 2] returns 422 from Pydantic validation."""
    response = test_client.post("/api/agents", json={
        "name": "Hot",
        "model": "x",
        "temperature": 3.0,
    })

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# PUT /api/agents/{agent_id} — update agent
# ---------------------------------------------------------------------------

def test_update_agent_success(test_client, mock_services):
    """Updating an existing agent returns 200 and the modified AgentOut."""
    agent = _make_agent(name="Updated", prompt="new-prompt")
    mock_services.agent_store.get_by_id.return_value = agent
    mock_services.agent_store.update.return_value = agent

    response = test_client.put(f"/api/agents/{FIXED_AGENT_ID}", json={
        "name": "Updated",
        "prompt": "new-prompt",
    })

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Updated"
    assert body["prompt"] == "new-prompt"
    mock_services.agent_store.update.assert_called_once()


def test_update_agent_nonexistent_returns_404(test_client, mock_services):
    """Updating a non-existent agent returns 404."""
    mock_services.agent_store.get_by_id.return_value = None

    response = test_client.put(f"/api/agents/{FIXED_AGENT_ID}", json={
        "name": "Ghost",
    })

    assert response.status_code == 404
    assert "Agent not found" in response.json()["detail"]


def test_update_agent_invalid_id_returns_422(test_client):
    """Passing a non-UUID agent_id returns 422."""
    response = test_client.put("/api/agents/not-a-uuid", json={
        "name": "BadID",
    })

    assert response.status_code == 422
    assert "Invalid agent ID" in response.json()["detail"]


def test_update_agent_different_user_returns_403(test_client, mock_services):
    """Updating an agent owned by a different user returns 403."""
    other_agent = _make_agent(user_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"))
    mock_services.agent_store.get_by_id.return_value = other_agent

    response = test_client.put(f"/api/agents/{FIXED_AGENT_ID}", json={
        "name": "NotYours",
    })

    assert response.status_code == 403
    assert "Not your agent" in response.json()["detail"]


# ---------------------------------------------------------------------------
# DELETE /api/agents/{agent_id} — delete agent
# ---------------------------------------------------------------------------

def test_delete_agent_success(test_client, mock_services):
    """Deleting an existing agent returns 204 with no body."""
    agent = _make_agent()
    mock_services.agent_store.get_by_id.return_value = agent

    response = test_client.delete(f"/api/agents/{FIXED_AGENT_ID}")

    assert response.status_code == 204
    assert response.content == b""
    mock_services.agent_store.delete.assert_called_once_with(FIXED_AGENT_ID)


def test_delete_agent_nonexistent_returns_404(test_client, mock_services):
    """Deleting a non-existent agent returns 404."""
    mock_services.agent_store.get_by_id.return_value = None

    response = test_client.delete(f"/api/agents/{FIXED_AGENT_ID}")

    assert response.status_code == 404


def test_delete_agent_default_returns_400(test_client, mock_services):
    """Deleting the default agent is not allowed — store raises ValueError → 400."""
    agent = _make_agent(is_default=True)
    mock_services.agent_store.get_by_id.return_value = agent
    mock_services.agent_store.delete.side_effect = ValueError("Cannot delete default")

    response = test_client.delete(f"/api/agents/{FIXED_AGENT_ID}")

    assert response.status_code == 400
    assert "Cannot delete default" in response.json()["detail"]


# ---------------------------------------------------------------------------
# GET /api/agents/default — get default agent
# ---------------------------------------------------------------------------

def test_get_default_agent_success(test_client, mock_services):
    """When a default agent exists, it is returned."""
    default_agent = _make_agent(is_default=True, name="Default")
    mock_services.agent_store.get_default.return_value = default_agent

    response = test_client.get("/api/agents/default")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Default"
    assert body["is_default"] is True
    mock_services.agent_store.get_default.assert_called_once_with(FIXED_USER_ID)


def test_get_default_agent_not_found_returns_404(test_client, mock_services):
    """When no default agent exists, a 404 is returned."""
    mock_services.agent_store.get_default.return_value = None

    response = test_client.get("/api/agents/default")

    assert response.status_code == 404
    assert "Default agent not found" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Unauthorized access
# ---------------------------------------------------------------------------

def test_list_agents_without_auth_returns_401(mock_services):
    """Requests without a valid token must receive 401 on every endpoint."""
    # Test on the list endpoint as a representative.
    client = _build_unauth_client(mock_services)

    response = client.get("/api/agents")

    assert response.status_code == 401


def test_create_agent_without_auth_returns_401(mock_services):
    """Creating an agent without auth must receive 401."""
    client = _build_unauth_client(mock_services)

    response = client.post("/api/agents", json={
        "name": "NoAuth",
        "model": "x",
    })

    assert response.status_code == 401
