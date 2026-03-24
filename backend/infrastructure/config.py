from pathlib import Path

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class OllamaConfig(BaseModel):
    base_url: str = "http://localhost:11434"
    generation_model: str = "llama3.2"
    fast_model: str | None = None
    embedding_model: str = "nomic-embed-text"
    timeout: int = 300


class GroqConfig(BaseModel):
    api_key: str = ""                               # set via DOCASSIST_GROQ__API_KEY
    base_url: str = "https://api.groq.com/openai/v1"
    model: str = "mixtral-8x7b-32768"
    fast_model: str | None = None                   # e.g. "llama-3.1-8b-instant"
    timeout: int = 60
    max_retries: int = 3                            # for 429 backoff


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


class PostgresConfig(BaseModel):
    host: str = "localhost"
    port: int = 5432
    database: str = "docassist"
    user: str = "docassist"
    password: str = "docassist_pass"


class AppConfig(BaseSettings):
    ollama: OllamaConfig = OllamaConfig()
    groq: GroqConfig = GroqConfig()
    qdrant: QdrantConfig = QdrantConfig()
    neo4j: Neo4jConfig = Neo4jConfig()
    chunking: ChunkingConfig = ChunkingConfig()
    postgres: PostgresConfig = PostgresConfig()
    llm_provider: str = "groq"  # "ollama" | "groq"

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

    groq_data: dict = {
        "base_url": config.groq.base_url,
        "model": config.groq.model,
        "timeout": config.groq.timeout,
        "max_retries": config.groq.max_retries,
    }
    if config.groq.fast_model:
        groq_data["fast_model"] = config.groq.fast_model
    # api_key is never written to YAML -- set via env var

    data = {
        "llm_provider": config.llm_provider,
        "ollama": ollama_data,
        "groq": groq_data,
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
        "postgres": {
            "host": config.postgres.host,
            "port": config.postgres.port,
            "database": config.postgres.database,
            "user": config.postgres.user,
            "password": config.postgres.password,
        },
    }

    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
