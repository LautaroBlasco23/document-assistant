#!/usr/bin/env bash
# Usage: bash scripts/setupEnv.sh
# Creates .env with random passwords and defaults copied from .env.example.
# Safe to re-run: existing non-empty values are never overwritten.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$ROOT_DIR/.env"
EXAMPLE_FILE="$ROOT_DIR/.env.example"

# ── Helpers ────────────────────────────────────────────────────────────────────

gen_password() {
    openssl rand -base64 32 | tr -d '/+=' | head -c 32
}

# Return the value of KEY from FILE, or empty string if absent/empty.
get_val() {
    local file="$1" key="$2"
    [ -f "$file" ] || { echo ""; return; }
    grep "^${key}=" "$file" 2>/dev/null | head -1 | cut -d= -f2- || echo ""
}

# Write KEY=VALUE to .env, updating in place if the key already exists.
write_val() {
    local key="$1" value="$2"
    if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
    else
        echo "${key}=${value}" >> "$ENV_FILE"
    fi
}

# ── Bootstrap .env from .env.example ──────────────────────────────────────────

touch "$ENV_FILE"

echo "Syncing defaults from .env.example..."

while IFS= read -r line; do
    # Skip comments and blank lines
    [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue

    key="${line%%=*}"
    current=$(get_val "$ENV_FILE" "$key")
    if [ -z "$current" ]; then
        default="${line#*=}"
        write_val "$key" "$default"
    fi
done < "$EXAMPLE_FILE"

# ── Generate passwords (only when missing) ────────────────────────────────────

echo "Checking secrets..."

for secret_key in POSTGRES_PASSWORD; do
    current=$(get_val "$ENV_FILE" "$secret_key")
    if [ -z "$current" ]; then
        write_val "$secret_key" "$(gen_password)"
        echo "  Generated $secret_key"
    else
        echo "  Kept existing $secret_key"
    fi
done

# Keep DOCASSIST_POSTGRES__PASSWORD in sync with POSTGRES_PASSWORD so the local
# backend (started outside Docker) uses the same credential as the container.
pg_pass=$(get_val "$ENV_FILE" "POSTGRES_PASSWORD")
write_val "DOCASSIST_POSTGRES__PASSWORD" "$pg_pass"

# ── Compute ALLOWED_ORIGINS from DOMAIN + NGINX_PORT ──────────────────────────

DOMAIN=$(get_val "$ENV_FILE" "DOMAIN"); DOMAIN="${DOMAIN:-localhost}"
NGINX_PORT=$(get_val "$ENV_FILE" "NGINX_PORT"); NGINX_PORT="${NGINX_PORT:-80}"

origins="http://${DOMAIN}"
[ "$NGINX_PORT" != "80" ] && origins="${origins},http://${DOMAIN}:${NGINX_PORT}"
write_val "ALLOWED_ORIGINS" "$origins"
echo "  Set ALLOWED_ORIGINS=${origins}"

# ── Done ───────────────────────────────────────────────────────────────────────

echo ""
echo "Done. .env is ready at ${ENV_FILE}"
echo ""
echo "Manual steps required:"
echo "  1. Set DOCASSIST_GROQ__API_KEY if using Groq (DOCASSIST_LLM_PROVIDER=groq)"
echo "  2. Or set DOCASSIST_LLM_PROVIDER=ollama to use local Ollama instead"
echo "  3. Update DOMAIN and NGINX_PORT if deploying beyond localhost,"
echo "     then re-run this script to refresh ALLOWED_ORIGINS."
