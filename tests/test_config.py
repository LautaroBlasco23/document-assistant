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
    from pathlib import Path

    config = load_config(Path("/nonexistent/config.yml"))
    assert isinstance(config, AppConfig)
    assert config.ollama.generation_model == "llama3.2"
