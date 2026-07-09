# AI BOS — API Service

FastAPI backend for the AI Business Operating System. Sprint 0 delivers the
production-ready foundation only: configuration, logging, database and Redis
connections, error handling, health checks, and the migration harness. No
business modules are implemented yet.

## Requirements

- Python 3.12+
- PostgreSQL 16
- Redis 7

## Setup

```bash
cd services/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Run

```bash
python -m src.main
# API:     http://localhost:8000
# Swagger: http://localhost:8000/docs
# Health:  http://localhost:8000/health
```

## Database migrations

```bash
alembic revision --autogenerate -m "message"
alembic upgrade head
```

## Quality checks

```bash
ruff check .
ruff format --check .
mypy .
pytest
```
