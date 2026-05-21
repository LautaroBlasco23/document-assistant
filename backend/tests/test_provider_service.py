"""
Unit tests for the provider service (connection testing and model fetching).

Subject: application/services/provider_service.py — test_provider()
Scope:   Provider connection testing for groq, openrouter, nvidia, gemini, huggingface,
         and unknown providers.
Out of scope:
  - Model fetcher internals            → test_model_fetcher.py
  - LLM provider behavior              → respective LLM provider tests
Setup:   Mocked model fetcher functions.
"""

from unittest.mock import MagicMock, patch

from infrastructure.config import AppConfig

from application.services.provider_service import test_provider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config():
    """Return a minimal AppConfig for testing."""
    return AppConfig()


# ---------------------------------------------------------------------------
# Groq provider
# ---------------------------------------------------------------------------


def test_provider_groq_success():
    """Groq connection test must return (True, None, model_count) on success."""
    with patch("application.services.provider_service.fetch_groq_models") as mock_fetch:
        mock_fetch.return_value = [{"id": "llama-3.3-70b"}, {"id": "mixtral-8x7b"}]

        ok, error, count = test_provider("groq", "gsk_key", _make_config())

        assert ok is True
        assert error is None
        assert count == 2


def test_provider_groq_failure():
    """Groq connection test must return (False, error, None) on failure."""
    with patch("application.services.provider_service.fetch_groq_models") as mock_fetch:
        mock_fetch.side_effect = Exception("API key invalid")

        ok, error, count = test_provider("groq", "bad_key", _make_config())

        assert ok is False
        assert "API key invalid" in error
        assert count is None


# ---------------------------------------------------------------------------
# OpenRouter provider
# ---------------------------------------------------------------------------


def test_provider_openrouter_success():
    """OpenRouter connection test must return (True, None, model_count) on success."""
    with patch("application.services.provider_service.fetch_openrouter_models") as mock_fetch:
        mock_fetch.return_value = [{"id": "openai/gpt-4"}]

        ok, error, count = test_provider("openrouter", "sk_key", _make_config())

        assert ok is True
        assert error is None
        assert count == 1


def test_provider_openrouter_failure():
    """OpenRouter connection test must return (False, error, None) on failure."""
    with patch("application.services.provider_service.fetch_openrouter_models") as mock_fetch:
        mock_fetch.side_effect = ConnectionError("timeout")

        ok, error, count = test_provider("openrouter", "bad_key", _make_config())

        assert ok is False
        assert "timeout" in error
        assert count is None


# ---------------------------------------------------------------------------
# Nvidia provider
# ---------------------------------------------------------------------------


def test_provider_nvidia_success():
    """Nvidia connection test must return (True, None, model_count) on success."""
    with patch("application.services.provider_service.fetch_nvidia_models") as mock_fetch:
        mock_fetch.return_value = [{"id": "meta/llama-3.1-70b"}]

        ok, error, count = test_provider("nvidia", "nvapi_key", _make_config())

        assert ok is True
        assert error is None
        assert count == 1


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------


def test_provider_gemini_success():
    """Gemini connection test must return (True, None, model_count) on success."""
    with patch("application.services.provider_service.fetch_gemini_models") as mock_fetch:
        mock_fetch.return_value = [{"id": "gemini-2.0-flash"}]

        ok, error, count = test_provider("gemini", "ai_key", _make_config())

        assert ok is True
        assert error is None
        assert count == 1


# ---------------------------------------------------------------------------
# HuggingFace provider
# ---------------------------------------------------------------------------


def test_provider_huggingface_always_ok():
    """HuggingFace does not support connection testing, so it always returns (True, None, None)."""
    ok, error, count = test_provider("huggingface", "hf_key", _make_config())

    assert ok is True
    assert error is None
    assert count is None


# ---------------------------------------------------------------------------
# Unknown provider
# ---------------------------------------------------------------------------


def test_provider_unknown():
    """An unknown provider must return (False, error, None) with a descriptive message."""
    ok, error, count = test_provider("unknown_provider", "key", _make_config())

    assert ok is False
    assert "unknown_provider" in error
    assert "does not support connection testing" in error
    assert count is None


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_provider_connection_empty_api_key():
    """An empty API key should be passed through to the fetcher (which will likely fail)."""
    with patch("application.services.provider_service.fetch_groq_models") as mock_fetch:
        mock_fetch.side_effect = Exception("Unauthorized")

        ok, error, count = test_provider("groq", "", _make_config())

        assert ok is False
        mock_fetch.assert_called_once_with("", "https://api.groq.com/openai/v1")


def test_provider_exception_during_fetch():
    """Any exception during model fetching must be caught and returned as (False, str(exc), None)."""
    with patch("application.services.provider_service.fetch_groq_models") as mock_fetch:
        mock_fetch.side_effect = ValueError("unexpected error")

        ok, error, count = test_provider("groq", "key", _make_config())

        assert ok is False
        assert "unexpected error" in error
        assert count is None
