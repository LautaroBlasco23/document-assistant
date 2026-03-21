.PHONY: start stop check help dev-deps infra-deps

DOCKER_COMPOSE := docker compose -f docker/docker-compose.yml

help:
	@echo "Document Assistant - Infrastructure Management"
	@echo ""
	@echo "Available commands:"
	@echo "  make start   - Start infrastructure, backend, and frontend (Ctrl+C to stop all)"
	@echo "  make stop    - Stop all services"
	@echo "  make check   - Health check all services (requires Ollama running)"
	@echo "  make help    - Show this help message"

start: infra-deps dev-deps
	@for port in 5173 5174 5175 5176 5177; do \
		if lsof -Pi :$$port -sTCP:LISTEN -t >/dev/null 2>&1; then \
			echo "Killing process on port $$port..."; \
			lsof -ti:$$port | xargs kill -9 2>/dev/null || true; \
		fi; \
	done
	@echo "Starting backend (http://localhost:8000) and frontend (http://localhost:5173)..."
	@trap "make stop" EXIT; \
	uv run python -m uvicorn api.main:app --port 8000 --log-level warning --no-access-log & \
	BACKEND_PID=$$!; \
	echo "Waiting for backend to be ready..."; \
	for i in $$(seq 1 15); do \
		if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then \
			echo "Backend is ready."; \
			break; \
		fi; \
		echo "Waiting... ($$i/15)"; \
		sleep 1; \
	done; \
	curl -sf http://localhost:8000/api/health > /dev/null 2>&1 || { echo "Backend failed to start."; kill $$BACKEND_PID 2>/dev/null; exit 1; }; \
	cd frontend && VITE_MOCK=false npm run dev 2>&1 | sed 's/^/[web] /'; \
	wait $$BACKEND_PID

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
