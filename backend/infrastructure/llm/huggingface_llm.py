import json
import logging
import threading
import time
from typing import Generator

import requests

from core.ports.llm import LLM
from infrastructure.config import HuggingFaceConfig

logger = logging.getLogger(__name__)

# Seconds to sleep before retrying a 503 (model cold start on free tier)
_MODEL_LOADING_RETRY_SLEEP = 10


class HuggingFaceRateLimiter:
    """Sliding-window rate limiter for HuggingFace Inference API requests.

    The free tier allows ~100 req/min globally. Uses a proactive threshold of
    80 req/min to avoid hitting the hard limit, matching the Groq limiter pattern.
    """

    def __init__(self, limit: int = 100, threshold: int = 80):
        self._limit = limit
        self._threshold = threshold
        self._window_seconds = 60
        self._timestamps: list[float] = []
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until a request slot is available, then record the request."""
        while True:
            with self._lock:
                now = time.monotonic()
                cutoff = now - self._window_seconds
                self._timestamps = [t for t in self._timestamps if t > cutoff]

                if len(self._timestamps) < self._threshold:
                    self._timestamps.append(now)
                    return

                oldest = self._timestamps[0]
                sleep_for = (oldest + self._window_seconds) - now
                logger.warning(
                    "HuggingFace rate limit approaching (%d/%d req/min), throttling for %.1fs",
                    len(self._timestamps),
                    self._limit,
                    sleep_for,
                )

            time.sleep(max(sleep_for, 0.1))


# Module-level singleton shared across all HuggingFaceLLM instances
_rate_limiter = HuggingFaceRateLimiter(limit=100, threshold=80)


class HuggingFaceLLM(LLM):
    """Implements the LLM port using HuggingFace's OpenAI-compatible Inference API.

    Uses the serverless free Inference API at https://router.huggingface.co/v1.
    Free-tier models may be cold on first request; retries on 503 (model loading)
    with a fixed sleep. Also retries on 429 (rate limit) with Retry-After backoff.
    """

    def __init__(self, config: HuggingFaceConfig):
        if not config.api_key:
            raise ValueError(
                "HuggingFace API key required. "
                "Set DOCASSIST_HUGGINGFACE__API_KEY environment variable."
            )
        if not config.api_key.startswith("hf_"):
            logger.warning(
                "HuggingFace API key does not start with 'hf_'; "
                "ensure it is a valid HuggingFace user access token."
            )
        self._base_url = config.base_url.rstrip("/")
        self._model = config.model
        self._api_key = config.api_key
        self._timeout = config.timeout
        self._max_retries = config.max_retries
        self._wait_for_model = config.wait_for_model

    def generate(self, prompt: str) -> str:
        """Generate a completion from a plain prompt string."""
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        resp = self._request(payload)
        return resp.json()["choices"][0]["message"]["content"]

    def chat(self, system: str, user: str, format: str | None = None) -> str:
        """Send system + user messages and return the response.

        When format='json', appends an instruction to the system prompt
        for portable JSON enforcement across models.
        """
        effective_system = system
        if format == "json":
            effective_system = (
                system
                + "\n\nRespond with valid JSON only. Do not include any explanation or markdown."
            )

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": effective_system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }
        resp = self._request(payload)
        return resp.json()["choices"][0]["message"]["content"]

    def chat_stream(self, system: str, user: str) -> Generator[str, None, None]:
        """Stream chat response tokens via SSE."""
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": True,
        }
        resp = self._request(payload, stream=True)
        for line in resp.iter_lines():
            if not line:
                continue
            if isinstance(line, bytes):
                line = line.decode("utf-8")
            if line == "data: [DONE]":
                break
            if not line.startswith("data: "):
                continue
            try:
                data = json.loads(line[len("data: "):])
            except json.JSONDecodeError:
                continue
            content = data.get("choices", [{}])[0].get("delta", {}).get("content")
            if content:
                yield content

    def _request(self, payload: dict, stream: bool = False) -> requests.Response:
        """POST to HuggingFace Inference API with retry logic for 429 and 503."""
        # Proactive rate limiting before sending
        _rate_limiter.acquire()

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        # x-wait-for-model tells the API to wait for model loading instead of
        # immediately returning 503, reducing the need for client-side retries.
        if self._wait_for_model:
            headers["x-wait-for-model"] = "true"

        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            resp = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self._timeout,
                stream=stream,
            )

            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                if retry_after is not None:
                    wait = float(retry_after)
                else:
                    wait = 2.0 * (2 ** attempt)  # exponential: 2, 4, 8
                logger.warning(
                    "HuggingFace HTTP 429 on attempt %d/%d, retrying in %.1fs",
                    attempt + 1,
                    self._max_retries,
                    wait,
                )
                time.sleep(wait)
                last_exc = requests.HTTPError(response=resp)
                continue

            if resp.status_code == 503:
                # Model is still loading (cold start on free tier)
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after is not None else _MODEL_LOADING_RETRY_SLEEP
                logger.warning(
                    "HuggingFace HTTP 503 (model loading) on attempt %d/%d, "
                    "retrying in %.1fs",
                    attempt + 1,
                    self._max_retries,
                    wait,
                )
                time.sleep(wait)
                last_exc = requests.HTTPError(response=resp)
                continue

            if resp.status_code == 401:
                raise ValueError("Invalid or missing HuggingFace API key")

            resp.raise_for_status()
            return resp

        # All retries exhausted
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("HuggingFace request failed after all retries")
