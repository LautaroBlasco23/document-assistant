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

logger = logging.getLogger(__name__)

router = APIRouter()

_PROVIDER_MODELS: dict[str, list[dict]] = {
    "groq": [
        {"id": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B Versatile", "role": "main"},
        {"id": "llama-3.1-8b-instant", "label": "Llama 3.1 8B Instant", "role": "fast"},
        {"id": "gemma2-9b-it", "label": "Gemma 2 9B", "role": None},
        {"id": "llama3-8b-8192", "label": "Llama 3 8B", "role": None},
        {"id": "llama3-70b-8192", "label": "Llama 3 70B", "role": None},
        {"id": "mixtral-8x7b-32768", "label": "Mixtral 8x7B", "role": None},
    ],
    "openrouter": [
        {"id": "meta-llama/llama-3.3-70b-instruct:free", "label": "Llama 3.3 70B (free)", "role": "main"},  # noqa: E501
        {"id": "qwen/qwen2.5-7b-instruct:free", "label": "Qwen 2.5 7B (free)", "role": "fast"},
        {"id": "google/gemma-3-12b-it:free", "label": "Gemma 3 12B (free)", "role": None},
        {"id": "mistralai/mistral-7b-instruct:free", "label": "Mistral 7B (free)", "role": None},
    ],
    "huggingface": [
        {"id": "Qwen/Qwen2.5-72B-Instruct", "label": "Qwen 2.5 72B", "role": "main"},
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
    """List available models for the current LLM provider."""
    config = services.config
    provider = config.llm_provider

    if provider == "groq":
        current = config.groq.model
        base = _PROVIDER_MODELS["groq"]
        ids = {m["id"] for m in base}
        fallback = [{"id": current, "label": current, "role": "main"}]
        models = base if current in ids else fallback + base
    elif provider == "openrouter":
        current = config.openrouter.model
        base = _PROVIDER_MODELS["openrouter"]
        ids = {m["id"] for m in base}
        fallback = [{"id": current, "label": current, "role": "main"}]
        models = base if current in ids else fallback + base
    elif provider == "huggingface":
        current = config.huggingface.model
        base = _PROVIDER_MODELS["huggingface"]
        ids = {m["id"] for m in base}
        fallback_hf = [{"id": current, "label": current, "role": "main"}]
        models = base if current in ids else fallback_hf + base
    else:  # ollama
        current = config.ollama.generation_model
        models = [{"id": current, "label": current, "role": "main"}]
        if config.ollama.fast_model:
            fm = config.ollama.fast_model
            models.append({"id": fm, "label": fm, "role": "fast"})

    return ModelsOut(
        provider=provider,
        current_model=current,
        models=[ModelInfo(**m) for m in models],
    )
