import logging

from core.ports.llm import LLM
from infrastructure.config import AppConfig

logger = logging.getLogger(__name__)


def create_llm(config: AppConfig) -> LLM:
    """Instantiate the main LLM based on config.llm_provider."""
    if config.llm_provider == "groq":
        if not config.groq.api_key:
            raise ValueError(
                "Groq API key required. Set DOCASSIST_GROQ__API_KEY environment variable."
            )
        from infrastructure.llm.groq_llm import GroqLLM
        logger.info("Using Groq LLM: model=%s", config.groq.model)
        return GroqLLM(config.groq)
    elif config.llm_provider == "openrouter":
        if not config.openrouter.api_key:
            raise ValueError(
                "OpenRouter API key required. "
                "Set DOCASSIST_OPENROUTER__API_KEY environment variable."
            )
        from infrastructure.llm.openrouter_llm import OpenRouterLLM
        logger.info("Using OpenRouter LLM: model=%s", config.openrouter.model)
        return OpenRouterLLM(config.openrouter)
    elif config.llm_provider == "huggingface":
        if not config.huggingface.api_key:
            raise ValueError(
                "HuggingFace API key required. "
                "Set DOCASSIST_HUGGINGFACE__API_KEY environment variable."
            )
        from infrastructure.llm.huggingface_llm import HuggingFaceLLM
        logger.info("Using HuggingFace LLM: model=%s", config.huggingface.model)
        return HuggingFaceLLM(config.huggingface)
    elif config.llm_provider == "nvidia":
        if not config.nvidia.api_key:
            raise ValueError(
                "Nvidia API key required. "
                "Set DOCASSIST_NVIDIA__API_KEY environment variable."
            )
        from infrastructure.llm.nvidia_llm import NvidiaLLM
        logger.info("Using Nvidia LLM: model=%s", config.nvidia.model)
        return NvidiaLLM(config.nvidia)
    elif config.llm_provider == "gemini":
        if not config.gemini.api_key:
            raise ValueError(
                "Gemini API key required. "
                "Set DOCASSIST_GEMINI__API_KEY environment variable."
            )
        from infrastructure.llm.gemini_llm import GeminiLLM
        logger.info("Using Gemini LLM: model=%s", config.gemini.model)
        return GeminiLLM(config.gemini)
    else:
        from infrastructure.llm.ollama import OllamaLLM
        logger.info("Using Ollama LLM: model=%s", config.ollama.generation_model)
        return OllamaLLM(config.ollama)


def create_fast_llm(config: AppConfig, fallback: LLM) -> LLM:
    """Instantiate a fast LLM for bulk tasks, falling back to the main LLM."""
    if config.llm_provider == "groq":
        if config.groq.fast_model:
            from infrastructure.llm.groq_llm import GroqLLM
            fast_cfg = config.groq.model_copy(update={"model": config.groq.fast_model})
            logger.info("Using Groq fast LLM: model=%s", fast_cfg.model)
            return GroqLLM(fast_cfg)
        return fallback
    elif config.llm_provider == "openrouter":
        if config.openrouter.fast_model:
            from infrastructure.llm.openrouter_llm import OpenRouterLLM
            fast_cfg = config.openrouter.model_copy(update={"model": config.openrouter.fast_model})
            logger.info("Using OpenRouter fast LLM: model=%s", fast_cfg.model)
            return OpenRouterLLM(fast_cfg)
        return fallback
    elif config.llm_provider == "huggingface":
        if config.huggingface.fast_model:
            from infrastructure.llm.huggingface_llm import HuggingFaceLLM
            fast_cfg = config.huggingface.model_copy(
                update={"model": config.huggingface.fast_model}
            )
            logger.info("Using HuggingFace fast LLM: model=%s", fast_cfg.model)
            return HuggingFaceLLM(fast_cfg)
        return fallback
    elif config.llm_provider == "nvidia":
        if config.nvidia.fast_model:
            from infrastructure.llm.nvidia_llm import NvidiaLLM
            fast_cfg = config.nvidia.model_copy(update={"model": config.nvidia.fast_model})
            logger.info("Using Nvidia fast LLM: model=%s", fast_cfg.model)
            return NvidiaLLM(fast_cfg)
        return fallback
    elif config.llm_provider == "gemini":
        if config.gemini.fast_model:
            from infrastructure.llm.gemini_llm import GeminiLLM
            fast_cfg = config.gemini.model_copy(update={"model": config.gemini.fast_model})
            logger.info("Using Gemini fast LLM: model=%s", fast_cfg.model)
            return GeminiLLM(fast_cfg)
        return fallback
    else:
        if config.ollama.fast_model:
            from infrastructure.llm.ollama import OllamaLLM
            fast_cfg = config.ollama.model_copy(
                update={"generation_model": config.ollama.fast_model}
            )
            logger.info("Using Ollama fast LLM: model=%s", fast_cfg.generation_model)
            return OllamaLLM(fast_cfg)
        return fallback


