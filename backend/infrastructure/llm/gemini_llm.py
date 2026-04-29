import logging
import threading
import time
from collections import deque

import requests

from core.exceptions import RateLimitError
from core.ports.llm import LLM, GenerationParams
from infrastructure.config import GeminiConfig
from infrastructure.llm.task_context import _current_task

logger = logging.getLogger(__name__)


class GeminiRateLimiter:
    """Sliding-window rate limiter for Gemini API requests."""

    def __init__(self, limit: int = 8, threshold: int | None = None):
        self._limit = limit
        self._threshold = threshold if threshold is not None else max(1, limit - 2)
        self._window_seconds = 60
        self._timestamps: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                cutoff = now - self._window_seconds
                while self._timestamps and self._timestamps[0] <= cutoff:
                    self._timestamps.popleft()

                if len(self._timestamps) < self._threshold:
                    self._timestamps.append(now)
                    return

                oldest = self._timestamps[0]
                sleep_for = (oldest + self._window_seconds) - now
                logger.warning(
                    "Gemini rate limit approaching (%d/%d req/min), throttling for %.1fs",
                    len(self._timestamps),
                    self._limit,
                    sleep_for,
                )

            time.sleep(max(sleep_for, 0.1))


class GeminiLLM(LLM):
    """Implements the LLM port using Gemini's OpenAI-compatible REST API."""

    def __init__(self, config: GeminiConfig):
        if not config.api_key:
            raise ValueError(
                "Gemini API key required. "
                "Set DOCASSIST_GEMINI__API_KEY environment variable."
            )
        self._base_url = config.base_url.rstrip("/")
        self._model = config.model
        self._api_key = config.api_key
        self._timeout = config.timeout
        self._max_retries = config.max_retries
        self._max_retries_chat = config.max_retries_chat
        self._rate_limiter = GeminiRateLimiter(limit=config.requests_per_minute)

    def _normalize_model(self, model: str) -> str:
        """Prepend ``models/`` if the model ID doesn't already start with it.

        Gemini's OpenAI-compat endpoint expects model IDs in the
        ``models/gemini-2.5-flash`` format.
        """
        if model.startswith("models/"):
            return model
        return f"models/{model}"

    def _apply_params(self, payload: dict, params: GenerationParams | None) -> None:
        if params is None:
            return
        if params.temperature is not None:
            payload["temperature"] = params.temperature
        if params.top_p is not None:
            payload["top_p"] = params.top_p
        if params.max_tokens is not None:
            payload["max_tokens"] = params.max_tokens

    def generate(self, prompt: str, params: GenerationParams | None = None) -> str:
        payload: dict = {
            "model": self._normalize_model(self._model),
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        self._apply_params(payload, params)
        resp = self._request(payload)
        return resp.json()["choices"][0]["message"]["content"]

    def chat(
        self,
        system: str,
        user: str,
        format: str | None = None,
        params: GenerationParams | None = None,
    ) -> str:
        """Send system + user messages and return the response."""
        effective_system = system
        if format == "json":
            effective_system = (
                system
                + "\n\nRespond with valid JSON only. Do not include any explanation or markdown."
            )

        payload: dict = {
            "model": self._normalize_model(self._model),
            "messages": [
                {"role": "system", "content": effective_system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }
        self._apply_params(payload, params)
        max_retries = self._max_retries if _current_task.get() is not None else self._max_retries_chat
        resp = self._request(payload, max_retries_override=max_retries)
        return resp.json()["choices"][0]["message"]["content"]

    def _request(
        self, payload: dict, stream: bool = False, max_retries_override: int | None = None
    ) -> requests.Response:
        """POST to Gemini with retry logic for 429s."""
        self._rate_limiter.acquire()

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        max_retries = max_retries_override if max_retries_override is not None else self._max_retries
        last_retry_after: float = 60.0

        for attempt in range(max_retries):
            resp = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self._timeout,
                stream=stream,
            )

            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after is not None else 2.0 * (2**attempt)
                last_retry_after = wait
                logger.warning(
                    "Gemini HTTP 429 on attempt %d/%d, retrying in %.1fs",
                    attempt + 1,
                    max_retries,
                    wait,
                )
                task = _current_task.get()
                if task is not None:
                    prev_progress = task.progress
                    task.progress = f"Rate limited by Gemini — retrying in {int(wait)}s"
                    time.sleep(wait)
                    task.progress = prev_progress
                else:
                    time.sleep(wait)
                continue

            if resp.status_code == 401:
                raise ValueError("Invalid or missing Gemini API key")

            if resp.status_code == 404:
                raise ValueError(
                    f"Gemini model '{self._model}' not found (404). "
                    "The model may have been deprecated or renamed. "
                    "Check available models and update your config."
                )

            resp.raise_for_status()
            return resp

        raise RateLimitError(provider="gemini", retry_after=last_retry_after)
