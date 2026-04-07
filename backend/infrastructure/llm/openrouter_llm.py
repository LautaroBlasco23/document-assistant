import logging
import threading
import time
from collections import deque

import requests

from core.ports.llm import LLM
from infrastructure.config import OpenRouterConfig

logger = logging.getLogger(__name__)


class OpenRouterRateLimiter:
    """Sliding-window rate limiter for OpenRouter free-tier models.

    Uses a threshold of (limit - 2) to proactively throttle before hitting the
    configured requests_per_minute limit, avoiding 429 cascades during bulk tasks.
    """

    def __init__(self, limit: int = 10, threshold: int | None = None):
        self._limit = limit
        self._threshold = threshold if threshold is not None else max(1, limit - 2)
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

                if len(self._timestamps) < self._threshold:
                    self._timestamps.append(now)
                    return

                oldest = self._timestamps[0]
                sleep_for = (oldest + self._window_seconds) - now
                logger.warning(
                    "OpenRouter rate limit approaching (%d/%d req/min), throttling for %.1fs",
                    len(self._timestamps),
                    self._limit,
                    sleep_for,
                )

            time.sleep(max(sleep_for, 0.1))


class OpenRouterLLM(LLM):
    """Implements the LLM port using OpenRouter's OpenAI-compatible REST API.

    OpenRouter requires HTTP-Referer and X-Title headers for free-tier usage.
    Rate limiting is handled proactively via a sliding-window limiter (configurable
    via `requests_per_minute`) plus reactive 429 retries as a safety net.
    """

    def __init__(self, config: OpenRouterConfig):
        if not config.api_key:
            raise ValueError(
                "OpenRouter API key required. "
                "Set DOCASSIST_OPENROUTER__API_KEY environment variable."
            )
        self._base_url = config.base_url.rstrip("/")
        self._model = config.model
        self._api_key = config.api_key
        self._timeout = config.timeout
        self._max_retries = config.max_retries
        self._site_url = config.site_url
        self._site_name = config.site_name
        self._rate_limiter = OpenRouterRateLimiter(limit=config.requests_per_minute)

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

    def _request(self, payload: dict, stream: bool = False) -> requests.Response:
        """POST to OpenRouter with retry logic for 429s."""
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        # Free-tier required headers for OpenRouter rankings/leaderboards
        if self._site_url:
            headers["HTTP-Referer"] = self._site_url
        if self._site_name:
            headers["X-Title"] = self._site_name

        last_exc: Exception | None = None
        ignored_providers: list[str] = []
        for attempt in range(self._max_retries):
            # Allow OpenRouter to route to an alternative provider when one is rate-limited.
            # Exclude any providers that have already returned 429 this request.
            provider_opts: dict = {"allow_fallbacks": True}
            if ignored_providers:
                provider_opts["ignore"] = ignored_providers
            attempt_payload = {**payload, "provider": provider_opts}

            self._rate_limiter.acquire()
            resp = requests.post(
                url,
                json=attempt_payload,
                headers=headers,
                timeout=self._timeout,
                stream=stream,
            )

            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                if retry_after is not None:
                    wait = float(retry_after)
                else:
                    # Free-tier models use 60-second rate limit windows.
                    # Short exponential backoff is not enough; wait for the full window.
                    wait = 60.0
                try:
                    error_body = resp.json()
                except Exception:
                    error_body = resp.text[:500]

                # If a specific upstream provider is rate-limiting us, exclude it
                # from future retries so OpenRouter routes to a different provider.
                if isinstance(error_body, dict):
                    provider_name = (
                        error_body.get("error", {})
                        .get("metadata", {})
                        .get("provider_name")
                    )
                    if provider_name and provider_name not in ignored_providers:
                        ignored_providers.append(provider_name)
                        logger.warning(
                            "OpenRouter HTTP 429 on attempt %d/%d from provider '%s', "
                            "excluding it and retrying immediately. Response: %s",
                            attempt + 1,
                            self._max_retries,
                            provider_name,
                            error_body,
                        )
                        last_exc = requests.HTTPError(response=resp)
                        continue

                logger.warning(
                    "OpenRouter HTTP 429 on attempt %d/%d, retrying in %.1fs. Response: %s",
                    attempt + 1,
                    self._max_retries,
                    wait,
                    error_body,
                )
                time.sleep(wait)
                last_exc = requests.HTTPError(response=resp)
                continue

            if resp.status_code == 401:
                raise ValueError("Invalid or missing OpenRouter API key")

            if resp.status_code == 404:
                raise ValueError(
                    f"OpenRouter model '{self._model}' not found (404). "
                    "The model may have been deprecated or renamed. "
                    "Check available models at https://openrouter.ai/models and update your config."
                )

            resp.raise_for_status()
            return resp

        # All retries exhausted
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("OpenRouter request failed after all retries")
