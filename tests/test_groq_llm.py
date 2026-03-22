"""Unit tests for GroqLLM adapter."""
import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from infrastructure.config import GroqConfig
from infrastructure.llm.groq_llm import GroqLLM

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**kwargs) -> GroqConfig:
    defaults = {
        "api_key": "test-key",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "mixtral-8x7b-32768",
        "timeout": 30,
        "max_retries": 3,
    }
    defaults.update(kwargs)
    return GroqConfig(**defaults)


def _mock_response(content: str, status_code: int = 200) -> MagicMock:
    """Create a mock requests.Response for a non-streaming call."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    resp.raise_for_status = MagicMock()
    resp.headers = {}
    return resp


# ---------------------------------------------------------------------------
# Test 1: generate() returns content
# ---------------------------------------------------------------------------

def test_generate_returns_content():
    config = _make_config()
    llm = GroqLLM(config)

    mock_resp = _mock_response("hello")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        result = llm.generate("some prompt")

    assert result == "hello"
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    payload = call_kwargs[1]["json"]
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][0]["content"] == "some prompt"
    assert payload["stream"] is False


# ---------------------------------------------------------------------------
# Test 2: chat() sends system and user messages
# ---------------------------------------------------------------------------

def test_chat_sends_system_and_user_messages():
    config = _make_config()
    llm = GroqLLM(config)

    mock_resp = _mock_response("answer text")

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
# Test 3: chat() with format="json" appends JSON instruction to system prompt
# ---------------------------------------------------------------------------

def test_chat_with_json_format():
    config = _make_config()
    llm = GroqLLM(config)

    mock_resp = _mock_response('{"key": "value"}')

    with patch("requests.post", return_value=mock_resp) as mock_post:
        result = llm.chat("Extract data.", "Here is some text.", format="json")

    assert result == '{"key": "value"}'
    payload = mock_post.call_args[1]["json"]
    system_content = payload["messages"][0]["content"]
    assert "Respond with valid JSON only" in system_content
    assert "Do not include any explanation or markdown" in system_content
    # Original system prompt is still present
    assert "Extract data." in system_content


# ---------------------------------------------------------------------------
# Test 4: chat_stream() yields tokens from SSE lines
# ---------------------------------------------------------------------------

def test_chat_stream_yields_tokens():
    config = _make_config()
    llm = GroqLLM(config)

    # Build SSE lines as bytes (as iter_lines would return)
    sse_lines = [
        b'data: ' + json.dumps({"choices": [{"delta": {"content": "Hello"}}]}).encode(),
        b'data: ' + json.dumps({"choices": [{"delta": {"content": " world"}}]}).encode(),
        b'data: [DONE]',
    ]

    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.headers = {}
    mock_resp.iter_lines.return_value = iter(sse_lines)

    with patch("requests.post", return_value=mock_resp):
        tokens = list(llm.chat_stream("system", "user"))

    assert tokens == ["Hello", " world"]


# ---------------------------------------------------------------------------
# Test 5: retry on HTTP 429
# ---------------------------------------------------------------------------

def test_retry_on_429():
    config = _make_config(max_retries=3)
    llm = GroqLLM(config)

    resp_429 = MagicMock(spec=requests.Response)
    resp_429.status_code = 429
    resp_429.headers = {"Retry-After": "0"}
    resp_429.raise_for_status = MagicMock()

    resp_ok = _mock_response("success after retry")

    with patch("requests.post", side_effect=[resp_429, resp_ok]) as mock_post:
        with patch("time.sleep"):
            result = llm.generate("prompt")

    assert result == "success after retry"
    assert mock_post.call_count == 2


# ---------------------------------------------------------------------------
# Test 6: HTTP 401 raises ValueError
# ---------------------------------------------------------------------------

def test_401_raises_value_error():
    config = _make_config()
    llm = GroqLLM(config)

    resp_401 = MagicMock(spec=requests.Response)
    resp_401.status_code = 401
    resp_401.headers = {}
    resp_401.raise_for_status = MagicMock()

    with patch("requests.post", return_value=resp_401):
        with pytest.raises(ValueError, match="Invalid or missing Groq API key"):
            llm.generate("prompt")


# ---------------------------------------------------------------------------
# Test 7: Empty API key raises ValueError at construction time
# ---------------------------------------------------------------------------

def test_empty_api_key_raises():
    config = _make_config(api_key="")
    with pytest.raises(ValueError, match="Groq API key required"):
        GroqLLM(config)
