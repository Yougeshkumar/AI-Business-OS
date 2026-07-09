#!/usr/bin/env bash
# Apply database migrations.
set -euo pipefail

cd "$(dirname "$0")/../services/api"
# shellcheck disable=SC1091
[ -d .venv ] && source .venv/bin/activate
alembic upgrade head
