import logging
import time

import requests

from core.ports.embedder import Embedder
from infrastructure.config import GroqConfig
from infrastructure.llm.embedding_cache import EmbeddingCache
from infrastructure.llm.groq_llm import _rate_limiter

logger = logging.getLogger(__name__)

_EMBED_BATCH_SIZE = 32


class GroqEmbedder(Embedder):
    """Implements the Embedder port using Groq's OpenAI-compatible embeddings endpoint."""

    def __init__(self, config: GroqConfig, cache: EmbeddingCache | None = None):
        if not config.api_key:
            raise ValueError(
                "Groq API key required. Set DOCASSIST_GROQ__API_KEY environment variable."
            )
        self._base_url = config.base_url.rstrip("/")
        self._model = config.embedding_model
        self._api_key = config.api_key
        self._timeout = config.timeout
        self._max_retries = config.max_retries
        self._cache = cache or EmbeddingCache()

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts in batches of 32, using cache when available."""
        results: list[list[float] | None] = [None] * len(texts)
        uncached_indices: list[int] = []

        for i, text in enumerate(texts):
            cached = self._cache.get(text)
            if cached is not None:
                results[i] = cached
            else:
                uncached_indices.append(i)

        for batch_start in range(0, len(uncached_indices), _EMBED_BATCH_SIZE):
            batch_idx = uncached_indices[batch_start : batch_start + _EMBED_BATCH_SIZE]
            batch_texts = [texts[i] for i in batch_idx]

            vectors = self._call_api(batch_texts)
            for idx, vec in zip(batch_idx, vectors):
                results[idx] = vec
                self._cache.set(texts[idx], vec)

        return [v for v in results if v is not None]

    def _call_api(self, texts: list[str]) -> list[list[float]]:
        _rate_limiter.acquire()

        url = f"{self._base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self._model, "input": texts}

        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            resp = requests.post(url, json=payload, headers=headers, timeout=self._timeout)

            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after is not None else 2.0 * (2 ** attempt)
                logger.warning(
                    "Groq embeddings HTTP 429 on attempt %d/%d, retrying in %.1fs",
                    attempt + 1,
                    self._max_retries,
                    wait,
                )
                time.sleep(wait)
                last_exc = requests.HTTPError(response=resp)
                continue

            if resp.status_code == 401:
                raise ValueError("Invalid or missing Groq API key")

            resp.raise_for_status()
            data = resp.json()
            # OpenAI-compatible response: {"data": [{"embedding": [...], "index": 0}, ...]}
            items = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in items]

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Groq embeddings request failed after all retries")
