from abc import ABC, abstractmethod


class LLM(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate a text completion from a prompt."""

    @abstractmethod
    def chat(self, system: str, user: str, format: str | None = None) -> str:
        """Send a system + user message and return the response."""
