"""
Unit tests for the FastAPI application factory and lifespan.

Subject: api/main.py — create_app(), lifespan(), _configure_logging(), exception handlers, middleware
Scope:   App creation, CORS configuration, exception handlers (RateLimitError 503,
         ProviderNotConfigured 412, unhandled 500), request logging middleware.
Out of scope:
  - Router behavior                    → individual router test files
  - Actual service initialization      → test_services.py
Setup:   Patches for init_services/shutdown_services to avoid real DB/LLM connections.
"""

import logging
import time
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from core.exceptions import ProviderNotConfigured, RateLimitError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PATCH_TARGETS = [
    "api.main.init_services",
    "api.main.shutdown_services",
]


def _make_app():
    """Create a test app with all real dependencies mocked."""
    patches = [patch(t) for t in _PATCH_TARGETS]
    for p in patches:
        p.start()

    # Configure init_services to return a mock Services object
    mock_services = MagicMock()
    patch("api.main.init_services", return_value=mock_services).start()

    # Import after patching so create_app() uses mocked dependencies
    from api.main import create_app

    app = create_app()
    return app, patches


def _cleanup(patches):
    for p in reversed(patches):
        p.stop()


# ---------------------------------------------------------------------------
# create_app
# ---------------------------------------------------------------------------


def test_create_app_returns_fastapi_instance():
    """create_app() must return a configured FastAPI application."""
    app, patches = _make_app()
    try:
        assert app.title == "Document Assistant API"
        assert app.version == "0.1.0"
    finally:
        _cleanup(patches)


def test_create_app_registers_all_routers():
    """create_app() must register all 9 routers."""
    app, patches = _make_app()
    try:
        routes = [r.path for r in app.routes]
        # Verify key endpoints from each router are present
        assert "/api/health" in routes
        assert "/api/config" in routes
        assert "/api/auth/register" in routes
        assert "/api/auth/login" in routes
        assert "/api/tasks/active" in routes
        assert "/api/knowledge-trees" in routes
        assert "/api/chat" in routes
        assert "/api/agents" in routes
        assert "/api/credentials" in routes
    finally:
        _cleanup(patches)


# ---------------------------------------------------------------------------
# CORS configuration
# ---------------------------------------------------------------------------


