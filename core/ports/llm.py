from abc import ABC, abstractmethod


class LLM(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate a text completion from a prompt."""
