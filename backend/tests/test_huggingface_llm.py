"""Unit tests for HuggingFaceLLM adapter.

Subject: infrastructure/llm/huggingface_llm.py
Scope:   HTTP request building, response parsing, 503 cold-start retry,
          x-wait-for-model header, 429 retry, timeout handling.
Out of scope:
  - Provider dispatch logic          → test_llm_factory.py
  - Generic LLM interface contracts  → covered by each provider's tests
Setup:   requests.post is patched at the module level; time.sleep is patched
          to keep tests fast.
"""
from unittest.mock import MagicMock, patch

import pytest
import requests

from infrastructure.config import HuggingFaceConfig
from infrastructure.llm.huggingface_llm import HuggingFaceLLM

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**kwargs) -> HuggingFaceConfig:
    defaults = {
        "api_key": "hf_testtoken",
        "base_url": "https://router.huggingface.co/v1",
        "model": "Qwen/Qwen2.5-72B-Instruct",
        "timeout": 30,
        "max_retries": 3,
        "wait_for_model": True,
    }
    defaults.update(kwargs)
    return HuggingFaceConfig(**defaults)


def _mock_response(content: str, status_code: int = 200, headers: dict | None = None) -> MagicMock:
    """Create a mock requests.Response for a non-streaming call."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    resp.raise_for_status = MagicMock()
    resp.headers = headers or {}
    return resp


# ---------------------------------------------------------------------------
# Test 1: generate() returns content
# ---------------------------------------------------------------------------

def test_generate_returns_content():
    """A plain prompt should return the assistant's message content."""
    config = _make_config()
    llm = HuggingFaceLLM(config)

    mock_resp = _mock_response("hello")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        result = llm.generate("some prompt")

    assert result == "hello"
    mock_post.assert_called_once()
    payload = mock_post.call_args[1]["json"]
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][0]["content"] == "some prompt"
    assert payload["stream"] is False


# ---------------------------------------------------------------------------
# Test 2: 503 cold-start retry
# ---------------------------------------------------------------------------

def test_retry_on_503_cold_start():
    """A 503 (model loading) should be retried after a fixed sleep."""
    config = _make_config(max_retries=3)
    llm = HuggingFaceLLM(config)

    resp_503 = MagicMock(spec=requests.Response)
    resp_503.status_code = 503
    resp_503.headers = {}
    resp_503.raise_for_status = MagicMock()

    resp_ok = _mock_response("loaded")

    with patch("requests.post", side_effect=[resp_503, resp_ok]) as mock_post:
        with patch("time.sleep"):
            result = llm.generate("prompt")

    assert result == "loaded"
    assert mock_post.call_count == 2


# ---------------------------------------------------------------------------
# Test 3: x-wait-for-model header present when wait_for_model=True
# ---------------------------------------------------------------------------

def test_wait_for_model_header_present():
    """When config.wait_for_model is True, the x-wait-for-model header should be sent."""
    config = _make_config(wait_for_model=True)
    llm = HuggingFaceLLM(config)

    mock_resp = _mock_response("hi")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        llm.generate("prompt")

    headers = mock_post.call_args[1]["headers"]
    assert headers.get("x-wait-for-model") == "true"


# ---------------------------------------------------------------------------
# Test 4: x-wait-for-model header absent when wait_for_model=False
# ---------------------------------------------------------------------------

def test_wait_for_model_header_absent():
    """When config.wait_for_model is False, the x-wait-for-model header should not be sent."""
    config = _make_config(wait_for_model=False)
    llm = HuggingFaceLLM(config)

    mock_resp = _mock_response("hi")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        llm.generate("prompt")

    headers = mock_post.call_args[1]["headers"]
    assert "x-wait-for-model" not in headers


# ---------------------------------------------------------------------------
# Test 5: timeout is passed to requests.post
# ---------------------------------------------------------------------------

def test_timeout_passed_to_requests():
    """The configured timeout should be forwarded to the HTTP request."""
    config = _make_config(timeout=42)
    llm = HuggingFaceLLM(config)

    mock_resp = _mock_response("hi")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        llm.generate("prompt")

    assert mock_post.call_args[1]["timeout"] == 42


# ---------------------------------------------------------------------------
# Test 6: HTTP 401 raises ValueError
# ---------------------------------------------------------------------------

def test_401_raises_value_error():
    """An authentication failure should raise a clear ValueError."""
    config = _make_config()
    llm = HuggingFaceLLM(config)

    resp_401 = MagicMock(spec=requests.Response)
    resp_401.status_code = 401
    resp_401.headers = {}
    resp_401.raise_for_status = MagicMock()

    with patch("requests.post", return_value=resp_401):
        with pytest.raises(ValueError, match="Invalid or missing HuggingFace API key"):
            llm.generate("prompt")


# ---------------------------------------------------------------------------
# Test 7: Empty API key raises ValueError at construction time
# ---------------------------------------------------------------------------

def test_empty_api_key_raises():
    """Construction with an empty API key should fail fast with a descriptive message."""
    config = _make_config(api_key="")
    with pytest.raises(ValueError, match="HuggingFace API key required"):
        HuggingFaceLLM(config)


# ---------------------------------------------------------------------------
# Test 8: chat() with format="json" appends JSON instruction
# ---------------------------------------------------------------------------

def test_chat_with_json_format():
    """When format='json', the system prompt should include a JSON-only directive."""
    config = _make_config()
    llm = HuggingFaceLLM(config)

    mock_resp = _mock_response('{"key": "value"}')

    with patch("requests.post", return_value=mock_resp) as mock_post:
        result = llm.chat("Extract data.", "Here is some text.", format="json")

    assert result == '{"key": "value"}'
    payload = mock_post.call_args[1]["json"]
    system_content = payload["messages"][0]["content"]
    assert "Respond with valid JSON only" in system_content


# ---------------------------------------------------------------------------
# Test 9: 429 triggers exponential backoff retry
# ---------------------------------------------------------------------------

def test_retry_on_429_with_exponential_backoff():
    """A 429 response should trigger retries with exponential backoff."""
    config = _make_config(max_retries=3)
    llm = HuggingFaceLLM(config)

    resp_429 = MagicMock(spec=requests.Response)
    resp_429.status_code = 429
    resp_429.headers = {}
    resp_429.raise_for_status = MagicMock()

    resp_ok = _mock_response("success")

    with patch("requests.post", side_effect=[resp_429, resp_ok]) as mock_post:
        with patch("time.sleep") as mock_sleep:
            result = llm.generate("prompt")

    assert result == "success"
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once()
