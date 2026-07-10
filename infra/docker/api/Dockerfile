# syntax=docker/dockerfile:1.7
# Multi-stage build for the FastAPI service.
# Build context is the repository root; service code lives in services/api.

# ---- Builder ----------------------------------------------------------------
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# System build deps for compiling wheels (asyncpg, etc.).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create a self-contained virtual environment. Copying an entire venv between
# stages is deterministic: it contains every installed package, its metadata,
# and working console scripts. This avoids the fragility of hand-picking
# system site-packages directories across build stages.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

# Install pinned runtime dependencies. Copying requirements.txt on its own line
# means this layer is only invalidated when dependencies actually change.
COPY services/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Sanity-check inside the build that every runtime dependency imports. If any
# dependency is missing, the build fails here rather than at container runtime.
RUN python - <<'PYCHECK'
import importlib
modules = [
    "fastapi", "starlette", "uvicorn", "pydantic", "pydantic_settings",
    "sqlalchemy", "asyncpg", "alembic", "redis", "structlog", "httpx",
]
for name in modules:
    importlib.import_module(name)
print("builder dependency import check: OK")
PYCHECK

# ---- Runtime ----------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:${PATH}"

# Non-root user.
RUN groupadd --gid 1001 app \
    && useradd --uid 1001 --gid app --create-home app

WORKDIR /app

# Runtime libpq for asyncpg.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy the complete virtual environment from the builder. Because PATH points at
# /opt/venv/bin, `python`, `uvicorn`, and `alembic` all resolve to this venv and
# every installed dependency (including structlog) is present.
COPY --from=builder /opt/venv /opt/venv

# Application source (imported as the `src` package via PYTHONPATH=/app).
COPY services/api/src ./src
COPY services/api/alembic.ini ./alembic.ini
COPY services/api/migrations ./migrations

USER app

EXPOSE 8000

# Liveness for orchestrators without a compose healthcheck.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

CMD ["python", "-m", "src.main"]
