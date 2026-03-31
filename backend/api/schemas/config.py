"""Configuration schemas."""

from pydantic import BaseModel


class OllamaConfigOut(BaseModel):
    """Ollama configuration."""

    base_url: str
    generation_model: str
    fast_model: str | None = None
    embedding_model: str
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


class QdrantConfigOut(BaseModel):
    """Qdrant configuration."""

    url: str
    collection_name: str


class Neo4jConfigOut(BaseModel):
    """Neo4j configuration."""

    uri: str
    user: str
    # password not exposed


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
    qdrant: QdrantConfigOut
    neo4j: Neo4jConfigOut
    chunking: ChunkingConfigOut


class ConfigUpdate(BaseModel):
    """Configuration update (optional fields)."""

    llm_provider: str | None = None
    ollama: OllamaConfigOut | None = None
    openrouter: OpenRouterConfigOut | None = None
    huggingface: HuggingFaceConfigOut | None = None
    qdrant: QdrantConfigOut | None = None
    neo4j: Neo4jConfigOut | None = None
    chunking: ChunkingConfigOut | None = None
