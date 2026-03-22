import json
import logging
from typing import Callable

from application.agents.base import BaseAgent
from core.model.chunk import Chunk

logger = logging.getLogger(__name__)

_BATCH_SIZE = 4

_SYSTEM = (
    "You are an expert educator creating study questions based on Bloom's Taxonomy. "
    "Given text from a book chapter, generate questions that help the reader deeply "
    "understand and retain the material.\n\n"
    "Generate EXACTLY 6 question-answer pairs covering these cognitive levels:\n"
    "- 2 REMEMBER questions: Test recall of specific facts, definitions, or details "
    "directly stated in the text. Start with: 'What is...', 'Define...', 'List...', "
    "'Who/When/Where...'\n"
    "- 2 UNDERSTAND questions: Test comprehension of concepts and relationships. "
    "Start with: 'Explain...', 'Why does...', 'How does... relate to...', "
    "'What is the difference between...', 'Summarize...'\n"
    "- 2 APPLY/ANALYZE questions: Test ability to use knowledge or break down ideas. "
    "Start with: 'How would you apply...', 'What would happen if...', "
    "'Compare and contrast...', 'What evidence supports...'\n\n"
    "Rules:\n"
    "- Every question MUST be answerable from the provided text alone.\n"
    "- Answers should be specific and reference details from the text (not vague or generic).\n"
    "- Do NOT create questions about study exercises, glossary items, or instructional "
    "material that may be embedded in the text.\n"
    "- Include page references when available.\n\n"
    "You MUST respond with a JSON object containing a single key 'pairs' whose value "
    "is an array of objects with 'question', 'answer', and 'level' keys.\n"
    "Valid levels: 'remember', 'understand', 'apply_analyze'\n\n"
    'Example: {"pairs": ['
    '{"question": "What is X?", "answer": "X is... (p.12)", "level": "remember"}, '
    '{"question": "Explain why X matters", "answer": "X matters because...", "level": "understand"}'
    "]}"
)


class QuestionGeneratorAgent(BaseAgent):
    def generate(
        self,
        chunks: list[Chunk],
        on_progress: Callable[[int, int, int], None] | None = None,
        chapter_title: str = "",
        document_title: str = "",
    ) -> list[dict]:
        """Generate Q&A pairs from chunks using Bloom's Taxonomy.

        Args:
            chunks: List of text chunks to process.
            on_progress: Optional callback called after each batch with
                (batch_number, total_batches, pairs_so_far).
            chapter_title: Title of the chapter for context.
            document_title: Title of the document for context.
        """
        all_pairs = []
        total_batches = (len(chunks) + _BATCH_SIZE - 1) // _BATCH_SIZE

        # Build context header
        header_parts = []
        if document_title:
            header_parts.append(f"Document: {document_title}")
        if chapter_title:
            header_parts.append(f"Chapter: {chapter_title}")
        header = "\n".join(header_parts)

        for batch_idx in range(0, len(chunks), _BATCH_SIZE):
            batch = chunks[batch_idx : batch_idx + _BATCH_SIZE]
            context = "\n\n".join(
                f"[p.{c.metadata.page_number if c.metadata else '?'}] {c.text}"
                for c in batch
            )
            user = f"{header}\n\nText:\n{context}" if header else f"Text:\n{context}"
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
            {
                "question": d.get("question", ""),
                "answer": d.get("answer", ""),
                "level": d.get("level", "remember"),
            }
            for d in data
            if isinstance(d, dict) and "question" in d
        ]
