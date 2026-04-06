#!/usr/bin/env bash
set -uo pipefail

# Load .env
set -a
[ -f .env ] && . ./.env
set +a

BACKEND_DIR="backend"
DOCKER_COMPOSE="docker compose"

# ── Provider menu ──────────────────────────────────────────────────────────────

select_provider() {
    local current="${DOCASSIST_LLM_PROVIDER:-groq}"
    echo ""
    echo "Select LLM provider:"
    echo "  1) groq        (Groq API — requires DOCASSIST_GROQ__API_KEY)"
    echo "  2) ollama      (local — no key needed)"
    echo "  3) openrouter  (OpenRouter free tier — requires DOCASSIST_OPENROUTER__API_KEY)"
    echo "  4) huggingface (HuggingFace free tier — requires DOCASSIST_HUGGINGFACE__API_KEY)"
    printf "Choice [1-4, Enter to keep .env default (%s)]: " "$current"
    read -r SELECTION || true
    case "$SELECTION" in
        1) CHOSEN_PROVIDER=groq ;;
        2) CHOSEN_PROVIDER=ollama ;;
        3) CHOSEN_PROVIDER=openrouter ;;
        4) CHOSEN_PROVIDER=huggingface ;;
        *) CHOSEN_PROVIDER="$current" ;;
    esac
}

# ── Environment menu ───────────────────────────────────────────────────────────

echo ""
echo "Select environment:"
echo "  1) dev          - backend + frontend in dev mode (infra in Docker)"
echo "  2) full-docker  - everything in Docker (backend, frontend, nginx)"
printf "Choice [1-2, default: dev]: "
read -r ENV_CHOICE || true

case "$ENV_CHOICE" in
    2) ENV_MODE=full-docker ;;
    *) ENV_MODE=dev ;;
esac

# ── Provider selection ─────────────────────────────────────────────────────────

if [ -n "${PROVIDER:-}" ]; then
    CHOSEN_PROVIDER="$PROVIDER"
else
    select_provider
fi
export DOCASSIST_LLM_PROVIDER="$CHOSEN_PROVIDER"

# ── Dev mode ───────────────────────────────────────────────────────────────────

if [ "$ENV_MODE" = "dev" ]; then

    # Kill any lingering frontend dev ports
    for port in 5173 5174 5175 5176 5177; do
        if lsof -Pi :"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo "Killing process on port $port..."
            lsof -ti:"$port" | xargs kill -9 2>/dev/null || true
        fi
    done

    echo "Starting infrastructure services (PostgreSQL)..."
    $DOCKER_COMPOSE up -d postgres

    echo "Installing Python dependencies..."
    cd "$BACKEND_DIR" && uv sync && cd ..

    echo "Pulling Ollama models..."
    ollama pull llama3.2
    ollama pull nomic-embed-text

    if [ ! -d "frontend/node_modules" ]; then
        echo "Installing frontend dependencies..."
        cd frontend && npm install && cd ..
    fi

    echo ""
    echo "Starting backend (http://localhost:8000) and frontend (http://localhost:5173) with provider: $CHOSEN_PROVIDER..."

    cleanup() {
        $DOCKER_COMPOSE stop postgres
        pkill -f "uvicorn api.main:app" 2>/dev/null || true
        pkill -f "npm run dev" 2>/dev/null || true
    }
    trap cleanup EXIT

    (cd "$BACKEND_DIR" && uv run uvicorn api.main:app --port 8000 --reload --log-level warning --no-access-log) &
    BACKEND_PID=$!

    echo "Waiting for backend to be ready..."
    for i in $(seq 1 15); do
        if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
            echo "Backend is ready."
            break
        fi
        echo "Waiting... ($i/15)"
        sleep 1
    done

    if ! curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "Backend failed to start."
        kill "$BACKEND_PID" 2>/dev/null
        exit 1
    fi

    cd frontend && VITE_MOCK=false npm run dev 2>&1 | sed 's/^/[web] /'
    wait "$BACKEND_PID"

# ── Full-docker mode ───────────────────────────────────────────────────────────

else

    # Checkbox build menu — select which images to rebuild before starting
    SERVICES=(backend frontend)
    SELECTED=(0 0)
    COUNT=${#SERVICES[@]}

    while true; do
        echo ""
        echo "Select images to rebuild (enter number to toggle, Enter to proceed):"
        for i in "${!SERVICES[@]}"; do
            if [ "${SELECTED[$i]}" -eq 1 ]; then
                mark="x"
            else
                mark=" "
            fi
            echo "  [$mark] $((i + 1))) ${SERVICES[$i]}"
        done
        printf "Toggle [1-%d] or Enter to proceed: " "$COUNT"
        read -r TOGGLE_INPUT || true

        if [ -z "${TOGGLE_INPUT:-}" ]; then
            break
        fi

        if [[ "$TOGGLE_INPUT" =~ ^[0-9]+$ ]]; then
            idx=$((TOGGLE_INPUT - 1))
            if [ "$idx" -ge 0 ] && [ "$idx" -lt "$COUNT" ]; then
                if [ "${SELECTED[$idx]}" -eq 1 ]; then
                    SELECTED[$idx]=0
                else
                    SELECTED[$idx]=1
                fi
            fi
        fi
    done

    # Run docker compose build for each selected service
    BUILD_TARGETS=""
    for i in "${!SERVICES[@]}"; do
        if [ "${SELECTED[$i]}" -eq 1 ]; then
            BUILD_TARGETS="$BUILD_TARGETS ${SERVICES[$i]}"
        fi
    done

    if [ -n "${BUILD_TARGETS:-}" ]; then
        echo ""
        echo "Building:$BUILD_TARGETS..."
        # shellcheck disable=SC2086
        $DOCKER_COMPOSE build $BUILD_TARGETS
    fi

    echo ""
    echo "Starting all services with provider: $CHOSEN_PROVIDER..."
    $DOCKER_COMPOSE up -d

    echo ""
    echo "Services started. Access the app at http://localhost:${NGINX_PORT:-80}"

fi
