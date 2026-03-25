"""Exam results and chapter progression endpoints."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from api.deps import ServicesDep
from api.schemas.exams import ChapterExamStatusOut, ExamResultOut, SubmitExamRequest
from core.model.exam import ExamResult
from infrastructure.config import ExamConfig

logger = logging.getLogger(__name__)

router = APIRouter()

_LEVEL_NAMES = {0: "none", 1: "completed", 2: "gold", 3: "platinum"}


def _compute_status(
    chapter_1based: int,
    results: list[ExamResult],
    level: int,
    exam_cfg: ExamConfig,
) -> ChapterExamStatusOut:
    """Compute ChapterExamStatusOut from exam results and current level."""
    if not results:
        return ChapterExamStatusOut(
            chapter=chapter_1based,
            level=level,
            level_name=_LEVEL_NAMES[level],
            last_exam_at=None,
            cooldown_until=None,
            can_take_exam=True,
        )

    last = results[0]  # already ordered by completed_at DESC
    last_at_utc = last.completed_at.replace(tzinfo=timezone.utc)
    last_exam_at_str = last_at_utc.isoformat()

    if not last.passed:
        cooldown = timedelta(hours=exam_cfg.cooldown_after_fail_hours)
    elif level == 1:
        cooldown = timedelta(days=exam_cfg.cooldown_completed_days)
    elif level == 2:
        cooldown = timedelta(days=exam_cfg.cooldown_gold_days)
    else:
        # level == 3 (Platinum) or higher
        cooldown = timedelta(days=exam_cfg.cooldown_platinum_days)

    cooldown_until_dt = last_at_utc + cooldown
    now = datetime.now(tz=timezone.utc)

    if now >= cooldown_until_dt:
        return ChapterExamStatusOut(
            chapter=chapter_1based,
            level=level,
            level_name=_LEVEL_NAMES[level],
            last_exam_at=last_exam_at_str,
            cooldown_until=None,
            can_take_exam=True,
        )

    return ChapterExamStatusOut(
        chapter=chapter_1based,
        level=level,
        level_name=_LEVEL_NAMES[level],
        last_exam_at=last_exam_at_str,
        cooldown_until=cooldown_until_dt.isoformat(),
        can_take_exam=False,
    )


@router.post("/exams", response_model=ExamResultOut)
async def submit_exam(req: SubmitExamRequest, services: ServicesDep) -> ExamResultOut:
    """Submit a completed exam session. chapter is 1-based."""
    chapter_index = req.chapter - 1  # convert to 0-based
    passed = req.correct_count == req.total_cards

    result = ExamResult(
        document_hash=req.document_hash,
        chapter_index=chapter_index,
        total_cards=req.total_cards,
        correct_count=req.correct_count,
        passed=passed,
    )
    services.content_store.save_exam_result(result)

    logger.info(
        "Exam submitted doc=%s chapter=%d passed=%s (%d/%d)",
        req.document_hash[:12],
        req.chapter,
        passed,
        req.correct_count,
        req.total_cards,
    )

    return ExamResultOut(
        id=result.id,
        chapter=req.chapter,
        total_cards=result.total_cards,
        correct_count=result.correct_count,
        passed=result.passed,
        completed_at=result.completed_at.replace(tzinfo=timezone.utc).isoformat(),
    )


@router.get("/documents/{file_hash}/exam-status", response_model=list[ChapterExamStatusOut])
async def get_exam_status(
    file_hash: str, services: ServicesDep
) -> list[ChapterExamStatusOut]:
    """Get exam status for all chapters of a document that have exam history."""
    exam_cfg = services.config.exam

    # Query distinct chapter_indexes from exam_results for this document

    conn = services.content_store._conn()  # type: ignore[attr-defined]
    with conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT chapter_index FROM exam_results WHERE document_hash = %s"
            " ORDER BY chapter_index",
            (file_hash,),
        )
        rows = cur.fetchall()

    statuses: list[ChapterExamStatusOut] = []
    for row in rows:
        chapter_index = row["chapter_index"]
        chapter_1based = chapter_index + 1
        results = services.content_store.get_exam_results(file_hash, chapter_index)
        level = services.content_store.get_chapter_level(file_hash, chapter_index)
        status = _compute_status(chapter_1based, results, level, exam_cfg)
        statuses.append(status)

    return statuses


@router.get("/documents/{file_hash}/exam-status/{chapter}", response_model=ChapterExamStatusOut)
async def get_exam_status_for_chapter(
    file_hash: str, chapter: int, services: ServicesDep
) -> ChapterExamStatusOut:
    """Get exam status for a specific chapter (1-based)."""
    exam_cfg = services.config.exam
    chapter_index = chapter - 1  # convert to 0-based

    results = services.content_store.get_exam_results(file_hash, chapter_index)
    level = services.content_store.get_chapter_level(file_hash, chapter_index)

    return _compute_status(chapter, results, level, exam_cfg)
