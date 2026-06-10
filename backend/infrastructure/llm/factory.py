import logging
from dataclasses import dataclass
from typing import Callable, Type

from core.ports.llm import LLM
from infrastructure.config import AppConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderSpec:
    """Registry entry for an LLM provider."""

    llm_cls: Type[LLM]
    config_fn: Callable[[AppConfig], object]
    key_fn: Callable[[AppConfig], str]
    model_field: str = "model"
    display_name: str = ""


_PROVIDER_REGISTRY: dict[str, ProviderSpec] = {
    "groq": ProviderSpec(
        llm_cls=lambda: _import_cls("infrastructure.llm.groq_llm", "GroqLLM"),
        config_fn=lambda c: c.groq,
        key_fn=lambda c: c.groq.api_key,
        display_name="Groq",
    ),
    "openrouter": ProviderSpec(
        llm_cls=lambda: _import_cls("infrastructure.llm.openrouter_llm", "OpenRouterLLM"),
        config_fn=lambda c: c.openrouter,
        key_fn=lambda c: c.openrouter.api_key,
        display_name="OpenRouter",
    ),
    "huggingface": ProviderSpec(
        llm_cls=lambda: _import_cls("infrastructure.llm.huggingface_llm", "HuggingFaceLLM"),
        config_fn=lambda c: c.huggingface,
        key_fn=lambda c: c.huggingface.api_key,
        display_name="HuggingFace",
    ),
    "nvidia": ProviderSpec(
        llm_cls=lambda: _import_cls("infrastructure.llm.nvidia_llm", "NvidiaLLM"),
        config_fn=lambda c: c.nvidia,
        key_fn=lambda c: c.nvidia.api_key,
        display_name="Nvidia",
    ),
    "gemini": ProviderSpec(
        llm_cls=lambda: _import_cls("infrastructure.llm.gemini_llm", "GeminiLLM"),
        config_fn=lambda c: c.gemini,
        key_fn=lambda c: c.gemini.api_key,
        display_name="Gemini",
    ),
    "ollama": ProviderSpec(
        llm_cls=lambda: _import_cls("infrastructure.llm.ollama", "OllamaLLM"),
        config_fn=lambda c: c.ollama,
        key_fn=lambda c: "",
        model_field="generation_model",
        display_name="Ollama",
    ),
    "llamacpp": ProviderSpec(
        llm_cls=lambda: _import_cls("infrastructure.llm.llamacpp_llm", "LlamaCppLLM"),
        config_fn=lambda c: c.llamacpp,
        key_fn=lambda c: "",
        display_name="llama.cpp",
    ),
}


def _import_cls(module_path: str, cls_name: str) -> Type[LLM]:
    """Lazy-import and return an LLM class."""
    import importlib

    mod = importlib.import_module(module_path)
    return getattr(mod, cls_name)


def _resolve_provider(provider: str) -> ProviderSpec:
    spec = _PROVIDER_REGISTRY.get(provider)
    if not spec:
        raise ValueError(f"Unknown LLM provider: {provider}")
    return spec


def _build_config_with_overrides(
    config: AppConfig,
    provider: str,
    model: str | None = None,
    api_key: str | None = None,
) -> object:
    """Return a provider config copy with optional model/api_key overrides."""
    spec = _resolve_provider(provider)
    provider_config = spec.config_fn(config)
    updates: dict = {}
    if model is not None:
        updates[spec.model_field] = model
    if api_key:
        updates["api_key"] = api_key
    if updates:
        provider_config = provider_config.model_copy(update=updates)
    return provider_config


def _create(
    provider: str,
    config: AppConfig,
    model: str | None = None,
    api_key: str | None = None,
) -> LLM:
    """Core creation logic: validate key, build config, instantiate LLM."""
    spec = _resolve_provider(provider)
    key = api_key or spec.key_fn(config)
    if not key and provider not in ("ollama", "llamacpp"):
        raise ValueError(
            f"{spec.display_name} API key required. "
            f"Set DOCASSIST_{provider.upper()}__API_KEY environment variable."
        )
    provider_config = _build_config_with_overrides(config, provider, model=model, api_key=api_key)
    llm_cls = spec.llm_cls()
    model_val = getattr(provider_config, spec.model_field, "unknown")
    logger.info("Using %s LLM: model=%s", spec.display_name, model_val)
    return llm_cls(provider_config)


def create_llm(config: AppConfig) -> LLM:
    """Instantiate the main LLM based on config.llm_provider."""
    if not config.llm_provider:
        raise ValueError(
            "No LLM provider configured. "
            "Set DOCASSIST_LLM_PROVIDER "
            "(e.g. groq, openrouter, ollama, huggingface, nvidia, gemini, llamacpp)."
        )
    return _create(config.llm_provider, config)


def create_fast_llm(config: AppConfig, fallback: LLM) -> LLM:
    """Instantiate a fast LLM for bulk tasks, falling back to the main LLM."""
    if not config.llm_provider:
        return fallback
    provider = config.llm_provider
    provider_config = _resolve_provider(provider).config_fn(config)
    fast_model = getattr(provider_config, "fast_model", None)
    if not fast_model:
        return fallback
    return _create(provider, config, model=fast_model)


def create_llm_with_model(config: AppConfig, model_name: str) -> LLM:
    """Create an LLM using the current provider config but with a different model."""
    if not config.llm_provider:
        raise ValueError(
            "No LLM provider configured. "
            "Set DOCASSIST_LLM_PROVIDER "
            "(e.g. groq, openrouter, ollama, huggingface, nvidia, gemini, llamacpp)."
        )
    return _create(config.llm_provider, config, model=model_name)


def create_llm_for_agent(provider: str, model: str, api_key: str, config: AppConfig) -> LLM:
    """Create an LLM instance with explicit credentials (api_key + model override).

    Args:
        provider: Provider slug (``groq``, ``nvidia``, ``gemini``, ``openrouter``,
                  ``huggingface``, ``ollama``).
        model: Model name to use.
        api_key: API key string. Ignored for ``ollama``.
        config: Full :class:`AppConfig` — the provider sub-config is copied and
                overridden.

    Returns:
        A configured :class:`LLM` instance.
    """
    return _create(provider, config, model=model, api_key=api_key)
