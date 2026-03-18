.PHONY: start stop check help

DOCKER_COMPOSE := docker compose -f docker/docker-compose.yml

help:
	@echo "Document Assistant - Infrastructure Management"
	@echo ""
	@echo "Available commands:"
	@echo "  make start   - Start Qdrant and Neo4j services"
	@echo "  make stop    - Stop all services"
	@echo "  make check   - Health check all services (requires Ollama running)"
	@echo "  make help    - Show this help message"

start:
	@echo "Starting infrastructure services (Qdrant, Neo4j)..."
	$(DOCKER_COMPOSE) up -d
	@echo "Installing Python dependencies..."
	uv sync
	@echo "Pulling Ollama models..."
	ollama pull llama3.2
	ollama pull nomic-embed-text
	@echo "Infrastructure ready. Run 'make check' to verify health."

stop:
	@echo "Stopping all services..."
	$(DOCKER_COMPOSE) down
	@echo "Services stopped."

check:
	@echo "Checking service health..."
	uv run python -m cli.main check
