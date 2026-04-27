"""
Unit tests for model fetchers (Groq and OpenRouter).

Subject: infrastructure/llm/model_fetcher.py
Scope:   Live model fetching from Groq and OpenRouter APIs with TTL caching,
         fallback to hardcoded defaults on HTTP errors / timeouts, stale cache
         reuse, and cache expiry.
Out of scope:
  - Provider LLM implementations       → test_*_llm.py files
  - Config loading                     → test_config.py
  - /api/models endpoint               → test_config_router.py
Setup:   Uses unittest.mock.patch to mock requests.get; imports module-level
         functions directly.  Cache is cleared between tests.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from infrastructure.llm.model_fetcher import (
    _CACHE_TTL,
    _cache_set,
    _groq_label,
    _model_cache,
    _parse_price,
    fetch_groq_models,
    fetch_openrouter_models,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GROQ_URL = "https://api.groq.com/openai/v1"
OR_URL = "https://openrouter.ai/api/v1"
API_KEY = "test-key"

FALLBACK_GROQ = [
    {"id": "fb-groq-1", "label": "Fallback Groq 1", "role": None},
]
FALLBACK_OR = [
    {"id": "fb-or-1", "label": "Fallback OpenRouter 1", "role": None},
]

GROQ_RESPONSE = {
    "object": "list",
    "data": [
        {"id": "llama-3.3-70b-versatile", "owned_by": "groq"},
        {"id": "gemma2-9b-it", "owned_by": "groq"},
        {"id": "mixtral-8x7b-32768", "owned_by": "groq"},
        {"id": "whisper-large-v3", "owned_by": "groq"},  # should be filtered out
        {"id": "playai-tts", "owned_by": "groq"},         # should be filtered out
    ],
}

OR_RESPONSE = {
    "data": [
        {
            "id": "meta-llama/llama-3.3-70b-instruct:free",
            "name": "Llama 3.3 70B",
            "pricing": {"prompt": "0", "completion": "0"},
            "context_length": 131072,
        },
        {
            "id": "google/gemini-pro:free",
            "name": "Gemini Pro",
            "pricing": {"prompt": "0", "completion": "0"},
            "context_length": 32768,
        },
        {
            "id": "openai/gpt-4",
            "name": "GPT-4",
            "pricing": {"prompt": "0.03", "completion": "0.06"},
            "context_length": 8192,
        },
    ],
}


def _mock_response(json_data, status_code=200):
    """Build a mock requests.Response with the given JSON data and status."""
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


def _clear_cache():
    _model_cache.clear()


@pytest.fixture(autouse=True)
def clear_cache_between_tests():
    """Remove any cached model data so tests start from a clean state."""
    _clear_cache()
    yield
    _clear_cache()


# ---------------------------------------------------------------------------
# Groq model fetching
# ---------------------------------------------------------------------------

def test_fetch_groq_models_returns_live_results():
    """When the Groq API responds successfully, models are returned with labels.
    Whisper and TTS models are filtered out."""
    with patch("infrastructure.llm.model_fetcher.requests.get") as mock_get:
        mock_get.return_value = _mock_response(GROQ_RESPONSE)

        result = fetch_groq_models(API_KEY, GROQ_URL)

    # 5 entries in data, but whisper + tts filtered → 3 chat models
    assert len(result) == 3
    ids = {m["id"] for m in result}
    assert ids == {"llama-3.3-70b-versatile", "gemma2-9b-it", "mixtral-8x7b-32768"}
    # Labels should be human-readable
    labels = {m["label"] for m in result}
    assert "Llama 3.3 70B Versatile" in labels


def test_fetch_groq_models_falls_back_on_http_error():
    """When the Groq API returns 500, the fallback list is returned."""
    with patch("infrastructure.llm.model_fetcher.requests.get") as mock_get:
        mock_get.return_value = _mock_response({}, status_code=500)

        result = fetch_groq_models(API_KEY, GROQ_URL, fallback=FALLBACK_GROQ)

    assert result == FALLBACK_GROQ


def test_fetch_groq_models_falls_back_on_timeout():
    """When the Groq API times out, the fallback list is returned."""
    with patch("infrastructure.llm.model_fetcher.requests.get") as mock_get:
        mock_get.side_effect = Exception("Connection timed out")

        result = fetch_groq_models(API_KEY, GROQ_URL, fallback=FALLBACK_GROQ)

    assert result == FALLBACK_GROQ


def test_fetch_groq_models_returns_empty_on_no_fallback():
    """When there is no fallback and the API fails, an empty list is returned."""
    with patch("infrastructure.llm.model_fetcher.requests.get") as mock_get:
        mock_get.side_effect = Exception("Boom")

        result = fetch_groq_models(API_KEY, GROQ_URL)

    assert result == []


# ---------------------------------------------------------------------------
# OpenRouter model fetching
# ---------------------------------------------------------------------------

def test_fetch_openrouter_models_returns_only_free_models():
    """Only free-tier models (price == 0) should be returned; paid models are filtered."""
    with patch("infrastructure.llm.model_fetcher.requests.get") as mock_get:
        mock_get.return_value = _mock_response(OR_RESPONSE)

        result = fetch_openrouter_models(API_KEY, OR_URL)

    assert len(result) == 2  # GPT-4 is paid, filtered out
    ids = {m["id"] for m in result}
    assert "openai/gpt-4" not in ids
    # Context length is included in label
    assert any("131k" in m["label"] for m in result)


def test_fetch_openrouter_models_falls_back_on_http_error():
    """When the OpenRouter API returns 500, the fallback list is returned."""
    with patch("infrastructure.llm.model_fetcher.requests.get") as mock_get:
        mock_get.return_value = _mock_response({}, status_code=500)

        result = fetch_openrouter_models(API_KEY, OR_URL, fallback=FALLBACK_OR)

    assert result == FALLBACK_OR


def test_fetch_openrouter_models_empty_fallback():
    """When no fallback is given and the API fails, an empty list is returned."""
    with patch("infrastructure.llm.model_fetcher.requests.get") as mock_get:
        mock_get.side_effect = Exception("Boom")

        result = fetch_openrouter_models(API_KEY, OR_URL)

    assert result == []


# ---------------------------------------------------------------------------
# TTL caching
# ---------------------------------------------------------------------------

def test_fetch_groq_models_returns_cached_results_within_ttl():
    """Models are cached for _CACHE_TTL seconds; a second call returns cached data
    without hitting the API again."""
    with patch("infrastructure.llm.model_fetcher.requests.get") as mock_get:
        mock_get.return_value = _mock_response(GROQ_RESPONSE)

        first = fetch_groq_models(API_KEY, GROQ_URL)
        # Second call — should use cache, not hit HTTP
        second = fetch_groq_models(API_KEY, GROQ_URL)

        assert first == second
        # Only one HTTP call was made
        assert mock_get.call_count == 1


def test_fetch_groq_models_refetches_after_cache_expiry():
    """After _CACHE_TTL seconds, the cache expires and a new HTTP call is made."""
    # Seed an expired cache entry
    cached_models = [{"id": "stale", "label": "Stale", "role": None}]
    _cache_set("groq", cached_models)
    # Artificially age the timestamp past TTL
    _model_cache["groq"] = (time.time() - _CACHE_TTL - 1, _model_cache["groq"][1])

    with patch("infrastructure.llm.model_fetcher.requests.get") as mock_get:
        mock_get.return_value = _mock_response(GROQ_RESPONSE)

        result = fetch_groq_models(API_KEY, GROQ_URL)

        # Should have fetched fresh data, not stale
        assert any(m["id"] == "llama-3.3-70b-versatile" for m in result)
        assert mock_get.call_count == 1


def test_fetch_groq_models_uses_stale_cache_when_live_fails():
    """When the live API call fails but a stale cache exists, the stale data
    is returned instead of the fallback."""
    # Seed a cache entry
    cached_models = [{"id": "cached-model", "label": "Cached", "role": None}]
    _cache_set("groq", cached_models)
    # Age the entry so _cache_get returns None (expired), but stale entry still exists
    _model_cache["groq"] = (time.time() - _CACHE_TTL - 1, cached_models)

    with patch("infrastructure.llm.model_fetcher.requests.get") as mock_get:
        # Now the HTTP call fails
        mock_get.side_effect = Exception("Network error")

        result = fetch_groq_models(API_KEY, GROQ_URL, fallback=FALLBACK_GROQ)

    # Stale cache wins over fallback
    assert result == cached_models


# ---------------------------------------------------------------------------
# _parse_price helper
# ---------------------------------------------------------------------------

def test_parse_price_none_returns_empty_string():
    """None input returns empty string."""
    assert _parse_price(None) == ""


def test_parse_price_zero_returns_zero_string():
    """Zero (int) returns '0'."""
    assert _parse_price(0) == "0"


def test_parse_price_float_returns_string():
    """Float values are converted to string."""
    assert _parse_price(0.03) == "0.03"


def test_parse_price_string_passthrough():
    """String values pass through unchanged."""
    assert _parse_price("0") == "0"
    assert _parse_price("0.06") == "0.06"


# ---------------------------------------------------------------------------
# _groq_label helper
# ---------------------------------------------------------------------------

def test_groq_label_known_model_returns_label():
    """A known model ID returns its hardcoded label."""
    assert _groq_label("llama-3.3-70b-versatile") == "Llama 3.3 70B Versatile"


def test_groq_label_unknown_model_returns_titlecased():
    """An unknown model ID is title-cased with hyphens replaced by spaces."""
    assert _groq_label("my-custom-model-42b") == "My Custom Model 42B"
