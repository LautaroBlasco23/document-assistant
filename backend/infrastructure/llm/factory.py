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
                "OpenRouter API key required. Set DOCASSIST_OPENROUTER__API_KEY environment variable."
            )
        from infrastructure.llm.openrouter_llm import OpenRouterLLM
        logger.info("Using OpenRouter LLM: model=%s", config.openrouter.model)
        return OpenRouterLLM(config.openrouter)
    elif config.llm_provider == "huggingface":
        if not config.huggingface.api_key:
            raise ValueError(
                "HuggingFace API key required. Set DOCASSIST_HUGGINGFACE__API_KEY environment variable."
            )
        from infrastructure.llm.huggingface_llm import HuggingFaceLLM
        logger.info("Using HuggingFace LLM: model=%s", config.huggingface.model)
        return HuggingFaceLLM(config.huggingface)
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
            fast_cfg = config.huggingface.model_copy(update={"model": config.huggingface.fast_model})
            logger.info("Using HuggingFace fast LLM: model=%s", fast_cfg.model)
            return HuggingFaceLLM(fast_cfg)
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
