import json
import logging
from typing import Callable

from application.agents.base import BaseAgent
from core.model.chunk import Chunk

logger = logging.getLogger(__name__)

_BATCH_SIZE = 4

_SYSTEM = (
    "You are a study-aid generator. Given text excerpts, produce 3-5 question-answer pairs "
    "that test comprehension. You MUST respond with a JSON object containing a single key "
    "'pairs' whose value is an array of objects with 'question' and 'answer' keys.\n"
    'Example: {"pairs": [{"question": "What is X?", "answer": "X is..."}]}'
)


class QuestionGeneratorAgent(BaseAgent):
    def generate(
        self,
        chunks: list[Chunk],
        on_progress: Callable[[int, int, int], None] | None = None,
    ) -> list[dict]:
        """Generate Q&A pairs from chunks.

        Args:
            chunks: List of text chunks to process.
            on_progress: Optional callback called after each batch with
                (batch_number, total_batches, pairs_so_far).
        """
        all_pairs = []
        total_batches = (len(chunks) + _BATCH_SIZE - 1) // _BATCH_SIZE
        for batch_idx in range(0, len(chunks), _BATCH_SIZE):
            batch = chunks[batch_idx : batch_idx + _BATCH_SIZE]
            context = "\n\n".join(c.text for c in batch)
            user = f"Text:\n{context}"
            batch_number = batch_idx // _BATCH_SIZE + 1
            logger.info(
                "Processing batch %d/%d (%d chunks)",
                batch_number,
                total_batches,
                len(batch),
            )
            raw = self._call_json(_SYSTEM, user)
            logger.debug(
                "Batch %d/%d: LLM returned %d chars",
                batch_number,
                total_batches,
                len(raw),
            )
            pairs = self._parse(raw)
            all_pairs.extend(pairs)
            if on_progress:
                on_progress(batch_number, total_batches, len(all_pairs))
        logger.info(
            "Generated %d Q&A pairs from %d chunks (%d batches)",
            len(all_pairs),
            len(chunks),
            total_batches,
        )
        return all_pairs

    @staticmethod
    def _parse(raw: str) -> list[dict]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse Q&A JSON. Raw response (first 500 chars): %s",
                raw[:500],
            )
            return []

        # Handle {"pairs": [...]} wrapper or bare array
        if isinstance(data, dict):
            data = data.get("pairs", data.get("questions", []))
        if not isinstance(data, list):
            logger.warning(
                "Q&A response is not a list. Type: %s, raw (first 500 chars): %s",
                type(data).__name__,
                raw[:500],
            )
            return []

        return [
            {"question": d.get("question", ""), "answer": d.get("answer", "")}
            for d in data
            if isinstance(d, dict) and "question" in d
        ]
