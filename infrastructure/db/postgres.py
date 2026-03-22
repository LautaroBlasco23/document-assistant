import logging
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from infrastructure.config import PostgresConfig

logger = logging.getLogger(__name__)

_SCHEMA_FILE = Path(__file__).parent / "schema.sql"
_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class PostgresPool:
    """Manages a psycopg connection for PostgreSQL."""

    def __init__(self, config: PostgresConfig):
        conninfo = (
            f"host={config.host} port={config.port} "
            f"dbname={config.database} user={config.user} password={config.password}"
        )
        self._conninfo = conninfo
        self._conn: psycopg.Connection | None = None

    def connect(self) -> None:
        """Open connection and run schema initialization."""
        self._conn = psycopg.connect(self._conninfo, row_factory=dict_row)
        self._conn.autocommit = False
        self._init_schema()
        logger.info("PostgreSQL connected")

    def _init_schema(self) -> None:
        """Execute schema.sql to create tables if they don't exist, then apply migrations."""
        sql = _SCHEMA_FILE.read_text()
        with self._conn.cursor() as cur:
            cur.execute(sql)
        self._conn.commit()
        self._apply_migrations()

    def _apply_migrations(self) -> None:
        """Run all .sql files in the migrations directory (idempotent)."""
        if not _MIGRATIONS_DIR.is_dir():
            return
        for path in sorted(_MIGRATIONS_DIR.glob("*.sql")):
            logger.info("Applying migration: %s", path.name)
            sql = path.read_text()
            with self._conn.cursor() as cur:
                cur.execute(sql)
            self._conn.commit()

    def connection(self) -> psycopg.Connection:
        """Return the active connection."""
        if self._conn is None or self._conn.closed:
            raise RuntimeError("PostgreSQL not connected. Call connect() first.")
        return self._conn

    def close(self) -> None:
        """Close the connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()
            logger.info("PostgreSQL connection closed")
