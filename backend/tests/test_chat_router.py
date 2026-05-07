"""
Unit tests for the chat router (/api/chat).

Subject: api/routers/chat.py
Scope:   POST /api/chat — document Q&A with conversation history.
Out of scope:
  - DocumentChatAgent internals            → test_document_chat_agent.py
  - LLM.generate() behavior                → test_base_agent.py
  - Authentication token validation        → test_api_auth.py
Setup:   FastAPI TestClient with mocked DocumentChatAgent and resolve_llm_for_agent.
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
from core.ports.llm import GenerationParams

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
    services = MagicMock()
    services.llm = MagicMock()
    return services


@pytest.fixture
def test_client(mock_services):
    app = FastAPI()
    app.include_router(chat_router.router, prefix="/api")
    app.dependency_overrides[get_services_dep] = lambda: mock_services
    app.dependency_overrides[get_current_user] = _make_user
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /api/chat — basic cases
# ---------------------------------------------------------------------------


def test_chat_with_valid_context_returns_reply(test_client, mock_services):
    """A valid chat request with context must return the agent's reply."""
    mock_llm = MagicMock()
    with patch("api.routers.chat.resolve_llm_for_agent", return_value=(mock_llm, None, None)), \
         patch("api.routers.chat.DocumentChatAgent") as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent.answer.return_value = "The answer is 42."
        mock_agent_cls.return_value = mock_agent

        response = test_client.post("/api/chat", json={
            "messages": [{"role": "user", "content": "What is the answer?"}],
            "context": "Document says the answer is 42.",
        })

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "The answer is 42."
    mock_agent.answer.assert_called_once()
    assert mock_agent.answer.call_args.kwargs.get("context") == "Document says the answer is 42."


def test_chat_empty_messages_handled(test_client, mock_services):
    """A chat request with an empty messages list is accepted and forwarded to the agent."""
    mock_llm = MagicMock()
    with patch("api.routers.chat.resolve_llm_for_agent", return_value=(mock_llm, None, None)), \
         patch("api.routers.chat.DocumentChatAgent") as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent.answer.return_value = "Please ask a question."
        mock_agent_cls.return_value = mock_agent

        response = test_client.post("/api/chat", json={
            "messages": [],
            "context": "Some document context.",
        })

    assert response.status_code == 200
    assert response.json()["reply"] == "Please ask a question."
    assert mock_agent.answer.call_args.args[0] == []


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


def test_chat_with_empty_message_content(test_client, mock_services):
    """A message with empty string content is accepted and forwarded."""
    mock_llm = MagicMock()
    with patch("api.routers.chat.resolve_llm_for_agent", return_value=(mock_llm, None, None)), \
         patch("api.routers.chat.DocumentChatAgent") as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent.answer.return_value = "I need more information."
        mock_agent_cls.return_value = mock_agent

        response = test_client.post("/api/chat", json={
            "messages": [{"role": "user", "content": ""}],
            "context": "Some context.",
        })

    assert response.status_code == 200
    assert response.json()["reply"] == "I need more information."


def test_chat_with_long_conversation_context(test_client, mock_services):
    """Many messages and a large context string are passed correctly to the agent."""
    long_messages = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
        for i in range(20)
    ]
    long_context = "The document states: " + "Lorem ipsum. " * 500

    mock_llm = MagicMock()
    with patch("api.routers.chat.resolve_llm_for_agent", return_value=(mock_llm, None, None)), \
         patch("api.routers.chat.DocumentChatAgent") as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent.answer.return_value = "Summary of the long context."
        mock_agent_cls.return_value = mock_agent

        response = test_client.post("/api/chat", json={
            "messages": long_messages,
            "context": long_context,
        })

    assert response.status_code == 200
    assert response.json()["reply"] == "Summary of the long context."
    call_args = mock_agent.answer.call_args
    assert call_args.kwargs["context"] == long_context
    assert len(call_args.args[0]) == 20


# ---------------------------------------------------------------------------
# Agent-id and model-override paths
# ---------------------------------------------------------------------------


def test_chat_with_agent_id_uses_agent_llm(test_client, mock_services):
    """When agent_id is provided, resolve_llm_for_agent is called with that UUID
    and the returned LLM and prompt are forwarded to DocumentChatAgent."""
    mock_llm = MagicMock()
    agent_prompt = "You are a specialist."
    agent_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")

    with patch(
        "api.routers.chat.resolve_llm_for_agent", return_value=(mock_llm, agent_prompt, None)
    ) as mock_resolve, \
         patch("api.routers.chat.DocumentChatAgent") as mock_agent_cls:
        doc_agent = MagicMock()
        doc_agent.answer.return_value = "Agent response."
        mock_agent_cls.return_value = doc_agent

        response = test_client.post("/api/chat", json={
            "messages": [{"role": "user", "content": "Hello"}],
            "agent_id": str(agent_id),
        })

    assert response.status_code == 200
    assert response.json()["reply"] == "Agent response."

    mock_resolve.assert_called_once()
    _, called_agent_id = mock_resolve.call_args.args[:2]
    assert called_agent_id == agent_id

    call_args = doc_agent.answer.call_args
    assert call_args.kwargs.get("agent_prompt") == agent_prompt


