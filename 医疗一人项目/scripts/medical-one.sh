#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
started_here=0

ensure_node_path() {
  if command -v node >/dev/null 2>&1; then
    return 0
  fi
  local pnpm_path
  local runtime_root
  pnpm_path="$(command -v pnpm 2>/dev/null || true)"
  [[ -n "${pnpm_path}" ]] || return 0
  runtime_root="$(cd "$(dirname "${pnpm_path}")/../.." 2>/dev/null && pwd)" || return 0
  if [[ -x "${runtime_root}/node/bin/node" ]]; then
    export PATH="${runtime_root}/node/bin:${PATH}"
  fi
}

load_unified_config() {
  config_path="${MEDICAL_ONE_CONFIG_FILE:-${project_root}/.env}"
  if [[ "${config_path}" != /* ]]; then
    config_path="${project_root}/${config_path}"
  fi
  export MEDICAL_ONE_CONFIG_FILE="${config_path}"
  if [[ ! -f "${config_path}" ]]; then
    return 0
  fi
  if ! command -v uv >/dev/null 2>&1; then
    return 0
  fi
  local exported_file
  exported_file="$(mktemp "${TMPDIR:-/tmp}/medical-one-config.XXXXXX")"
  if ! (
    cd "${project_root}" &&
      uv run --quiet --project services/core --frozen python \
        -m medical_one_person.config_file shell-export --path "${config_path}" \
        > "${exported_file}"
  ); then
    rm -f "${exported_file}"
    printf 'Could not parse configuration file: %s\n' "${config_path}" >&2
    return 1
  fi
  local assignment
  while IFS= read -r -d '' assignment; do
    export "${assignment}"
  done < "${exported_file}"
  rm -f "${exported_file}"
}

usage() {
  cat <<'EOF'
Usage: scripts/medical-one.sh <command>

Commands:
  doctor [--structural-only]  Check runtime files, configuration and dependencies
  bootstrap                   Apply migrations and create the local owner if absent
  start [--skip-bootstrap]    Start API, worker and web in the background
  status                      Query live/ready/capabilities and show managed PIDs
  smoke                       Start, verify and stop the complete local mock chain
  config                      Show the resolved non-secret runtime configuration
  stop                        Stop only processes recorded in the W23 PID files
  logs [api|worker|web]       Follow one process log

Runtime state, logs and PID files default to
$XDG_STATE_HOME/medical-one-person (or ~/.local/state/medical-one-person).
Set MEDICAL_ONE_CONFIG_FILE to use one repository-external dotenv file for
Shell, Python and Next.js. Override ports with MEDICAL_ONE_API_PORT and
MEDICAL_ONE_WEB_PORT in that file or the parent process environment.
EOF
}

ok() {
  printf 'PASS: %s\n' "$*"
}

warn() {
  printf 'WARN: %s\n' "$*"
}

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  doctor_failed=1
}

ensure_runtime_dir() {
  mkdir -p "${runtime_dir}/logs"
  chmod 700 "${runtime_dir}" "${runtime_dir}/logs"
}

pid_file() {
  printf '%s/%s.pid' "${runtime_dir}" "$1"
}

log_file() {
  printf '%s/logs/%s.log' "${runtime_dir}" "$1"
}

process_pattern() {
  case "$1" in
    api) printf '%s' 'uvicorn medical_one_person.main:app' ;;
    worker) printf '%s' 'medical_one_person.worker' ;;
    web) printf '%s' 'next dev' ;;
    *) return 1 ;;
  esac
}

pid_is_managed() {
  local name="$1"
  local pid="$2"
  local pattern
  pattern="$(process_pattern "${name}")"
  if [[ -z "${pid}" ]] || ! kill -0 "${pid}" 2>/dev/null; then
    return 1
  fi
  local command_line
  command_line="$(ps -p "${pid}" -o command= 2>/dev/null)" || return 1
  [[ "${command_line}" == *"${pattern}"* ]]
}

read_managed_pid() {
  local name="$1"
  local file
  file="$(pid_file "${name}")"
  [[ -f "${file}" ]] || return 1
  local pid
  pid="$(tr -dc '0-9' < "${file}")"
  if pid_is_managed "${name}" "${pid}"; then
    printf '%s' "${pid}"
    return 0
  fi
  rm -f "${file}"
  return 1
}

descendant_pids() {
  local root="$1"
  local child
  for child in $(pgrep -P "${root}" 2>/dev/null || true); do
    printf '%s\n' "${child}"
    descendant_pids "${child}"
  done
}

stop_service() {
  local name="$1"
  local file
  local pid
  file="$(pid_file "${name}")"
  if ! pid="$(read_managed_pid "${name}")"; then
    printf '%s is not running under this runtime directory\n' "${name}"
    rm -f "${file}"
    return 0
  fi
  local tree
  tree="$(descendant_pids "${pid}")"
  if [[ -n "${tree}" ]]; then
    while IFS= read -r child; do
      kill -TERM "${child}" 2>/dev/null || true
    done <<< "${tree}"
  fi
  kill -TERM "${pid}" 2>/dev/null || true
  local attempt
  for attempt in $(seq 1 50); do
    if ! kill -0 "${pid}" 2>/dev/null; then
      rm -f "${file}"
      ok "${name} stopped"
      return 0
    fi
    sleep 0.1
  done
  if pid_is_managed "${name}" "${pid}"; then
    if [[ -n "${tree}" ]]; then
      while IFS= read -r child; do
        kill -KILL "${child}" 2>/dev/null || true
      done <<< "${tree}"
    fi
    kill -KILL "${pid}" 2>/dev/null || true
  fi
  rm -f "${file}"
  ok "${name} force-stopped after timeout"
}

start_service() {
  local name="$1"
  local directory="$2"
  shift 2
  if read_managed_pid "${name}" >/dev/null; then
    fail "${name} is already running"
    return 1
  fi
  local pid
  pid="$(
    python3 - "${directory}" "$(log_file "${name}")" "$@" <<'PY'
import subprocess
import sys

directory, log_path, *command = sys.argv[1:]
with open(log_path, "ab", buffering=0) as log:
    process = subprocess.Popen(
        command,
        cwd=directory,
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        close_fds=True,
        start_new_session=True,
    )
print(process.pid)
PY
  )"
  printf '%s\n' "${pid}" > "$(pid_file "${name}")"
  sleep 0.2
  if ! pid="$(read_managed_pid "${name}")"; then
    fail "${name} exited during startup; inspect $(log_file "${name}")"
    return 1
  fi
  ok "${name} started with PID ${pid}"
}

wait_for_url() {
  local label="$1"
  local url="$2"
  local attempts="${3:-60}"
  local expected_status="${4:-200}"
  local attempt
  local status_code
  for attempt in $(seq 1 "${attempts}"); do
    status_code="$(
      curl -sS -o /dev/null -w '%{http_code}' --max-time 2 "${url}" 2>/dev/null || true
    )"
    if [[ "${expected_status}" == "web" ]]; then
      if [[ "${status_code}" =~ ^[23][0-9][0-9]$ ]]; then
        ok "${label} responded with HTTP ${status_code}"
        return 0
      fi
    elif [[ "${status_code}" == "${expected_status}" ]]; then
      ok "${label} responded with HTTP ${status_code}"
      return 0
    fi
    sleep 0.5
  done
  return 1
}

rollback_started_services() {
  if [[ "${started_here}" -eq 1 ]]; then
    warn "startup failed; stopping processes started by this command"
    stop_service web
    stop_service worker
    stop_service api
  fi
}

doctor() {
  local structural_only=0
  if [[ "${1:-}" == "--structural-only" ]]; then
    structural_only=1
  elif [[ -n "${1:-}" ]]; then
    fail "unknown doctor argument: $1"
    return 1
  fi
  doctor_failed=0
  if [[ -f "${config_path}" ]]; then
    ok "configuration source ${config_path}"
  elif [[ "${structural_only}" -eq 0 ]]; then
    fail "configuration file does not exist: ${config_path}"
  else
    warn "configuration file does not exist: ${config_path}"
  fi
  local required_files=(
    "最高思想.md"
    "技术路线与实施路径.md"
    "traceability/manifest.json"
    "config/agents/roles.yaml"
    "config/skills/catalog.yaml"
    "config/source_policies/catalog.yaml"
    "config/workflows/catalog.yaml"
    "config/templates/catalog.yaml"
    "fixtures/w17-audit-cases.json"
    "schemas/openapi.v1.json"
    "services/core/requirements.lock"
    "services/core/Dockerfile"
    "apps/web/Dockerfile"
    "deploy/compose.yaml"
    ".env.example"
  )
  local relative
  for relative in "${required_files[@]}"; do
    if [[ -f "${project_root}/${relative}" ]]; then
      ok "runtime file ${relative}"
    else
      fail "required file is missing: ${relative}"
    fi
  done

  if command -v uv >/dev/null 2>&1; then
    local python_version
    python_version="$(
      cd "${project_root}" &&
        uv run --project services/core --frozen python --version 2>/dev/null
    )" || python_version=""
    if [[ "${python_version}" == "Python 3.12."* ]]; then
      ok "uv Python ${python_version#Python }"
    else
      fail "uv did not provide the pinned Python 3.12 runtime"
    fi
  else
    fail "uv is not installed"
  fi

  if command -v pnpm >/dev/null 2>&1; then
    local pnpm_version
    pnpm_version="$(pnpm --version 2>/dev/null)" || pnpm_version=""
    if [[ "${pnpm_version}" == "11.25.0" ]]; then
      ok "pnpm ${pnpm_version}"
    else
      fail "pnpm 11.25.0 is required; found ${pnpm_version:-unknown}"
    fi
    if command -v node >/dev/null 2>&1; then
      local node_version
      node_version="$(node --version 2>/dev/null)" || node_version=""
      if [[ "${node_version}" == "v22.23.4" ]]; then
        ok "Node.js ${node_version}"
      else
        warn "package.json requires Node.js v22.23.4; found ${node_version:-unknown}"
      fi
    else
      warn "node is not on PATH; pnpm's bundled runtime will be used and may not match package.json"
    fi
  else
    fail "pnpm is not installed"
  fi

  if git -C "${project_root}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    local tracked_secret_pattern
    tracked_secret_pattern='-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}'
    if git -C "${project_root}" grep -n -I -E -e "${tracked_secret_pattern}" -- . ':!.env.example' >/dev/null 2>&1; then
      fail "tracked files contain a secret-like credential pattern"
    else
      local grep_status=$?
      if [[ "${grep_status}" -eq 1 ]]; then
        ok "no high-confidence credential patterns in tracked files"
      else
        fail "could not complete tracked-file credential scan"
      fi
    fi
    if git -C "${project_root}" ls-files | grep -Ev '(^|/)\.env\.example$' |
      grep -Eq '(^|/)\.env($|\.)|\.(sqlite|sqlite3|db|dump|bak|pem|key)$'; then
      fail "tracked files include an environment file or runtime/secret data"
    else
      ok "no tracked environment, database, backup or key files"
    fi
  else
    fail "deployment directory is not inside a Git worktree"
  fi

  local deployment_output
  if deployment_output="$(
    cd "${project_root}" &&
      uv run --project services/core --frozen python tools/check_deployment.py
  )"; then
    ok "${deployment_output#PASS: }"
  else
    fail "static Compose/Docker packaging check failed"
    printf '%s\n' "${deployment_output}" >&2
  fi

  if command -v docker >/dev/null 2>&1; then
    if docker compose -f "${project_root}/deploy/compose.yaml" config --quiet; then
      ok "docker compose configuration parses"
    else
      fail "docker compose configuration does not parse"
    fi
  else
    warn "Docker is not installed; Compose/container execution remains unverified"
  fi

  if [[ "${structural_only}" -eq 0 ]]; then
    if [[ ! -f "${config_path}" ]]; then
      fail "configuration file is required for database-backed doctor checks"
    else
      local database_probe
      if database_probe="$(
        cd "${project_root}/services/core" &&
          uv run --frozen python -c '
from medical_one_person.config import get_settings
from medical_one_person.infrastructure.db.engine import create_database_engine, database_status
from medical_one_person.infrastructure.runtime_health import storage_status, worker_status
from pathlib import Path
from shutil import which

settings = get_settings()
engine = create_database_engine(settings.database_url)
try:
    print("database=" + database_status(engine).status)
finally:
    engine.dispose()
print("storage=" + storage_status(settings).status)
print("worker=" + worker_status(settings.run_root).status)
print("soffice=" + ("ready" if (settings.office_soffice_path and Path(settings.office_soffice_path).is_file()) or which("soffice") else "unavailable"))
print("pdftoppm=" + ("ready" if (settings.office_pdftoppm_path and Path(settings.office_pdftoppm_path).is_file()) or which("pdftoppm") else "unavailable"))
'
      )"; then
        printf '%s\n' "${database_probe}" | sed 's/^/INFO: /'
        if printf '%s\n' "${database_probe}" | grep -q '^database=ready$'; then
          ok "PostgreSQL connectivity and migration head"
        else
          fail "PostgreSQL is unavailable or not at the expected migration head"
        fi
        if printf '%s\n' "${database_probe}" | grep -q '^storage=ready$'; then
          ok "runtime storage roots are writable"
        else
          fail "one or more runtime storage roots are unavailable"
        fi
        if printf '%s\n' "${database_probe}" | grep -q '^worker=ready$'; then
          ok "mock worker heartbeat is current"
        else
          warn "mock worker is not currently running"
        fi
        if printf '%s\n' "${database_probe}" | grep -q '^soffice=ready$'; then
          ok "LibreOffice executable is available"
        else
          warn "LibreOffice is unavailable; real Office export checks will skip"
        fi
        if printf '%s\n' "${database_probe}" | grep -q '^pdftoppm=ready$'; then
          ok "Poppler pdftoppm is available"
        else
          warn "Poppler is unavailable; PDF page preview checks will skip"
        fi
      else
        fail "database/runtime probe failed"
      fi
    fi
  else
    warn "database, storage, worker, Office and Poppler checks skipped in structural-only mode"
  fi

  if [[ "${doctor_failed}" -ne 0 ]]; then
    return 1
  fi
  printf 'Doctor result: READY for the checks performed; Docker execution is not implied.\n'
}

bootstrap() {
  if [[ ! -f "${config_path}" ]]; then
    printf 'Create the configured dotenv file before bootstrap: %s\n' "${config_path}" >&2
    return 1
  fi
  (
    cd "${project_root}/services/core"
    uv run --frozen alembic upgrade head
    uv run --frozen python -m medical_one_person.bootstrap
  )
}

start() {
  local skip_bootstrap=0
  if [[ "${1:-}" == "--skip-bootstrap" ]]; then
    skip_bootstrap=1
  elif [[ -n "${1:-}" ]]; then
    printf 'Unknown start argument: %s\n' "$1" >&2
    return 1
  fi
  ensure_runtime_dir
  local name
  for name in api worker web; do
    if read_managed_pid "${name}" >/dev/null; then
      printf '%s is already running with PID %s\n' "${name}" "$(read_managed_pid "${name}")" >&2
      return 1
    fi
  done
  started_here=1
  trap rollback_started_services EXIT INT TERM
  if [[ "${skip_bootstrap}" -eq 0 ]]; then
    bootstrap
  fi
  doctor >/dev/null
  start_service api "${project_root}/services/core" \
    uv run --frozen uvicorn medical_one_person.main:app \
    --host 127.0.0.1 --port "${api_port}"
  if ! wait_for_url "API live endpoint" "${api_url}/health/live" 40; then
    fail "API did not become live"
    return 1
  fi
  start_service worker "${project_root}/services/core" \
    uv run --frozen python -m medical_one_person.worker --poll-seconds 1
  start_service web "${project_root}/apps/web" \
    node node_modules/next/dist/bin/next dev \
    --hostname 127.0.0.1 --port "${web_port}"
  if ! wait_for_url "API ready endpoint" "${api_url}/health/ready" 60 200; then
    fail "API did not become ready; inspect doctor/status and process logs"
    return 1
  fi
  if ! wait_for_url "Web page" "${web_url}" 120 web; then
    fail "web did not become reachable"
    return 1
  fi
  started_here=0
  trap - EXIT INT TERM
  printf 'Started: web=%s api=%s runtime=%s\n' "${web_url}" "${api_url}" "${runtime_dir}"
}

status() {
  ensure_runtime_dir
  local name
  local pid
  for name in api worker web; do
    if pid="$(read_managed_pid "${name}")"; then
      printf 'process %-6s running pid=%s log=%s\n' "${name}" "${pid}" "$(log_file "${name}")"
    else
      printf 'process %-6s stopped\n' "${name}"
    fi
  done
  curl -fsS --max-time 3 "${api_url}/health/live" |
    python3 -m json.tool
  local ready_json
  local ready_status
  if ! ready_json="$(
    curl -sS --max-time 3 "${api_url}/health/ready"
  )"; then
    printf 'API ready endpoint is unreachable at %s\n' "${api_url}" >&2
    return 1
  fi
  ready_status="$(
    curl -sS -o /dev/null -w '%{http_code}' --max-time 3 "${api_url}/health/ready"
  )"
  printf '%s\n' "${ready_json}" | python3 -m json.tool
  curl -fsS --max-time 3 "${api_url}/api/v1/system/capabilities" |
    python3 -c '
import json
import sys

body = json.load(sys.stdin)
print("capabilities mode=" + body["mode"])
for name, item in sorted(body["dependencies"].items()):
    print("  %s: %s - %s" % (name, item["status"], item["detail"]))
'
  if ! curl -fsS --max-time 3 "${web_url}" >/dev/null; then
    printf 'Web is unreachable at %s\n' "${web_url}" >&2
    return 1
  fi
  if [[ "${ready_status}" != "200" ]]; then
    printf 'Readiness FAILED with HTTP %s\n' "${ready_status}" >&2
    return 1
  fi
  printf '%s\n' "${ready_json}" |
    python3 -c 'import json,sys; raise SystemExit(0 if json.load(sys.stdin)["status"] == "ok" else 1)'
}

config() {
  (
    cd "${project_root}"
    uv run --quiet --project services/core --frozen python \
      -m medical_one_person.config_file --path "${config_path}" summary
  )
  printf 'api_url=%s\n' "${api_url}"
  printf 'web_url=%s\n' "${web_url}"
  printf 'runtime_dir=%s\n' "${runtime_dir}"
}

smoke() {
  ensure_runtime_dir
  start
  trap '
    stop_service web
    stop_service worker
    stop_service api
  ' EXIT INT TERM
  status
  stop_service web
  stop_service worker
  stop_service api
  trap - EXIT INT TERM
  printf 'W23 smoke passed: local API, worker and web started, became ready and stopped.\n'
}

logs() {
  local name="${1:-api}"
  process_pattern "${name}" >/dev/null
  ensure_runtime_dir
  tail -n 100 -f "$(log_file "${name}")"
}

ensure_node_path
command="${1:-}"
if [[ -z "${command}" ]]; then
  usage
  exit 2
fi
load_unified_config
runtime_dir="${MEDICAL_ONE_RUNTIME_DIR:-${XDG_STATE_HOME:-${HOME}/.local/state}/medical-one-person}"
api_port="${MEDICAL_ONE_API_PORT:-8000}"
web_port="${MEDICAL_ONE_WEB_PORT:-3000}"
api_url="http://127.0.0.1:${api_port}"
web_url="http://127.0.0.1:${web_port}"
shift || true
case "${command}" in
  doctor) doctor "$@" ;;
  bootstrap) bootstrap ;;
  start) start "$@" ;;
  status) status ;;
  config) config ;;
  smoke) smoke ;;
  stop)
    ensure_runtime_dir
    stop_service web
    stop_service worker
    stop_service api
    ;;
  logs) logs "$@" ;;
  help|-h|--help) usage ;;
  *)
    printf 'Unknown command: %s\n' "${command}" >&2
    usage >&2
    exit 2
    ;;
esac
