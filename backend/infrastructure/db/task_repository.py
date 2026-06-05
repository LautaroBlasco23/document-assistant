import json
import logging
from datetime import datetime
from uuid import UUID

import psycopg
from psycopg.pq import TransactionStatus

from infrastructure.db.postgres import PostgresConnection

logger = logging.getLogger(__name__)


class TaskRepository:
    def __init__(self, pool: PostgresConnection):
        self._pool = pool

    def _conn(self) -> psycopg.Connection:
        conn = self._pool.connection()
        if conn.info.transaction_status == TransactionStatus.INERROR:
            conn.rollback()
        return conn

    def create(
        self,
        task_id: str,
        task_type: str,
        doc_hash: str = "",
        filename: str = "",
        chapter: int = 0,
        book_title: str = "",
        user_id: UUID | None = None,
        prompt: str = "",
    ) -> None:
        with self._pool.lock:
            with self._conn().cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO background_tasks
                        (task_id, task_type, doc_hash, filename, status, progress,
                         progress_pct, chapter, book_title, user_id, prompt)
                    VALUES (%s, %s, %s, %s, 'pending', '', 0, %s, %s, %s, %s)
                    ON CONFLICT (task_id) DO NOTHING
                    """,
                    (task_id, task_type, doc_hash, filename, chapter, book_title, user_id, prompt),
                )
            self._conn().commit()

    def update_status(
        self,
        task_id: str,
        status: str,
        progress: str = "",
        progress_pct: int = 0,
        result: dict | None = None,
        error: str | None = None,
        result_excerpt: str = "",
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> None:
        with self._pool.lock:
            with self._conn().cursor() as cur:
                cur.execute(
                    """
                    UPDATE background_tasks
                    SET status = %s,
                        progress = %s,
                        progress_pct = %s,
                        result = %s,
                        error = %s,
                        result_excerpt = %s,
                        started_at = COALESCE(%s, started_at),
                        finished_at = COALESCE(%s, finished_at),
                        updated_at = NOW()
                    WHERE task_id = %s
                    """,
                    (
                        status,
                        progress,
                        progress_pct,
                        json.dumps(result) if result else None,
                        error,
                        result_excerpt,
                        started_at,
                        finished_at,
                        task_id,
                    ),
                )
            self._conn().commit()

    def fail_orphaned(self) -> int:
        """Mark all pending/running tasks as failed.

        Called on server startup to clear stale tasks.
        """
        with self._pool.lock:
            with self._conn().cursor() as cur:
                cur.execute(
                    """
                    UPDATE background_tasks
                    SET status = 'failed',
                        error = 'Server was restarted before this task could complete',
                        updated_at = NOW()
                    WHERE status IN ('pending', 'running')
                    """,
                )
                count = cur.rowcount
            self._conn().commit()
        if count:
            logger.info("Marked %d orphaned task(s) as failed on startup", count)
        return count

    def list_active(self) -> list[dict]:
        with self._pool.lock:
            with self._conn().cursor() as cur:
                cur.execute(
                    """
                    SELECT task_id, task_type, doc_hash, filename, status, progress,
                           progress_pct, result, error, chapter, book_title
                    FROM background_tasks
                    WHERE status IN ('pending', 'running')
                    ORDER BY created_at ASC
                    """,
                )
                rows = cur.fetchall()
            return rows

    def list_active_for_user(self, user_id: UUID) -> list[dict]:
        """List active tasks for a specific user."""
        with self._pool.lock:
            with self._conn().cursor() as cur:
                cur.execute(
                    """
                    SELECT task_id, task_type, doc_hash, filename, status, progress,
                           progress_pct, result, error, chapter, book_title,
                           user_id, prompt, result_excerpt, started_at, finished_at,
                           created_at
                    FROM background_tasks
                    WHERE status IN ('pending', 'running') AND user_id = %s
                    ORDER BY created_at ASC
                    """,
                    (user_id,),
                )
                rows = cur.fetchall()
            return rows

    def list_for_user(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
        status_filter: str | None = None,
    ) -> tuple[list[dict], int]:
        """List tasks for a user with pagination. Returns (rows, total_count)."""
        with self._pool.lock:
            with self._conn().cursor() as cur:
                where = "WHERE user_id = %s"
                params: list = [user_id]
                if status_filter:
                    where += " AND status = %s"
                    params.append(status_filter)

                # Total count
                cur.execute(f"SELECT COUNT(*) FROM background_tasks {where}", params)
                total = cur.fetchone()["count"]

                # Page
                cur.execute(
                    f"""
                    SELECT task_id, task_type, status, progress, progress_pct,
                           chapter, book_title, prompt, result_excerpt, error,
                           created_at, started_at, finished_at
                    FROM background_tasks
                    {where}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    params + [limit, offset],
                )
                rows = cur.fetchall()
            return rows, total

    def get_for_user(self, task_id: str, user_id: UUID) -> dict | None:
        """Get a single task if it belongs to the user."""
        with self._pool.lock:
            with self._conn().cursor() as cur:
                cur.execute(
                    """
                    SELECT task_id, task_type, status, progress, progress_pct,
                           chapter, book_title, prompt, result_excerpt, error,
                           created_at, started_at, finished_at
                    FROM background_tasks
                    WHERE task_id = %s AND user_id = %s
                    """,
                    (task_id, user_id),
                )
                return cur.fetchone()

    def cancel_task(self, task_id: str, user_id: UUID) -> dict | None:
        """Best-effort cancel: flip status to cancelled if still running/pending."""
        with self._pool.lock:
            with self._conn().cursor() as cur:
                cur.execute(
                    """
                    UPDATE background_tasks
                    SET status = 'cancelled',
                        error = 'Cancelled by user',
                        finished_at = NOW(),
                        updated_at = NOW()
                    WHERE task_id = %s AND user_id = %s AND status IN ('pending', 'running')
                    RETURNING task_id, status
                    """,
                    (task_id, user_id),
                )
                result = cur.fetchone()
            self._conn().commit()
        return result
