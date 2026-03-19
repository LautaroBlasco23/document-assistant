"""FastAPI application factory and lifespan management."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.services import init_services, shutdown_services

logger = logging.getLogger(__name__)


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

    # Import and register routers
    from api.routers import health, documents, search, ask, chapters, config, tasks

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(documents.router, prefix="/api", tags=["documents"])
    app.include_router(search.router, prefix="/api", tags=["search"])
    app.include_router(ask.router, prefix="/api", tags=["ask"])
    app.include_router(chapters.router, prefix="/api", tags=["chapters"])
    app.include_router(config.router, prefix="/api", tags=["config"])
    app.include_router(tasks.router, prefix="/api", tags=["tasks"])

    return app


# Create app instance for uvicorn
app = create_app()
