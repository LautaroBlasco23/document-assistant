import logging
import threading
import time

import requests

from core.exceptions import RateLimitError
from core.ports.llm import LLM, GenerationParams
from infrastructure.config import HuggingFaceConfig
from infrastructure.llm.task_context import _current_task

logger = logging.getLogger(__name__)

_MODEL_LOADING_RETRY_SLEEP = 10

_limiters: dict[int, "HuggingFaceRateLimiter"] = {}
_limiters_lock = threading.Lock()


def _get_limiter(requests_per_minute: int) -> "HuggingFaceRateLimiter":
    with _limiters_lock:
        if requests_per_minute not in _limiters:
            _limiters[requests_per_minute] = HuggingFaceRateLimiter(
                limit=requests_per_minute + 20,
                threshold=requests_per_minute,
            )
        return _limiters[requests_per_minute]


class HuggingFaceRateLimiter:
    """Sliding-window rate limiter for HuggingFace Inference API requests."""

    def __init__(self, limit: int = 100, threshold: int = 80):
        self._limit = limit
        self._threshold = threshold
        self._window_seconds = 60
        self._timestamps: list[float] = []
        self._lock = threading.Lock()

    def acquire(self) -> None:
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


class HuggingFaceLLM(LLM):
    """Implements the LLM port using HuggingFace's OpenAI-compatible Inference API."""

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
        self._max_retries_chat = config.max_retries_chat
        self._wait_for_model = config.wait_for_model
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
        """Send system + user messages and return the response."""
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
        max_retries = self._max_retries if _current_task.get() is not None else self._max_retries_chat
        resp = self._request(payload, max_retries_override=max_retries)
        return resp.json()["choices"][0]["message"]["content"]

    def _request(
        self, payload: dict, stream: bool = False, max_retries_override: int | None = None
    ) -> requests.Response:
        """POST to HuggingFace Inference API with retry logic for 429 and 503."""
        self._rate_limiter.acquire()

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if self._wait_for_model:
            headers["x-wait-for-model"] = "true"

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
                    "HuggingFace HTTP 429 on attempt %d/%d, retrying in %.1fs",
                    attempt + 1,
                    max_retries,
                    wait,
                )
                task = _current_task.get()
                if task is not None:
                    prev_progress = task.progress
                    task.progress = f"Rate limited by HuggingFace — retrying in {int(wait)}s"
                    time.sleep(wait)
                    task.progress = prev_progress
                else:
                    time.sleep(wait)
                last_exc = requests.HTTPError(response=resp)
                continue

            if resp.status_code == 503:
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after is not None else _MODEL_LOADING_RETRY_SLEEP
                logger.warning(
                    "HuggingFace HTTP 503 (model loading) on attempt %d/%d, retrying in %.1fs",
                    attempt + 1,
                    max_retries,
                    wait,
                )
                time.sleep(wait)
                last_exc = requests.HTTPError(response=resp)
                continue

            if resp.status_code == 401:
                raise ValueError("Invalid or missing HuggingFace API key")

            resp.raise_for_status()
            return resp

        raise RateLimitError(provider="huggingface", retry_after=last_retry_after)
