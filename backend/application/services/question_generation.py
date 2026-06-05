"""Question generation orchestration."""

import logging
import time
from uuid import UUID

from api.services import Services
from api.tasks import Task, set_task_progress
from application.agents.question_generator import QuestionGeneratorAgent
from application.llm_resolver import resolve_llm_for_agent
from core.model.chunk import Chunk, ChunkMetadata
from core.model.question import Question, QuestionType

logger = logging.getLogger(__name__)


def generate_questions_task(
    task: Task,
    tree_id: UUID,
    chapter_id: UUID,
    chapter_number: int,
    services: Services,
    user_id: UUID,
    requested_types: list[QuestionType] | None = None,
    model: str | None = None,
    agent_id: str | None = None,
    num_questions: int | None = None,
) -> dict:
    """Background task: generate questions for a knowledge chapter."""
    t0 = time.perf_counter()
    try:
        set_task_progress(task, 5, f"Retrieving chunks for chapter {chapter_number}...")
        kt_chunks = services.kt_content_store.get_chunks(tree_id, chapter_number)
        if not kt_chunks:
            raise ValueError(f"No content found for chapter {chapter_number}")

        chunks = [
            Chunk(
                text=kc.text,
                token_count=kc.token_count,
                metadata=ChunkMetadata(
                    source_file=str(kc.tree_id),
                    chapter_index=chapter_number - 1,
                    page_number=0,
                    start_char=0,
                    end_char=0,
                ),
            )
            for kc in kt_chunks
        ]

        set_task_progress(task, 15, "Starting question generation...")
        agent_uid = UUID(agent_id) if agent_id else None
        llm, agent_prompt, _ = resolve_llm_for_agent(
            user_id, agent_uid, services, model_override=model
        )
        agent = QuestionGeneratorAgent(llm)

        types_to_generate: list[QuestionType] = requested_types or [
            "true_false",
            "multiple_choice",
            "matching",
            "checkbox",
        ]
        num_types = len(types_to_generate)
        progress_per_type = (85 - 20) // num_types if num_types > 0 else 65

        type_progress_base = [20]

        def on_progress(qtype: QuestionType, batch_i: int, total_batches: int) -> None:
            base = type_progress_base[0]
            within = int((batch_i / total_batches) * progress_per_type) if total_batches > 0 else 0
            set_task_progress(
                task,
                base + within,
                f"Generating {qtype.replace('_', ' ')} questions... "
                f"batch {batch_i}/{total_batches}",
            )

        all_questions: list[Question] = []
        counts: dict[str, int] = {}

        for i, qtype in enumerate(types_to_generate):
            type_progress_base[0] = 20 + i * progress_per_type
            set_task_progress(
                task,
                type_progress_base[0],
                f"Generating {qtype.replace('_', ' ')} questions...",
            )

            result = agent.generate(
                chunks,
                question_types=[qtype],
                on_progress=on_progress,
                num_questions=num_questions,
                agent_prompt=agent_prompt or None,
            )
            items = result.get(qtype, [])

            for item in items:
                all_questions.append(
                    Question(
                        tree_id=tree_id,
                        chapter_id=chapter_id,
                        question_type=qtype,
                        question_data=item,
                    )
                )
            counts[qtype] = len(items)

        set_task_progress(task, 90, f"Saving {len(all_questions)} questions...")
        if all_questions:
            services.kt_question_store.save_questions(all_questions)

        set_task_progress(task, 100, "Done")
        task.result_excerpt = f"Generated {len(all_questions)} questions"
        elapsed = time.perf_counter() - t0
        logger.info(
            "Generated questions for knowledge chapter %d in %.1fs: %s",
            chapter_number,
            elapsed,
            counts,
        )
        return {"chapter": chapter_number, "counts": counts}
    except Exception as e:
        logger.error("Knowledge question generation failed: %s", e)
        raise
