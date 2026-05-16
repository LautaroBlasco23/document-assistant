.PHONY: start dev dev-backend mock stop app-logs app-ps dev-kill check clean prune help env-check dev-deps infra-deps tools jwt-secret encryption-key

DOCKER_COMPOSE := docker compose
BACKEND_DIR := backend
PROVIDER ?=

help:
	@echo "\033[1;36mDocument Assistant - Infrastructure Management\033[0m"
	@echo ""
	@echo "\033[1mAvailable commands:\033[0m"
	@echo ""
	@echo "  \033[1;32mSetup\033[0m"
	@echo "    make tools                          Check/install required development tools"
	@echo "    make tools install                  Install missing tools (auto-installs uv)"
	@echo ""
	@echo "  \033[1;32mDocker\033[0m"
	@echo "    make start                          Build & run all containers (detached)"
	@echo "    make stop                           Stop all containers"
	@echo "    make app-logs                       View container logs"
	@echo "    make app-ps                         List container status"
	@echo ""
	@echo "  \033[1;32mDevelopment (host backend + frontend)\033[0m"
	@echo "    make dev                            Start dev server"
	@echo "    make dev PROVIDER=groq              Start dev server with specific provider"
	@echo "    make dev-backend                    Start backend only (with PostgreSQL)"
	@echo "    make dev-backend PROVIDER=groq      Start backend only with specific provider"
	@echo "    make mock                           Frontend only, no backend (mock data)"
	@echo ""
	@echo "  \033[1;32mServices\033[0m"
	@echo "    make dev-kill                       Force kill backend (8000) & frontend (5173)"
	@echo "    make check                          Health check all services"
	@echo ""
	@echo "  \033[1;32mMaintenance\033[0m"
	@echo "    make clean                          Remove volumes, cache, generated output"
	@echo "    make prune                          Remove orphaned documents"
	@echo ""
	@echo "  \033[1;32mHelp\033[0m"
	@echo "    make encryption-key                 Generate a Fernet encryption key for .env"
	@echo "    make help                           Show this help message"

tools-check:
	@bash scripts/check-tools.sh check || { \
		echo ""; \
		echo "\033[1;31mSome required tools are missing.\033[0m"; \
		echo ""; \
		echo "Please run \033[1;32mmake tools\033[0m to check and install the required tools"; \
		echo "before using \033[1;32mmake start\033[0m."; \
		echo ""; \
		echo "For more details, see: make tools help"; \
		exit 1; \
	}

tools:
	@bash scripts/check-tools.sh install

jwt-secret:
	@bash scripts/generate-jwt-secret.sh

encryption-key:
	@bash scripts/generate-encryption-key.sh

start: env-check
	@echo "Building Docker images (current code)..."
	$(DOCKER_COMPOSE) build
	@echo "Starting all services (detached)..."
	$(DOCKER_COMPOSE) up -d --remove-orphans

stop:
	@echo "Stopping containers and dev processes..."
	$(DOCKER_COMPOSE) down
	pkill -f "uvicorn api.main:app" || true
	pkill -f "npm run dev" || true

app-logs:
	$(DOCKER_COMPOSE) logs -f

app-ps:
	$(DOCKER_COMPOSE) ps

dev: env-check tools-check
	@echo "Starting dev server (dev mode)..."
	@AUTO_DEFAULTS=1 PROVIDER=$(PROVIDER) bash scripts/start.sh

dev-backend: env-check tools-check
	@echo "Starting backend only..."
	@echo "Starting PostgreSQL..."
	$(DOCKER_COMPOSE) up -d postgres
	@echo "Waiting for PostgreSQL to be ready..."
	@until $(DOCKER_COMPOSE) exec -T postgres pg_isready -U docassist > /dev/null 2>&1; do sleep 1; done
	@echo "Installing Python dependencies..."
	cd $(BACKEND_DIR) && uv sync
	@echo "Starting backend on port 8000..."
	@set -a; [ -f .env ] && . ./.env; set +a; \
	cd $(BACKEND_DIR) && DOCASSIST_POSTGRES__HOST=localhost DOCASSIST_POSTGRES__PORT="$${DEV_POSTGRES_PORT:-5433}" DOCASSIST_LLM_PROVIDER="$(PROVIDER)" uv run uvicorn api.main:app --port 8000 --reload

mock: tools-check dev-deps
	@echo "Starting frontend in mock mode (no backend required)..."
	@cd frontend && VITE_MOCK=true npm run dev

env-check:
	@bash scripts/setupEnv.sh

infra-deps: tools-check
	@echo "Starting infrastructure services (PostgreSQL)..."
	$(DOCKER_COMPOSE) up -d postgres
	@echo "Installing Python dependencies..."
	cd $(BACKEND_DIR) && uv sync


dev-deps:
	@if [ ! -d "frontend/node_modules" ]; then \
		echo "Installing frontend dependencies..."; \
		cd frontend && npm install; \
	fi

dev-kill:
	@echo "Force killing backend (port 8000) and frontend (port 5173)..."
	@fuser -k 8000/tcp 2>/dev/null || true
	@fuser -k 5173/tcp 2>/dev/null || true
	@echo "Processes killed."

check:
	@echo "Checking service health..."
	@set -a; [ -f .env ] && . ./.env; set +a; \
	cd $(BACKEND_DIR) && uv run python -m cli.main check

clean:
	@echo "Stopping services and removing Docker volumes..."
	$(DOCKER_COMPOSE) down -v
	@echo "Clearing embedding cache..."
	rm -rf data/.cache
	@echo "Clearing generated output..."
	rm -rf data/output/*
	@echo "Clearing uploaded files..."
	rm -rf data/uploads/*
	@echo "Clean complete. Source files in data/raw/ are untouched."

prune:
	@echo "Pruning orphaned documents (no Qdrant data)..."
	@set -a; [ -f .env ] && . ./.env; set +a; \
	cd $(BACKEND_DIR) && uv run python -m cli.main prune
