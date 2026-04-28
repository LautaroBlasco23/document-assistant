import logging
import threading
import time
from collections import deque

import requests

from core.exceptions import RateLimitError
from core.ports.llm import LLM, GenerationParams
from infrastructure.config import GroqConfig
from infrastructure.llm.task_context import _current_task

logger = logging.getLogger(__name__)

# Module-level dict of limiters keyed by (requests_per_minute) so each unique
# config value gets its own singleton bucket shared across all GroqLLM instances
# with that config, while still respecting the configured limit.
_limiters: dict[int, "GroqRateLimiter"] = {}
_limiters_lock = threading.Lock()


def _get_limiter(requests_per_minute: int) -> "GroqRateLimiter":
    with _limiters_lock:
        if requests_per_minute not in _limiters:
            _limiters[requests_per_minute] = GroqRateLimiter(
                limit=requests_per_minute + 5,
                threshold=requests_per_minute,
            )
        return _limiters[requests_per_minute]


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
                cutoff = now - self._window_seconds
                while self._timestamps and self._timestamps[0] <= cutoff:
                    self._timestamps.popleft()

                current_count = len(self._timestamps)

                if current_count < self._threshold:
                    self._timestamps.append(now)
                    return

                oldest = self._timestamps[0]
                sleep_for = (oldest + self._window_seconds) - now
                logger.warning(
                    "Groq rate limit approaching (%d/%d req/min), throttling for %.1fs",
                    current_count,
                    self._limit,
                    sleep_for,
                )

            time.sleep(max(sleep_for, 0.1))


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
        self._max_retries_chat = config.max_retries_chat
        self._rate_limiter = _get_limiter(config.requests_per_minute)

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
            "model": self._model,
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

        payload: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": effective_system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }
        self._apply_params(payload, params)
        # Use fail-fast retry count when called from a foreground/synchronous context
        # (no background task registered in the ContextVar).
        max_retries = self._max_retries if _current_task.get() is not None else self._max_retries_chat
        resp = self._request(payload, max_retries_override=max_retries)
        return resp.json()["choices"][0]["message"]["content"]

    def _log_error_response(self, resp: requests.Response) -> None:
        try:
            err_body = resp.json()
            logger.error("Groq API error (status=%d): %s", resp.status_code, err_body)
        except Exception:
            logger.error("Groq API error (status=%d): %s", resp.status_code, resp.text[:500])

    def _request(
        self, payload: dict, stream: bool = False, max_retries_override: int | None = None
    ) -> requests.Response:
        """POST to Groq with retry logic for 429s."""
        self._rate_limiter.acquire()

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        max_retries = max_retries_override if max_retries_override is not None else self._max_retries
        last_retry_after: float = 60.0
        last_exc: Exception | None = None

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
                    "Groq HTTP 429 on attempt %d/%d, retrying in %.1fs",
                    attempt + 1,
                    max_retries,
                    wait,
                )
                task = _current_task.get()
                if task is not None:
                    prev_progress = task.progress
                    task.progress = f"Rate limited by Groq — retrying in {int(wait)}s"
                    time.sleep(wait)
                    task.progress = prev_progress
                else:
                    time.sleep(wait)
                last_exc = requests.HTTPError(response=resp)
                continue

            if resp.status_code == 401:
                raise ValueError("Invalid or missing Groq API key")

            if not resp.ok:
                self._log_error_response(resp)
            resp.raise_for_status()
            return resp

        raise RateLimitError(provider="groq", retry_after=last_retry_after)
