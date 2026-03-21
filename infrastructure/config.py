from pathlib import Path

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class OllamaConfig(BaseModel):
    base_url: str = "http://localhost:11434"
    generation_model: str = "llama3.2"
    fast_model: str | None = None
    embedding_model: str = "nomic-embed-text"
    timeout: int = 120


class QdrantConfig(BaseModel):
    url: str = "http://localhost:6333"
    collection_name: str = "documents"


class Neo4jConfig(BaseModel):
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "document_assistant_pass"


class ChunkingConfig(BaseModel):
    max_tokens: int = 512
    overlap_tokens: int = 128


class AppConfig(BaseSettings):
    ollama: OllamaConfig = OllamaConfig()
    qdrant: QdrantConfig = QdrantConfig()
    neo4j: Neo4jConfig = Neo4jConfig()
    chunking: ChunkingConfig = ChunkingConfig()

    model_config = {"env_prefix": "DOCASSIST_", "env_nested_delimiter": "__"}


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load config from YAML file, with env var overrides."""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "default.yml"

    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        return AppConfig(**data)

    return AppConfig()


def save_config(config: AppConfig, config_path: Path | None = None) -> None:
    """Save config to YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "default.yml"

    config_path.parent.mkdir(parents=True, exist_ok=True)

    ollama_data: dict = {
        "base_url": config.ollama.base_url,
        "generation_model": config.ollama.generation_model,
        "embedding_model": config.ollama.embedding_model,
        "timeout": config.ollama.timeout,
    }
    if config.ollama.fast_model:
        ollama_data["fast_model"] = config.ollama.fast_model

    data = {
        "ollama": ollama_data,
        "qdrant": {
            "url": config.qdrant.url,
            "collection_name": config.qdrant.collection_name,
        },
        "neo4j": {
            "uri": config.neo4j.uri,
            "user": config.neo4j.user,
            "password": config.neo4j.password,
        },
        "chunking": {
            "max_tokens": config.chunking.max_tokens,
            "overlap_tokens": config.chunking.overlap_tokens,
        },
    }

    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
