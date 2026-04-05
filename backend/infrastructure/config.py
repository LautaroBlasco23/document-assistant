import os
from pathlib import Path

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class OllamaConfig(BaseModel):
    base_url: str = "http://localhost:11434"
    generation_model: str = "llama3.2"
    fast_model: str | None = None
    timeout: int = 300


class GroqConfig(BaseModel):
    api_key: str = ""  # set via DOCASSIST_GROQ__API_KEY
    base_url: str = "https://api.groq.com/openai/v1"
    model: str = "mixtral-8x7b-32768"
    fast_model: str | None = None  # e.g. "llama-3.1-8b-instant"
    timeout: int = 60
    max_retries: int = 3  # for 429 backoff


class OpenRouterConfig(BaseModel):
    api_key: str = ""  # set via DOCASSIST_OPENROUTER__API_KEY
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "meta-llama/llama-3.3-70b-instruct:free"
    fast_model: str | None = None  # e.g. "google/gemma-2-9b-it:free"
    timeout: int = 120  # some models are slower
    max_retries: int = 3
    requests_per_minute: int = 10  # proactive rate limiter; reduce for :free models
    site_url: str = ""  # optional HTTP-Referer for OpenRouter rankings
    site_name: str = ""  # optional X-Title for OpenRouter rankings


class HuggingFaceConfig(BaseModel):
    api_key: str = ""  # set via DOCASSIST_HUGGINGFACE__API_KEY (hf_ token)
    base_url: str = "https://router.huggingface.co/v1"
    model: str = "mistralai/Mistral-7B-Instruct-v0.3"
    fast_model: str | None = None
    timeout: int = 120  # free tier can be slow (model loading)
    max_retries: int = 3
    wait_for_model: bool = True  # send x-wait-for-model header


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
    chapter_depth: int = 1  # ToC depth level that defines "chapters" (1 = top-level only)
    min_chapter_words: int = 100  # Merge items shorter than this into the previous chapter


class AppConfig(BaseSettings):
    ollama: OllamaConfig = OllamaConfig()
    groq: GroqConfig = GroqConfig()
    openrouter: OpenRouterConfig = OpenRouterConfig()
    huggingface: HuggingFaceConfig = HuggingFaceConfig()
    chunking: ChunkingConfig = ChunkingConfig()
    postgres: PostgresConfig = PostgresConfig()
    exam: ExamConfig = ExamConfig()
    epub: EpubConfig = EpubConfig()
    llm_provider: str = "groq"  # "ollama" | "groq" | "openrouter" | "huggingface"
    flashcard_model: str = "main"  # "main" | "fast"

    model_config = {
        "env_prefix": "DOCASSIST_",
        "env_nested_delimiter": "__",
        "extra": "ignore",
    }


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
        parts = key[len(prefix) :].lower().split("__")
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

    openrouter_data: dict = {
        "base_url": config.openrouter.base_url,
        "model": config.openrouter.model,
        "timeout": config.openrouter.timeout,
        "max_retries": config.openrouter.max_retries,
    }
    if config.openrouter.fast_model:
        openrouter_data["fast_model"] = config.openrouter.fast_model
    if config.openrouter.site_url:
        openrouter_data["site_url"] = config.openrouter.site_url
    if config.openrouter.site_name:
        openrouter_data["site_name"] = config.openrouter.site_name
    # api_key is never written to YAML -- set via env var

    huggingface_data: dict = {
        "base_url": config.huggingface.base_url,
        "model": config.huggingface.model,
        "timeout": config.huggingface.timeout,
        "max_retries": config.huggingface.max_retries,
        "wait_for_model": config.huggingface.wait_for_model,
    }
    if config.huggingface.fast_model:
        huggingface_data["fast_model"] = config.huggingface.fast_model
    # api_key is never written to YAML -- set via env var

    data = {
        "llm_provider": config.llm_provider,
        "flashcard_model": config.flashcard_model,
        "ollama": ollama_data,
        "groq": groq_data,
        "openrouter": openrouter_data,
        "huggingface": huggingface_data,
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
