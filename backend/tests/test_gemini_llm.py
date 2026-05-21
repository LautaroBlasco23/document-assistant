"""
Unit tests for GeminiLLM adapter.

Subject: infrastructure/llm/gemini_llm.py — GeminiLLM, GeminiRateLimiter
Scope:   generate(), chat(), _normalize_model(), _apply_params(), 429 retry, 401/404 errors, rate limiter.
Out of scope:
  - Actual Gemini API behavior       → integration tests
  - Rate limiter timing              → tested with mocked time
Setup:   Mocked requests.post responses.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from core.exceptions import RateLimitError
from infrastructure.config import GeminiConfig
from infrastructure.llm.gemini_llm import GeminiLLM, GeminiRateLimiter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(**kwargs) -> GeminiConfig:
    defaults = {
        "api_key": "ai-test-key",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.0-flash",
        "timeout": 30,
        "max_retries": 3,
        "max_retries_chat": 2,
        "requests_per_minute": 8,
    }
    defaults.update(kwargs)
    return GeminiConfig(**defaults)


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
# Constructor
# ---------------------------------------------------------------------------


def test_gemini_llm_requires_api_key():
    """GeminiLLM must raise ValueError when no API key is provided."""
    config = _make_config(api_key="")

    with pytest.raises(ValueError, match="Gemini API key required"):
        GeminiLLM(config)


def test_gemini_llm_strips_trailing_slash():
    """The base URL must have trailing slashes stripped."""
    config = _make_config(base_url="https://api.gemini.com/v1/")
    llm = GeminiLLM(config)

    assert llm._base_url == "https://api.gemini.com/v1"


# ---------------------------------------------------------------------------
# _normalize_model
# ---------------------------------------------------------------------------


def test_normalize_model_prepends_models_prefix():
    """Model IDs without 'models/' prefix must get it prepended."""
    config = _make_config()
    llm = GeminiLLM(config)

    assert llm._normalize_model("gemini-2.0-flash") == "models/gemini-2.0-flash"


def test_normalize_model_keeps_existing_prefix():
    """Model IDs already starting with 'models/' must be unchanged."""
    config = _make_config()
    llm = GeminiLLM(config)

    assert llm._normalize_model("models/gemini-2.0-flash") == "models/gemini-2.0-flash"


# ---------------------------------------------------------------------------
# generate()
# ---------------------------------------------------------------------------


def test_generate_returns_content():
    """generate() must return the response content."""
    config = _make_config()
    llm = GeminiLLM(config)

    mock_resp = _mock_response("hello from gemini")

    with patch("requests.post", return_value=mock_resp):
        result = llm.generate("some prompt")

    assert result == "hello from gemini"


def test_generate_sends_normalized_model():
    """generate() must send the model with 'models/' prefix."""
    config = _make_config()
    llm = GeminiLLM(config)

    mock_resp = _mock_response("ok")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        llm.generate("test prompt")

    payload = mock_post.call_args[1]["json"]
    assert payload["model"] == "models/gemini-2.0-flash"


def test_generate_applies_params():
    """generate() must apply temperature, top_p, and max_tokens when provided."""
    config = _make_config()
    llm = GeminiLLM(config)

    mock_resp = _mock_response("ok")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        from core.ports.llm import GenerationParams
        llm.generate("prompt", params=GenerationParams(temperature=0.5, top_p=0.9, max_tokens=512))

    payload = mock_post.call_args[1]["json"]
    assert payload["temperature"] == 0.5
    assert payload["top_p"] == 0.9
    assert payload["max_tokens"] == 512


# ---------------------------------------------------------------------------
# chat()
# ---------------------------------------------------------------------------


def test_chat_returns_content():
    """chat() must return the response content."""
    config = _make_config()
    llm = GeminiLLM(config)

    mock_resp = _mock_response("chat response")

    with patch("requests.post", return_value=mock_resp):
        result = llm.chat(system="You are helpful", user="Hello")

    assert result == "chat response"


def test_chat_sends_system_and_user():
    """chat() must send both system and user messages."""
    config = _make_config()
    llm = GeminiLLM(config)

    mock_resp = _mock_response("ok")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        llm.chat(system="Be concise", user="What is 2+2?")

    payload = mock_post.call_args[1]["json"]
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["role"] == "user"


def test_chat_json_format_appends_instruction():
    """When format='json', chat() must append JSON-only instruction to system."""
    config = _make_config()
    llm = GeminiLLM(config)

    mock_resp = _mock_response("{}")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        llm.chat(system="Extract data", user="text", format="json")

    payload = mock_post.call_args[1]["json"]
    assert "valid JSON only" in payload["messages"][0]["content"]


def test_chat_applies_params():
    """chat() must apply generation params."""
    config = _make_config()
    llm = GeminiLLM(config)

    mock_resp = _mock_response("ok")

    with patch("requests.post", return_value=mock_resp) as mock_post:
        from core.ports.llm import GenerationParams
        llm.chat("sys", "user", params=GenerationParams(temperature=0.3))

    payload = mock_post.call_args[1]["json"]
    assert payload["temperature"] == 0.3


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_401_raises_value_error():
    """A 401 response must raise ValueError with a clear message."""
    config = _make_config()
    llm = GeminiLLM(config)

    resp = MagicMock(spec=requests.Response)
    resp.status_code = 401

    with patch("requests.post", return_value=resp):
        with pytest.raises(ValueError, match="Invalid or missing Gemini API key"):
            llm.generate("prompt")


def test_404_raises_value_error_with_model_info():
    """A 404 response must raise ValueError mentioning the model."""
    config = _make_config()
    llm = GeminiLLM(config)

    resp = MagicMock(spec=requests.Response)
    resp.status_code = 404

    with patch("requests.post", return_value=resp):
        with pytest.raises(ValueError, match="gemini-2.0-flash"):
            llm.generate("prompt")


def test_429_retries_and_raises_rate_limit_error():
    """Repeated 429 responses must eventually raise RateLimitError."""
    config = _make_config(max_retries=2)
    llm = GeminiLLM(config)

    resp = MagicMock(spec=requests.Response)
    resp.status_code = 429
    resp.headers = {"Retry-After": "0"}

    with patch("requests.post", return_value=resp):
        with patch("infrastructure.llm.gemini_llm.time.sleep"):
            with pytest.raises(RateLimitError) as exc_info:
                llm.generate("prompt")

            assert exc_info.value.provider == "gemini"


def test_429_respects_retry_after_header():
    """The Retry-After header value must be used for the RateLimitError."""
    config = _make_config(max_retries=2)
    llm = GeminiLLM(config)

    resp = MagicMock(spec=requests.Response)
    resp.status_code = 429
    resp.headers = {"Retry-After": "30"}

    with patch("requests.post", return_value=resp):
        with patch("infrastructure.llm.gemini_llm.time.sleep"):
            with pytest.raises(RateLimitError) as exc_info:
                llm.generate("prompt")

            assert exc_info.value.retry_after == 30.0


# ---------------------------------------------------------------------------
# GeminiRateLimiter
# ---------------------------------------------------------------------------


def test_rate_limiter_allows_under_threshold():
    """Requests under the threshold must pass without blocking."""
    limiter = GeminiRateLimiter(limit=10, threshold=5)

    for _ in range(5):
        limiter.acquire()


def test_rate_limiter_blocks_over_threshold():
    """Requests over the threshold must trigger throttling (sleep is called)."""
    limiter = GeminiRateLimiter(limit=10, threshold=2)

    limiter.acquire()
    limiter.acquire()

    import infrastructure.llm.gemini_llm as gemini_module
    original_sleep = gemini_module.time.sleep
    sleep_calls = []

    def mock_sleep(duration):
        sleep_calls.append(duration)
        limiter._timestamps.clear()

    gemini_module.time.sleep = mock_sleep
    try:
        limiter.acquire()
        assert len(sleep_calls) >= 1
    finally:
        gemini_module.time.sleep = original_sleep


def test_rate_limiter_default_threshold():
    """The default threshold should be limit - 2 (minimum 1)."""
    limiter = GeminiRateLimiter(limit=8)
    assert limiter._threshold == 6
