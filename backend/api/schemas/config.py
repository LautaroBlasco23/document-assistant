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


class GroqConfigOut(BaseModel):
    """Groq configuration (API key excluded)."""

    base_url: str
    model: str
    fast_model: str | None = None
    timeout: int
    max_retries: int


class NvidiaConfigOut(BaseModel):
    """NVIDIA configuration (API key excluded)."""

    base_url: str
    model: str
    fast_model: str | None = None
    timeout: int
    max_retries: int


class GeminiConfigOut(BaseModel):
    """Google Gemini configuration (API key excluded)."""

    base_url: str
    model: str
    fast_model: str | None = None
    timeout: int
    max_retries: int


class ChunkingConfigOut(BaseModel):
    """Chunking configuration."""

    max_tokens: int
    overlap_tokens: int


class ConfigOut(BaseModel):
    """Full application configuration."""

    llm_provider: str
    groq: GroqConfigOut
    nvidia: NvidiaConfigOut
    gemini: GeminiConfigOut
    ollama: OllamaConfigOut
    openrouter: OpenRouterConfigOut
    huggingface: HuggingFaceConfigOut
    chunking: ChunkingConfigOut


class ConfigUpdate(BaseModel):
    """Configuration update (optional fields)."""

    llm_provider: str | None = None
    groq: GroqConfigOut | None = None
    nvidia: NvidiaConfigOut | None = None
    gemini: GeminiConfigOut | None = None
    ollama: OllamaConfigOut | None = None
    openrouter: OpenRouterConfigOut | None = None
    huggingface: HuggingFaceConfigOut | None = None
    chunking: ChunkingConfigOut | None = None
