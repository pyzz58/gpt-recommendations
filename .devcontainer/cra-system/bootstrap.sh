#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
project_root="$repo_root/cra system"

bash "$repo_root/.devcontainer/cra-system/start-database.sh"
python3 -m pip install --user uv==0.12.13
cd "$project_root"
uv sync --frozen --group dev
npm --prefix web ci

export CRA_ENV=synthetic
export CRA_DATABASE_URL=postgresql+psycopg://cra:synthetic@localhost:5432/cra
export CRA_SESSION_SECRET=synthetic-only-codespaces-session-secret
uv run --frozen alembic upgrade head
uv run --frozen python tools/seed_synthetic.py

docker compose -f "$project_root/deploy/compose.dev.yml" exec -T postgres \
  psql -U cra -d postgres -Atc \
  "SELECT 1 FROM pg_database WHERE datname = 'cra_test'" |
  grep -q 1 ||
  docker compose -f "$project_root/deploy/compose.dev.yml" exec -T postgres \
    createdb -U cra cra_test

CRA_DATABASE_URL=postgresql+psycopg://cra:synthetic@localhost:5432/cra_test \
  uv run --frozen alembic upgrade head
