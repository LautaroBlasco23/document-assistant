"""Provider model fetching and connection testing."""

from infrastructure.config import AppConfig
from infrastructure.llm.model_fetcher import (
    fetch_gemini_models,
    fetch_groq_models,
    fetch_llamacpp_models,
    fetch_nvidia_models,
    fetch_openrouter_models,
)


def test_provider(
    provider: str, api_key: str, config: AppConfig,
) -> tuple[bool, str | None, int | None]:
    """Return (ok, error_str, model_count) for a provider connection test."""
    try:
        if provider == "groq":
            models = fetch_groq_models(api_key, config.groq.base_url)
        elif provider == "openrouter":
            models = fetch_openrouter_models(api_key, config.openrouter.base_url)
        elif provider == "nvidia":
            models = fetch_nvidia_models(api_key, config.nvidia.base_url)
        elif provider == "gemini":
            models = fetch_gemini_models(api_key, config.gemini.base_url)
        elif provider == "huggingface":
            return True, None, None
        elif provider == "llamacpp":
            models = fetch_llamacpp_models("", config.llamacpp.base_url)
        else:
            return False, f"Provider '{provider}' does not support connection testing", None
        return True, None, len(models)
    except Exception as exc:
        return False, str(exc), None
