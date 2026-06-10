import os
from pathlib import Path

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class OllamaConfig(BaseModel):
    base_url: str = "http://localhost:11434"
    generation_model: str = ""
    fast_model: str | None = None
    timeout: int = 300


class GroqConfig(BaseModel):
    api_key: str = ""  # set via DOCASSIST_GROQ__API_KEY
    base_url: str = "https://api.groq.com/openai/v1"
    model: str = ""
    fast_model: str | None = None
    timeout: int = 60
    max_retries: int = 3  # for 429 backoff in background tasks
    max_retries_chat: int = 1  # fail-fast for synchronous chat
    requests_per_minute: int = 25  # proactive rate limiter threshold


class OpenRouterConfig(BaseModel):
    api_key: str = ""  # set via DOCASSIST_OPENROUTER__API_KEY
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = ""
    fast_model: str | None = None
    timeout: int = 120  # some models are slower
    max_retries: int = 3
    max_retries_chat: int = 1  # fail-fast for synchronous chat
    requests_per_minute: int = 10  # proactive rate limiter; reduce for :free models
    site_url: str = ""  # optional HTTP-Referer for OpenRouter rankings
    site_name: str = ""  # optional X-Title for OpenRouter rankings


class HuggingFaceConfig(BaseModel):
    api_key: str = ""  # set via DOCASSIST_HUGGINGFACE__API_KEY (hf_ token)
    base_url: str = "https://router.huggingface.co/v1"
    model: str = ""
    fast_model: str | None = None
    timeout: int = 180  # free tier can be slow (model loading)
    max_retries: int = 3
    max_retries_chat: int = 1  # fail-fast for synchronous chat
    requests_per_minute: int = 80  # proactive rate limiter threshold
    wait_for_model: bool = True  # send x-wait-for-model header


class NvidiaConfig(BaseModel):
    api_key: str = ""  # set via DOCASSIST_NVIDIA__API_KEY
    base_url: str = "https://integrate.api.nvidia.com/v1"
    model: str = ""
    fast_model: str | None = None
    timeout: int = 120
    max_retries: int = 3
    max_retries_chat: int = 1  # fail-fast for synchronous chat
    requests_per_minute: int = 35  # proactive rate limiter threshold


class GeminiConfig(BaseModel):
    api_key: str = ""  # set via DOCASSIST_GEMINI__API_KEY
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    model: str = ""
    fast_model: str | None = None
    timeout: int = 120
    max_retries: int = 3
    max_retries_chat: int = 1  # fail-fast for synchronous chat
    requests_per_minute: int = 8  # Flash has hard 250 RPD cap


class LlamaCppConfig(BaseModel):
    base_url: str = "http://localhost:8080/v1"
    model: str = ""
    fast_model: str | None = None
    timeout: int = 300


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


class AuthConfig(BaseModel):
    jwt_secret: str = ""  # Set via DOCASSIST_AUTH__JWT_SECRET
    encryption_key: str = ""  # Set via DOCASSIST_AUTH__ENCRYPTION_KEY (32-byte url-safe base64)
    token_expire_days: int = 7


class AppConfig(BaseSettings):
    ollama: OllamaConfig = OllamaConfig()
    groq: GroqConfig = GroqConfig()
    openrouter: OpenRouterConfig = OpenRouterConfig()
    huggingface: HuggingFaceConfig = HuggingFaceConfig()
    nvidia: NvidiaConfig = NvidiaConfig()
    gemini: GeminiConfig = GeminiConfig()
    llamacpp: LlamaCppConfig = LlamaCppConfig()
    chunking: ChunkingConfig = ChunkingConfig()
    postgres: PostgresConfig = PostgresConfig()
    exam: ExamConfig = ExamConfig()
    epub: EpubConfig = EpubConfig()
    auth: AuthConfig = AuthConfig()
    llm_provider: str = ""
    # supported: ollama | groq | openrouter | huggingface | nvidia | gemini | llamacpp
    flashcard_model: str = "main"  # "main" | "fast"

    model_config = {
        "env_prefix": "DOCASSIST_",
        "env_nested_delimiter": "__",
        "extra": "ignore",
    }


# 3 levels up: project root (host) or / (Docker)
_candidate = Path(__file__).resolve().parent.parent.parent
if not (_candidate / "docker-compose.yml").is_file():
    # Docker: 3 levels gives /, but app root is /app (2 levels from __file__)
    _candidate = Path(__file__).resolve().parent.parent  # = /app in Docker
PROJECT_ROOT = _candidate


def _config_path() -> Path:
    p = PROJECT_ROOT / "config" / "default.yml"
    if not p.exists():
        p = Path("/config/default.yml")  # Docker fallback
    return p


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load config from YAML file, with env var overrides."""
    if config_path is None:
        config_path = _config_path()

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
        config_path = _config_path()

    config_path.parent.mkdir(parents=True, exist_ok=True)

    data = config.model_dump(mode="json")

    # Never persist secrets -- they are set via env vars
    data.pop("auth", None)
    for section in ("groq", "openrouter", "huggingface", "nvidia", "gemini"):
        data[section].pop("api_key", None)

    # Remove empty optional fields to keep YAML clean
    _prune_empty(data.get("ollama", {}), "fast_model")
    _prune_empty(data.get("groq", {}), "fast_model")
    _prune_empty(data.get("openrouter", {}), "fast_model", "site_url", "site_name")
    _prune_empty(data.get("huggingface", {}), "fast_model")
    _prune_empty(data.get("nvidia", {}), "fast_model")
    _prune_empty(data.get("gemini", {}), "fast_model")
    _prune_empty(data.get("llamacpp", {}), "fast_model")

    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)


def _prune_empty(section: dict, *keys: str) -> None:
    """Remove keys with None or empty-string values from a config section."""
    for key in keys:
        val = section.get(key)
        if val is None or val == "":
            section.pop(key, None)
