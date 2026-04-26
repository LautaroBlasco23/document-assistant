"""PostgreSQL implementation for Agent repository."""

import logging
import threading
from datetime import datetime, timezone
from uuid import UUID

import psycopg
from psycopg.pq import TransactionStatus

from core.model.agent import Agent
from core.ports.agent_store import AgentRepository
from infrastructure.db.postgres import PostgresPool

logger = logging.getLogger(__name__)


def _ensure_naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


class PostgresAgentRepository(AgentRepository):
    def __init__(self, pool: PostgresPool) -> None:
        self._pool = pool
        self._lock = threading.Lock()

    def _conn(self) -> psycopg.Connection:
        conn = self._pool.connection()
        if conn.info.transaction_status == TransactionStatus.INERROR:
            conn.rollback()
        return conn

    def ensure_default(self, user_id: UUID, model: str) -> Agent | None:
        """Ensure the user has a default agent. Creates one if not found."""
        existing = self.get_default(user_id)
        if existing:
            return existing
        agent = Agent(
            user_id=user_id,
            name="Default",
            model=model,
            temperature=0.7,
            top_p=1.0,
            max_tokens=1024,
            is_default=True,
            prompt="",
        )
        return self.create(agent)

    def list_by_user(self, user_id: UUID) -> list[Agent]:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, name, prompt, model, temperature, top_p, "
                "max_tokens, is_default, created_at, updated_at "
                "FROM agents WHERE user_id = %s ORDER BY is_default DESC, created_at ASC",
                (user_id,),
            )
            rows = cur.fetchall()
        return [self._row_to_agent(row) for row in rows]

    def get_by_id(self, agent_id: UUID) -> Agent | None:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, name, prompt, model, temperature, top_p, "
                "max_tokens, is_default, created_at, updated_at "
                "FROM agents WHERE id = %s",
                (agent_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_agent(row)

    def get_default(self, user_id: UUID) -> Agent | None:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, name, prompt, model, temperature, top_p, "
                "max_tokens, is_default, created_at, updated_at "
                "FROM agents WHERE user_id = %s AND is_default = TRUE",
                (user_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_agent(row)

    def create(self, agent: Agent) -> Agent:
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    try:
                        cur.execute(
                            "INSERT INTO agents (user_id, name, prompt, model, temperature, "
                            "top_p, max_tokens, is_default) "
                            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
                            "RETURNING id, user_id, name, prompt, model, temperature, "
                            "top_p, max_tokens, is_default, created_at, updated_at",
                            (
                                agent.user_id,
                                agent.name,
                                agent.prompt,
                                agent.model,
                                agent.temperature,
                                agent.top_p,
                                agent.max_tokens,
                                agent.is_default,
                            ),
                        )
                        row = cur.fetchone()
                    except psycopg.errors.UniqueViolation:
                        raise ValueError(
                            f"Agent with name '{agent.name}' already exists"
                        )
        logger.info("Created agent '%s' for user %s", agent.name, agent.user_id)
        return self._row_to_agent(row)

    def update(self, agent: Agent) -> Agent:
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    try:
                        cur.execute(
                            "UPDATE agents SET name = %s, prompt = %s, model = %s, "
                            "temperature = %s, top_p = %s, max_tokens = %s, "
                            "updated_at = NOW() "
                            "WHERE id = %s "
                            "RETURNING id, user_id, name, prompt, model, temperature, "
                            "top_p, max_tokens, is_default, created_at, updated_at",
                            (
                                agent.name,
                                agent.prompt,
                                agent.model,
                                agent.temperature,
                                agent.top_p,
                                agent.max_tokens,
                                agent.id,
                            ),
                        )
                        row = cur.fetchone()
                    except psycopg.errors.UniqueViolation:
                        raise ValueError(
                            f"Agent with name '{agent.name}' already exists"
                        )
        return self._row_to_agent(row)

    def delete(self, agent_id: UUID) -> None:
        agent = self.get_by_id(agent_id)
        if agent is None:
            raise ValueError("Agent not found")
        if agent.is_default:
            raise ValueError("Cannot delete the default agent")
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM agents WHERE id = %s",
                        (agent_id,),
                    )

    @staticmethod
    def _row_to_agent(row: dict) -> Agent:
        return Agent(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            prompt=row.get("prompt", ""),
            model=row["model"],
            temperature=row["temperature"],
            top_p=row["top_p"],
            max_tokens=row["max_tokens"],
            is_default=row["is_default"],
            created_at=_ensure_naive(row["created_at"]),
            updated_at=_ensure_naive(row["updated_at"]),
        )
