"""
Unit tests for OllamaEmbedder with mocked HTTP calls.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from infrastructure.config import OllamaConfig
from infrastructure.llm.embedding_cache import EmbeddingCache
from infrastructure.llm.ollama import OllamaEmbedder


@pytest.fixture()
def cache(tmp_path: Path) -> EmbeddingCache:
    return EmbeddingCache(tmp_path / "test_embeddings.db")


@pytest.fixture()
def config() -> OllamaConfig:
    return OllamaConfig(
        base_url="http://localhost:11434",
        embedding_model="nomic-embed-text",
    )


def _fake_response(vectors: list[list[float]]):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"embeddings": vectors}
    resp.raise_for_status = MagicMock()
    return resp


def test_embed_returns_correct_dimensions(config, cache):
    expected = [[0.1] * 768, [0.2] * 768]
    with patch("requests.post", return_value=_fake_response(expected)) as mock_post:
        embedder = OllamaEmbedder(config, cache)
        result = embedder.embed(["text one", "text two"])

    assert len(result) == 2
    assert len(result[0]) == 768
    mock_post.assert_called_once()


def test_embed_uses_cache_on_second_call(config, cache):
    expected = [[0.5] * 768]
    with patch("requests.post", return_value=_fake_response(expected)):
        embedder = OllamaEmbedder(config, cache)
        embedder.embed(["cached text"])

    # Second call: should not hit the API
    with patch("requests.post") as mock_post:
        embedder2 = OllamaEmbedder(config, cache)
        result = embedder2.embed(["cached text"])

    mock_post.assert_not_called()
    assert result[0] == [0.5] * 768


def test_embed_batches_large_input(config, cache):
    texts = [f"text {i}" for i in range(70)]
    # Return 32-element batches
    def side_effect(*args, **kwargs):
        body = kwargs.get("json", {})
        n = len(body.get("input", []))
        return _fake_response([[0.1] * 10] * n)

    with patch("requests.post", side_effect=side_effect) as mock_post:
        embedder = OllamaEmbedder(config, cache)
        result = embedder.embed(texts)

    # 70 texts: 3 batches (32 + 32 + 6)
    assert mock_post.call_count == 3
    assert len(result) == 70
