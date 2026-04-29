"""FastAPI application factory and lifespan management."""

import logging
import os
import time
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

from api.services import init_services, shutdown_services
from core.exceptions import ProviderNotConfigured, RateLimitError

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
    for name in ("httpcore", "httpx", "urllib3"):
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

    # CORS: ALLOWED_ORIGINS env var (comma-separated) overrides the dev defaults.
    # Set it via scripts/setupEnv.sh when running behind the nginx reverse proxy.
    _env_origins = os.getenv("ALLOWED_ORIGINS", "")
    _origins = (
        [o.strip() for o in _env_origins.split(",") if o.strip()]
        if _env_origins
        else [
            "http://localhost:5173",  # Vite dev server
            "app://.",  # Electron app (packaged)
            "file://",  # Electron renderer process
        ]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RateLimitError)
    async def rate_limit_handler(request: Request, exc: RateLimitError):
        logger.warning("Rate limit exceeded for provider '%s': retry_after=%.0fs", exc.provider, exc.retry_after)
        return JSONResponse(
            status_code=503,
            headers={"Retry-After": str(int(exc.retry_after))},
            content={
                "detail": "rate_limited",
                "provider": exc.provider,
                "retry_after": exc.retry_after,
            },
        )

    @app.exception_handler(ProviderNotConfigured)
    async def provider_not_configured_handler(request: Request, exc: ProviderNotConfigured):
        return JSONResponse(
            status_code=412,
            content={
                "detail": "provider_not_configured",
                "provider": exc.provider,
                "message": str(exc),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception: %s", traceback.format_exc())
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

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
    from api.routers import (  # noqa: PLC0415
        agents,
        auth,
        chat,
        config,
        credentials,
        health,
        knowledge_trees,
        tasks,
        users,
    )

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(config.router, prefix="/api", tags=["config"])
    app.include_router(auth.router, prefix="/api", tags=["auth"])
    app.include_router(users.router, prefix="/api", tags=["users"])
    app.include_router(tasks.router, prefix="/api", tags=["tasks"])
    app.include_router(knowledge_trees.router, prefix="/api", tags=["knowledge-trees"])
    app.include_router(chat.router, prefix="/api", tags=["chat"])
    app.include_router(agents.router, prefix="/api", tags=["agents"])
    app.include_router(credentials.router, prefix="/api", tags=["credentials"])

    return app


# Create app instance for uvicorn
app = create_app()
