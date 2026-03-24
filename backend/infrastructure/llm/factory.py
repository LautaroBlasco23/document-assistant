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
    else:
        if config.ollama.fast_model:
            from infrastructure.llm.ollama import OllamaLLM
            fast_cfg = config.ollama.model_copy(
                update={"generation_model": config.ollama.fast_model}
            )
            logger.info("Using Ollama fast LLM: model=%s", fast_cfg.generation_model)
            return OllamaLLM(fast_cfg)
        return fallback
