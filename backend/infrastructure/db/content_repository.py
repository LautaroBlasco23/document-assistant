import json
import logging
import threading
from datetime import datetime, timezone

import psycopg
from psycopg.pq import TransactionStatus

from core.model.chunk import Chunk, ChunkMetadata
from core.model.document_metadata import DocumentMetadata
from core.model.exam import ExamResult
from core.model.generated_content import Flashcard, Summary
from core.ports.content_store import ContentStore
from infrastructure.db.postgres import PostgresPool

logger = logging.getLogger(__name__)


class PostgresContentStore(ContentStore):
    """PostgreSQL implementation of the ContentStore port."""

    def __init__(self, pool: PostgresPool):
        self._pool = pool
        # Single connection shared across threads; lock prevents concurrent writes
        self._lock = threading.Lock()

    def _conn(self) -> psycopg.Connection:
        conn = self._pool.connection()
        if conn.info.transaction_status == TransactionStatus.INERROR:
            conn.rollback()
        return conn

    @staticmethod
    def _rollback_if_failed(conn: psycopg.Connection) -> None:
        """Roll back any aborted transaction so the connection can be reused."""
        if conn.info.transaction_status == TransactionStatus.INERROR:
            conn.rollback()

    # --- Summaries ---

    def get_summary(self, document_hash: str, chapter_index: int) -> Summary | None:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT content, description, bullets, created_at FROM summaries"
                " WHERE document_hash = %s AND chapter_index = %s",
                (document_hash, chapter_index),
            )
            row = cur.fetchone()
        if row is None:
            return None
        raw_bullets = row["bullets"]
        try:
            bullets = json.loads(raw_bullets) if raw_bullets else []
        except (json.JSONDecodeError, TypeError):
            bullets = []
        description = row["description"] or ""
        # Recover from JSON-stringified description (legacy/corrupted data)
        if description.startswith("{"):
            try:
                inner = json.loads(description)
                if isinstance(inner, dict):
                    description = inner.get("description", description)
                    inner_bullets = inner.get("bullets")
                    if isinstance(inner_bullets, list) and not bullets:
                        bullets = inner_bullets
            except (json.JSONDecodeError, TypeError):
                pass  # Keep original description
        return Summary(
            document_hash=document_hash,
            chapter_index=chapter_index,
            content=row["content"],
            description=description,
            bullets=bullets,
            created_at=_ensure_naive(row["created_at"]),
        )

    def get_summaries(self, document_hash: str) -> list[Summary]:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT chapter_index, content, description, bullets, created_at FROM summaries"
                " WHERE document_hash = %s ORDER BY chapter_index",
                (document_hash,),
            )
            rows = cur.fetchall()
        result = []
        for row in rows:
            raw_bullets = row["bullets"]
            try:
                bullets = json.loads(raw_bullets) if raw_bullets else []
            except (json.JSONDecodeError, TypeError):
                bullets = []
            description = row["description"] or ""
            # Recover from JSON-stringified description (legacy/corrupted data)
            if description.startswith("{"):
                try:
                    inner = json.loads(description)
                    if isinstance(inner, dict):
                        description = inner.get("description", description)
                        inner_bullets = inner.get("bullets")
                        if isinstance(inner_bullets, list) and not bullets:
                            bullets = inner_bullets
                except (json.JSONDecodeError, TypeError):
                    pass  # Keep original description
            result.append(
                Summary(
                    document_hash=document_hash,
                    chapter_index=row["chapter_index"],
                    content=row["content"],
                    description=description,
                    bullets=bullets,
                    created_at=_ensure_naive(row["created_at"]),
                )
            )
        return result

    def save_summary(self, summary: Summary) -> None:
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO summaries"
                        " (document_hash, chapter_index, content, description, bullets, created_at)"
                        " VALUES (%s, %s, %s, %s, %s, %s)"
                        " ON CONFLICT (document_hash, chapter_index)"
                        " DO UPDATE SET content = EXCLUDED.content,"
                        " description = EXCLUDED.description,"
                        " bullets = EXCLUDED.bullets,"
                        " created_at = EXCLUDED.created_at",
                        (
                            summary.document_hash,
                            summary.chapter_index,
                            summary.content,
                            summary.description,
                            json.dumps(summary.bullets),
                            summary.created_at,
                        ),
                    )
        logger.debug(
            "Saved summary doc=%s chapter=%d", summary.document_hash[:12], summary.chapter_index
        )

    # --- Flashcards ---

    def get_flashcards(
        self,
        document_hash: str,
        chapter_index: int | None = None,
        status: str | None = "approved",
    ) -> list[Flashcard]:
        conn = self._conn()
        with conn.cursor() as cur:
            conditions = ["document_hash = %s"]
            params: list = [document_hash]
            if chapter_index is not None:
                conditions.append("chapter_index = %s")
                params.append(chapter_index)
            if status is not None:
                conditions.append("status = %s")
                params.append(status)
            where = " AND ".join(conditions)
            cur.execute(
                f"SELECT id, chapter_index, front, back,"
                f" source_page, source_chunk_id, source_text, status, created_at"
                f" FROM flashcards WHERE {where} ORDER BY created_at",
                params,
            )
            rows = cur.fetchall()
        return [
            Flashcard(
                id=str(row["id"]),
                document_hash=document_hash,
                chapter_index=row["chapter_index"],
                front=row["front"],
                back=row["back"],
                source_page=row["source_page"],
                source_chunk_id=row["source_chunk_id"] or "",
                source_text=row["source_text"] or "",
                status=row["status"] or "pending",
                created_at=_ensure_naive(row["created_at"]),
            )
            for row in rows
        ]

    def save_flashcards(self, flashcards: list[Flashcard]) -> None:
        if not flashcards:
            return
        doc_hash = flashcards[0].document_hash
        chapter_index = flashcards[0].chapter_index
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    # Delete existing flashcards for this chapter before inserting new ones
                    cur.execute(
                        "DELETE FROM flashcards WHERE document_hash = %s AND chapter_index = %s",
                        (doc_hash, chapter_index),
                    )
                    for card in flashcards:
                        cur.execute(
                            "INSERT INTO flashcards"
                            " (id, document_hash, chapter_index, front, back,"
                            "  source_page, source_chunk_id, source_text, status, created_at)"
                            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            (
                                card.id,
                                card.document_hash,
                                card.chapter_index,
                                card.front,
                                card.back,
                                card.source_page,
                                card.source_chunk_id,
                                card.source_text,
                                card.status,
                                card.created_at,
                            ),
                        )
        logger.debug(
            "Saved %d flashcards doc=%s chapter=%d", len(flashcards), doc_hash[:12], chapter_index
        )

    def approve_flashcards(self, flashcard_ids: list[str]) -> int:
        if not flashcard_ids:
            return 0
        with self._lock:
            conn = self._conn()
            self._rollback_if_failed(conn)
            with conn.transaction():
                with conn.cursor() as cur:
                    placeholders = ",".join(["%s"] * len(flashcard_ids))
                    cur.execute(
                        f"UPDATE flashcards SET status = 'approved' WHERE id IN ({placeholders})",
                        flashcard_ids,
                    )
                    count = cur.rowcount
        logger.debug("Approved %d flashcards", count)
        return count

    def delete_flashcards_by_ids(self, flashcard_ids: list[str]) -> int:
        if not flashcard_ids:
            return 0
        with self._lock:
            conn = self._conn()
            self._rollback_if_failed(conn)
            with conn.transaction():
                with conn.cursor() as cur:
                    placeholders = ",".join(["%s"] * len(flashcard_ids))
                    cur.execute(
                        f"DELETE FROM flashcards WHERE id IN ({placeholders})",
                        flashcard_ids,
                    )
                    count = cur.rowcount
        logger.debug("Deleted %d flashcards by IDs", count)
        return count

    def approve_all_flashcards(self, document_hash: str, chapter_index: int | None = None) -> int:
        with self._lock:
            conn = self._conn()
            self._rollback_if_failed(conn)
            with conn.transaction():
                with conn.cursor() as cur:
                    if chapter_index is not None:
                        cur.execute(
                            "UPDATE flashcards SET status = 'approved'"
                            " WHERE document_hash = %s AND chapter_index = %s"
                            " AND status = 'pending'",
                            (document_hash, chapter_index),
                        )
                    else:
                        cur.execute(
                            "UPDATE flashcards SET status = 'approved'"
                            " WHERE document_hash = %s AND status = 'pending'",
                            (document_hash,),
                        )
                    count = cur.rowcount
        logger.debug(
            "Approved all pending flashcards for doc=%s chapter=%s: %d updated",
            document_hash[:12],
            chapter_index,
            count,
        )
        return count

    # --- Metadata ---

    def get_metadata(self, document_hash: str) -> DocumentMetadata | None:
        conn = self._conn()
        self._rollback_if_failed(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT description, document_type, file_extension "
                "FROM document_metadata WHERE document_hash = %s",
                (document_hash,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return DocumentMetadata(
            description=row["description"] or "",
            document_type=row["document_type"] or "",
            file_extension=row["file_extension"] or "",
        )

    def save_metadata(self, document_hash: str, metadata: DocumentMetadata) -> None:
        with self._lock:
            conn = self._conn()
            self._rollback_if_failed(conn)
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO document_metadata"
                        " (document_hash, description, document_type, file_extension, updated_at)"
                        " VALUES (%s, %s, %s, %s, NOW())"
                        " ON CONFLICT (document_hash)"
                        " DO UPDATE SET description = EXCLUDED.description,"
                        " document_type = EXCLUDED.document_type,"
                        " file_extension = COALESCE("
                        "   EXCLUDED.file_extension,"
                        "   document_metadata.file_extension"
                        " ),"
                        " updated_at = NOW()",
                        (
                            document_hash,
                            metadata.description,
                            metadata.document_type,
                            metadata.file_extension,
                        ),
                    )
        logger.debug("Saved metadata for doc=%s", document_hash[:12])

    # --- Cleanup ---

    def delete_by_document(self, document_hash: str) -> None:
        with self._lock:
            conn = self._conn()
            self._rollback_if_failed(conn)
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM summaries WHERE document_hash = %s", (document_hash,))
                    cur.execute("DELETE FROM flashcards WHERE document_hash = %s", (document_hash,))
                    cur.execute(
                        "DELETE FROM document_metadata WHERE document_hash = %s", (document_hash,)
                    )
                    cur.execute(
                        "DELETE FROM exam_results WHERE document_hash = %s", (document_hash,)
                    )
                    cur.execute(
                        "DELETE FROM custom_documents WHERE document_hash = %s", (document_hash,)
                    )
                    cur.execute(
                        "DELETE FROM document_content WHERE file_hash = %s", (document_hash,)
                    )
                    cur.execute(
                        "DELETE FROM document_chunks WHERE file_hash = %s", (document_hash,)
                    )
        logger.debug("Deleted all content for doc=%s", document_hash[:12])

    def delete_summary(self, document_hash: str, chapter_index: int) -> None:
        with self._lock:
            conn = self._conn()
            self._rollback_if_failed(conn)
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM summaries WHERE document_hash = %s AND chapter_index = %s",
                        (document_hash, chapter_index),
                    )
        logger.debug("Deleted summary for doc=%s chapter=%d", document_hash[:12], chapter_index)

    def delete_chapter(self, document_hash: str, chapter_index: int) -> None:
        with self._lock:
            conn = self._conn()
            self._rollback_if_failed(conn)
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM summaries WHERE document_hash = %s AND chapter_index = %s",
                        (document_hash, chapter_index),
                    )
                    cur.execute(
                        "DELETE FROM flashcards WHERE document_hash = %s AND chapter_index = %s",
                        (document_hash, chapter_index),
                    )
                    cur.execute(
                        "DELETE FROM exam_results WHERE document_hash = %s AND chapter_index = %s",
                        (document_hash, chapter_index),
                    )
                    cur.execute(
                        "DELETE FROM document_chunks WHERE file_hash = %s AND chapter_index = %s",
                        (document_hash, chapter_index),
                    )
        logger.debug("Deleted chapter %d content for doc=%s", chapter_index, document_hash[:12])

    # --- Exam results ---

    def save_exam_result(self, result: ExamResult) -> None:
        with self._lock:
            conn = self._conn()
            self._rollback_if_failed(conn)
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO exam_results"
                        " (id, document_hash, chapter_index,"
                        "  total_cards, correct_count, passed, completed_at)"
                        " VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (
                            result.id,
                            result.document_hash,
                            result.chapter_index,
                            result.total_cards,
                            result.correct_count,
                            result.passed,
                            result.completed_at,
                        ),
                    )
        logger.debug(
            "Saved exam result doc=%s chapter=%d passed=%s",
            result.document_hash[:12],
            result.chapter_index,
            result.passed,
        )

    def get_exam_results(self, document_hash: str, chapter_index: int) -> list[ExamResult]:
        conn = self._conn()
        self._rollback_if_failed(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, total_cards, correct_count, passed, completed_at FROM exam_results"
                " WHERE document_hash = %s AND chapter_index = %s"
                " ORDER BY completed_at DESC",
                (document_hash, chapter_index),
            )
            rows = cur.fetchall()
        return [
            ExamResult(
                id=str(row["id"]),
                document_hash=document_hash,
                chapter_index=chapter_index,
                total_cards=row["total_cards"],
                correct_count=row["correct_count"],
                passed=row["passed"],
                completed_at=_ensure_naive(row["completed_at"]),
            )
            for row in rows
        ]

    def get_chapter_level(self, document_hash: str, chapter_index: int) -> int:
        conn = self._conn()
        self._rollback_if_failed(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS pass_count FROM exam_results"
                " WHERE document_hash = %s AND chapter_index = %s AND passed = true",
                (document_hash, chapter_index),
            )
            row = cur.fetchone()
        count = row["pass_count"] if row else 0
        return min(int(count), 3)

    def reset_exam_progress(self, document_hash: str, chapter_index: int) -> None:
        with self._lock:
            conn = self._conn()
            self._rollback_if_failed(conn)
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM exam_results WHERE document_hash = %s AND chapter_index = %s",
                        (document_hash, chapter_index),
                    )
        logger.debug("Reset exam progress for doc=%s chapter=%d", document_hash[:12], chapter_index)

    # --- Custom documents ---

    def save_custom_document(self, document_hash: str, title: str, content: str) -> None:
        with self._lock:
            conn = self._conn()
            self._rollback_if_failed(conn)
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO custom_documents (document_hash, title, content)"
                        " VALUES (%s, %s, %s)"
                        " ON CONFLICT (document_hash)"
                        " DO UPDATE SET content = EXCLUDED.content, updated_at = NOW()",
                        (document_hash, title, content),
                    )
        logger.debug("Saved custom document doc=%s", document_hash[:12])

    def get_custom_document(self, document_hash: str) -> tuple[str, str] | None:
        conn = self._conn()
        self._rollback_if_failed(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT title, content FROM custom_documents WHERE document_hash = %s",
                (document_hash,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return (row["title"], row["content"])

    def append_custom_document(self, document_hash: str, new_content: str) -> str:
        with self._lock:
            conn = self._conn()
            self._rollback_if_failed(conn)
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE custom_documents"
                        " SET content = content || E'\\n\\n' || %s, updated_at = NOW()"
                        " WHERE document_hash = %s"
                        " RETURNING content",
                        (new_content, document_hash),
                    )
                    row = cur.fetchone()
            if row is None:
                raise ValueError("Custom document not found")
            return row["content"]

    def delete_custom_document(self, document_hash: str) -> None:
        with self._lock:
            conn = self._conn()
            self._rollback_if_failed(conn)
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM custom_documents WHERE document_hash = %s",
                        (document_hash,),
                    )
        logger.debug("Deleted custom document doc=%s", document_hash[:12])

    # --- Document content ---

    def get_content(self, file_hash: str) -> str | None:
        conn = self._conn()
        self._rollback_if_failed(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT content FROM document_content WHERE file_hash = %s",
                (file_hash,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return row["content"]

    def save_content(self, file_hash: str, content: str) -> None:
        with self._lock:
            conn = self._conn()
            self._rollback_if_failed(conn)
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO document_content (file_hash, content, updated_at)"
                        " VALUES (%s, %s, NOW())"
                        " ON CONFLICT (file_hash)"
                        " DO UPDATE SET content = EXCLUDED.content, updated_at = NOW()",
                        (file_hash, content),
                    )
        logger.debug("Saved content for doc=%s", file_hash[:12])

    # --- Chunks ---

    def has_file(self, file_hash: str) -> bool:
        conn = self._conn()
        self._rollback_if_failed(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM document_chunks WHERE file_hash = %s LIMIT 1",
                (file_hash,),
            )
            row = cur.fetchone()
        return row is not None

    def save_chunks(self, file_hash: str, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        # Track chunk_index per chapter (position within the chapter)
        chapter_counters: dict[int, int] = {}
        rows: list[tuple] = []
        for chunk in chunks:
            meta = chunk.metadata
            chapter_index = meta.chapter_index if meta else 0
            page_number = meta.page_number if meta else None
            idx = chapter_counters.get(chapter_index, 0)
            chapter_counters[chapter_index] = idx + 1
            rows.append((
                file_hash,
                chapter_index,
                idx,
                chunk.text,
                page_number,
                chunk.token_count,
            ))
        with self._lock:
            conn = self._conn()
            self._rollback_if_failed(conn)
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.executemany(
                        "INSERT INTO document_chunks"
                        " (file_hash, chapter_index, chunk_index, text, page_number, token_count)"
                        " VALUES (%s, %s, %s, %s, %s, %s)"
                        " ON CONFLICT (file_hash, chapter_index, chunk_index) DO NOTHING",
                        rows,
                    )
        logger.debug("Saved %d chunks for doc=%s", len(rows), file_hash[:12])

    def get_chunks_by_chapter(self, file_hash: str, chapter_index: int) -> list[Chunk]:
        conn = self._conn()
        self._rollback_if_failed(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT chunk_index, text, page_number, token_count"
                " FROM document_chunks"
                " WHERE file_hash = %s AND chapter_index = %s"
                " ORDER BY chunk_index",
                (file_hash, chapter_index),
            )
            rows = cur.fetchall()
        return [
            Chunk(
                text=row["text"],
                token_count=row["token_count"],
                metadata=ChunkMetadata(
                    source_file=file_hash,
                    chapter_index=chapter_index,
                    page_number=row["page_number"] or 0,
                    start_char=0,
                    end_char=0,
                ),
            )
            for row in rows
        ]

    def get_chunks_by_file(self, file_hash: str) -> list[Chunk]:
        conn = self._conn()
        self._rollback_if_failed(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT chapter_index, chunk_index, text, page_number, token_count"
                " FROM document_chunks"
                " WHERE file_hash = %s"
                " ORDER BY chapter_index, chunk_index",
                (file_hash,),
            )
            rows = cur.fetchall()
        return [
            Chunk(
                text=row["text"],
                token_count=row["token_count"],
                metadata=ChunkMetadata(
                    source_file=file_hash,
                    chapter_index=row["chapter_index"],
                    page_number=row["page_number"] or 0,
                    start_char=0,
                    end_char=0,
                ),
            )
            for row in rows
        ]

    def get_chapter_structure(self, file_hash: str) -> list[tuple[int, int]]:
        conn = self._conn()
        self._rollback_if_failed(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT chapter_index, COUNT(*) AS chunk_count"
                " FROM document_chunks"
                " WHERE file_hash = %s"
                " GROUP BY chapter_index"
                " ORDER BY chapter_index",
                (file_hash,),
            )
            rows = cur.fetchall()
        return [(row["chapter_index"], row["chunk_count"]) for row in rows]

    def delete_chunks_by_file(self, file_hash: str) -> None:
        with self._lock:
            conn = self._conn()
            self._rollback_if_failed(conn)
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM document_chunks WHERE file_hash = %s",
                        (file_hash,),
                    )
        logger.debug("Deleted all chunks for doc=%s", file_hash[:12])

    def delete_chunks_by_chapter(self, file_hash: str, chapter_index: int) -> None:
        with self._lock:
            conn = self._conn()
            self._rollback_if_failed(conn)
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM document_chunks"
                        " WHERE file_hash = %s AND chapter_index = %s",
                        (file_hash, chapter_index),
                    )
        logger.debug(
            "Deleted chunks for doc=%s chapter=%d", file_hash[:12], chapter_index
        )


def _ensure_naive(dt: datetime) -> datetime:
    """Strip timezone info from a datetime returned from PostgreSQL (TIMESTAMPTZ)."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt
