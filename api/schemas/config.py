"""Configuration schemas."""

from pydantic import BaseModel


class OllamaConfigOut(BaseModel):
    """Ollama configuration."""

    base_url: str
    generation_model: str
    embedding_model: str
    timeout: int


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

    ollama: OllamaConfigOut
    qdrant: QdrantConfigOut
    neo4j: Neo4jConfigOut
    chunking: ChunkingConfigOut


class ConfigUpdate(BaseModel):
    """Configuration update (optional fields)."""

    ollama: OllamaConfigOut | None = None
    qdrant: QdrantConfigOut | None = None
    neo4j: Neo4jConfigOut | None = None
    chunking: ChunkingConfigOut | None = None
