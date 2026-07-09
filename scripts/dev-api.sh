#!/usr/bin/env bash
# Run the API locally (requires Postgres + Redis running).
set -euo pipefail

cd "$(dirname "$0")/../services/api"

if [ ! -d .venv ]; then
  python -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -e ".[dev]"

if [ ! -f .env ]; then
  cp .env.example .env
fi

python -m src.main
