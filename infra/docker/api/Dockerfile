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

# System build deps for asyncpg and friends.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install into an isolated prefix we can copy to the runtime image.
COPY services/api/pyproject.toml ./pyproject.toml
COPY services/api/README.md ./README.md
COPY services/api/src ./src

RUN pip install --prefix=/install .

# ---- Runtime ----------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:${PATH}"

# Non-root user.
RUN groupadd --gid 1001 app \
    && useradd --uid 1001 --gid app --create-home app

WORKDIR /app

# Runtime libpq for asyncpg.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /install
COPY services/api/src ./src
COPY services/api/alembic.ini ./alembic.ini
COPY services/api/migrations ./migrations

USER app

EXPOSE 8000

# Liveness for orchestrators without a compose healthcheck.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

CMD ["python", "-m", "src.main"]
