"""
Unit tests for the chat router (/api/chat).

Subject: api/routers/chat.py
Scope:   POST /api/chat — document Q&A with conversation history.
Out of scope:
  - DocumentChatAgent internals            → test_document_chat_agent.py
  - LLM.generate() behavior                → test_base_agent.py
  - Authentication token validation        → test_api_auth.py
Setup:   FastAPI TestClient with mocked DocumentChatAgent and current user.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.auth import get_current_user
from api.deps import get_services_dep
from api.routers import chat as chat_router
from core.model.user import User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXED_UUID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")


def _make_user():
    return User(
        id=FIXED_UUID,
        email="user@example.com",
        password_hash="hash",
        display_name="User",
        is_active=True,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )


@pytest.fixture
def mock_services():
    """Return a Services-like object with a mocked LLM."""
    services = MagicMock()
    services.llm = MagicMock()
    return services


@pytest.fixture
def test_client(mock_services):
    """Build a FastAPI test app with the chat router and dependencies overridden."""
    app = FastAPI()
    app.include_router(chat_router.router, prefix="/api")
    app.dependency_overrides[get_services_dep] = lambda: mock_services
    app.dependency_overrides[get_current_user] = _make_user
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /api/chat
# ---------------------------------------------------------------------------


def test_chat_with_valid_context_returns_reply(test_client, mock_services):
    """A valid chat request with context must return the agent's reply."""
    with patch(
        "api.routers.chat.DocumentChatAgent"
    ) as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent.answer.return_value = "The answer is 42."
        mock_agent_cls.return_value = mock_agent

        response = test_client.post("/api/chat", json={
            "messages": [
                {"role": "user", "content": "What is the answer?"},
            ],
            "context": "Document says the answer is 42.",
        })

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "The answer is 42."
    mock_agent.answer.assert_called_once()
    call_args = mock_agent.answer.call_args
    assert call_args.kwargs.get("context") == "Document says the answer is 42."


def test_chat_empty_messages_handled(test_client, mock_services):
    """A chat request with an empty messages list must still be accepted
    and passed through to the agent (the agent handles empty history)."""
    with patch(
        "api.routers.chat.DocumentChatAgent"
    ) as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent.answer.return_value = "Please ask a question."
        mock_agent_cls.return_value = mock_agent

        response = test_client.post("/api/chat", json={
            "messages": [],
            "context": "Some document context.",
        })

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Please ask a question."
    # Agent should receive empty messages list
    call_args = mock_agent.answer.call_args
    assert call_args.args[0] == []


def test_chat_invalid_request_returns_422(test_client):
    """A request with a completely invalid body must trigger FastAPI validation (422)."""
    response = test_client.post("/api/chat", json={
        "messages": "not-a-list",
        "context": "Document context.",
    })

    assert response.status_code == 422


def test_chat_missing_messages_field_returns_422(test_client):
    """Omitting the required 'messages' field must trigger Pydantic validation."""
    response = test_client.post("/api/chat", json={
        "context": "Document context.",
    })

    assert response.status_code == 422
