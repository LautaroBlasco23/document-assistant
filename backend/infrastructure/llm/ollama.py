import logging

import requests

from core.ports.llm import LLM, GenerationParams
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

    def _apply_params(self, payload: dict, params: GenerationParams | None) -> None:
        """Apply generation parameters to the Ollama payload."""
        if params is None:
            return
        opts: dict = {}
        if params.temperature is not None:
            opts["temperature"] = params.temperature
        if params.top_p is not None:
            opts["top_p"] = params.top_p
        if params.max_tokens is not None:
            opts["num_predict"] = params.max_tokens
        if opts:
            payload["options"] = opts

    def generate(self, prompt: str, params: GenerationParams | None = None) -> str:
        payload: dict = {"model": self.model, "prompt": prompt, "stream": False}
        self._apply_params(payload, params)
        resp = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()["response"]

    def chat(
        self,
        system: str,
        user: str,
        format: str | None = None,
        params: GenerationParams | None = None,
    ) -> str:
        """Convenience method for system+user prompt pattern.

        Args:
            system: System prompt.
            user: User message.
            format: Optional Ollama format constraint (e.g. "json").
            params: Optional generation parameters.
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
        self._apply_params(payload, params)
        resp = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]

