"""llama-server (llama.cpp) LLM — OpenAI-compatible, local, no auth.

Supports streaming responses with progress tracking, automatic retries for
transient failures (ConnectionError, ReadTimeout, 5xx), and task serialization
to prevent concurrent requests from overwhelming a single-threaded server.
"""

import json
import logging
import threading
import time

import requests

from core.ports.llm import LLM, GenerationParams
from infrastructure.config import LlamaCppConfig
from infrastructure.llm.task_context import _current_task

logger = logging.getLogger(__name__)

# Module-level lock for serializing requests to llama-server.
# Prevents multiple concurrent requests from queuing up and hitting timeouts.
_request_lock = threading.Lock()

# Per-chunk timeout for streaming (seconds). If no data arrives within this
# window, the stream is considered stalled and we abort.
_STREAM_CHUNK_TIMEOUT = 30

# Health check cache — avoid hitting /health on every request
_health_cache: dict[str, tuple[bool, float]] = {}
_HEALTH_CACHE_TTL = 10  # seconds


class LlamaCppLLM(LLM):
    """Implements the LLM port using llama-server's OpenAI-compatible REST API.

    llama-server (part of llama.cpp) exposes ``/v1/chat/completions`` and
    ``/v1/models`` following the OpenAI API spec.  No API key is required.

    Features:
        - Streaming responses with per-chunk timeout and progress tracking
        - Automatic retries for transient failures (ConnectionError, ReadTimeout, 5xx)
        - Request serialization via module-level lock
        - Health check caching
    """

    def __init__(self, config: LlamaCppConfig):
        self._base_url = config.base_url.rstrip("/")
        self._model = config.model
        self._timeout = config.timeout
        self._connect_timeout = config.connect_timeout
        self._max_retries = config.max_retries
        self._max_retries_chat = config.max_retries_chat
        self._streaming = config.streaming

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
            "stream": self._streaming,
        }
        self._apply_params(payload, params)
        if self._streaming:
            return self._request_streaming(payload)
        resp = self._request(payload)
        return resp.json()["choices"][0]["message"]["content"]

    def chat(
        self,
        system: str,
        user: str,
        format: str | None = None,
        params: GenerationParams | None = None,
    ) -> str:
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
            "stream": self._streaming,
        }
        self._apply_params(payload, params)

        if self._streaming:
            return self._request_streaming(payload)
        resp = self._request(payload)
        return resp.json()["choices"][0]["message"]["content"]

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    def _request_streaming(self, payload: dict) -> str:
        """Send a streaming request and accumulate the full response.

        Uses a per-chunk timeout to detect stalled generation, and updates
        the current background task progress as tokens arrive.
        """
        url = f"{self._base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}

        task = _current_task.get()
        max_retries = self._max_retries if task is not None else self._max_retries_chat

        for attempt in range(max_retries):
            try:
                return self._do_streaming(url, payload, headers, task)
            except (
                requests.ConnectionError,
                requests.ReadTimeout,
                requests.exceptions.ChunkedEncodingError,
            ) as exc:
                wait = 2 ** (attempt + 1)  # 2s, 4s, 8s
                if attempt < max_retries - 1:
                    logger.warning(
                        "llama-server streaming error (attempt %d/%d): %s — retrying in %ds",
                        attempt + 1, max_retries, exc, wait,
                    )
                    if task is not None:
                        prev = task.progress
                        task.progress = f"Retrying ({attempt + 2}/{max_retries})..."
                        time.sleep(wait)
                        task.progress = prev
                    else:
                        time.sleep(wait)
                    continue
                raise

        raise RuntimeError(
            f"llama-server streaming request failed after {max_retries} attempts: {url}"
        )

    def _do_streaming(self, url: str, payload: dict, headers: dict, task) -> str:
        """Execute a single streaming request, returning the accumulated text."""
        resp = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=(self._connect_timeout, _STREAM_CHUNK_TIMEOUT),
            stream=True,
        )
        resp.raise_for_status()

        content_parts: list[str] = []
        token_count = 0

        try:
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]  # strip "data: " prefix
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                choices = chunk.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                text = delta.get("content", "")
                if text:
                    content_parts.append(text)
                    token_count += 1

                    # Update task progress every 50 tokens
                    if task is not None and token_count % 50 == 0:
                        task.progress = f"Generating... ~{token_count} tokens"
        finally:
            resp.close()

        result = "".join(content_parts)
        if task is not None:
            task.progress = f"Generated ~{token_count} tokens"

        return result

    # ------------------------------------------------------------------
    # Non-streaming fallback
    # ------------------------------------------------------------------

    def _request(self, payload: dict) -> requests.Response:
        """Non-streaming POST with retries and request serialization."""
        url = f"{self._base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}

        task = _current_task.get()
        max_retries = self._max_retries if task is not None else self._max_retries_chat

        for attempt in range(max_retries):
            try:
                with _request_lock:
                    resp = requests.post(
                        url,
                        json=payload,
                        headers=headers,
                        timeout=(self._connect_timeout, self._timeout),
                    )
                resp.raise_for_status()
                return resp
            except (
                requests.ConnectionError,
                requests.ReadTimeout,
            ) as exc:
                wait = 2 ** (attempt + 1)
                if attempt < max_retries - 1:
                    logger.warning(
                        "llama-server error (attempt %d/%d): %s — retrying in %ds",
                        attempt + 1, max_retries, exc, wait,
                    )
                    if task is not None:
                        prev = task.progress
                        task.progress = f"Retrying ({attempt + 2}/{max_retries})..."
                        time.sleep(wait)
                        task.progress = prev
                    else:
                        time.sleep(wait)
                    continue
                raise
            except requests.HTTPError as exc:
                # Retry on 5xx server errors (not 4xx client errors)
                resp = getattr(exc, "response", None)
                if resp is not None and resp.status_code >= 500 and attempt < max_retries - 1:
                    wait = 2 ** (attempt + 1)
                    logger.warning(
                        "llama-server HTTP %d (attempt %d/%d) — retrying in %ds",
                        resp.status_code, attempt + 1, max_retries, wait,
                    )
                    if task is not None:
                        prev = task.progress
                        task.progress = f"Server error, retrying ({attempt + 2}/{max_retries})..."
                        time.sleep(wait)
                        task.progress = prev
                    else:
                        time.sleep(wait)
                    continue
                raise

        raise RuntimeError(f"llama-server request failed after {max_retries} attempts: {url}")

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def is_healthy(self) -> bool:
        """Check if llama-server is reachable and healthy.

        Results are cached for _HEALTH_CACHE_TTL seconds to avoid hammering
        the endpoint.
        """
        now = time.monotonic()
        cached = _health_cache.get(self._base_url)
        if cached is not None:
            is_ok, ts = cached
            if now - ts < _HEALTH_CACHE_TTL:
                return is_ok

        try:
            health_url = self._base_url.rsplit("/v1", 1)[0] + "/health"
            resp = requests.get(health_url, timeout=self._connect_timeout)
            is_ok = resp.status_code == 200
        except Exception:
            is_ok = False

        _health_cache[self._base_url] = (is_ok, now)
        return is_ok
