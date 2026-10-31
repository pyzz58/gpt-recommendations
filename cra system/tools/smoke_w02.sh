#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

api_port="${CRA_SMOKE_API_PORT:-8000}"
web_port="${CRA_SMOKE_WEB_PORT:-5173}"
api_log="${TMPDIR:-/tmp}/cra-w02-api.log"
web_log="${TMPDIR:-/tmp}/cra-w02-web.log"
cookie_jar="${TMPDIR:-/tmp}/cra-w02-cookies.txt"
api_pid=""
web_pid=""

cleanup() {
  if [[ -n "$web_pid" ]]; then
    kill "$web_pid" 2>/dev/null || true
    wait "$web_pid" 2>/dev/null || true
  fi
  if [[ -n "$api_pid" ]]; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT

.venv/bin/uvicorn cra_app.main:app \
  --app-dir backend --host 127.0.0.1 --port "$api_port" >"$api_log" 2>&1 &
api_pid=$!

for _ in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:$api_port/health/live" >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done
if ! curl -fsS "http://127.0.0.1:$api_port/health/live" | grep -q '"status":"ok"'; then
  cat "$api_log" >&2
  exit 1
fi
curl -fsS "http://127.0.0.1:$api_port/health/ready" | grep -q '"status":"ready"'

uv run --frozen python tools/seed_synthetic.py >/dev/null
curl -fsS -c "$cookie_jar" -X POST \
  "http://127.0.0.1:$api_port/api/v1/auth/synthetic/session" >/dev/null
scopes="$(curl -fsS -b "$cookie_jar" "http://127.0.0.1:$api_port/api/v1/me/scopes")"
printf '%s' "$scopes" | grep -q '"code":"SYNTH-001"'
printf '%s' "$scopes" | grep -q '"code":"S01"'
printf '%s' "$scopes" | grep -q '"code":"S02"'

CRA_API_PROXY_TARGET="http://127.0.0.1:$api_port" \
  node web/node_modules/vite/bin/vite.js web \
  --host 127.0.0.1 --port "$web_port" --strictPort >"$web_log" 2>&1 &
web_pid=$!
for _ in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:$web_port/" >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done
if ! curl -fsS "http://127.0.0.1:$web_port/" | grep -q "CRA 监查工作台"; then
  cat "$web_log" >&2
  exit 1
fi

echo "W02 runtime smoke passed: API, synthetic session, scopes and Vite shell"
