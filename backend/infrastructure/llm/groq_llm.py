import logging
import threading
import time
from collections import deque

import requests

from core.ports.llm import LLM, GenerationParams
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

    def _apply_params(self, payload: dict, params: GenerationParams | None) -> None:
        """Apply generation parameters to the payload."""
        if params is None:
            return
        if params.temperature is not None:
            payload["temperature"] = params.temperature
        if params.top_p is not None:
            payload["top_p"] = params.top_p
        if params.max_tokens is not None:
            payload["max_tokens"] = params.max_tokens

    def generate(self, prompt: str, params: GenerationParams | None = None) -> str:
        """Generate a completion from a plain prompt string."""
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
        resp = self._request(payload)
        return resp.json()["choices"][0]["message"]["content"]

    def _log_error_response(self, resp: requests.Response) -> None:
        """Log the Groq API error response body for debugging."""
        try:
            err_body = resp.json()
            logger.error("Groq API error (status=%d): %s", resp.status_code, err_body)
        except Exception:
            logger.error("Groq API error (status=%d): %s", resp.status_code, resp.text[:500])

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

            if not resp.ok:
                self._log_error_response(resp)
            resp.raise_for_status()
            return resp

        # All retries exhausted
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Groq request failed after all retries")
