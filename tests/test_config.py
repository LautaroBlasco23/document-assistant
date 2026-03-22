import tempfile
from pathlib import Path

import yaml

from infrastructure.config import AppConfig, GroqConfig, load_config


def test_load_default_config():
    config = load_config()
    assert isinstance(config, AppConfig)
    assert config.ollama.base_url == "http://localhost:11434"
    assert config.qdrant.url == "http://localhost:6333"
    assert config.neo4j.uri == "bolt://localhost:7687"
    assert config.chunking.max_tokens == 512
    assert config.chunking.overlap_tokens == 128


def test_load_missing_config():
    config = load_config(Path("/nonexistent/config.yml"))
    assert isinstance(config, AppConfig)
    assert config.ollama.generation_model == "llama3.2"


def test_fast_model_from_yaml():
    data = {
        "ollama": {
            "base_url": "http://localhost:11434",
            "generation_model": "llama3.2",
            "fast_model": "orca-mini:3b",
            "embedding_model": "nomic-embed-text",
            "timeout": 120,
        }
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yml", delete=False
    ) as f:
        yaml.dump(data, f)
        tmp_path = Path(f.name)

    try:
        config = load_config(tmp_path)
        assert config.ollama.fast_model == "orca-mini:3b"
    finally:
        tmp_path.unlink()


def test_default_llm_provider_is_groq():
    """Default provider in default.yml is groq."""
    config = load_config()
    assert config.llm_provider == "groq"


def test_llm_provider_from_yaml():
    """llm_provider field is parsed correctly from YAML."""
    data = {"llm_provider": "ollama"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(data, f)
        tmp_path = Path(f.name)

    try:
        config = load_config(tmp_path)
        assert config.llm_provider == "ollama"
    finally:
        tmp_path.unlink()


def test_groq_config_defaults():
    """GroqConfig default values are sensible."""
    groq = GroqConfig()
    assert groq.base_url == "https://api.groq.com/openai/v1"
    assert groq.model == "mixtral-8x7b-32768"
    assert groq.timeout == 60
    assert groq.max_retries == 3
    assert groq.api_key == ""


def test_groq_config_from_yaml():
    """groq section in YAML is parsed into GroqConfig."""
    data = {
        "groq": {
            "base_url": "https://api.groq.com/openai/v1",
            "model": "mixtral-8x7b-32768",
            "fast_model": "llama-3.1-8b-instant",
            "timeout": 60,
            "max_retries": 3,
        }
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(data, f)
        tmp_path = Path(f.name)

    try:
        config = load_config(tmp_path)
        assert config.groq.model == "mixtral-8x7b-32768"
        assert config.groq.fast_model == "llama-3.1-8b-instant"
        assert config.groq.timeout == 60
    finally:
        tmp_path.unlink()


def test_groq_api_key_env_override(monkeypatch):
    """DOCASSIST_GROQ__API_KEY env var overrides the empty default."""
    monkeypatch.setenv("DOCASSIST_GROQ__API_KEY", "sk-test-key")
    config = AppConfig()
    assert config.groq.api_key == "sk-test-key"


def test_fast_llm_fallback_via_factory():
    """create_fast_llm returns main LLM when no fast_model is set."""
    from unittest.mock import MagicMock

    from infrastructure.llm.factory import create_fast_llm

    data = {"llm_provider": "ollama", "ollama": {"fast_model": None}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(data, f)
        tmp_path = Path(f.name)

    try:
        config = load_config(tmp_path)
        fake_llm = MagicMock()
        fast_llm = create_fast_llm(config, fake_llm)
        assert fast_llm is fake_llm
    finally:
        tmp_path.unlink()
