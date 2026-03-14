import requests

from infrastructure.config import OllamaConfig


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
