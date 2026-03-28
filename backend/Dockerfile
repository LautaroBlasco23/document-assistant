FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /usr/local/bin/

WORKDIR /app

# Install dependencies first for better layer caching
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-cache

# Copy backend source
COPY backend/ ./

# Config lives one level above backend/ in the repo; replicate that here.
# infrastructure/config.py resolves PROJECT_ROOT as Path(__file__).parent.parent.parent
# which, from /app/infrastructure/config.py, evaluates to /  → looks for /config/default.yml
COPY config/ /config/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
