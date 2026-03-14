import argparse
import sys

import requests
from neo4j import GraphDatabase
from qdrant_client import QdrantClient

from infrastructure.config import load_config


def check_ollama(base_url: str) -> bool:
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=5)
        return resp.status_code == 200
    except requests.ConnectionError:
        return False


def check_qdrant(url: str) -> bool:
    try:
        client = QdrantClient(url=url, timeout=5)
        client.get_collections()
        return True
    except Exception:
        return False


def check_neo4j(uri: str, user: str, password: str) -> bool:
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        driver.close()
        return True
    except Exception:
        return False


def run_check() -> int:
    config = load_config()
    all_ok = True

    # Ollama
    ok = check_ollama(config.ollama.base_url)
    status = "OK" if ok else "FAIL"
    print(f"  Ollama ({config.ollama.base_url}): {status}")
    all_ok = all_ok and ok

    # Qdrant
    ok = check_qdrant(config.qdrant.url)
    status = "OK" if ok else "FAIL"
    print(f"  Qdrant ({config.qdrant.url}): {status}")
    all_ok = all_ok and ok

    # Neo4j
    ok = check_neo4j(config.neo4j.uri, config.neo4j.user, config.neo4j.password)
    status = "OK" if ok else "FAIL"
    print(f"  Neo4j  ({config.neo4j.uri}): {status}")
    all_ok = all_ok and ok

    return 0 if all_ok else 1


def main():
    parser = argparse.ArgumentParser(prog="document-assistant")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("check", help="Check connectivity to all services")

    args = parser.parse_args()

    if args.command == "check":
        print("Service health checks:")
        code = run_check()
        sys.exit(code)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
