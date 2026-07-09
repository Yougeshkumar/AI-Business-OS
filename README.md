# AI Business Operating System

Monorepo for the AI Business Operating System platform.

**Sprint 0 — Foundation.** This is the production-ready project skeleton only:
configuration, logging, database and Redis connections, error handling, health
checks, CI, Docker, and the migration harness. No business features (CRM,
Finance, HR, Inventory, Support, AI) are implemented yet — those arrive in later
sprints per the Implementation Roadmap.

## Repository layout

```
ai-bos/
├── apps/
│   └── web/                 # Next.js 15 web client
├── services/
│   └── api/                 # FastAPI backend (modular monolith)
│       ├── src/
│       │   ├── core/        # shared kernel: config, db, cache, logging,
│       │   │                #   middleware, errors, health
│       │   └── main/        # application factory + entrypoint
│       ├── migrations/      # Alembic
│       └── tests/           # unit + integration
├── packages/
│   └── contracts/           # shared API/event contracts (populated later)
├── infra/
│   ├── docker/              # per-service Dockerfiles
│   └── nginx/               # reverse proxy config
├── scripts/                 # dev + CI helper scripts
├── .github/workflows/       # CI
└── docker-compose.yml       # full local stack
```

## Prerequisites

- Docker + Docker Compose (for the full stack), **or**
- Python 3.12 + PostgreSQL 16 + Redis 7 (backend), and Node 22 + pnpm 10 (frontend)

## Quick start (Docker Compose)

```bash
cp .env.example .env
docker compose up --build
```

Services:

| Service  | URL                          |
|----------|------------------------------|
| Web      | http://localhost:3000        |
| API      | http://localhost:8000        |
| Swagger  | http://localhost:8000/docs   |
| Health   | http://localhost:8000/health |
| Nginx    | http://localhost:80          |

## Local development (without Docker)

Backend:

```bash
./scripts/dev-api.sh          # venv + install + run on :8000
```

Frontend:

```bash
./scripts/dev-web.sh          # npm install + dev server on :3000
```

## Quality checks

```bash
./scripts/check.sh            # lint + typecheck + tests (backend + frontend)
```

Backend individually:

```bash
cd services/api
ruff check . && ruff format --check . && mypy . && pytest
```

Frontend individually:

```bash
cd apps/web
npm run lint && npm run typecheck && npm run build
```

## Database migrations

```bash
./scripts/migrate.sh          # alembic upgrade head
```

## Validation checklist (Sprint 0 exit criteria)

Run these once dependencies are installed (they require network access to the
package registries):

```bash
# Frontend
cd apps/web && npm install && npm run lint && npm run typecheck && npm run build

# Backend
cd services/api && pip install -e ".[dev]"
python -m src.main            # FastAPI starts on :8000
# GET http://localhost:8000/health        -> 200
# GET http://localhost:8000/health/ready   -> 200 (with DB + Redis up)
# GET http://localhost:8000/docs           -> Swagger UI
pytest                        # unit + integration tests pass

# Full stack
docker compose up --build     # all five services start
```

## Design documents

The authoritative design lives in the approved documents: System Architecture,
Implementation Roadmap, Database Design, API Specification, Security
Architecture, and the ADR collection.
