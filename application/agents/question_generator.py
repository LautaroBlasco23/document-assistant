import json
import logging

from application.agents.base import BaseAgent
from core.model.chunk import Chunk

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a study-aid generator. Given text excerpts, produce 5–10 question-answer pairs "
    "that test comprehension. Return ONLY a JSON array of objects with 'question' and 'answer' "
    "keys. Example: [{\"question\": \"What is X?\", \"answer\": \"X is...\"}]"
)


class QuestionGeneratorAgent(BaseAgent):
    def generate(self, chunks: list[Chunk]) -> list[dict]:
        context = "\n\n".join(c.text for c in chunks)
        user = f"Text:\n{context}"
        raw = self._call(_SYSTEM, user)

        pairs = self._parse(raw)
        logger.info("Generated %d Q&A pairs from %d chunks", len(pairs), len(chunks))
        return pairs

    @staticmethod
    def _parse(raw: str) -> list[dict]:
        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end == -1:
            return []
        try:
            data = json.loads(raw[start : end + 1])
            return [
                {"question": d.get("question", ""), "answer": d.get("answer", "")}
                for d in data
                if isinstance(d, dict) and "question" in d
            ]
        except json.JSONDecodeError:
            logger.warning("Failed to parse Q&A JSON")
            return []
