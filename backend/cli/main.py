import argparse
import logging
import sys

import requests

from infrastructure.config import load_config

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

    sub.add_parser("check", help="Check connectivity to all services")

    args = parser.parse_args()
    _setup_logging(args.log_format)

    if args.command == "check":
        print("Service health checks:")
        sys.exit(run_check())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
