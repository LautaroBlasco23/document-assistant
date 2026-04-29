"""Unit tests for resolve_llm_for_agent."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from application.llm_resolver import resolve_llm_for_agent
from core.exceptions import ProviderNotConfigured


def _make_services(*, encrypted_key=None, config_key="", provider="groq"):
    """Build a minimal mock Services object."""
    services = MagicMock()
    services.config.llm_provider = provider

    # Per-provider config stubs
    for p in ("groq", "openrouter", "huggingface", "nvidia", "gemini"):
        cfg = MagicMock()
        cfg.api_key = config_key if p == provider else ""
        setattr(services.config, p, cfg)

    services.llm_credential_store.get_encrypted_key.return_value = encrypted_key
    services.encryption.decrypt.return_value = "decrypted-key"
    services.agent_store.get_by_id.return_value = None
    return services


@patch("application.llm_resolver.create_llm_for_agent")
def test_env_fallback(mock_create):
    services = _make_services(config_key="admin-key", provider="groq")
    user_id = uuid4()
    resolve_llm_for_agent(user_id, None, services, model_override="llama-3.3-70b-versatile", provider_override="groq")
    mock_create.assert_called_once()
    _, _, api_key, _ = mock_create.call_args[0]
    assert api_key == "admin-key"


@patch("application.llm_resolver.create_llm_for_agent")
def test_user_credential_takes_precedence(mock_create):
    services = _make_services(encrypted_key=b"blob", config_key="admin-key", provider="groq")
    user_id = uuid4()
    resolve_llm_for_agent(user_id, None, services, provider_override="groq", model_override="m")
    # Should decrypt user key, not use admin key
    services.encryption.decrypt.assert_called_once_with(b"blob")
    _, _, api_key, _ = mock_create.call_args[0]
    assert api_key == "decrypted-key"


@patch("application.llm_resolver.create_llm_for_agent")
def test_provider_not_configured_raises(mock_create):
    services = _make_services(encrypted_key=None, config_key="", provider="gemini")
    user_id = uuid4()
    with pytest.raises(ProviderNotConfigured) as exc_info:
        resolve_llm_for_agent(user_id, None, services, provider_override="gemini", model_override="m")
    assert exc_info.value.provider == "gemini"
    mock_create.assert_not_called()


@patch("application.llm_resolver.create_llm_for_agent")
def test_ollama_keyless(mock_create):
    services = _make_services(provider="ollama")
    user_id = uuid4()
    resolve_llm_for_agent(user_id, None, services, provider_override="ollama", model_override="llama3")
    # No credential lookup for ollama
    services.llm_credential_store.get_encrypted_key.assert_not_called()
    _, _, api_key, _ = mock_create.call_args[0]
    assert api_key == ""


@patch("application.llm_resolver.create_llm_for_agent")
def test_agent_id_resolution(mock_create):
    agent = MagicMock()
    agent.provider = "nvidia"
    agent.model = "meta/llama-3.3-70b-instruct"
    agent.prompt = "You are helpful"
    agent.temperature = 0.5
    agent.top_p = 1.0
    agent.max_tokens = 512
    services = _make_services(config_key="nv-key", provider="nvidia")
    services.agent_store.get_by_id.return_value = agent
    user_id = uuid4()
    agent_id = uuid4()
    llm, prompt, params = resolve_llm_for_agent(user_id, agent_id, services)
    assert prompt == "You are helpful"
    assert params.temperature == 0.5
