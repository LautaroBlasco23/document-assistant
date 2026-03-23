import json
import logging
import threading
from datetime import datetime, timezone

import psycopg
from psycopg.pq import TransactionStatus

from core.model.document_metadata import DocumentMetadata
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
        return Summary(
            document_hash=document_hash,
            chapter_index=chapter_index,
            content=row["content"],
            description=row["description"] or "",
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
            result.append(
                Summary(
                    document_hash=document_hash,
                    chapter_index=row["chapter_index"],
                    content=row["content"],
                    description=row["description"] or "",
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
        self, document_hash: str, chapter_index: int | None = None
    ) -> list[Flashcard]:
        conn = self._conn()
        with conn.cursor() as cur:
            if chapter_index is not None:
                cur.execute(
                    "SELECT id, chapter_index, front, back, created_at FROM flashcards"
                    " WHERE document_hash = %s AND chapter_index = %s ORDER BY created_at",
                    (document_hash, chapter_index),
                )
            else:
                cur.execute(
                    "SELECT id, chapter_index, front, back, created_at FROM flashcards"
                    " WHERE document_hash = %s ORDER BY created_at",
                    (document_hash,),
                )
            rows = cur.fetchall()
        return [
            Flashcard(
                id=str(row["id"]),
                document_hash=document_hash,
                chapter_index=row["chapter_index"],
                front=row["front"],
                back=row["back"],
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
                            " (id, document_hash, chapter_index, front, back, created_at)"
                            " VALUES (%s, %s, %s, %s, %s, %s)",
                            (
                                card.id,
                                card.document_hash,
                                card.chapter_index,
                                card.front,
                                card.back,
                                card.created_at,
                            ),
                        )
        logger.debug(
            "Saved %d flashcards doc=%s chapter=%d", len(flashcards), doc_hash[:12], chapter_index
        )

    # --- Metadata ---

    def get_metadata(self, document_hash: str) -> DocumentMetadata | None:
        conn = self._conn()
        self._rollback_if_failed(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT description, document_type FROM document_metadata WHERE document_hash = %s",
                (document_hash,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return DocumentMetadata(
            description=row["description"] or "",
            document_type=row["document_type"] or "",
        )

    def save_metadata(self, document_hash: str, metadata: DocumentMetadata) -> None:
        with self._lock:
            conn = self._conn()
            self._rollback_if_failed(conn)
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO document_metadata"
                        " (document_hash, description, document_type, updated_at)"
                        " VALUES (%s, %s, %s, NOW())"
                        " ON CONFLICT (document_hash)"
                        " DO UPDATE SET description = EXCLUDED.description,"
                        " document_type = EXCLUDED.document_type,"
                        " updated_at = NOW()",
                        (document_hash, metadata.description, metadata.document_type),
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
        logger.debug("Deleted all content for doc=%s", document_hash[:12])

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
        logger.debug(
            "Deleted chapter %d content for doc=%s", chapter_index, document_hash[:12]
        )


def _ensure_naive(dt: datetime) -> datetime:
    """Strip timezone info from a datetime returned from PostgreSQL (TIMESTAMPTZ)."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt
