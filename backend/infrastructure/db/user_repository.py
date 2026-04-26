"""PostgreSQL implementations for User and Subscription stores."""

import logging
import threading
from datetime import datetime, timezone
from uuid import UUID

import psycopg
from psycopg.pq import TransactionStatus

from core.model.user import (
    SubscriptionPlan,
    User,
    UserLimits,
    UserSubscription,
)
from infrastructure.db.postgres import PostgresPool

logger = logging.getLogger(__name__)


def _ensure_naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


class _BaseRepo:
    def __init__(self, pool: PostgresPool) -> None:
        self._pool = pool
        self._lock = threading.Lock()

    def _conn(self) -> psycopg.Connection:
        conn = self._pool.connection()
        if conn.info.transaction_status == TransactionStatus.INERROR:
            conn.rollback()
        return conn


class PostgresUserStore(_BaseRepo):
    """CRUD for users table."""

    def get_by_id(self, user_id: UUID) -> User | None:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, password_hash, display_name, is_active, created_at, updated_at "
                "FROM users WHERE id = %s",
                (user_id,)
            )
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_user(row)

    def get_by_email(self, email: str) -> User | None:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, password_hash, display_name, is_active, created_at, updated_at "
                "FROM users WHERE email = %s",
                (email,)
            )
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_user(row)

    def create(self, email: str, password_hash: str, display_name: str | None) -> User:
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO users (email, password_hash, display_name) "
                        "VALUES (%s, %s, %s) "
                        "RETURNING id, email, password_hash, display_name, "
                        "is_active, created_at, updated_at",
                        (email, password_hash, display_name)
                    )
                    row = cur.fetchone()
        logger.info("Created user: %s", email)
        return self._row_to_user(row)

    def update(self, user: User) -> User:
        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE users SET email = %s, display_name = %s, "
                        "is_active = %s, updated_at = NOW() "
                        "WHERE id = %s "
                        "RETURNING id, email, password_hash, display_name, "
                        "is_active, created_at, updated_at",
                        (user.email, user.display_name, user.is_active, user.id)
                    )
                    row = cur.fetchone()
        return self._row_to_user(row)

    def get_document_count(self, user_id: UUID) -> int:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM knowledge_documents d "
                "JOIN knowledge_trees t ON d.tree_id = t.id "
                "WHERE t.user_id = %s",
                (user_id,)
            )
            return cur.fetchone()["count"]

    def get_tree_count(self, user_id: UUID) -> int:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM knowledge_trees WHERE user_id = %s",
                (user_id,)
            )
            return cur.fetchone()["count"]

    @staticmethod
    def _row_to_user(row: dict) -> User:
        return User(
            id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            display_name=row["display_name"],
            is_active=row["is_active"],
            created_at=_ensure_naive(row["created_at"]),
            updated_at=_ensure_naive(row["updated_at"]),
        )


class PostgresSubscriptionPlanStore(_BaseRepo):
    """CRUD for subscription_plans table."""

    def get_by_slug(self, slug: str) -> SubscriptionPlan | None:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, slug, name, description, max_documents, "
                "max_knowledge_trees, is_active, created_at "
                "FROM subscription_plans WHERE slug = %s",
                (slug,)
            )
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_plan(row)

    def get_by_id(self, plan_id: UUID) -> SubscriptionPlan | None:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, slug, name, description, max_documents, "
                "max_knowledge_trees, is_active, created_at "
                "FROM subscription_plans WHERE id = %s",
                (plan_id,)
            )
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_plan(row)

    def list_active(self) -> list[SubscriptionPlan]:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, slug, name, description, max_documents, "
                "max_knowledge_trees, is_active, created_at "
                "FROM subscription_plans WHERE is_active = TRUE ORDER BY created_at"
            )
            rows = cur.fetchall()
        return [self._row_to_plan(row) for row in rows]

    @staticmethod
    def _row_to_plan(row: dict) -> SubscriptionPlan:
        return SubscriptionPlan(
            id=row["id"],
            slug=row["slug"],
            name=row["name"],
            description=row["description"],
            max_documents=row["max_documents"],
            max_knowledge_trees=row["max_knowledge_trees"],
            is_active=row["is_active"],
            created_at=_ensure_naive(row["created_at"]),
        )


class PostgresUserSubscriptionStore(_BaseRepo):
    """CRUD for user_subscriptions table."""

    def get_for_user(self, user_id: UUID) -> UserSubscription | None:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, plan_id, assigned_at "
                "FROM user_subscriptions WHERE user_id = %s",
                (user_id,)
            )
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_subscription(row)

    def get_plan_for_user(self, user_id: UUID) -> SubscriptionPlan | None:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT p.id, p.slug, p.name, p.description, "
                "p.max_documents, p.max_knowledge_trees, p.is_active, p.created_at "
                "FROM subscription_plans p "
                "JOIN user_subscriptions s ON s.plan_id = p.id "
                "WHERE s.user_id = %s",
                (user_id,)
            )
            row = cur.fetchone()
        if row is None:
            return None
        return PostgresSubscriptionPlanStore._row_to_plan(row)

    def assign_plan(self, user_id: UUID, plan_slug: str) -> UserSubscription:
        plan_store = PostgresSubscriptionPlanStore(self._pool)
        plan = plan_store.get_by_slug(plan_slug)
        if plan is None:
            raise ValueError(f"Plan not found: {plan_slug}")

        with self._lock:
            conn = self._conn()
            with conn.transaction():
                with conn.cursor() as cur:
                    # Remove existing subscription
                    cur.execute(
                        "DELETE FROM user_subscriptions WHERE user_id = %s",
                        (user_id,)
                    )
                    # Create new subscription
                    cur.execute(
                        "INSERT INTO user_subscriptions (user_id, plan_id) "
                        "VALUES (%s, %s) "
                        "RETURNING id, user_id, plan_id, assigned_at",
                        (user_id, plan.id)
                    )
                    row = cur.fetchone()
        logger.info("Assigned plan %s to user %s", plan_slug, user_id)
        return self._row_to_subscription(row)

    def get_user_limits(self, user_id: UUID) -> UserLimits:
        plan = self.get_plan_for_user(user_id)

        if plan is None:
            return UserLimits(
                max_documents=0,
                max_knowledge_trees=0,
                current_documents=0,
                current_knowledge_trees=0,
                can_create_document=False,
                can_create_tree=False
            )

        user_store = PostgresUserStore(self._pool)
        current_docs = user_store.get_document_count(user_id)
        current_trees = user_store.get_tree_count(user_id)

        return UserLimits(
            max_documents=plan.max_documents,
            max_knowledge_trees=plan.max_knowledge_trees,
            current_documents=current_docs,
            current_knowledge_trees=current_trees,
            can_create_document=current_docs < plan.max_documents,
            can_create_tree=current_trees < plan.max_knowledge_trees,
        )

    @staticmethod
    def _row_to_subscription(row: dict) -> UserSubscription:
        return UserSubscription(
            id=row["id"],
            user_id=row["user_id"],
            plan_id=row["plan_id"],
            assigned_at=_ensure_naive(row["assigned_at"]),
        )
