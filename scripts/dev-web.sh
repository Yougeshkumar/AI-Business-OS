#!/usr/bin/env bash
# Run the web app locally.
set -euo pipefail

cd "$(dirname "$0")/../apps/web"

if [ ! -f .env ]; then
  cp .env.example .env
fi

npm install
npm run dev
