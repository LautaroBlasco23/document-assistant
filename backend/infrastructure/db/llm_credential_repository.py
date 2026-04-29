"""PostgreSQL implementation for LLMCredentialStore."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from core.model.llm_credential import LLMCredential
from infrastructure.db.user_repository import _BaseRepo

logger = logging.getLogger(__name__)

_SELECT_COLS = (
    "id, user_id, provider, api_key_last4, "
    "last_tested_at, last_test_ok, last_test_error, "
    "created_at, updated_at"
)


def _ensure_naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


class PostgresLLMCredentialStore(_BaseRepo):
    """CRUD for user_llm_credentials table."""

    def get(self, user_id: UUID, provider: str) -> LLMCredential | None:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_SELECT_COLS} FROM user_llm_credentials "
                "WHERE user_id = %s AND provider = %s",
                (user_id, provider),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_cred(row)

    def upsert(
        self,
        user_id: UUID,
        provider: str,
        encrypted_key: bytes,
        last4: str,
    ) -> LLMCredential:
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        f"INSERT INTO user_llm_credentials "
                        f"(user_id, provider, api_key_encrypted, api_key_last4) "
                        f"VALUES (%s, %s, %s, %s) "
                        f"ON CONFLICT (user_id, provider) DO UPDATE SET "
                        f"api_key_encrypted = EXCLUDED.api_key_encrypted, "
                        f"api_key_last4 = EXCLUDED.api_key_last4, "
                        f"updated_at = NOW() "
                        f"RETURNING {_SELECT_COLS}",
                        (user_id, provider, encrypted_key, last4),
                    )
                    row = cur.fetchone()
        logger.info("Upserted LLM credential: user=%s provider=%s", user_id, provider)
        return self._row_to_cred(row)

    def delete(self, user_id: UUID, provider: str) -> bool:
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM user_llm_credentials "
                        "WHERE user_id = %s AND provider = %s",
                        (user_id, provider),
                    )
                    deleted = cur.rowcount > 0
        if deleted:
            logger.info("Deleted LLM credential: user=%s provider=%s", user_id, provider)
        return deleted

    def list_for_user(self, user_id: UUID) -> list[LLMCredential]:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_SELECT_COLS} FROM user_llm_credentials "
                "WHERE user_id = %s ORDER BY provider",
                (user_id,),
            )
            rows = cur.fetchall()
        return [self._row_to_cred(row) for row in rows]

    def update_test_result(
        self,
        user_id: UUID,
        provider: str,
        ok: bool,
        error: str | None,
    ) -> None:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE user_llm_credentials "
                "SET last_tested_at = NOW(), last_test_ok = %s, "
                "last_test_error = %s, updated_at = NOW() "
                "WHERE user_id = %s AND provider = %s",
                (ok, error, user_id, provider),
            )
        logger.debug(
            "Updated test result: user=%s provider=%s ok=%s", user_id, provider, ok
        )

    def get_encrypted_key(self, user_id: UUID, provider: str) -> bytes | None:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT api_key_encrypted FROM user_llm_credentials "
                "WHERE user_id = %s AND provider = %s",
                (user_id, provider),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return bytes(row["api_key_encrypted"])

    @staticmethod
    def _row_to_cred(row: dict) -> LLMCredential:
        last_tested_at = row["last_tested_at"]
        return LLMCredential(
            id=row["id"],
            user_id=row["user_id"],
            provider=row["provider"],
            api_key_last4=row["api_key_last4"],
            last_tested_at=_ensure_naive(last_tested_at) if last_tested_at is not None else None,
            last_test_ok=row["last_test_ok"],
            last_test_error=row["last_test_error"],
            created_at=_ensure_naive(row["created_at"]),
            updated_at=_ensure_naive(row["updated_at"]),
        )
