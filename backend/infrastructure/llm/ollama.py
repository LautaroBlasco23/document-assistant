import json
import logging
from typing import Generator

import requests

from core.ports.llm import LLM
from infrastructure.config import OllamaConfig

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, config: OllamaConfig):
        self.base_url = config.base_url.rstrip("/")
        self.timeout = config.timeout

    def is_healthy(self) -> bool:
        """Check if Ollama is reachable."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except requests.ConnectionError:
            return False

    def list_models(self) -> list[str]:
        """List available models."""
        resp = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        return [m["name"] for m in data.get("models", [])]


class OllamaLLM(LLM):
    """Implements the LLM port using Ollama's /api/generate endpoint."""

    def __init__(self, config: OllamaConfig):
        self._base_url = config.base_url.rstrip("/")
        self.model = config.generation_model
        self.timeout = config.timeout

    @property
    def base_url(self) -> str:
        """Access to base URL."""
        return self._base_url

    def generate(self, prompt: str) -> str:
        resp = requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()["response"]

    def chat(self, system: str, user: str, format: str | None = None) -> str:
        """Convenience method for system+user prompt pattern.

        Args:
            system: System prompt.
            user: User message.
            format: Optional Ollama format constraint (e.g. "json").
        """
        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }
        if format is not None:
            payload["format"] = format
        resp = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    def chat_stream(self, system: str, user: str) -> Generator[str, None, None]:
        """Stream chat response tokens from Ollama one at a time."""
        resp = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": True,
            },
            timeout=self.timeout,
            stream=True,
        )
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if parsed.get("done") is True:
                break
            content = parsed.get("message", {}).get("content", "")
            if content:
                yield content
