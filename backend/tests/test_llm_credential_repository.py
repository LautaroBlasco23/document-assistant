"""Unit tests for PostgreSQL LLM credential repository.

Scope: PostgresLLMCredentialStore — get, upsert, delete, list_for_user,
       update_test_result, get_encrypted_key.
Out-of-scope: integration with real PostgreSQL, encryption logic.
Setup: Mock psycopg.Connection and PostgresConnection via unittest.mock.
"""
from datetime import datetime
from unittest.mock import MagicMock
from uuid import UUID

from core.model.llm_credential import LLMCredential
from infrastructure.db.llm_credential_repository import PostgresLLMCredentialStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXED_UUID = UUID("12345678-1234-5678-1234-567812345678")
FIXED_USER_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def _make_pool_and_cursor():
    pool = MagicMock()
    cur = MagicMock()
    conn = MagicMock()

    cur.fetchone.return_value = None
    cur.fetchall.return_value = []

    cm_cur = MagicMock()
    cm_cur.__enter__ = MagicMock(return_value=cur)
    cm_cur.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cm_cur

    cm_tx = MagicMock()
    cm_tx.__enter__ = MagicMock(return_value=None)
    cm_tx.__exit__ = MagicMock(return_value=False)
    conn.transaction.return_value = cm_tx

    conn.info.transaction_status = 0

    pool.connection.return_value = conn

    return pool, cur, conn


def _cred_row(
    cred_id=FIXED_UUID,
    user_id=FIXED_USER_ID,
    provider="groq",
    api_key_last4="abcd",
    last_tested_at=None,
    last_test_ok=None,
    last_test_error=None,
    created_at=None,
    updated_at=None,
):
    return {
        "id": cred_id,
        "user_id": user_id,
        "provider": provider,
        "api_key_last4": api_key_last4,
        "last_tested_at": last_tested_at,
        "last_test_ok": last_test_ok,
        "last_test_error": last_test_error,
        "created_at": created_at or datetime(2024, 1, 1),
        "updated_at": updated_at or datetime(2024, 1, 1),
    }


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------

def test_cred_store_get_found():
    """get must return the LLMCredential when it exists."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _cred_row(provider="groq", api_key_last4="xyz1")

    store = PostgresLLMCredentialStore(pool)
    cred = store.get(FIXED_USER_ID, "groq")

    assert cred is not None
    assert cred.provider == "groq"
    assert cred.api_key_last4 == "xyz1"


def test_cred_store_get_not_found():
    """get must return None when the credential does not exist."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = None

    store = PostgresLLMCredentialStore(pool)
    cred = store.get(FIXED_USER_ID, "openrouter")

    assert cred is None


# ---------------------------------------------------------------------------
# upsert
# ---------------------------------------------------------------------------

def test_cred_store_upsert_new():
    """upsert must insert a new credential and return it."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _cred_row(provider="groq", api_key_last4="new1")

    store = PostgresLLMCredentialStore(pool)
    cred = store.upsert(FIXED_USER_ID, "groq", b"encrypted_key", "new1")

    assert isinstance(cred, LLMCredential)
    assert cred.provider == "groq"
    assert cred.api_key_last4 == "new1"


def test_cred_store_upsert_existing():
    """upsert must update an existing credential via ON CONFLICT."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = _cred_row(provider="groq", api_key_last4="upd1")

    store = PostgresLLMCredentialStore(pool)
    cred = store.upsert(FIXED_USER_ID, "groq", b"new_encrypted", "upd1")

    assert cred.api_key_last4 == "upd1"


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

def test_cred_store_delete_existing():
    """delete must return True when a credential is deleted."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.rowcount = 1

    store = PostgresLLMCredentialStore(pool)
    result = store.delete(FIXED_USER_ID, "groq")

    assert result is True


def test_cred_store_delete_not_found():
    """delete must return False when no credential exists."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.rowcount = 0

    store = PostgresLLMCredentialStore(pool)
    result = store.delete(FIXED_USER_ID, "nonexistent")

    assert result is False


# ---------------------------------------------------------------------------
# list_for_user
# ---------------------------------------------------------------------------

def test_cred_store_list_for_user():
    """list_for_user must return all credentials for a user."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchall.return_value = [
        _cred_row(provider="groq"),
        _cred_row(provider="openrouter"),
    ]

    store = PostgresLLMCredentialStore(pool)
    creds = store.list_for_user(FIXED_USER_ID)

    assert len(creds) == 2
    assert creds[0].provider == "groq"
    assert creds[1].provider == "openrouter"


def test_cred_store_list_for_user_empty():
    """list_for_user must return an empty list when the user has no credentials."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchall.return_value = []

    store = PostgresLLMCredentialStore(pool)
    creds = store.list_for_user(FIXED_USER_ID)

    assert creds == []


# ---------------------------------------------------------------------------
# update_test_result
# ---------------------------------------------------------------------------

def test_cred_store_update_test_result_ok():
    """update_test_result must store a successful test result."""
    pool, cur, _ = _make_pool_and_cursor()

    store = PostgresLLMCredentialStore(pool)
    store.update_test_result(FIXED_USER_ID, "groq", ok=True, error=None)

    assert cur.execute.call_count == 1


def test_cred_store_update_test_result_error():
    """update_test_result must store a failed test result with error message."""
    pool, cur, _ = _make_pool_and_cursor()

    store = PostgresLLMCredentialStore(pool)
    store.update_test_result(FIXED_USER_ID, "groq", ok=False, error="Connection refused")

    assert cur.execute.call_count == 1


# ---------------------------------------------------------------------------
# get_encrypted_key
# ---------------------------------------------------------------------------

def test_cred_store_get_encrypted_key_found():
    """get_encrypted_key must return the encrypted key bytes."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = {"api_key_encrypted": b"secret_bytes"}

    store = PostgresLLMCredentialStore(pool)
    key = store.get_encrypted_key(FIXED_USER_ID, "groq")

    assert key == b"secret_bytes"


def test_cred_store_get_encrypted_key_not_found():
    """get_encrypted_key must return None when the credential does not exist."""
    pool, cur, _ = _make_pool_and_cursor()
    cur.fetchone.return_value = None

    store = PostgresLLMCredentialStore(pool)
    key = store.get_encrypted_key(FIXED_USER_ID, "groq")

    assert key is None
