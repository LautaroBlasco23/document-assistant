"""Unit tests for LLM factory.

Subject: infrastructure/llm/factory.py
Scope:   Provider dispatch (create_llm, create_fast_llm), config validation,
          fast-model override logic.
Out of scope:
  - Provider-specific HTTP behavior  → test_<provider>_llm.py files
  - Config loading itself            → test_config.py
Setup:   Uses real config objects with fake API keys.
"""
import pytest

from core.ports.llm import LLM
from infrastructure.config import AppConfig, GroqConfig, HuggingFaceConfig, OpenRouterConfig, OllamaConfig
from infrastructure.llm.factory import create_llm, create_fast_llm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(provider: str = "groq", **kwargs) -> AppConfig:
    """Build an AppConfig with a fake API key for the chosen provider."""
    base = AppConfig(llm_provider=provider)
    if provider == "groq":
        base.groq = GroqConfig(api_key="groq-test-key", model="groq-main", fast_model="groq-fast")
    elif provider == "openrouter":
        base.openrouter = OpenRouterConfig(
            api_key="or-test-key", model="or-main", fast_model="or-fast"
        )
    elif provider == "huggingface":
        base.huggingface = HuggingFaceConfig(
            api_key="hf_testtoken", model="hf-main", fast_model="hf-fast"
        )
    elif provider == "ollama":
        base.ollama = OllamaConfig(generation_model="ollama-main", fast_model="ollama-fast")

    for key, value in kwargs.items():
        setattr(base, key, value)
    return base


# ---------------------------------------------------------------------------
# Test 1: create_llm dispatches to Groq
# ---------------------------------------------------------------------------

def test_create_llm_groq():
    """When llm_provider='groq', create_llm should return a GroqLLM with the main model."""
    config = _make_config("groq")
    llm = create_llm(config)

    from infrastructure.llm.groq_llm import GroqLLM

    assert isinstance(llm, GroqLLM)


# ---------------------------------------------------------------------------
# Test 2: create_llm dispatches to OpenRouter
# ---------------------------------------------------------------------------

def test_create_llm_openrouter():
    """When llm_provider='openrouter', create_llm should return an OpenRouterLLM."""
    config = _make_config("openrouter")
    llm = create_llm(config)

    from infrastructure.llm.openrouter_llm import OpenRouterLLM

    assert isinstance(llm, OpenRouterLLM)


# ---------------------------------------------------------------------------
# Test 3: create_llm dispatches to HuggingFace
# ---------------------------------------------------------------------------

def test_create_llm_huggingface():
    """When llm_provider='huggingface', create_llm should return a HuggingFaceLLM."""
    config = _make_config("huggingface")
    llm = create_llm(config)

    from infrastructure.llm.huggingface_llm import HuggingFaceLLM

    assert isinstance(llm, HuggingFaceLLM)


# ---------------------------------------------------------------------------
# Test 4: create_llm dispatches to Ollama
# ---------------------------------------------------------------------------

def test_create_llm_ollama():
    """When llm_provider='ollama', create_llm should return an OllamaLLM."""
    config = _make_config("ollama")
    llm = create_llm(config)

    from infrastructure.llm.ollama import OllamaLLM

    assert isinstance(llm, OllamaLLM)


# ---------------------------------------------------------------------------
# Test 5: unknown provider raises ValueError
# ---------------------------------------------------------------------------

def test_create_llm_unknown_provider_falls_back_to_ollama():
    """An unsupported provider string falls through to the Ollama branch."""
    config = _make_config("ollama")
    config.llm_provider = "unknown"
    llm = create_llm(config)

    from infrastructure.llm.ollama import OllamaLLM

    assert isinstance(llm, OllamaLLM)


# ---------------------------------------------------------------------------
# Test 6: create_fast_llm uses fast_model for Groq
# ---------------------------------------------------------------------------

def test_create_fast_llm_groq():
    """When groq.fast_model is set, create_fast_llm should return a GroqLLM using it."""
    config = _make_config("groq")
    fallback = create_llm(config)
    fast_llm = create_fast_llm(config, fallback)

    from infrastructure.llm.groq_llm import GroqLLM

    assert isinstance(fast_llm, GroqLLM)
    assert fast_llm is not fallback
    assert fast_llm._model == "groq-fast"


