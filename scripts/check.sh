#!/usr/bin/env bash
# Run all quality checks (backend + frontend).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "== Backend =="
cd "$ROOT/services/api"
ruff check .
ruff format --check .
mypy .
pytest

echo "== Frontend =="
cd "$ROOT/apps/web"
npm run lint
npm run typecheck
npm run format:check
