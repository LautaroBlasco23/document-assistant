from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GenerationParams:
    """Parameters for controlling LLM output generation."""

    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None


class LLM(ABC):
    @abstractmethod
    def generate(self, prompt: str, params: GenerationParams | None = None) -> str:
        """Generate a text completion from a prompt."""

    @abstractmethod
    def chat(
        self,
        system: str,
        user: str,
        format: str | None = None,
        params: GenerationParams | None = None,
    ) -> str:
        """Send a system + user message and return the response."""
