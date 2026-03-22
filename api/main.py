"""FastAPI application factory and lifespan management."""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request

from api.services import init_services, shutdown_services

logger = logging.getLogger(__name__)

# ANSI color codes for log levels
_LEVEL_COLORS = {
    "DEBUG": "\033[36m",     # Cyan
    "INFO": "\033[32m",      # Green
    "WARNING": "\033[33m",   # Yellow
    "ERROR": "\033[31m",     # Red
    "CRITICAL": "\033[35m",  # Magenta
}
_RESET = "\033[0m"


class _ApiFormatter(logging.Formatter):
    """Formatter that adds [api] prefix and ANSI colors to log level names."""

    def format(self, record: logging.LogRecord) -> str:
        color = _LEVEL_COLORS.get(record.levelname, "")
        colored_level = f"{color}{record.levelname:<8}{_RESET}"
        # Temporarily override levelname for formatting
        original_levelname = record.levelname
        record.levelname = colored_level
        msg = super().format(record)
        record.levelname = original_levelname
        return f"[api] {msg}"


def _configure_logging() -> None:
    """Configure root logger for API server use."""
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    handler = logging.StreamHandler()
    handler.setFormatter(_ApiFormatter(fmt=fmt, datefmt="%H:%M:%S"))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # Remove any handlers uvicorn or other importers added before us,
    # then install our single formatted handler to avoid double-emission.
    root.handlers = []
    root.addHandler(handler)

    # Suppress noisy third-party loggers
    for name in ("httpcore", "httpx", "urllib3", "neo4j", "qdrant_client"):
        logging.getLogger(name).setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    init_services()
    logger.info("FastAPI app started")

    yield

    # Shutdown
    shutdown_services()
    logger.info("FastAPI app shut down")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    _configure_logging()

    app = FastAPI(
        title="Document Assistant API",
        description="Local document reader with hybrid retrieval",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS configuration: allow Electron app, dev Vite server, and file:// protocol
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",  # Vite dev server
            "app://.",  # Electron app (packaged)
            "file://",  # Electron renderer process
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        path = request.url.path
        level = (
            logging.DEBUG
            if path == "/api/health" or path.startswith("/api/tasks/")
            else logging.INFO
        )
        logger.log(
            level,
            "%s %s -> %d (%.0fms)",
            request.method,
            path,
            response.status_code,
            duration_ms,
        )
        return response

    # Import and register routers
    from api.routers import health, documents, search, ask, chapters, config, tasks, content

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(documents.router, prefix="/api", tags=["documents"])
    app.include_router(search.router, prefix="/api", tags=["search"])
    app.include_router(ask.router, prefix="/api", tags=["ask"])
    app.include_router(chapters.router, prefix="/api", tags=["chapters"])
    app.include_router(config.router, prefix="/api", tags=["config"])
    app.include_router(tasks.router, prefix="/api", tags=["tasks"])
    app.include_router(content.router, prefix="/api", tags=["content"])

    return app


# Create app instance for uvicorn
app = create_app()
