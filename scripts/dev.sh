#!/usr/bin/env bash
# Start the full local stack with Docker Compose.
set -euo pipefail

if [ ! -f .env ]; then
  echo "No .env found — copying from .env.example"
  cp .env.example .env
fi

docker compose up --build "$@"
