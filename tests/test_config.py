import tempfile
from pathlib import Path

import yaml

from infrastructure.config import AppConfig, load_config


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


def test_fast_model_default_is_none():
    config = load_config()
    assert config.ollama.fast_model is None


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


def test_fast_llm_fallback():
    from infrastructure.llm.ollama import OllamaLLM

    config = load_config()
    assert config.ollama.fast_model is None

    llm = OllamaLLM(config.ollama)

    # When fast_model is None, _make_fast_llm returns the same instance
    from cli.main import _make_fast_llm
    fast_llm = _make_fast_llm(config, llm)
    assert fast_llm is llm
