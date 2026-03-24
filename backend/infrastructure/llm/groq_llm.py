import json
import logging
import threading
import time
from collections import deque
from typing import Generator

import requests

from core.ports.llm import LLM
from infrastructure.config import GroqConfig

logger = logging.getLogger(__name__)


class GroqRateLimiter:
    """Sliding-window rate limiter for Groq API requests.

    Tracks timestamps of recent requests within a 60-second window.
    When the number of requests in the window reaches the threshold,
    the calling thread sleeps until capacity is available.
    """

    def __init__(self, limit: int = 30, threshold: int = 25):
        self._limit = limit
        self._threshold = threshold
        self._window_seconds = 60
        self._timestamps: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until a request slot is available, then record the request."""
        while True:
            with self._lock:
                now = time.monotonic()
                # Expire timestamps older than the window
                cutoff = now - self._window_seconds
                while self._timestamps and self._timestamps[0] <= cutoff:
                    self._timestamps.popleft()

                current_count = len(self._timestamps)

                if current_count < self._threshold:
                    # Capacity available -- record and proceed
                    self._timestamps.append(now)
                    return

                # At or over threshold -- calculate how long to sleep
                oldest = self._timestamps[0]
                sleep_for = (oldest + self._window_seconds) - now
                logger.warning(
                    "Groq rate limit approaching (%d/%d req/min), throttling for %.1fs",
                    current_count,
                    self._limit,
                    sleep_for,
                )

            # Sleep outside the lock so other threads can check
            time.sleep(max(sleep_for, 0.1))


# Module-level singleton shared across all GroqLLM instances
_rate_limiter = GroqRateLimiter(limit=30, threshold=25)


class GroqLLM(LLM):
    """Implements the LLM port using Groq's OpenAI-compatible REST API."""

    def __init__(self, config: GroqConfig):
        if not config.api_key:
            raise ValueError(
                "Groq API key required. Set DOCASSIST_GROQ__API_KEY environment variable."
            )
        self._base_url = config.base_url.rstrip("/")
        self._model = config.model
        self._api_key = config.api_key
        self._timeout = config.timeout
        self._max_retries = config.max_retries

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
        because Groq's json_object mode is model-dependent and prompt-based
        enforcement is more portable.
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
        """POST to Groq with retry logic for 429s."""
        # Proactive rate limiting before sending
        _rate_limiter.acquire()

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

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
                    "Groq HTTP 429 on attempt %d/%d, retrying in %.1fs",
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
            return resp

        # All retries exhausted
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Groq request failed after all retries")
