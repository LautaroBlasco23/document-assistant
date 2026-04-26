"""Unit tests for OllamaLLM adapter.

Subject: infrastructure/llm/ollama.py
Scope:   HTTP request building for generate/chat, response parsing,
          model-not-found (404) handling, connection-refused handling.
Out of scope:
  - Provider dispatch logic          → test_llm_factory.py
  - Generic LLM interface contracts  → covered by each provider's tests
Setup:   requests.post and requests.get are patched at the module level.
"""
from unittest.mock import MagicMock, patch

import pytest
import requests

from infrastructure.config import OllamaConfig
from infrastructure.llm.ollama import OllamaClient, OllamaLLM

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**kwargs) -> OllamaConfig:
    defaults = {
        "base_url": "http://localhost:11434",
        "generation_model": "llama3.2",
        "timeout": 300,
    }
    defaults.update(kwargs)
    return OllamaConfig(**defaults)


def _mock_generate_response(content: str, status_code: int = 200) -> MagicMock:
    """Create a mock requests.Response for /api/generate."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = {"response": content}
    resp.raise_for_status = MagicMock()
    return resp


def _mock_chat_response(content: str, status_code: int = 200) -> MagicMock:
    """Create a mock requests.Response for /api/chat."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = {"message": {"content": content}}
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# Test 1: generate() returns content
# ---------------------------------------------------------------------------

def test_generate_returns_content():
    """A plain prompt should return the 'response' field from Ollama's /api/generate."""
    config = _make_config()
    llm = OllamaLLM(config)

    mock_resp = _mock_generate_response("hello")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        result = llm.generate("some prompt")

    assert result == "hello"
    mock_post.assert_called_once()
    payload = mock_post.call_args[1]["json"]
    assert payload["model"] == "llama3.2"
    assert payload["prompt"] == "some prompt"
    assert payload["stream"] is False


# ---------------------------------------------------------------------------
# Test 2: chat() sends system and user messages
# ---------------------------------------------------------------------------

def test_chat_sends_system_and_user_messages():
    """chat() should POST to /api/chat with a messages array and return the assistant content."""
    config = _make_config()
    llm = OllamaLLM(config)

    mock_resp = _mock_chat_response("answer text")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        result = llm.chat("You are a helpful assistant.", "What is 2+2?")

    assert result == "answer text"
    payload = mock_post.call_args[1]["json"]
    messages = payload["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "You are a helpful assistant."
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "What is 2+2?"


# ---------------------------------------------------------------------------
# Test 3: chat() with format="json" includes format field
# ---------------------------------------------------------------------------

def test_chat_with_json_format():
    """When format='json', the payload should include a 'format' key set to 'json'."""
    config = _make_config()
    llm = OllamaLLM(config)

    mock_resp = _mock_chat_response('{"key": "value"}')

    with patch("requests.post", return_value=mock_resp) as mock_post:
        result = llm.chat("Extract data.", "Here is some text.", format="json")

    assert result == '{"key": "value"}'
    payload = mock_post.call_args[1]["json"]
    assert payload.get("format") == "json"


# ---------------------------------------------------------------------------
# Test 4: model not found (404) raises HTTPError
# ---------------------------------------------------------------------------

def test_model_not_found_raises():
    """A 404 from Ollama should propagate as an HTTPError via raise_for_status."""
    config = _make_config()
    llm = OllamaLLM(config)

    resp_404 = MagicMock(spec=requests.Response)
    resp_404.status_code = 404
    resp_404.raise_for_status.side_effect = requests.HTTPError("404 Client Error")

    with patch("requests.post", return_value=resp_404):
        with pytest.raises(requests.HTTPError):
            llm.generate("prompt")


# ---------------------------------------------------------------------------
# Test 5: connection refused raises ConnectionError
# ---------------------------------------------------------------------------

def test_connection_refused_raises():
    """If Ollama is not running, requests.post should raise ConnectionError."""
    config = _make_config()
    llm = OllamaLLM(config)

    with patch("requests.post", side_effect=requests.ConnectionError("Connection refused")):
        with pytest.raises(requests.ConnectionError, match="Connection refused"):
            llm.generate("prompt")


# ---------------------------------------------------------------------------
# Test 6: OllamaClient.is_healthy returns True on 200
# ---------------------------------------------------------------------------

def test_client_is_healthy_true():
    """is_healthy should return True when /api/tags responds with 200."""
    config = _make_config()
    client = OllamaClient(config)

    resp = MagicMock(spec=requests.Response)
    resp.status_code = 200

    with patch("requests.get", return_value=resp):
        assert client.is_healthy() is True


# ---------------------------------------------------------------------------
# Test 7: OllamaClient.is_healthy returns False on ConnectionError
# ---------------------------------------------------------------------------

def test_client_is_healthy_false_on_connection_error():
    """is_healthy should return False when Ollama is unreachable."""
    config = _make_config()
    client = OllamaClient(config)

    with patch("requests.get", side_effect=requests.ConnectionError):
        assert client.is_healthy() is False


# ---------------------------------------------------------------------------
# Test 8: OllamaClient.list_models returns model names
# ---------------------------------------------------------------------------

def test_client_list_models():
    """list_models should extract model names from /api/tags."""
    config = _make_config()
    client = OllamaClient(config)

    resp = MagicMock(spec=requests.Response)
    resp.status_code = 200
    resp.json.return_value = {"models": [{"name": "llama3.2"}, {"name": "mistral"}]}
    resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=resp):
        models = client.list_models()

    assert models == ["llama3.2", "mistral"]
