"""Live model fetching from Groq and OpenRouter APIs with TTL caching."""

import logging
import time

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Label helpers — map known Groq model IDs to human-readable labels.
# Unknown IDs get a title-cased fallback.
# ---------------------------------------------------------------------------

_GROQ_LABELS: dict[str, str] = {
    "llama-3.3-70b-versatile": "Llama 3.3 70B Versatile",
    "llama-3.1-8b-instant": "Llama 3.1 8B Instant",
    "llama-3.2-1b-preview": "Llama 3.2 1B (preview)",
    "llama-3.2-3b-preview": "Llama 3.2 3B (preview)",
    "llama-3.2-11b-vision-preview": "Llama 3.2 11B Vision (preview)",
    "llama-3.2-90b-vision-preview": "Llama 3.2 90B Vision (preview)",
    "gemma2-9b-it": "Gemma 2 9B",
    "mixtral-8x7b-32768": "Mixtral 8x7B",
    "deepseek-r1-distill-llama-70b": "DeepSeek R1 Distill Llama 70B",
    "deepseek-r1-distill-qwen-32b": "DeepSeek R1 Distill Qwen 32B",
    "qwen-qwq-32b": "Qwen QWQ 32B",
    "qwen-2.5-32b": "Qwen 2.5 32B",
    "qwen-2.5-coder-32b": "Qwen 2.5 Coder 32B",
    "mistral-saba-24b": "Mistral Saba 24B",
    "playai-tts-0-125b": "PlayAI TTS (preview)",
    "playai-tts": "PlayAI TTS",
    "whisper-large-v3": "Whisper Large V3",
    "whisper-large-v3-turbo": "Whisper Large V3 Turbo",
}


def _groq_label(model_id: str) -> str:
    if model_id in _GROQ_LABELS:
        return _GROQ_LABELS[model_id]
    # Fallback: title-case and replace hyphens with spaces
    return model_id.replace("-", " ").title()


# ---------------------------------------------------------------------------
# Simple in-memory cache (keys = provider name, values = (timestamp, models))
# ---------------------------------------------------------------------------

_model_cache: dict[str, tuple[float, list[dict]]] = {}
_CACHE_TTL = 3600  # 1 hour


def _cache_get(provider: str) -> list[dict] | None:
    entry = _model_cache.get(provider)
    if entry is None:
        return None
    ts, data = entry
    if time.time() - ts < _CACHE_TTL:
        return data
    return None


def _cache_set(provider: str, models: list[dict]) -> None:
    _model_cache[provider] = (time.time(), models)


# ---------------------------------------------------------------------------
# Groq model fetching — uses the OpenAI-compatible /models endpoint
# ---------------------------------------------------------------------------

def _fetch_groq_live(api_key: str, base_url: str) -> list[dict]:
    """Fetch available Groq models via GET /models."""
    url = f"{base_url.rstrip('/')}/models"
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json().get("data", [])
    if not isinstance(data, list):
        logger.warning("Groq /models returned unexpected format: %s", type(data))
        return []

    models: list[dict] = []
    for entry in data:
        mid = entry.get("id", "")
        if not mid or not isinstance(mid, str):
            continue
        # Skip audio / whisper models — they aren't for chat
        if "whisper" in mid or "tts" in mid or "distil" in mid:
            continue
        models.append({"id": mid, "label": _groq_label(mid), "role": None})
    return models


# ---------------------------------------------------------------------------
# OpenRouter model fetching — filters to free-tier models
# ---------------------------------------------------------------------------

def _fetch_openrouter_live(api_key: str, base_url: str) -> list[dict]:
    """Fetch OpenRouter models and keep only free-tier entries (price == 0)."""
    url = f"{base_url.rstrip('/')}/models"
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    if not isinstance(data, list):
        logger.warning("OpenRouter /models returned unexpected format: %s", type(data))
        return []

    models: list[dict] = []
    for entry in data:
        mid = entry.get("id", "")
        if not mid or not isinstance(mid, str):
            continue

        # Keep only free models
        pricing = entry.get("pricing", {})
        prompt_price = _parse_price(pricing.get("prompt"))
        completion_price = _parse_price(pricing.get("completion"))
        if prompt_price != "0" or completion_price != "0":
            continue

        name = entry.get("name", "") or mid
        context = entry.get("context_length")
        suffix = f" ({context // 1000}k)" if isinstance(context, int) and context > 0 else ""
        label = f"{name}{suffix}"

        models.append({"id": mid, "label": label, "role": None})
    return models


def _parse_price(price_val: str | float | int | None) -> str:
    """Normalise price to a string; OpenRouter returns '0' for free."""
    if price_val is None:
        return ""
    if isinstance(price_val, (int, float)):
        return str(int(price_val)) if price_val == int(price_val) else str(price_val)
    return str(price_val)


# ---------------------------------------------------------------------------
# Public cached fetchers — try live, fall back to hardcoded list
# ---------------------------------------------------------------------------

def fetch_groq_models(
    api_key: str, base_url: str, fallback: list[dict] | None = None
) -> list[dict]:
    """Return Groq models (cached 1 h), falling back to *fallback* on failure."""
    cached = _cache_get("groq")
    if cached is not None:
        return cached

    try:
        live = _fetch_groq_live(api_key, base_url)
        if live:
            _cache_set("groq", live)
            return live
    except Exception:
        logger.warning("Failed to fetch live Groq models", exc_info=True)

    # Return stale cache if available
    stale = _model_cache.get("groq")
    if stale is not None:
        logger.info("Using stale Groq model cache")
        return stale[1]

    return fallback or []


def fetch_openrouter_models(
    api_key: str, base_url: str, fallback: list[dict] | None = None
) -> list[dict]:
    """Return OpenRouter free models (cached 1 h), falling back to *fallback* on failure."""
    cached = _cache_get("openrouter")
    if cached is not None:
        return cached

    try:
        live = _fetch_openrouter_live(api_key, base_url)
        if live:
            _cache_set("openrouter", live)
            return live
    except Exception:
        logger.warning("Failed to fetch live OpenRouter models", exc_info=True)

    stale = _model_cache.get("openrouter")
    if stale is not None:
        logger.info("Using stale OpenRouter model cache")
        return stale[1]

    return fallback or []
