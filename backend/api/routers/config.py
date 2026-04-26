"""Configuration endpoints."""

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from api.deps import ServicesDep
from api.schemas.config import (
    ChunkingConfigOut,
    ConfigOut,
    HuggingFaceConfigOut,
    OllamaConfigOut,
    OpenRouterConfigOut,
)
from infrastructure.llm.model_fetcher import fetch_groq_models, fetch_openrouter_models

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
}


class ModelInfo(BaseModel):
    id: str
    label: str
    role: str | None


class ModelsOut(BaseModel):
    provider: str
    current_model: str
    models: list[ModelInfo]


@router.get("/config", response_model=ConfigOut)
async def get_config(services: ServicesDep) -> ConfigOut:
    """Get current configuration."""
    logger.info("Config read")
    config = services.config
    return ConfigOut(
        llm_provider=config.llm_provider,
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
async def get_models(services: ServicesDep) -> ModelsOut:
    """List available models for the current LLM provider.

    For Groq and OpenRouter the list is fetched live from the provider API
    and cached for one hour.  On failure the hardcoded fallback list is used.
    """
    config = services.config
    provider = config.llm_provider

    if provider == "groq":
        current = config.groq.model
        fast = config.groq.fast_model
        models = fetch_groq_models(
            config.groq.api_key,
            config.groq.base_url,
            fallback=_FALLBACK_MODELS[provider],
        )
    elif provider == "openrouter":
        current = config.openrouter.model
        fast = config.openrouter.fast_model
        models = fetch_openrouter_models(
            config.openrouter.api_key,
            config.openrouter.base_url,
            fallback=_FALLBACK_MODELS[provider],
        )
    elif provider == "huggingface":
        current = config.huggingface.model
        fast = config.huggingface.fast_model
        models = _FALLBACK_MODELS[provider]
    else:  # ollama
        current = config.ollama.generation_model
        fast = config.ollama.fast_model
        models = [{"id": current, "label": current}]
        if fast and fast != current:
            models.append({"id": fast, "label": fast})

    # Assign roles (main / fast) based on config defaults
    _assign_roles(models, main_current=current, fast_current=fast)

    # Ensure the currently configured model is always present
    existing_ids = {m["id"] for m in models}
    if current and current not in existing_ids:
        models.insert(0, {"id": current, "label": current})

    return ModelsOut(
        provider=provider,
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
