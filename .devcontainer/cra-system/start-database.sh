#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
project_root="$repo_root/cra system"

docker compose -f "$project_root/deploy/compose.dev.yml" up -d postgres
for _ in $(seq 1 60); do
  if docker compose -f "$project_root/deploy/compose.dev.yml" \
    exec -T postgres pg_isready -U cra -d cra >/dev/null 2>&1; then
    exit 0
  fi
  sleep 1
done

echo "PostgreSQL did not become ready" >&2
exit 1
