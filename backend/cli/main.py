import argparse
import logging
import sys

import requests

from infrastructure.auth.jwt_handler import get_password_hash
from infrastructure.config import load_config
from infrastructure.db.postgres import PostgresPool
from infrastructure.db.user_repository import (
    PostgresUserStore,
    PostgresUserSubscriptionStore,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Service health check
# ---------------------------------------------------------------------------


def check_ollama(base_url: str) -> bool:
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=5)
        return resp.status_code == 200
    except requests.ConnectionError:
        return False


def check_postgres(config) -> bool:
    try:
        from infrastructure.db.postgres import PostgresPool

        pool = PostgresPool(config.postgres)
        pool.connect()
        with pool.connection().cursor() as cur:
            cur.execute("SELECT 1")
        pool.close()
        return True
    except Exception:
        return False


def run_check() -> int:
    config = load_config()
    all_ok = True

    # ANSI color codes
    GREEN = "\033[92m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    if config.llm_provider == "ollama":
        llm_url = config.ollama.base_url
        llm_ok = check_ollama(config.ollama.base_url)
    else:
        llm_url = f"groq (key={'set' if config.groq.api_key else 'missing'})"
        llm_ok = bool(config.groq.api_key)

    postgres_url = f"{config.postgres.host}:{config.postgres.port}"
    postgres_ok = check_postgres(config)

    checks = [
        ("LLM", llm_url, llm_ok),
        ("PostgreSQL", postgres_url, postgres_ok),
    ]

    # Calculate column widths for alignment
    service_width = max(len(c[0]) for c in checks)
    url_width = max(len(c[1]) for c in checks)

    # Print header
    print(f"\n{BOLD}┌─ Service Health Status ─────────────────────────────────────┐{RESET}")
    print(f"{BOLD}│{RESET}")

    # Print each service
    for service, url, ok in checks:
        status_text = f"{GREEN}✓ OK{RESET}" if ok else f"{RED}✗ FAIL{RESET}"
        print(
            f"{BOLD}│{RESET}  {service.ljust(service_width)}  {url.ljust(url_width)}  {status_text}"
        )
        all_ok = all_ok and ok

    # Print footer
    print(f"{BOLD}│{RESET}")
    print(f"{BOLD}└────────────────────────────────────────────────────────────┘{RESET}\n")

    return 0 if all_ok else 1


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------


def create_user(email: str, password: str, display_name: str | None) -> int:
    """Create a new user with free plan."""
    config = load_config()
    pool = PostgresPool(config.postgres)
    pool.connect()

    try:
        store = PostgresUserStore(pool)
        existing = store.get_by_email(email)
        if existing:
            print(f"Error: User already exists: {email}")
            return 1

        password_hash = get_password_hash(password)
        user = store.create(email, password_hash, display_name)

        # Assign free plan
        sub_store = PostgresUserSubscriptionStore(pool)
        sub_store.assign_plan(user.id, "free")

        print(f"Created user: {email} (ID: {user.id})")
        return 0
    except Exception as e:
        print(f"Error creating user: {e}")
        return 1
    finally:
        pool.close()


def set_user_plan(email: str, plan_slug: str) -> int:
    """Assign plan to user."""
    config = load_config()
    pool = PostgresPool(config.postgres)
    pool.connect()

    try:
        user_store = PostgresUserStore(pool)
        user = user_store.get_by_email(email)
        if not user:
            print(f"Error: User not found: {email}")
            return 1

        sub_store = PostgresUserSubscriptionStore(pool)
        sub_store.assign_plan(user.id, plan_slug)

        print(f"Assigned plan '{plan_slug}' to {email}")
        return 0
    except Exception as e:
        print(f"Error setting plan: {e}")
        return 1
    finally:
        pool.close()


def show_user_limits(email: str) -> int:
    """Show user limits."""
    config = load_config()
    pool = PostgresPool(config.postgres)
    pool.connect()

    try:
        user_store = PostgresUserStore(pool)
        user = user_store.get_by_email(email)
        if not user:
            print(f"Error: User not found: {email}")
            return 1

        sub_store = PostgresUserSubscriptionStore(pool)
        limits = sub_store.get_user_limits(user.id)

        print(f"\nUser: {email}")
        print(f"Knowledge Trees: {limits.current_knowledge_trees} / {limits.max_knowledge_trees}")
        print(f"Documents: {limits.current_documents} / {limits.max_documents}")
        print(f"Can create tree: {limits.can_create_tree}")
        print(f"Can create document: {limits.can_create_document}\n")
        return 0
    except Exception as e:
        print(f"Error showing limits: {e}")
        return 1
    finally:
        pool.close()


def list_users() -> int:
    """List all users with their plan info."""
    config = load_config()
    pool = PostgresPool(config.postgres)
    pool.connect()

    try:
        pool_conn = pool.connection()
        with pool_conn.cursor() as cur:
            cur.execute("""
                SELECT u.id, u.email, u.display_name, u.is_active, u.created_at,
                       p.slug as plan_slug, p.max_documents, p.max_knowledge_trees
                FROM users u
                LEFT JOIN user_subscriptions s ON s.user_id = u.id
                LEFT JOIN subscription_plans p ON p.id = s.plan_id
                ORDER BY u.created_at DESC
            """)
            rows = cur.fetchall()

        if not rows:
            print("No users found.")
            return 0

        print(f"\n{'ID':<36} {'Email':<30} {'Plan':<10} {'Active':<8} {'Created'}")
        print("-" * 100)
        for row in rows:
            plan = row['plan_slug'] or 'none'
            active = 'yes' if row['is_active'] else 'no'
            created = row['created_at'].strftime('%Y-%m-%d')
            print(f"{str(row['id']):<36} {row['email']:<30} {plan:<10} {active:<8} {created}")
        print()
        return 0
    except Exception as e:
        print(f"Error listing users: {e}")
        return 1
    finally:
        pool.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _setup_logging(log_format: str) -> None:
    if log_format == "json":
        fmt = '{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","msg":"%(message)s"}'
    else:
        fmt = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt, datefmt="%H:%M:%S")


def main() -> None:
    parser = argparse.ArgumentParser(prog="document-assistant")
    parser.add_argument(
        "--log-format",
        choices=["text", "json"],
        default="text",
        help="Log output format",
    )
    sub = parser.add_subparsers(dest="command")

    # Check command
    sub.add_parser("check", help="Check connectivity to all services")

    # User commands
    user_parser = sub.add_parser("create-user", help="Create a new user")
    user_parser.add_argument("email", help="User email")
    user_parser.add_argument("password", help="User password")
    user_parser.add_argument("--display-name", help="Display name (optional)")

    plan_parser = sub.add_parser("set-plan", help="Assign plan to user")
    plan_parser.add_argument("email", help="User email")
    plan_parser.add_argument("plan_slug", help="Plan slug (e.g., 'free', 'pro')")

    limits_parser = sub.add_parser("user-limits", help="Show user limits")
    limits_parser.add_argument("email", help="User email")

    list_parser = sub.add_parser("list-users", help="List all users")

    args = parser.parse_args()
    _setup_logging(args.log_format)

    if args.command == "check":
        print("Service health checks:")
        sys.exit(run_check())
    elif args.command == "create-user":
        sys.exit(create_user(args.email, args.password, args.display_name))
    elif args.command == "set-plan":
        sys.exit(set_user_plan(args.email, args.plan_slug))
    elif args.command == "user-limits":
        sys.exit(show_user_limits(args.email))
    elif args.command == "list-users":
        sys.exit(list_users())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
