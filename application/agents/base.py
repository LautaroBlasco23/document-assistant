import logging

from core.ports.llm import LLM

logger = logging.getLogger(__name__)


class BaseAgent:
    def __init__(self, llm: LLM):
        self._llm = llm

    def _call(self, system: str, user: str) -> str:
        """Call the LLM with a system + user prompt."""
        return self._llm.chat(system, user)

    def _call_json(self, system: str, user: str) -> str:
        """Call the LLM with format='json' enforced."""
        return self._llm.chat(system, user, format="json")
