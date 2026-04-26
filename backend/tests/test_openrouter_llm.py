"""Unit tests for OpenRouterLLM adapter.

Subject: infrastructure/llm/openrouter_llm.py
Scope:   HTTP request building, response parsing, 429 retry with fallback routing,
          proactive rate limiting, JSON format enforcement.
Out of scope:
  - Provider dispatch logic          → test_llm_factory.py
  - Generic LLM interface contracts  → covered by each provider's tests
Setup:   requests.post is patched at the module level; time.sleep is patched
          to keep tests fast.
"""
from unittest.mock import MagicMock, patch

import pytest
import requests

from infrastructure.config import OpenRouterConfig
from infrastructure.llm.openrouter_llm import OpenRouterLLM, OpenRouterRateLimiter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**kwargs) -> OpenRouterConfig:
    defaults = {
        "api_key": "test-key",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "timeout": 30,
        "max_retries": 3,
        "requests_per_minute": 10,
        "site_url": "https://example.com",
        "site_name": "TestApp",
    }
    defaults.update(kwargs)
    return OpenRouterConfig(**defaults)


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
    llm = OpenRouterLLM(config)

    mock_resp = _mock_response("hello")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        result = llm.generate("some prompt")

    assert result == "hello"
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args[1]
    payload = call_kwargs["json"]
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][0]["content"] == "some prompt"
    assert payload["stream"] is False


# ---------------------------------------------------------------------------
# Test 2: chat() sends system and user messages
# ---------------------------------------------------------------------------

def test_chat_sends_system_and_user_messages():
    """chat() should build a two-message payload with system first, user second."""
    config = _make_config()
    llm = OpenRouterLLM(config)

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
    """When format='json', the system prompt should include a JSON-only directive."""
    config = _make_config()
    llm = OpenRouterLLM(config)

    mock_resp = _mock_response('{"key": "value"}')

    with patch("requests.post", return_value=mock_resp) as mock_post:
        result = llm.chat("Extract data.", "Here is some text.", format="json")

    assert result == '{"key": "value"}'
    payload = mock_post.call_args[1]["json"]
    system_content = payload["messages"][0]["content"]
    assert "Respond with valid JSON only" in system_content
    assert "Do not include any explanation or markdown" in system_content
    assert "Extract data." in system_content


# ---------------------------------------------------------------------------
# Test 4: retry on HTTP 429
# ---------------------------------------------------------------------------

def test_retry_on_429():
    """A 429 response should trigger a retry; the next successful response is returned."""
    config = _make_config(max_retries=3)
    llm = OpenRouterLLM(config)

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
# Test 5: fallback routing — provider excluded after 429 with provider_name
# ---------------------------------------------------------------------------

def test_fallback_routing_excludes_provider_on_429():
    """If a 429 includes an upstream provider name, that provider is ignored on retries."""
    config = _make_config(max_retries=3)
    llm = OpenRouterLLM(config)

    resp_429 = MagicMock(spec=requests.Response)
    resp_429.status_code = 429
    resp_429.headers = {}
    resp_429.json.return_value = {
        "error": {"metadata": {"provider_name": "ProviderX"}}
    }
    resp_429.raise_for_status = MagicMock()

    resp_ok = _mock_response("routed fallback")

    with patch("requests.post", side_effect=[resp_429, resp_ok]) as mock_post:
        with patch("time.sleep"):
            result = llm.generate("prompt")

    assert result == "routed fallback"
    assert mock_post.call_count == 2
    # Second call should include ignored provider list
    second_payload = mock_post.call_args_list[1][1]["json"]
    assert second_payload["provider"]["ignore"] == ["ProviderX"]


# ---------------------------------------------------------------------------
# Test 6: rate limiter proactively throttles near the threshold
# ---------------------------------------------------------------------------

def test_rate_limiter_blocks_when_threshold_reached():
    """The sliding-window limiter should sleep when the request count reaches threshold."""
    limiter = OpenRouterRateLimiter(limit=10, threshold=2)

    # First two calls should succeed immediately
    limiter.acquire()
    limiter.acquire()

    # Third call should attempt to sleep because threshold=2
    with patch("time.sleep", side_effect=RuntimeError("throttled")):
        with pytest.raises(RuntimeError, match="throttled"):
            limiter.acquire()


# ---------------------------------------------------------------------------
# Test 7: HTTP 401 raises ValueError
# ---------------------------------------------------------------------------

def test_401_raises_value_error():
    """An authentication failure should raise a clear ValueError."""
    config = _make_config()
    llm = OpenRouterLLM(config)

    resp_401 = MagicMock(spec=requests.Response)
    resp_401.status_code = 401
    resp_401.headers = {}
    resp_401.raise_for_status = MagicMock()

    with patch("requests.post", return_value=resp_401):
        with pytest.raises(ValueError, match="Invalid or missing OpenRouter API key"):
            llm.generate("prompt")


# ---------------------------------------------------------------------------
# Test 8: HTTP 404 raises ValueError with model hint
# ---------------------------------------------------------------------------

def test_404_raises_value_error_with_model_hint():
    """A missing/deprecated model should raise a ValueError that names the model."""
    config = _make_config(model="deprecated-model")
    llm = OpenRouterLLM(config)

    resp_404 = MagicMock(spec=requests.Response)
    resp_404.status_code = 404
    resp_404.headers = {}
    resp_404.raise_for_status = MagicMock()

    with patch("requests.post", return_value=resp_404):
        with pytest.raises(ValueError, match="deprecated-model"):
            llm.generate("prompt")


# ---------------------------------------------------------------------------
# Test 9: Empty API key raises ValueError at construction time
# ---------------------------------------------------------------------------

def test_empty_api_key_raises():
    """Construction with an empty API key should fail fast with a descriptive message."""
    config = _make_config(api_key="")
    with pytest.raises(ValueError, match="OpenRouter API key required"):
        OpenRouterLLM(config)


# ---------------------------------------------------------------------------
# Test 10: headers include HTTP-Referer and X-Title when configured
# ---------------------------------------------------------------------------

def test_headers_include_referer_and_title():
    """Free-tier required headers should be sent when site_url and site_name are set."""
    config = _make_config(site_url="https://example.com", site_name="TestApp")
    llm = OpenRouterLLM(config)

    mock_resp = _mock_response("hi")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        llm.generate("prompt")

    headers = mock_post.call_args[1]["headers"]
    assert headers["HTTP-Referer"] == "https://example.com"
    assert headers["X-Title"] == "TestApp"
