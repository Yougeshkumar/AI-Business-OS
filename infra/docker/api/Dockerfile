# Multi-stage build for the FastAPI service.
# Build context is the repository root; service code lives in services/api.

# ---- Builder ----------------------------------------------------------------
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# System build dependencies for compiling wheels (asyncpg, etc.).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install pinned runtime dependencies into an isolated virtual environment.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY services/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ---- Runtime ----------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Runtime library for asyncpg.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user.
RUN groupadd --gid 1001 app \
    && useradd --uid 1001 --gid app --create-home app

# Copy the virtual environment (all dependencies) from the builder.
COPY --from=builder /opt/venv /opt/venv

# Copy application source and migration assets.
COPY services/api/src ./src
COPY services/api/alembic.ini ./alembic.ini
COPY services/api/migrations ./migrations

USER app

EXPOSE 8000

CMD ["python", "-m", "src.main"]
