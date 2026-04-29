"""Integration tests for PostgresLLMCredentialStore.

Requires a running PostgreSQL instance (docker compose up -d).
Run with:  uv run pytest -m integration
"""

from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from infrastructure.config import AppConfig
from infrastructure.db.llm_credential_repository import PostgresLLMCredentialStore
from infrastructure.db.postgres import PostgresPool
from infrastructure.auth.encryption import EncryptionService

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def pool():
    cfg = AppConfig().postgres
    p = PostgresPool(cfg)
    try:
        p.connect()
    except Exception:
        pytest.skip("PostgreSQL not reachable — skipping integration tests")
    yield p
    p.close()


@pytest.fixture(scope="module")
def store(pool):
    return PostgresLLMCredentialStore(pool)


@pytest.fixture(scope="module")
def enc():
    return EncryptionService(Fernet.generate_key())


@pytest.fixture
def user_id(pool):
    """Create a temp user and clean up after test."""
    uid = uuid4()
    conn = pool.connection()
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (id, email, password_hash) VALUES (%s, %s, %s)",
                (uid, f"test-{uid}@example.com", "hash"),
            )
    yield uid
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s", (uid,))


def test_upsert_and_get(store, enc, user_id):
    blob = enc.encrypt("sk-test-key")
    cred = store.upsert(user_id, "groq", blob, "r-key"[:4])
    assert cred.provider == "groq"
    assert cred.api_key_last4 == "-key"

    fetched = store.get(user_id, "groq")
    assert fetched is not None
    assert fetched.user_id == user_id


def test_get_encrypted_key(store, enc, user_id):
    plain = "gsk_secretvalue"
    blob = enc.encrypt(plain)
    store.upsert(user_id, "openrouter", blob, plain[-4:])
    raw = store.get_encrypted_key(user_id, "openrouter")
    assert raw is not None
    assert enc.decrypt(raw) == plain


def test_unique_constraint_upsert(store, enc, user_id):
    blob1 = enc.encrypt("key1")
    blob2 = enc.encrypt("key2")
    store.upsert(user_id, "nvidia", blob1, "key1"[-4:])
    store.upsert(user_id, "nvidia", blob2, "key2"[-4:])  # should not raise
    raw = store.get_encrypted_key(user_id, "nvidia")
    assert enc.decrypt(raw) == "key2"


def test_delete(store, enc, user_id):
    blob = enc.encrypt("del-key")
    store.upsert(user_id, "gemini", blob, "l-key"[:4])
    deleted = store.delete(user_id, "gemini")
    assert deleted is True
    assert store.get(user_id, "gemini") is None


def test_list_for_user(store, enc, user_id):
    for p in ("groq", "openrouter"):
        store.upsert(user_id, p, enc.encrypt("x"), "xxxx")
    creds = store.list_for_user(user_id)
    providers = {c.provider for c in creds}
    assert "groq" in providers
    assert "openrouter" in providers


def test_update_test_result(store, enc, user_id):
    blob = enc.encrypt("testkey")
    store.upsert(user_id, "huggingface", blob, "tkey")
    store.update_test_result(user_id, "huggingface", ok=True, error=None)
    cred = store.get(user_id, "huggingface")
    assert cred.last_test_ok is True
    assert cred.last_test_error is None


def test_cross_user_isolation(store, enc, pool):
    uid_a = uuid4()
    uid_b = uuid4()
    conn = pool.connection()
    for uid in (uid_a, uid_b):
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (id, email, password_hash) VALUES (%s, %s, %s)",
                    (uid, f"iso-{uid}@example.com", "h"),
                )
    try:
        store.upsert(uid_a, "groq", enc.encrypt("a-key"), "a-ke")
        assert store.get(uid_b, "groq") is None
    finally:
        for uid in (uid_a, uid_b):
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM users WHERE id = %s", (uid,))
