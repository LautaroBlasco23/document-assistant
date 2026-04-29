"""Central resolver: maps (user_id, agent_id) → (LLM, prompt, GenerationParams)."""

import logging
from uuid import UUID

from core.exceptions import ProviderNotConfigured
from core.ports.llm import GenerationParams
from infrastructure.llm.factory import create_llm_for_agent

logger = logging.getLogger(__name__)

_KNOWN_PROVIDERS = frozenset({"groq", "openrouter", "huggingface", "nvidia", "gemini", "ollama"})


def resolve_llm_for_agent(
    user_id: UUID,
    agent_id: UUID | None,
    services,
    *,
    model_override: str | None = None,
    provider_override: str | None = None,
) -> tuple:  # (LLM, prompt | None, GenerationParams | None)
    """
    Resolve the correct LLM instance for a user + agent combination.

    Resolution order:
    1. If agent_id is given → fetch agent; use agent.provider + agent.model
    2. If provider_override + model_override → use those directly
    3. Fall back to global config provider + model_override (or default model)
    """
    provider = None
    model = None
    prompt = None
    params = None

    if agent_id is not None:
        agent = services.agent_store.get_by_id(agent_id)
        if agent is None:
            raise ValueError(f"Agent {agent_id} not found")
        provider = agent.provider
        model = agent.model
        prompt = agent.prompt or None
        params = GenerationParams(
            temperature=agent.temperature,
            top_p=agent.top_p,
            max_tokens=agent.max_tokens,
        )
    elif provider_override:
        provider = provider_override
        model = model_override or ""
    else:
        provider = services.config.llm_provider
        model = model_override or ""

    api_key = _resolve_api_key(user_id, provider, services)
    llm = create_llm_for_agent(provider, model, api_key, services.config)
    return llm, prompt, params


def _resolve_api_key(user_id: UUID, provider: str, services) -> str:
    """
    Look up the API key for (user_id, provider).

    Priority:
    1. Per-user encrypted credential from DB
    2. Env-var / config fallback (admin key)
    3. Ollama: no key needed → return ""
    4. Raise ProviderNotConfigured
    """
    if provider == "ollama":
        return ""

    # Per-user credential
    encrypted = services.llm_credential_store.get_encrypted_key(user_id, provider)
    if encrypted is not None:
        return services.encryption.decrypt(encrypted)

    # Admin env-var fallback
    fallback = _get_config_key(provider, services.config)
    if fallback:
        logger.debug("Using admin env-var key for provider=%s user=%s", provider, user_id)
        return fallback

    raise ProviderNotConfigured(provider)


def _get_config_key(provider: str, config) -> str:
    """Read the operator-level API key for a provider from AppConfig."""
    mapping = {
        "groq": lambda c: c.groq.api_key,
        "openrouter": lambda c: c.openrouter.api_key,
        "huggingface": lambda c: c.huggingface.api_key,
        "nvidia": lambda c: c.nvidia.api_key,
        "gemini": lambda c: c.gemini.api_key,
    }
    getter = mapping.get(provider)
    if getter is None:
        return ""
    try:
        return getter(config) or ""
    except AttributeError:
        return ""
