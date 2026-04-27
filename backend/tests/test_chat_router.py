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


# ---------------------------------------------------------------------------
# Additional chat router tests
# ---------------------------------------------------------------------------


def test_chat_with_empty_message_content(test_client, mock_services):
    """A chat request where the message content is an empty string must still
    be accepted and passed through to the agent."""
    with patch(
        "api.routers.chat.DocumentChatAgent"
    ) as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent.answer.return_value = "I need more information."
        mock_agent_cls.return_value = mock_agent

        response = test_client.post("/api/chat", json={
            "messages": [
                {"role": "user", "content": ""},
            ],
            "context": "Some context.",
        })

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "I need more information."


def test_chat_with_long_conversation_context(test_client, mock_services):
    """A chat request with many messages (long conversation history) and a large
    context string is passed correctly to the agent."""
    long_messages = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
        for i in range(20)
    ]
    long_context = "The document states: " + "Lorem ipsum. " * 500

    with patch(
        "api.routers.chat.DocumentChatAgent"
    ) as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent.answer.return_value = "Summary of the long context."
        mock_agent_cls.return_value = mock_agent

        response = test_client.post("/api/chat", json={
            "messages": long_messages,
            "context": long_context,
        })

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Summary of the long context."
    # Verify the full context was passed
    call_args = mock_agent.answer.call_args
    assert call_args.kwargs["context"] == long_context
    assert len(call_args.args[0]) == 20


def test_chat_with_agent_id_uses_agent_llm(test_client, mock_services):
    """When an agent_id is provided in the request, the endpoint resolves the
    agent and uses its model for the LLM, passing the agent's prompt."""
    from uuid import UUID

    import api.routers.chat as chat_module

    mock_services.agent_store = MagicMock()
    mock_services.config = MagicMock()

    # Create a mock agent returned by get_by_id
    mock_agent = MagicMock()
    mock_agent.model = "agent-specific-model"
    mock_agent.prompt = "You are a specialist."
    mock_services.agent_store.get_by_id.return_value = mock_agent

    with patch.object(
        chat_module, "DocumentChatAgent"
    ) as mock_agent_cls:
        with patch.object(
            chat_module, "create_llm_with_model"
        ) as mock_create_llm:
            mock_llm = MagicMock()
            mock_create_llm.return_value = mock_llm
            doc_agent = MagicMock()
            doc_agent.answer.return_value = "Agent response."
            mock_agent_cls.return_value = doc_agent

            agent_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
            response = test_client.post("/api/chat", json={
                "messages": [
                    {"role": "user", "content": "Hello"},
                ],
                "agent_id": str(agent_id),
            })

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Agent response."
    # Make sure the agent's LLM was created with the agent's model
    mock_create_llm.assert_called_once()
    assert mock_create_llm.call_args[0][1] == "agent-specific-model"
    # The agent_prompt should be passed
    call_args = doc_agent.answer.call_args
    assert call_args.kwargs.get("agent_prompt") == "You are a specialist."


def test_chat_with_invalid_agent_id_returns_422(test_client, mock_services):
    """When agent_id is not a valid UUID, a 422 is returned."""
    response = test_client.post("/api/chat", json={
        "messages": [{"role": "user", "content": "Hi"}],
        "agent_id": "not-a-uuid",
    })

    assert response.status_code == 422
    assert "Invalid agent_id" in response.json()["detail"]


def test_chat_with_nonexistent_agent_id_returns_404(test_client, mock_services):
    """When agent_id points to a non-existent agent, a 404 is returned."""
    from uuid import UUID

    mock_services.agent_store = MagicMock()
    mock_services.agent_store.get_by_id.return_value = None

    agent_id = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
    response = test_client.post("/api/chat", json={
        "messages": [{"role": "user", "content": "Hi"}],
        "agent_id": str(agent_id),
    })

    assert response.status_code == 404
    assert "Agent not found" in response.json()["detail"]


def test_chat_agent_system_error_propagates(test_client, mock_services):
    """When the DocumentChatAgent raises an unexpected runtime error, the
    exception propagates to the caller (the endpoint has no try/except around
    the agent.answer() call)."""
    with patch(
        "api.routers.chat.DocumentChatAgent"
    ) as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent.answer.side_effect = RuntimeError("LLM internal failure")
        mock_agent_cls.return_value = mock_agent

        with pytest.raises(RuntimeError, match="LLM internal failure"):
            test_client.post("/api/chat", json={
                "messages": [{"role": "user", "content": "Explain."}],
                "context": "Some context.",
            })


def test_chat_with_model_override(test_client, mock_services):
    """When a model name is provided (without agent_id), the endpoint creates
    an LLM with that model instead of the default."""
    import api.routers.chat as chat_module

    mock_services.config = MagicMock()

    with patch.object(
        chat_module, "DocumentChatAgent"
    ) as mock_agent_cls:
        with patch.object(
            chat_module, "create_llm_with_model"
        ) as mock_create_llm:
            mock_llm = MagicMock()
            mock_create_llm.return_value = mock_llm
            doc_agent = MagicMock()
            doc_agent.answer.return_value = "Model override response."
            mock_agent_cls.return_value = doc_agent

            response = test_client.post("/api/chat", json={
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "custom-model-v2",
            })

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Model override response."
    mock_create_llm.assert_called_once()
    assert mock_create_llm.call_args[0][1] == "custom-model-v2"
    # No agent prompt when using model override directly
    call_args = doc_agent.answer.call_args
    assert call_args.kwargs.get("agent_prompt") is None


def test_chat_with_agent_overrides_generation_params(test_client, mock_services):
    """When agent_id is provided and the body includes temperature/top_p/max_tokens,
    the request body values take priority over agent defaults."""
    from uuid import UUID

    import api.routers.chat as chat_module

    mock_services.agent_store = MagicMock()
    mock_services.config = MagicMock()

    # Agent with specific defaults
    mock_agent = MagicMock()
    mock_agent.model = "agent-model"
    mock_agent.prompt = "You are an assistant."
    mock_agent.temperature = 0.5
    mock_agent.top_p = 0.9
    mock_agent.max_tokens = 512
    mock_services.agent_store.get_by_id.return_value = mock_agent

    with patch.object(chat_module, "DocumentChatAgent") as mock_agent_cls:
        with patch.object(chat_module, "create_llm_with_model") as mock_create_llm:
            mock_create_llm.return_value = MagicMock()
            doc_agent = MagicMock()
            doc_agent.answer.return_value = "Params used."
            mock_agent_cls.return_value = doc_agent

            agent_id = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
            response = test_client.post("/api/chat", json={
                "messages": [{"role": "user", "content": "Hi"}],
                "agent_id": str(agent_id),
                "temperature": 0.8,   # overrides agent's 0.5
                "top_p": 0.95,        # overrides agent's 0.9
                "max_tokens": 2048,   # overrides agent's 512
            })

    assert response.status_code == 200
    call_args = doc_agent.answer.call_args
    params = call_args.kwargs.get("params")
    assert params.temperature == 0.8
    assert params.top_p == 0.95
    assert params.max_tokens == 2048
