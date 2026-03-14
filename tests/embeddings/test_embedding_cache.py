from pathlib import Path

import pytest

from infrastructure.llm.embedding_cache import EmbeddingCache


@pytest.fixture()
def cache(tmp_path: Path) -> EmbeddingCache:
    return EmbeddingCache(tmp_path / "test.db")


def test_cache_miss_returns_none(cache):
    assert cache.get("unknown text") is None


def test_cache_set_and_get(cache):
    vec = [0.1, 0.2, 0.3]
    cache.set("hello world", vec)
    assert cache.get("hello world") == vec


def test_cache_different_texts_independent(cache):
    cache.set("text a", [1.0])
    cache.set("text b", [2.0])
    assert cache.get("text a") == [1.0]
    assert cache.get("text b") == [2.0]


def test_cache_overwrite(cache):
    cache.set("key", [1.0, 2.0])
    cache.set("key", [9.0])
    assert cache.get("key") == [9.0]
