import logging

from core.ports.llm import LLM

logger = logging.getLogger(__name__)


class BaseAgent:
    def __init__(self, llm: LLM):
        self._llm = llm

    def _call(self, system: str, user: str) -> str:
        """Call the LLM with a system + user prompt."""
        if hasattr(self._llm, "chat"):
            return self._llm.chat(system, user)
        # Fallback: concatenate into a single prompt
        return self._llm.generate(f"{system}\n\n{user}")
