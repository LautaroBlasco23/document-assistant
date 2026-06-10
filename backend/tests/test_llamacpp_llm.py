"""
Unit tests for LlamaCppLLM adapter.

Subject: infrastructure/llm/llamacpp_llm.py — LlamaCppLLM
Scope:   generate(), chat(), _apply_params(), connection error handling.
Out of scope:
  - Actual llama-server behavior     → integration tests
Setup:   Mocked requests.post responses.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from infrastructure.config import LlamaCppConfig
from infrastructure.llm.llamacpp_llm import LlamaCppLLM

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(**kwargs) -> LlamaCppConfig:
    defaults = {
        "base_url": "http://localhost:8080/v1",
        "model": "local-model",
        "timeout": 30,
    }
    defaults.update(kwargs)
    return LlamaCppConfig(**defaults)


def _mock_response(content: str, status_code: int = 200) -> MagicMock:
    """Create a mock requests.Response for a non-streaming call."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


def test_llamacpp_strips_trailing_slash():
    """The base URL must have trailing slashes stripped."""
    config = _make_config(base_url="http://localhost:8080/v1/")
    llm = LlamaCppLLM(config)

    assert llm._base_url == "http://localhost:8080/v1"


def test_llamacpp_stores_model():
    """The model name must be stored from config."""
    config = _make_config(model="my-gguf-model")
    llm = LlamaCppLLM(config)

    assert llm._model == "my-gguf-model"


# ---------------------------------------------------------------------------
# generate()
# ---------------------------------------------------------------------------


def test_generate_returns_content():
    """generate() must return the response content."""
    config = _make_config()
    llm = LlamaCppLLM(config)

    mock_resp = _mock_response("hello from llama")

    with patch("requests.post", return_value=mock_resp):
        result = llm.generate("some prompt")

    assert result == "hello from llama"


def test_generate_sends_model():
    """generate() must send the configured model name."""
    config = _make_config(model="my-model")
    llm = LlamaCppLLM(config)

    mock_resp = _mock_response("ok")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        llm.generate("test prompt")

    payload = mock_post.call_args[1]["json"]
    assert payload["model"] == "my-model"


def test_generate_applies_params():
    """generate() must apply temperature, top_p, and max_tokens when provided."""
    config = _make_config()
    llm = LlamaCppLLM(config)

    mock_resp = _mock_response("ok")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        from core.ports.llm import GenerationParams
        llm.generate("prompt", params=GenerationParams(temperature=0.5, top_p=0.9, max_tokens=512))

    payload = mock_post.call_args[1]["json"]
    assert payload["temperature"] == 0.5
    assert payload["top_p"] == 0.9
    assert payload["max_tokens"] == 512


def test_generate_no_auth_header():
    """generate() must not send an Authorization header."""
    config = _make_config()
    llm = LlamaCppLLM(config)

    mock_resp = _mock_response("ok")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        llm.generate("prompt")

    headers = mock_post.call_args[1]["headers"]
    assert "Authorization" not in headers


# ---------------------------------------------------------------------------
# chat()
# ---------------------------------------------------------------------------


def test_chat_returns_content():
    """chat() must return the response content."""
    config = _make_config()
    llm = LlamaCppLLM(config)

    mock_resp = _mock_response("chat response")

    with patch("requests.post", return_value=mock_resp):
        result = llm.chat(system="You are helpful", user="Hello")

    assert result == "chat response"


def test_chat_sends_system_and_user():
    """chat() must send both system and user messages."""
    config = _make_config()
    llm = LlamaCppLLM(config)

    mock_resp = _mock_response("ok")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        llm.chat(system="Be concise", user="What is 2+2?")

    payload = mock_post.call_args[1]["json"]
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["role"] == "user"


def test_chat_json_format_appends_instruction():
    """When format='json', chat() must append JSON-only instruction to system."""
    config = _make_config()
    llm = LlamaCppLLM(config)

    mock_resp = _mock_response("{}")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        llm.chat(system="Extract data", user="text", format="json")

    payload = mock_post.call_args[1]["json"]
    assert "valid JSON only" in payload["messages"][0]["content"]


def test_chat_applies_params():
    """chat() must apply generation params."""
    config = _make_config()
    llm = LlamaCppLLM(config)

    mock_resp = _mock_response("ok")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        from core.ports.llm import GenerationParams
        llm.chat("sys", "user", params=GenerationParams(temperature=0.3))

    payload = mock_post.call_args[1]["json"]
    assert payload["temperature"] == 0.3


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_connection_error_retries_once():
    """A ConnectionError must be retried once, then re-raised."""
    config = _make_config()
    llm = LlamaCppLLM(config)

    with patch("requests.post") as mock_post:
        mock_post.side_effect = requests.ConnectionError("refused")

        with patch("infrastructure.llm.llamacpp_llm.time.sleep"):
            with pytest.raises(requests.ConnectionError):
                llm.generate("prompt")

    assert mock_post.call_count == 2


def test_http_error_raises():
    """A non-connection HTTP error must be raised after raise_for_status."""
    config = _make_config()
    llm = LlamaCppLLM(config)

    resp = MagicMock(spec=requests.Response)
    resp.status_code = 500
    resp.raise_for_status.side_effect = requests.HTTPError("500 Server Error")

    with patch("requests.post", return_value=resp):
        with pytest.raises(requests.HTTPError):
            llm.generate("prompt")
