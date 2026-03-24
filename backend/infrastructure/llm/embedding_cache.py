import hashlib
import json
import logging
import sqlite3
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path(__file__).parent.parent.parent.parent / "data" / ".cache" / "embeddings.db"


class EmbeddingCache:
    """SQLite-backed cache for embeddings, keyed by SHA-256 of text."""

    def __init__(self, db_path: Path = _DEFAULT_DB):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS embeddings (hash TEXT PRIMARY KEY, vector TEXT NOT NULL)"
        )
        self._conn.commit()

    def get(self, text: str) -> list[float] | None:
        key = self._hash(text)
        with self._lock:
            row = self._conn.execute(
                "SELECT vector FROM embeddings WHERE hash = ?", (key,)
            ).fetchone()
        if row:
            return json.loads(row[0])
        return None

    def set(self, text: str, vector: list[float]) -> None:
        key = self._hash(text)
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO embeddings (hash, vector) VALUES (?, ?)",
                (key, json.dumps(vector)),
            )
            self._conn.commit()

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def close(self) -> None:
        self._conn.close()
