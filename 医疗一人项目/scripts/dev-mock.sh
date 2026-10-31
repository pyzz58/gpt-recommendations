#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
api_pid=""
web_pid=""

cleanup() {
  if [[ -n "${api_pid}" ]]; then
    kill "${api_pid}" 2>/dev/null || true
  fi
  if [[ -n "${web_pid}" ]]; then
    kill "${web_pid}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

cd "${project_root}/services/core"
uv run uvicorn medical_one_person.main:app --host 127.0.0.1 --port 8000 &
api_pid=$!

cd "${project_root}"
pnpm --dir apps/web dev &
web_pid=$!

printf 'mock development chain: web=http://127.0.0.1:3000 api=http://127.0.0.1:8000\n'
wait "${api_pid}" "${web_pid}"
