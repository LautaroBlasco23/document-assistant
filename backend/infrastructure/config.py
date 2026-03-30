import os
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
    embedding_model: str = "nomic-embed-text-v1.5"
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


class ExamConfig(BaseModel):
    cooldown_after_fail_hours: int = 2
    cooldown_completed_days: int = 4
    cooldown_gold_days: int = 14
    cooldown_platinum_days: int = 30


class EpubConfig(BaseModel):
    chapter_depth: int = 1          # ToC depth level that defines "chapters" (1 = top-level only)
    min_chapter_words: int = 100    # Merge items shorter than this into the previous chapter


class AppConfig(BaseSettings):
    ollama: OllamaConfig = OllamaConfig()
    groq: GroqConfig = GroqConfig()
    qdrant: QdrantConfig = QdrantConfig()
    neo4j: Neo4jConfig = Neo4jConfig()
    chunking: ChunkingConfig = ChunkingConfig()
    postgres: PostgresConfig = PostgresConfig()
    exam: ExamConfig = ExamConfig()
    epub: EpubConfig = EpubConfig()
    llm_provider: str = "groq"  # "ollama" | "groq"

    model_config = {"env_prefix": "DOCASSIST_", "env_nested_delimiter": "__"}


PROJECT_ROOT = Path(__file__).parent.parent.parent  # infrastructure → backend → project root


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load config from YAML file, with env var overrides."""
    if config_path is None:
        config_path = PROJECT_ROOT / "config" / "default.yml"

    data: dict = {}
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}

    # pydantic-settings treats __init__ kwargs as highest priority, so YAML
    # data passed via **data would shadow env var overrides for nested models.
    # Manually merge DOCASSIST_* env vars on top so they always win.
    prefix = "DOCASSIST_"
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        parts = key[len(prefix):].lower().split("__")
        node = data
        for part in parts[:-1]:
            if not isinstance(node.get(part), dict):
                node[part] = {}
            node = node[part]
        node[parts[-1]] = value

    return AppConfig(**data)


def save_config(config: AppConfig, config_path: Path | None = None) -> None:
    """Save config to YAML file."""
    if config_path is None:
        config_path = PROJECT_ROOT / "config" / "default.yml"

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
        "embedding_model": config.groq.embedding_model,
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
        "exam": {
            "cooldown_after_fail_hours": config.exam.cooldown_after_fail_hours,
            "cooldown_completed_days": config.exam.cooldown_completed_days,
            "cooldown_gold_days": config.exam.cooldown_gold_days,
            "cooldown_platinum_days": config.exam.cooldown_platinum_days,
        },
        "epub": {
            "chapter_depth": config.epub.chapter_depth,
            "min_chapter_words": config.epub.min_chapter_words,
        },
    }

    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
