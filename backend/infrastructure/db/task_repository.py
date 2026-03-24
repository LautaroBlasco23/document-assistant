import json
import logging
import threading

import psycopg

from infrastructure.db.postgres import PostgresPool

logger = logging.getLogger(__name__)


class TaskRepository:
    def __init__(self, pool: PostgresPool):
        self._pool = pool
        self._lock = threading.Lock()

    def _conn(self) -> psycopg.Connection:
        return self._pool.connection()

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

    def list_active(self) -> list[dict]:
        with self._lock:
            with self._conn().cursor() as cur:
                cur.execute(
                    """
                    SELECT task_id, task_type, doc_hash, filename, status, progress,
                           progress_pct, result, error
                    FROM background_tasks
                    WHERE status IN ('pending', 'running')
                    ORDER BY created_at ASC
                    """,
                )
                rows = cur.fetchall()
            return rows
