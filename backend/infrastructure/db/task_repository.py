import json
import logging
import threading

import psycopg
from psycopg.pq import TransactionStatus

from infrastructure.db.postgres import PostgresPool

logger = logging.getLogger(__name__)


class TaskRepository:
    def __init__(self, pool: PostgresPool):
        self._pool = pool
        self._lock = threading.Lock()

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
    ) -> None:
        with self._lock:
            with self._conn().cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO background_tasks
                        (task_id, task_type, doc_hash, filename, status, progress,
                         progress_pct, chapter, book_title)
                    VALUES (%s, %s, %s, %s, 'pending', '', 0, %s, %s)
                    ON CONFLICT (task_id) DO NOTHING
                    """,
                    (task_id, task_type, doc_hash, filename, chapter, book_title),
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
    ) -> None:
        with self._lock:
            with self._conn().cursor() as cur:
                cur.execute(
                    """
                    UPDATE background_tasks
                    SET status = %s,
                        progress = %s,
                        progress_pct = %s,
                        result = %s,
                        error = %s,
                        updated_at = NOW()
                    WHERE task_id = %s
                    """,
                    (
                        status,
                        progress,
                        progress_pct,
                        json.dumps(result) if result else None,
                        error,
                        task_id,
                    ),
                )
            self._conn().commit()

    def fail_orphaned(self) -> int:
        """Mark all pending/running tasks as failed.

        Called on server startup to clear stale tasks.
        """
        with self._lock:
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
        with self._lock:
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
