"""Configuration schemas."""

from pydantic import BaseModel


class OllamaConfigOut(BaseModel):
    """Ollama configuration."""

    base_url: str
    generation_model: str
    fast_model: str | None = None
    timeout: int


class OpenRouterConfigOut(BaseModel):
    """OpenRouter configuration (API key excluded)."""

    base_url: str
    model: str
    fast_model: str | None = None
    timeout: int
    max_retries: int


class HuggingFaceConfigOut(BaseModel):
    """HuggingFace configuration (API key excluded)."""

    base_url: str
    model: str
    fast_model: str | None = None
    timeout: int
    max_retries: int
    wait_for_model: bool


class ChunkingConfigOut(BaseModel):
    """Chunking configuration."""

    max_tokens: int
    overlap_tokens: int


class ConfigOut(BaseModel):
    """Full application configuration."""

    llm_provider: str
    ollama: OllamaConfigOut
    openrouter: OpenRouterConfigOut
    huggingface: HuggingFaceConfigOut
    chunking: ChunkingConfigOut


class ConfigUpdate(BaseModel):
    """Configuration update (optional fields)."""

    llm_provider: str | None = None
    ollama: OllamaConfigOut | None = None
    openrouter: OpenRouterConfigOut | None = None
    huggingface: HuggingFaceConfigOut | None = None
    chunking: ChunkingConfigOut | None = None
