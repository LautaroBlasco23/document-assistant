.PHONY: start mock stop dev-kill check clean prune help env-check dev-deps infra-deps desktop-dev desktop-build desktop-dist desktop-exe desktop-exe-docker

DOCKER_COMPOSE := docker compose
BACKEND_DIR := backend
PROVIDER ?=
DESKTOP_DIR := desktop

help:
	@echo "\033[1;36mDocument Assistant - Infrastructure Management\033[0m"
	@echo ""
	@echo "\033[1mAvailable commands:\033[0m"
	@echo ""
	@echo "  \033[1;32mStartup\033[0m"
	@echo "    make start                          Interactive menu for environment & provider"
	@echo "    make start PROVIDER=groq            Use Groq"
	@echo "    make start PROVIDER=ollama          Use local Ollama"
	@echo "    make start PROVIDER=openrouter      Use OpenRouter"
	@echo "    make start PROVIDER=huggingface     Use HuggingFace"
	@echo "    make mock                           Frontend only, no backend (mock data)"
	@echo ""
	@echo "  \033[1;32mServices\033[0m"
	@echo "    make stop                           Stop all services"
	@echo "    make dev-kill                       Force kill backend (8000) & frontend (5173)"
	@echo "    make check                          Health check all services"
	@echo ""
	@echo "  \033[1;32mMaintenance\033[0m"
	@echo "    make clean                          Remove volumes, cache, generated output"
	@echo "    make prune                          Remove orphaned documents"
	@echo ""
	@echo "  \033[1;32mDesktop (Electron)\033[0m"
	@echo "    make desktop-dev                    Start desktop app in development mode"
	@echo "    make desktop-build                  Build desktop app for production"
	@echo "    make desktop-dist                   Package desktop app for distribution (Linux)"
	@echo "    make desktop-exe                    Build Windows executable (.exe) - requires Wine"
	@echo "    make desktop-exe-docker             Build Windows executable using Docker (recommended)"
	@echo ""
	@echo "  \033[1;32mHelp\033[0m"
	@echo "    make help                           Show this help message"

start: env-check
	@PROVIDER=$(PROVIDER) bash scripts/start.sh

mock: dev-deps
	@echo "Starting frontend in mock mode (no backend required)..."
	@cd frontend && VITE_MOCK=true npm run dev

env-check:
	@bash scripts/setupEnv.sh

infra-deps:
	@echo "Starting infrastructure services (PostgreSQL)..."
	$(DOCKER_COMPOSE) up -d postgres
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

# Desktop (Electron) commands
desktop-dev: dev-deps
	@echo "Starting desktop app in development mode..."
	@cd $(DESKTOP_DIR) && npm install && npm run dev

desktop-build: dev-deps
	@echo "Building desktop app..."
	@cd $(DESKTOP_DIR) && npm install && npm run build

desktop-dist: dev-deps
	@echo "Packaging desktop app for distribution..."
	@cd $(DESKTOP_DIR) && npm install && npm run dist

desktop-exe: dev-deps
	@echo "Building Windows executable..."
	@cd $(DESKTOP_DIR) && npm install
	@cd frontend && npm run build
	@cd $(DESKTOP_DIR) && npm run build
	@cd $(DESKTOP_DIR) && npx electron-builder --win --x64 --publish never
	@echo ""
	@echo "✅ Windows executable created!"
	@echo "📍 Location: $(DESKTOP_DIR)/dist/"
	@echo "📁 Files:"
	@echo "   - Document Assistant Setup 1.0.0.exe  (installer)"
	@echo "   - Document Assistant 1.0.0.exe        (portable)"

# Build Windows executable using Docker (recommended - avoids Wine issues on WSL)
desktop-exe-docker:
	@echo "Building Windows executable using Docker..."
	@docker run --rm -it \
		-v "$(PWD)":/project \
		-w /project/desktop \
		electronuserland/builder:wine \
		bash -c "cd ../frontend && npm install && npm run build && cd ../desktop && npm install && npm run build && npx electron-builder --win --x64 --publish never"
	@echo ""
	@echo "✅ Windows executable created!"
	@echo "📍 Location: $(DESKTOP_DIR)/dist/"
