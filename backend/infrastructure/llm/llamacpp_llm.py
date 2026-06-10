"""llama-server (llama.cpp) LLM — OpenAI-compatible, local, no auth."""

import logging
import time

import requests

from core.ports.llm import LLM, GenerationParams
from infrastructure.config import LlamaCppConfig
from infrastructure.llm.task_context import _current_task

logger = logging.getLogger(__name__)


class LlamaCppLLM(LLM):
    """Implements the LLM port using llama-server's OpenAI-compatible REST API.

    llama-server (part of llama.cpp) exposes ``/v1/chat/completions`` and
    ``/v1/models`` following the OpenAI API spec.  No API key is required.
    """

    def __init__(self, config: LlamaCppConfig):
        self._base_url = config.base_url.rstrip("/")
        self._model = config.model
        self._timeout = config.timeout

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

    def _request(self, payload: dict) -> requests.Response:
        url = f"{self._base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}

        task = _current_task.get()
        for attempt in range(2):
            try:
                resp = requests.post(
                    url, json=payload, headers=headers, timeout=self._timeout,
                )
                resp.raise_for_status()
                return resp
            except requests.ConnectionError:
                if attempt == 0:
                    logger.warning(
                        "llama-server unreachable at %s, retrying in 2s", url,
                    )
                    if task is not None:
                        prev = task.progress
                        task.progress = "Waiting for llama-server..."
                        time.sleep(2)
                        task.progress = prev
                    else:
                        time.sleep(2)
                    continue
                raise

        # Unreachable — the loop either returns on success or raises on second ConnectionError
        raise RuntimeError(f"llama-server request failed: {url}")
