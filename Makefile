.PHONY: start stop check help dev-deps infra-deps

DOCKER_COMPOSE := docker compose -f docker/docker-compose.yml

help:
	@echo "Document Assistant - Infrastructure Management"
	@echo ""
	@echo "Available commands:"
	@echo "  make start   - Start infrastructure, backend, and frontend"
	@echo "  make stop    - Stop all services"
	@echo "  make check   - Health check all services (requires Ollama running)"
	@echo "  make help    - Show this help message"

start: infra-deps dev-deps
	@echo "Starting backend (http://localhost:8000)..."
	@nohup uv run uvicorn api.main:app --port 8000 > .backend.log 2>&1 &
	@sleep 1
	@echo "Starting frontend dev server (http://localhost:5173)..."
	@cd frontend && npm run dev &
	@echo "✓ Infrastructure, backend, and frontend started"
	@echo "  Backend:  http://localhost:8000/api/health"
	@echo "  Frontend: http://localhost:5173"
	@echo "  Logs: tail -f .backend.log"

infra-deps:
	@echo "Starting infrastructure services (Qdrant, Neo4j)..."
	$(DOCKER_COMPOSE) up -d
	@echo "Installing Python dependencies..."
	uv sync
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
	uv run python -m cli.main check