def create_llm_with_model(config: AppConfig, model_name: str) -> LLM:
    """Create an LLM using the current provider config but with a different model."""
    if config.llm_provider == "groq":
        from infrastructure.llm.groq_llm import GroqLLM
        cfg = config.groq.model_copy(update={"model": model_name})
        logger.info("Using Groq LLM with override: model=%s", model_name)
        return GroqLLM(cfg)
    elif config.llm_provider == "openrouter":
        from infrastructure.llm.openrouter_llm import OpenRouterLLM
        cfg = config.openrouter.model_copy(update={"model": model_name})
        logger.info("Using OpenRouter LLM with override: model=%s", model_name)
        return OpenRouterLLM(cfg)
    elif config.llm_provider == "huggingface":
        from infrastructure.llm.huggingface_llm import HuggingFaceLLM
        cfg = config.huggingface.model_copy(update={"model": model_name})
        logger.info("Using HuggingFace LLM with override: model=%s", model_name)
        return HuggingFaceLLM(cfg)
    elif config.llm_provider == "nvidia":
        from infrastructure.llm.nvidia_llm import NvidiaLLM
        cfg = config.nvidia.model_copy(update={"model": model_name})
        logger.info("Using Nvidia LLM with override: model=%s", model_name)
        return NvidiaLLM(cfg)
    elif config.llm_provider == "gemini":
        from infrastructure.llm.gemini_llm import GeminiLLM
        cfg = config.gemini.model_copy(update={"model": model_name})
        logger.info("Using Gemini LLM with override: model=%s", model_name)
        return GeminiLLM(cfg)
    else:
        from infrastructure.llm.ollama import OllamaLLM
        cfg = config.ollama.model_copy(update={"generation_model": model_name})
        logger.info("Using Ollama LLM with override: model=%s", model_name)
        return OllamaLLM(cfg)


def create_llm_for_agent(provider: str, model: str, api_key: str, config: AppConfig) -> LLM:
    """Create an LLM instance with explicit credentials (api_key + model override).

    Each provider branch creates a ``model_copy`` of its config with the supplied
    *api_key* and *model* overridden so that the returned LLM instance uses the
    provided credentials rather than environment variables.

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
    if provider == "groq":
        from infrastructure.llm.groq_llm import GroqLLM

        cfg = config.groq.model_copy(update={"api_key": api_key, "model": model})
        logger.info("Creating Groq LLM for agent: model=%s", model)
        return GroqLLM(cfg)
    elif provider == "nvidia":
        from infrastructure.llm.nvidia_llm import NvidiaLLM

        cfg = config.nvidia.model_copy(update={"api_key": api_key, "model": model})
        logger.info("Creating Nvidia LLM for agent: model=%s", model)
        return NvidiaLLM(cfg)
    elif provider == "gemini":
        from infrastructure.llm.gemini_llm import GeminiLLM

        cfg = config.gemini.model_copy(update={"api_key": api_key, "model": model})
        logger.info("Creating Gemini LLM for agent: model=%s", model)
        return GeminiLLM(cfg)
    elif provider == "openrouter":
        from infrastructure.llm.openrouter_llm import OpenRouterLLM

        cfg = config.openrouter.model_copy(update={"api_key": api_key, "model": model})
        logger.info("Creating OpenRouter LLM for agent: model=%s", model)
        return OpenRouterLLM(cfg)
    elif provider == "huggingface":
        from infrastructure.llm.huggingface_llm import HuggingFaceLLM

        cfg = config.huggingface.model_copy(update={"api_key": api_key, "model": model})
        logger.info("Creating HuggingFace LLM for agent: model=%s", model)
        return HuggingFaceLLM(cfg)
    elif provider == "ollama":
        from infrastructure.llm.ollama import OllamaLLM

        cfg = config.ollama.model_copy(update={"generation_model": model})
        logger.info("Creating Ollama LLM for agent: model=%s", model)
        return OllamaLLM(cfg)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
