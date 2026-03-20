from abc import ABC, abstractmethod
from typing import Generator


class LLM(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate a text completion from a prompt."""

    def chat_stream(self, system: str, user: str) -> Generator[str, None, None]:
        """Stream chat response tokens. Default: yield full response as single token."""
        result = self.generate(f"{system}\n\n{user}")
        yield result
