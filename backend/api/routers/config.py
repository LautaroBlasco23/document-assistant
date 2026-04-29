"""Configuration endpoints."""

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from api.deps import ServicesDep
from api.schemas.config import (
    ChunkingConfigOut,
    ConfigOut,
    GeminiConfigOut,
    GroqConfigOut,
    HuggingFaceConfigOut,
    NvidiaConfigOut,
    OllamaConfigOut,
    OpenRouterConfigOut,
)
from infrastructure.llm.model_fetcher import (
    fetch_gemini_models,
    fetch_groq_models,
    fetch_nvidia_models,
    fetch_openrouter_models,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Hardcoded model lists — used as fallback when live fetching fails.
# Live fetchers in model_fetcher.py are the primary source.
_FALLBACK_MODELS: dict[str, list[dict]] = {
    "groq": [
        {"id": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B Versatile"},
        {"id": "llama-3.1-8b-instant", "label": "Llama 3.1 8B Instant"},
        {"id": "gemma2-9b-it", "label": "Gemma 2 9B"},
        {"id": "mixtral-8x7b-32768", "label": "Mixtral 8x7B"},
        {"id": "deepseek-r1-distill-llama-70b", "label": "DeepSeek R1 Distill Llama 70B"},
        {"id": "qwen-qwq-32b", "label": "Qwen QWQ 32B"},
    ],
    "openrouter": [
        {"id": "meta-llama/llama-3.3-70b-instruct:free", "label": "Llama 3.3 70B (free)"},
        {"id": "qwen/qwen2.5-7b-instruct:free", "label": "Qwen 2.5 7B (free)"},
        {"id": "google/gemma-3-12b-it:free", "label": "Gemma 3 12B (free)"},
        {"id": "mistralai/mistral-7b-instruct:free", "label": "Mistral 7B (free)"},
    ],
    "huggingface": [
        {"id": "Qwen/Qwen2.5-72B-Instruct", "label": "Qwen 2.5 72B"},
    ],
    "ollama": [],
    "nvidia": [
        {"id": "meta/llama-3.3-70b-instruct", "label": "Llama 3.3 70B"},
        {"id": "meta/llama-3.1-8b-instruct", "label": "Llama 3.1 8B"},
        {"id": "nvidia/llama-3.1-nemotron-70b-instruct", "label": "Nemotron 70B"},
    ],
    "gemini": [
        {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash (250 RPD cap)"},
        {"id": "gemini-2.5-flash-lite", "label": "Gemini 2.5 Flash-Lite (1000 RPD)"},
        {"id": "gemini-2.0-flash", "label": "Gemini 2.0 Flash"},
    ],
}

# Model capability metadata — maps model ID patterns to quality tier and recommendations.
# Evaluated in order; first match wins. Unknown models default to medium/chat.
_MODEL_CAPABILITIES: list[tuple[str, str, list[str]]] = [
    # Low tier exceptions (checked first to avoid broader matches)
    ("-lite", "low", ["chat"]),
    # High tier: 70B+ models and Gemini Flash-class
    ("70b", "high", ["questions", "flashcards", "summaries", "chat"]),
    ("72b", "high", ["questions", "flashcards", "summaries", "chat"]),
    ("gemini-2.5-pro", "high", ["questions", "flashcards", "summaries", "chat"]),
    ("gemini-2.5-flash", "high", ["questions", "flashcards", "summaries", "chat"]),
    ("gemini-2.0-flash", "high", ["questions", "flashcards", "summaries", "chat"]),
    ("nemotron-70b", "high", ["questions", "flashcards", "summaries", "chat"]),
    # Medium tier: 14B–32B models
    ("32b", "medium", ["flashcards", "summaries", "chat"]),
    ("27b", "medium", ["flashcards", "summaries", "chat"]),
    ("14b", "medium", ["flashcards", "summaries", "chat"]),
    ("12b", "medium", ["summaries", "chat"]),
    ("11b", "medium", ["summaries", "chat"]),
    # Low tier: <14B models, fast/bulk models
    ("9b", "low", ["chat"]),
    ("8b", "low", ["chat"]),
    ("7b", "low", ["chat"]),
    ("3b", "low", ["chat"]),
    ("1b", "low", ["chat"]),
]


def _get_model_capabilities(model_id: str) -> tuple[str, list[str]]:
    """Return (quality_tier, recommended_for) for a model ID."""
    mid = model_id.lower()
    for pattern, tier, recs in _MODEL_CAPABILITIES:
        if pattern in mid:
            return tier, recs
    return "medium", ["chat"]


class ModelInfo(BaseModel):
    id: str
    label: str
    role: str | None
    quality_tier: str = "medium"
    recommended_for: list[str] = ["chat"]


class ModelsOut(BaseModel):
    provider: str
    current_model: str
    models: list[ModelInfo]


class ProviderInfo(BaseModel):
    slug: str
    label: str
    key_required: bool
    key_format_hint: str


_PROVIDERS: list[ProviderInfo] = [
    ProviderInfo(slug="groq", label="Groq", key_required=True, key_format_hint="gsk_..."),
    ProviderInfo(slug="openrouter", label="OpenRouter", key_required=True, key_format_hint="sk-or-..."),
    ProviderInfo(slug="huggingface", label="HuggingFace", key_required=True, key_format_hint="hf_..."),
    ProviderInfo(slug="nvidia", label="NVIDIA", key_required=True, key_format_hint="nvapi-..."),
    ProviderInfo(slug="gemini", label="Google Gemini", key_required=True, key_format_hint="AIza..."),
    ProviderInfo(slug="ollama", label="Ollama (local)", key_required=False, key_format_hint=""),
]


@router.get("/providers", response_model=list[ProviderInfo])
async def list_providers() -> list[ProviderInfo]:
    """Return static list of supported LLM providers."""
    return _PROVIDERS


@router.get("/config", response_model=ConfigOut)
async def get_config(services: ServicesDep) -> ConfigOut:
    """Get current configuration."""
    logger.info("Config read")
    config = services.config
    return ConfigOut(
        llm_provider=config.llm_provider,
        groq=GroqConfigOut(
            base_url=config.groq.base_url,
            model=config.groq.model,
            fast_model=config.groq.fast_model,
            timeout=config.groq.timeout,
            max_retries=config.groq.max_retries,
        ),
        nvidia=NvidiaConfigOut(
            base_url=config.nvidia.base_url,
            model=config.nvidia.model,
            fast_model=config.nvidia.fast_model,
            timeout=config.nvidia.timeout,
            max_retries=config.nvidia.max_retries,
        ),
        gemini=GeminiConfigOut(
            base_url=config.gemini.base_url,
            model=config.gemini.model,
            fast_model=config.gemini.fast_model,
            timeout=config.gemini.timeout,
            max_retries=config.gemini.max_retries,
        ),
        ollama=OllamaConfigOut(
            base_url=config.ollama.base_url,
            generation_model=config.ollama.generation_model,
            fast_model=config.ollama.fast_model,
            timeout=config.ollama.timeout,
        ),
        openrouter=OpenRouterConfigOut(
            base_url=config.openrouter.base_url,
            model=config.openrouter.model,
            fast_model=config.openrouter.fast_model,
            timeout=config.openrouter.timeout,
            max_retries=config.openrouter.max_retries,
        ),
        huggingface=HuggingFaceConfigOut(
            base_url=config.huggingface.base_url,
            model=config.huggingface.model,
            fast_model=config.huggingface.fast_model,
            timeout=config.huggingface.timeout,
            max_retries=config.huggingface.max_retries,
            wait_for_model=config.huggingface.wait_for_model,
        ),
        chunking=ChunkingConfigOut(
            max_tokens=config.chunking.max_tokens,
            overlap_tokens=config.chunking.overlap_tokens,
        ),
    )


@router.put("/config", response_model=ConfigOut)
async def update_config(update: dict, services: ServicesDep) -> ConfigOut:
    """Update configuration and reload services."""
    # For now, this is a placeholder since dynamic config reload is complex
    # In a real implementation, you'd merge the update with current config and reinitialize services
    logger.info("Configuration update requested (not yet implemented)")
    return await get_config(services)


@router.get("/models", response_model=ModelsOut)
async def get_models(services: ServicesDep, provider: str | None = None) -> ModelsOut:
    """List available models for the current (or specified) LLM provider.

    For Groq and OpenRouter the list is fetched live from the provider API
    and cached for one hour.  On failure the hardcoded fallback list is used.
    Pass ?provider=<slug> to fetch models for any provider regardless of global config.
    """
    config = services.config
    active_provider = provider or config.llm_provider

    if active_provider == "groq":
        current = config.groq.model
        fast = config.groq.fast_model
        models = fetch_groq_models(
            config.groq.api_key,
            config.groq.base_url,
            fallback=_FALLBACK_MODELS["groq"],
        )
    elif active_provider == "openrouter":
        current = config.openrouter.model
        fast = config.openrouter.fast_model
        models = fetch_openrouter_models(
            config.openrouter.api_key,
            config.openrouter.base_url,
            fallback=_FALLBACK_MODELS["openrouter"],
        )
    elif active_provider == "huggingface":
        current = config.huggingface.model
        fast = config.huggingface.fast_model
        models = _FALLBACK_MODELS["huggingface"]
    elif active_provider == "nvidia":
        current = config.nvidia.model
        fast = config.nvidia.fast_model
        models = fetch_nvidia_models(
            config.nvidia.api_key,
            config.nvidia.base_url,
            fallback=_FALLBACK_MODELS["nvidia"],
        )
    elif active_provider == "gemini":
        current = config.gemini.model
        fast = config.gemini.fast_model
        models = fetch_gemini_models(
            config.gemini.api_key,
            config.gemini.base_url,
            fallback=_FALLBACK_MODELS["gemini"],
        )
    else:  # ollama
        current = config.ollama.generation_model
        fast = config.ollama.fast_model
        models = [{"id": current, "label": current}]
        if fast and fast != current:
            models.append({"id": fast, "label": fast})

    # Assign roles (main / fast) based on config defaults
    _assign_roles(models, main_current=current, fast_current=fast)

    # Assign quality tier and recommendations
    _assign_capabilities(models)

    # Ensure the currently configured model is always present
    existing_ids = {m["id"] for m in models}
    if current and current not in existing_ids:
        tier, recs = _get_model_capabilities(current)
        models.insert(
            0,
            {"id": current, "label": current, "quality_tier": tier, "recommended_for": recs},
        )

    return ModelsOut(
        provider=active_provider,
        current_model=current,
        models=[ModelInfo(**m) for m in models],
    )


def _assign_roles(
    models: list[dict],
    *,
    main_current: str | None = None,
    fast_current: str | None = None,
) -> None:
    """Tag entries whose id matches the configured main or fast model."""
    for m in models:
        if m.get("role") is not None:
            continue  # already tagged
        if main_current and m["id"] == main_current:
            m["role"] = "main"
        elif fast_current and m["id"] == fast_current:
            m["role"] = "fast"


def _assign_capabilities(models: list[dict]) -> None:
    """Tag each model with quality_tier and recommended_for based on its ID."""
    for m in models:
        if "quality_tier" in m and "recommended_for" in m:
            continue  # already tagged
        tier, recs = _get_model_capabilities(m["id"])
        m["quality_tier"] = tier
        m["recommended_for"] = recs