def test_chat_with_invalid_agent_id_returns_422(test_client, mock_services):
    """When agent_id is not a valid UUID, a 422 is returned."""
    response = test_client.post("/api/chat", json={
        "messages": [{"role": "user", "content": "Hi"}],
        "agent_id": "not-a-uuid",
    })
    assert response.status_code == 422
    assert "Invalid agent_id" in response.json()["detail"]


def test_chat_with_nonexistent_agent_id_returns_404(test_client, mock_services):
    """When resolve_llm_for_agent raises ValueError (agent not found), a 404 is returned."""
    agent_id = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")

    with patch(
        "api.routers.chat.resolve_llm_for_agent",
        side_effect=ValueError(f"Agent {agent_id} not found"),
    ):
        response = test_client.post("/api/chat", json={
            "messages": [{"role": "user", "content": "Hi"}],
            "agent_id": str(agent_id),
        })

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_chat_agent_system_error_propagates(test_client, mock_services):
    """When DocumentChatAgent.answer raises RuntimeError, a 500 is returned."""
    mock_llm = MagicMock()
    with patch("api.routers.chat.resolve_llm_for_agent", return_value=(mock_llm, None, None)), \
         patch("api.routers.chat.DocumentChatAgent") as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent.answer.side_effect = RuntimeError("LLM internal failure")
        mock_agent_cls.return_value = mock_agent

        with pytest.raises(RuntimeError, match="LLM internal failure"):
            test_client.post("/api/chat", json={
                "messages": [{"role": "user", "content": "Explain."}],
                "context": "Some context.",
            })


def test_chat_with_model_override(test_client, mock_services):
    """When a model name is provided (without agent_id), resolve_llm_for_agent is called
    with model_override set to that model name."""
    mock_llm = MagicMock()

    with patch(
        "api.routers.chat.resolve_llm_for_agent", return_value=(mock_llm, None, None)
    ) as mock_resolve, \
         patch("api.routers.chat.DocumentChatAgent") as mock_agent_cls:
        doc_agent = MagicMock()
        doc_agent.answer.return_value = "Model override response."
        mock_agent_cls.return_value = doc_agent

        response = test_client.post("/api/chat", json={
            "messages": [{"role": "user", "content": "Hello"}],
            "model": "custom-model-v2",
        })

    assert response.status_code == 200
    assert response.json()["reply"] == "Model override response."

    mock_resolve.assert_called_once()
    assert mock_resolve.call_args.kwargs.get("model_override") == "custom-model-v2"

    call_args = doc_agent.answer.call_args
    assert call_args.kwargs.get("agent_prompt") is None


def test_chat_with_agent_overrides_generation_params(test_client, mock_services):
    """Request body temperature/top_p/max_tokens override the agent defaults."""
    mock_llm = MagicMock()
    agent_defaults = GenerationParams(temperature=0.5, top_p=0.9, max_tokens=512)
    agent_id = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")

    with patch(
        "api.routers.chat.resolve_llm_for_agent",
        return_value=(mock_llm, "You are an assistant.", agent_defaults),
    ), \
         patch("api.routers.chat.DocumentChatAgent") as mock_agent_cls:
        doc_agent = MagicMock()
        doc_agent.answer.return_value = "Params used."
        mock_agent_cls.return_value = doc_agent

        response = test_client.post("/api/chat", json={
            "messages": [{"role": "user", "content": "Hi"}],
            "agent_id": str(agent_id),
            "temperature": 0.8,
            "top_p": 0.95,
            "max_tokens": 2048,
        })

    assert response.status_code == 200
    params = doc_agent.answer.call_args.kwargs.get("params")
    assert params.temperature == 0.8
    assert params.top_p == 0.95
    assert params.max_tokens == 2048


def test_chat_agent_params_fallback_to_agent_defaults(test_client, mock_services):
    """When no override params in body, the agent defaults from resolve_llm_for_agent are used."""
    mock_llm = MagicMock()
    agent_defaults = GenerationParams(temperature=0.3, top_p=0.8, max_tokens=1024)
    agent_id = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")

    with patch(
        "api.routers.chat.resolve_llm_for_agent",
        return_value=(mock_llm, None, agent_defaults),
    ), \
         patch("api.routers.chat.DocumentChatAgent") as mock_agent_cls:
        doc_agent = MagicMock()
        doc_agent.answer.return_value = "Defaults used."
        mock_agent_cls.return_value = doc_agent

        response = test_client.post("/api/chat", json={
            "messages": [{"role": "user", "content": "Hi"}],
            "agent_id": str(agent_id),
        })

    assert response.status_code == 200
    params = doc_agent.answer.call_args.kwargs.get("params")
    assert params.temperature == 0.3
    assert params.top_p == 0.8
    assert params.max_tokens == 1024
