import json
import logging
from typing import Callable

from application.agents._batching import batch_chunks_by_words
from application.agents.base import BaseAgent
from application.prompts import (
    QUESTIONS_CHECKBOX,
    QUESTIONS_MATCHING,
    QUESTIONS_MULTIPLE_CHOICE,
    QUESTIONS_TRUE_FALSE,
)
from core.model.chunk import Chunk
from core.model.question import QuestionType

logger = logging.getLogger(__name__)


class QuestionGeneratorAgent(BaseAgent):
    _MAX_WORDS_PER_BATCH = 2500
    _PROMPTS: dict[str, str] = {
        "true_false": QUESTIONS_TRUE_FALSE,
        "multiple_choice": QUESTIONS_MULTIPLE_CHOICE,
        "matching": QUESTIONS_MATCHING,
        "checkbox": QUESTIONS_CHECKBOX,
    }

    def generate(
        self,
        chunks: list[Chunk],
        question_types: list[QuestionType] | None = None,
        on_progress: Callable[[QuestionType, int, int], None] | None = None,
    ) -> dict[QuestionType, list[dict]]:
        """Generate questions from chunks for the requested types.

        Args:
            chunks: Text chunks to process.
            question_types: Which types to generate. Defaults to all four.
            on_progress: Called after each batch with (question_type, batch_i, total_batches).

        Returns:
            Dict mapping QuestionType to list of validated question_data dicts.
        """
        if question_types is None:
            question_types = ["true_false", "multiple_choice", "matching", "checkbox"]

        text_batches = batch_chunks_by_words(chunks, self._MAX_WORDS_PER_BATCH)
        if not text_batches:
            return {qt: [] for qt in question_types}

        total_batches = len(text_batches)
        results: dict[QuestionType, list[dict]] = {}

        for qtype in question_types:
            prompt = self._PROMPTS[qtype]
            all_items: list[dict] = []

            for batch_i, batch_text in enumerate(text_batches, 1):
                logger.info(
                    "Generating %s questions: batch %d/%d (%d words)",
                    qtype,
                    batch_i,
                    total_batches,
                    len(batch_text.split()),
                )
                raw = self._call_json_with_retry(prompt, batch_text)

                try:
                    parsed = json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    logger.warning(
                        "Could not parse JSON for %s batch %d/%d. Raw (first 300 chars): %s",
                        qtype,
                        batch_i,
                        total_batches,
                        raw[:300],
                    )
                    if on_progress:
                        on_progress(qtype, batch_i, total_batches)
                    continue

                raw_items = parsed.get("questions", [])
                if not isinstance(raw_items, list):
                    logger.warning("'questions' key is not a list for %s batch %d", qtype, batch_i)
                    if on_progress:
                        on_progress(qtype, batch_i, total_batches)
                    continue

                validator = self._get_validator(qtype)
                for item in raw_items:
                    if not isinstance(item, dict):
                        logger.warning("Skipping non-dict item in %s response", qtype)
                        continue
                    if validator(item):
                        all_items.append(item)
                    else:
                        logger.warning(
                            "Skipping invalid %s item: %s", qtype, str(item)[:200]
                        )

                if on_progress:
                    on_progress(qtype, batch_i, total_batches)

            results[qtype] = all_items
            logger.info("Generated %d valid %s questions", len(all_items), qtype)

        return results

    # ---------------------------------------------------------------------------
    # Per-type validators
    # ---------------------------------------------------------------------------

    @staticmethod
    def _validate_true_false(item: dict) -> bool:
        statement = item.get("statement", "")
        answer = item.get("answer")
        if not isinstance(statement, str) or not statement.strip():
            return False
        if not isinstance(answer, bool):
            return False
        if statement.strip().lower().startswith("true or false"):
            return False
        return True

    @staticmethod
    def _validate_multiple_choice(item: dict) -> bool:
        question = item.get("question", "")
        choices = item.get("choices", [])
        correct_index = item.get("correct_index")
        if not isinstance(question, str) or not question.strip():
            return False
        if not isinstance(choices, list) or len(choices) != 4:
            return False
        if not all(isinstance(c, str) and c.strip() for c in choices):
            return False
        if correct_index not in (0, 1, 2, 3):
            return False
        return True

    @staticmethod
    def _validate_matching(item: dict) -> bool:
        pairs = item.get("pairs", [])
        if not isinstance(pairs, list) or not (3 <= len(pairs) <= 6):
            return False
        terms = []
        definitions = []
        for pair in pairs:
            if not isinstance(pair, dict):
                return False
            term = pair.get("term", "")
            definition = pair.get("definition", "")
            if not isinstance(term, str) or not term.strip():
                return False
            if not isinstance(definition, str) or not definition.strip():
                return False
            terms.append(term.strip())
            definitions.append(definition.strip())
        if len(set(terms)) != len(terms):
            return False
        if len(set(definitions)) != len(definitions):
            return False
        return True

    @staticmethod
    def _validate_checkbox(item: dict) -> bool:
        question = item.get("question", "")
        choices = item.get("choices", [])
        correct_indices = item.get("correct_indices", [])
        if not isinstance(question, str) or not question.strip():
            return False
        if not isinstance(choices, list) or not (4 <= len(choices) <= 6):
            return False
        if not all(isinstance(c, str) and c.strip() for c in choices):
            return False
        if not isinstance(correct_indices, list) or not (2 <= len(correct_indices) <= 4):
            return False
        if not all(isinstance(i, int) for i in correct_indices):
            return False
        if not all(0 <= i < len(choices) for i in correct_indices):
            return False
        if len(set(correct_indices)) != len(correct_indices):
            return False
        if set(correct_indices) == set(range(len(choices))):
            return False
        return True

    def _get_validator(self, qtype: QuestionType) -> Callable[[dict], bool]:
        validators = {
            "true_false": self._validate_true_false,
            "multiple_choice": self._validate_multiple_choice,
            "matching": self._validate_matching,
            "checkbox": self._validate_checkbox,
        }
        return validators[qtype]
