import json
import logging
import time
from typing import Generator

import requests

from core.ports.llm import LLM
from infrastructure.config import OpenRouterConfig

logger = logging.getLogger(__name__)


class OpenRouterLLM(LLM):
    """Implements the LLM port using OpenRouter's OpenAI-compatible REST API.

    OpenRouter requires HTTP-Referer and X-Title headers for free-tier usage.
    Rate limiting is handled reactively via 429 + Retry-After retries only
    (no proactive limiter, since limits vary by model and key tier).
    """

    def __init__(self, config: OpenRouterConfig):
        if not config.api_key:
            raise ValueError(
                "OpenRouter API key required. Set DOCASSIST_OPENROUTER__API_KEY environment variable."
            )
        self._base_url = config.base_url.rstrip("/")
        self._model = config.model
        self._api_key = config.api_key
        self._timeout = config.timeout
        self._max_retries = config.max_retries
        self._site_url = config.site_url
        self._site_name = config.site_name

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
                    # Free-tier models use 60-second rate limit windows.
                    # Short exponential backoff is not enough; wait for the full window.
                    wait = 60.0
                logger.warning(
                    "OpenRouter HTTP 429 on attempt %d/%d, retrying in %.1fs",
                    attempt + 1,
                    self._max_retries,
                    wait,
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
