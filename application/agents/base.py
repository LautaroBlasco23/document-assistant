import logging
import re

from core.ports.llm import LLM

logger = logging.getLogger(__name__)

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL)


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences that some LLMs add despite instructions."""
    stripped = text.strip()
    m = _CODE_FENCE_RE.match(stripped)
    return m.group(1).strip() if m else stripped


class BaseAgent:
    def __init__(self, llm: LLM):
        self._llm = llm

    def _call(self, system: str, user: str) -> str:
        """Call the LLM with a system + user prompt."""
        return self._llm.chat(system, user)

    def _call_json(self, system: str, user: str) -> str:
        """Call the LLM with format='json' enforced, stripping any code fences."""
        raw = self._llm.chat(system, user, format="json")
        return _strip_code_fences(raw)