# ---------------------------------------------------------------------------
# Test 7: create_fast_llm falls back when no fast_model for Groq
# ---------------------------------------------------------------------------

def test_create_fast_llm_groq_fallback():
    """When groq.fast_model is None, create_fast_llm should return the fallback LLM."""
    config = _make_config("groq")
    config.groq.fast_model = None
    fallback = create_llm(config)
    fast_llm = create_fast_llm(config, fallback)

    assert fast_llm is fallback


# ---------------------------------------------------------------------------
# Test 8: create_fast_llm uses fast_model for OpenRouter
# ---------------------------------------------------------------------------

def test_create_fast_llm_openrouter():
    """When openrouter.fast_model is set, create_fast_llm should return an OpenRouterLLM using it."""
    config = _make_config("openrouter")
    fallback = create_llm(config)
    fast_llm = create_fast_llm(config, fallback)

    from infrastructure.llm.openrouter_llm import OpenRouterLLM

    assert isinstance(fast_llm, OpenRouterLLM)
    assert fast_llm is not fallback
    assert fast_llm._model == "or-fast"


# ---------------------------------------------------------------------------
# Test 9: create_fast_llm uses fast_model for HuggingFace
# ---------------------------------------------------------------------------

def test_create_fast_llm_huggingface():
    """When huggingface.fast_model is set, create_fast_llm should return a HuggingFaceLLM using it."""
    config = _make_config("huggingface")
    fallback = create_llm(config)
    fast_llm = create_fast_llm(config, fallback)

    from infrastructure.llm.huggingface_llm import HuggingFaceLLM

    assert isinstance(fast_llm, HuggingFaceLLM)
    assert fast_llm is not fallback
    assert fast_llm._model == "hf-fast"


# ---------------------------------------------------------------------------
# Test 10: create_fast_llm uses fast_model for Ollama
# ---------------------------------------------------------------------------

def test_create_fast_llm_ollama():
    """When ollama.fast_model is set, create_fast_llm should return an OllamaLLM using it."""
    config = _make_config("ollama")
    fallback = create_llm(config)
    fast_llm = create_fast_llm(config, fallback)

    from infrastructure.llm.ollama import OllamaLLM

    assert isinstance(fast_llm, OllamaLLM)
    assert fast_llm is not fallback
    assert fast_llm.model == "ollama-fast"


# ---------------------------------------------------------------------------
# Test 11: create_fast_llm falls back for Ollama when no fast_model
# ---------------------------------------------------------------------------

def test_create_fast_llm_ollama_fallback():
    """When ollama.fast_model is None, create_fast_llm should return the fallback LLM."""
    config = _make_config("ollama")
    config.ollama.fast_model = None
    fallback = create_llm(config)
    fast_llm = create_fast_llm(config, fallback)

    assert fast_llm is fallback


# ---------------------------------------------------------------------------
# Test 12: missing Groq API key raises ValueError
# ---------------------------------------------------------------------------

def test_create_llm_groq_missing_key_raises():
    """create_llm should raise ValueError when groq.api_key is empty."""
    config = _make_config("groq")
    config.groq.api_key = ""
    with pytest.raises(ValueError, match="Groq API key required"):
        create_llm(config)


# ---------------------------------------------------------------------------
# Test 13: missing OpenRouter API key raises ValueError
# ---------------------------------------------------------------------------

def test_create_llm_openrouter_missing_key_raises():
    """create_llm should raise ValueError when openrouter.api_key is empty."""
    config = _make_config("openrouter")
    config.openrouter.api_key = ""
    with pytest.raises(ValueError, match="OpenRouter API key required"):
        create_llm(config)


# ---------------------------------------------------------------------------
# Test 14: missing HuggingFace API key raises ValueError
# ---------------------------------------------------------------------------

def test_create_llm_huggingface_missing_key_raises():
    """create_llm should raise ValueError when huggingface.api_key is empty."""
    config = _make_config("huggingface")
    config.huggingface.api_key = ""
    with pytest.raises(ValueError, match="HuggingFace API key required"):
        create_llm(config)