def test_cors_default_origins():
    """Without ALLOWED_ORIGINS env var, CORS must allow Vite dev, Electron app, and file://."""
    app, patches = _make_app()
    try:
        client = TestClient(app)
        response = client.options(
            "/api/health",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    finally:
        _cleanup(patches)


def test_cors_allows_electron_origin():
    """CORS must allow the Electron app origin (app://.)."""
    app, patches = _make_app()
    try:
        client = TestClient(app)
        response = client.options(
            "/api/health",
            headers={"Origin": "app://.", "Access-Control-Request-Method": "GET"},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "app://."
    finally:
        _cleanup(patches)


def test_cors_env_override():
    """ALLOWED_ORIGINS env var must override the default CORS origins."""
    with patch.dict("os.environ", {"ALLOWED_ORIGINS": "https://myapp.example.com"}):
        # Need to reload the module to pick up the new env var
        import importlib

        import api.main
        importlib.reload(api.main)


        app, patches = _make_app()
        try:
            client = TestClient(app)
            response = client.options(
                "/api/health",
                headers={"Origin": "https://myapp.example.com", "Access-Control-Request-Method": "GET"},
            )
            assert response.status_code == 200
            assert response.headers.get("access-control-allow-origin") == "https://myapp.example.com"

            # Default origins should no longer work
            response2 = client.options(
                "/api/health",
                headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
            )
            # The origin should not be in the allow list
            assert response2.headers.get("access-control-allow-origin") != "http://localhost:5173"
        finally:
            _cleanup(patches)


# ---------------------------------------------------------------------------
# RateLimitError exception handler
# ---------------------------------------------------------------------------


def test_rate_limit_error_returns_503():
    """RateLimitError must be handled with HTTP 503 and Retry-After header."""
    app, patches = _make_app()
    try:

        @app.get("/trigger-rate-limit")
        def _trigger():
            raise RateLimitError(provider="groq", retry_after=30.0)

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/trigger-rate-limit")

        assert response.status_code == 503
        body = response.json()
        assert body["detail"] == "rate_limited"
        assert body["provider"] == "groq"
        assert body["retry_after"] == 30.0
        assert response.headers.get("Retry-After") == "30"
    finally:
        _cleanup(patches)


def test_rate_limit_error_retry_after_header():
    """Retry-After header must be the integer part of retry_after."""
    app, patches = _make_app()
    try:

        @app.get("/trigger-rate-limit-float")
        def _trigger():
            raise RateLimitError(provider="ollama", retry_after=15.7)

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/trigger-rate-limit-float")

        assert response.status_code == 503
        assert response.headers.get("Retry-After") == "15"
    finally:
        _cleanup(patches)


# ---------------------------------------------------------------------------
# ProviderNotConfigured exception handler
# ---------------------------------------------------------------------------


def test_provider_not_configured_returns_412():
    """ProviderNotConfigured must be handled with HTTP 412."""
    app, patches = _make_app()
    try:

        @app.get("/trigger-provider-not-configured")
        def _trigger():
            raise ProviderNotConfigured(provider="gemini")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/trigger-provider-not-configured")

        assert response.status_code == 412
        body = response.json()
        assert body["detail"] == "provider_not_configured"
        assert body["provider"] == "gemini"
        assert "gemini" in body["message"].lower()
    finally:
        _cleanup(patches)


# ---------------------------------------------------------------------------
# Unhandled exception handler
# ---------------------------------------------------------------------------


def test_unhandled_exception_returns_500():
    """Any unhandled Exception must return HTTP 500 with a JSON error body."""
    app, patches = _make_app()
    try:

        @app.get("/trigger-unhandled")
        def _trigger():
            raise ValueError("unexpected error")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/trigger-unhandled")

        assert response.status_code == 500
        body = response.json()
        assert body["detail"] == "Internal Server Error"
    finally:
        _cleanup(patches)


def test_unhandled_exception_logs_error():
    """Unhandled exceptions must be logged with traceback."""
    app, patches = _make_app()
    try:

        @app.get("/trigger-logging")
        def _trigger():
            raise RuntimeError("test error for logging")

        with patch("api.main.logger") as mock_logger:
            client = TestClient(app, raise_server_exceptions=False)
            client.get("/trigger-logging")
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args[0]
            assert "Unhandled exception" in call_args[0]
    finally:
        _cleanup(patches)


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------


def test_log_requests_logs_normal_requests_at_info():
    """Non-health/task requests must be logged at INFO level."""
    app, patches = _make_app()
    try:

        @app.get("/test-endpoint")
        def _test():
            return {"ok": True}

        with patch("api.main.logger") as mock_logger:
            client = TestClient(app)
            client.get("/test-endpoint")

            # Find the log call for our endpoint
            info_calls = [c for c in mock_logger.log.call_args_list if c[0][0] == logging.INFO]
            assert len(info_calls) >= 1
            # The log message format string should contain the expected pattern
            log_format = info_calls[0][0][1]
            assert "%s" in log_format  # Format string placeholder
            # Check the args passed to the formatter
            log_args = info_calls[0][0][2:]
            assert "GET" in log_args
            assert "/test-endpoint" in log_args
    finally:
        _cleanup(patches)


def test_log_requests_logs_health_at_debug():
    """Health check requests must be logged at DEBUG level to reduce noise."""
    app, patches = _make_app()
    try:
        # The health router needs app.state.services
        mock_services = MagicMock()
        app.state.services = mock_services

        with patch("api.main.logger") as mock_logger:
            client = TestClient(app)
            client.get("/api/health")

            debug_calls = [c for c in mock_logger.log.call_args_list if c[0][0] == logging.DEBUG]
            assert len(debug_calls) >= 1
            log_args = debug_calls[0][0][2:]
            assert "/api/health" in log_args
    finally:
        _cleanup(patches)


def test_log_requests_logs_task_polling_at_debug():
    """Task polling requests must be logged at DEBUG level."""
    app, patches = _make_app()
    try:
        # The tasks router needs app.state.services
        mock_services = MagicMock()
        mock_services.task_registry.list_active.return_value = []
        app.state.services = mock_services

        with patch("api.main.logger") as mock_logger:
            client = TestClient(app)
            client.get("/api/tasks/active")

            debug_calls = [c for c in mock_logger.log.call_args_list if c[0][0] == logging.DEBUG]
            assert len(debug_calls) >= 1
            log_args = debug_calls[0][0][2:]
            assert "/api/tasks/active" in log_args
    finally:
        _cleanup(patches)


def test_log_requests_includes_duration():
    """Log messages must include request duration in milliseconds."""
    app, patches = _make_app()
    try:

        @app.get("/slow-endpoint")
        def _slow():
            time.sleep(0.01)
            return {"ok": True}

        with patch("api.main.logger") as mock_logger:
            client = TestClient(app)
            client.get("/slow-endpoint")

            info_calls = [c for c in mock_logger.log.call_args_list if c[0][0] == logging.INFO]
            assert len(info_calls) >= 1
            log_msg = info_calls[0][0][1]
            # The format string includes (%.0fms)
            assert "ms" in log_msg
    finally:
        _cleanup(patches)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


def test_lifespan_calls_init_and_shutdown():
    """The lifespan context manager must call init_services on startup and shutdown_services on exit."""
    app, patches = _make_app()
    try:
        mock_init = patch("api.main.init_services").start()
        mock_shutdown = patch("api.main.shutdown_services").start()

        import asyncio

        from api.main import lifespan

        async def _test():
            async with lifespan(app):
                mock_init.assert_called_once()
                mock_shutdown.assert_not_called()
                assert hasattr(app.state, "services")
            mock_shutdown.assert_called_once()

        asyncio.run(_test())
    finally:
        _cleanup(patches)
