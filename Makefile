.PHONY: start stop check clean prune help env-check dev-deps infra-deps

DOCKER_COMPOSE := docker compose
BACKEND_DIR := backend
PROVIDER ?=

help:
	@echo "Document Assistant - Infrastructure Management"
	@echo ""
	@echo "Available commands:"
	@echo "  make start                  - Interactive menu: choose environment and LLM provider"
	@echo "  make start PROVIDER=groq    - Skip provider menu, use Groq"
	@echo "  make start PROVIDER=ollama  - Skip provider menu, use Ollama"
	@echo "  make start PROVIDER=openrouter   - Skip provider menu, use OpenRouter"
	@echo "  make start PROVIDER=huggingface  - Skip provider menu, use HuggingFace"
	@echo "  make stop    - Stop all services"
	@echo "  make check   - Health check all services (requires Ollama running)"
	@echo "  make clean   - Remove all stored data (Docker volumes, cache, generated output)"
	@echo "  make prune   - Remove orphaned documents (manifest exists but no Qdrant data)"
	@echo "  make help    - Show this help message"

start: env-check
	@PROVIDER=$(PROVIDER) bash scripts/start.sh

env-check:
	@bash scripts/setupEnv.sh

infra-deps:
	@echo "Starting infrastructure services (Qdrant, Neo4j)..."
	$(DOCKER_COMPOSE) up -d
	@echo "Installing Python dependencies..."
	cd $(BACKEND_DIR) && uv sync
	@echo "Pulling Ollama models..."
	ollama pull llama3.2
	ollama pull nomic-embed-text

dev-deps:
	@if [ ! -d "frontend/node_modules" ]; then \
		echo "Installing frontend dependencies..."; \
		cd frontend && npm install; \
	fi

stop:
	@echo "Stopping all services..."
	$(DOCKER_COMPOSE) down
	pkill -f "uvicorn api.main:app" || true
	pkill -f "npm run dev" || true
	@echo "Services stopped."

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
