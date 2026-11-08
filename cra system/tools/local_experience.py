"""Run and inspect the loopback-only synthetic CRA experience on macOS."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime" / "local-experience"
POSTGRES_ROOT = ROOT / "runtime" / "local-postgres"
POSTGRES_APP = POSTGRES_ROOT / "Postgres.app"
POSTGRES_DATA = POSTGRES_ROOT / "data"
POSTGRES_VERSION = "18"
POSTGRES_PORT = 55432
API_PORT = 18000
WEB_PORT = 15173
API_URL = f"http://127.0.0.1:{API_PORT}"
WEB_URL = f"http://127.0.0.1:{WEB_PORT}"
POSTGRES_DMG = (
    "https://github.com/PostgresApp/PostgresApp/releases/download/"
    "v2.9.6/Postgres-2.9.6-18.dmg"
)
POSTGRES_DMG_SHA256 = (
    "9fc7d0dc08cf46dfd94bb32cbaaad81b41b37847a42d6dcb2f9fbd292813defb"
)
NODE_VERSION = "24.22.2"
PID_FILES = {
    "api": RUNTIME / "api.pid",
    "worker": RUNTIME / "worker.pid",
    "web": RUNTIME / "web.pid",
}
LOGS = {
    name: RUNTIME / f"{name}.log"
    for name in ("api", "worker", "web", "postgres")
}


def _run(
    command: list[str],
    *,
    env: dict[str, str] | None = None,
    timeout: int = 120,
    check: bool = True,
) -> subprocess.CompletedProcess:
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if check and result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stderr[-2000:]}"
        )
    return result


def _download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as source:
        with destination.open("wb") as target:
            shutil.copyfileobj(source, target)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _postgres_bin() -> Path:
    return POSTGRES_APP / "Contents" / "Versions" / POSTGRES_VERSION / "bin"


def ensure_postgres() -> Path:
    if (_postgres_bin() / "postgres").is_file():
        return _postgres_bin()
    if sys.platform != "darwin":
        raise RuntimeError("the embedded local experience currently supports macOS")
    dmg = ROOT / "runtime" / "cache" / "Postgres-2.9.6-18.dmg"
    if not dmg.is_file() or _sha256(dmg) != POSTGRES_DMG_SHA256:
        _download(POSTGRES_DMG, dmg)
    if _sha256(dmg) != POSTGRES_DMG_SHA256:
        dmg.unlink(missing_ok=True)
        raise RuntimeError("Postgres.app download hash did not match the pinned SHA-256")
    mount_point = Path(tempfile.mkdtemp(prefix="cra-postgres-mount-"))
    try:
        _run(
            [
                "hdiutil",
                "attach",
                "-nobrowse",
                "-readonly",
                "-mountpoint",
                str(mount_point),
                str(dmg),
            ]
        )
        source = mount_point / "Postgres.app"
        if not source.is_dir():
            raise RuntimeError("Postgres.app was not found in the mounted image")
        if POSTGRES_APP.exists():
            shutil.rmtree(POSTGRES_APP)
        POSTGRES_APP.parent.mkdir(parents=True, exist_ok=True)
        _run(["ditto", str(source), str(POSTGRES_APP)])
    finally:
        _run(
            ["hdiutil", "detach", str(mount_point)],
            check=False,
            timeout=30,
        )
        mount_point.rmdir()
    version = _run([str(_postgres_bin() / "postgres"), "--version"]).stdout
    if "18." not in version:
        raise RuntimeError(f"expected PostgreSQL 18, got: {version.strip()}")
    return _postgres_bin()


def _database_env() -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "CRA_ENV": "synthetic",
            "CRA_DATABASE_URL": (
                "postgresql+psycopg://cra:local-synthetic-only@"
                f"127.0.0.1:{POSTGRES_PORT}/cra_local"
            ),
            "CRA_SESSION_SECRET": "local-synthetic-only-session-secret",
            "CRA_SESSION_COOKIE_SECURE": "false",
            "CRA_SYNTHETIC_ACTOR_ID": "synthetic-cra",
            "CRA_SYNTHETIC_TENANT_ID": "synthetic",
            "CRA_PUBLIC_BASE_URL": WEB_URL,
            "CRA_STORAGE_BACKEND": "local",
            "CRA_PRIVATE_STORAGE_LOCAL_PATH": str(
                ROOT / "runtime" / "local-private"
            ),
            "CRA_COMMON_POLICY_PATH": "tests/fixtures/rules/common_policy.json",
            "CRA_MODEL_PROVIDER": "disabled",
            "CRA_ANALYSIS_PROVIDER": "disabled",
            "CRA_ANALYSIS_DATA_CLASSIFICATION": "pure_synthetic",
            "CRA_OCR_PROVIDER": "docling",
            "CRA_API_PROXY_TARGET": API_URL,
        }
    )
    return environment


def _postgres_status(bin_dir: Path) -> bool:
    if not POSTGRES_DATA.is_dir():
        return False
    result = subprocess.run(
        [
            str(bin_dir / "pg_ctl"),
            "-D",
            str(POSTGRES_DATA),
            "status",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def start_postgres(bin_dir: Path) -> None:
    POSTGRES_ROOT.mkdir(parents=True, exist_ok=True)
    POSTGRES_ROOT.chmod(0o700)
    if not (POSTGRES_DATA / "PG_VERSION").is_file():
        POSTGRES_DATA.mkdir(parents=True, exist_ok=True)
        POSTGRES_DATA.chmod(0o700)
        password_file = POSTGRES_ROOT / "pwfile"
        password_file.write_text("local-synthetic-only\n", encoding="utf-8")
        password_file.chmod(0o600)
        _run(
            [
                str(bin_dir / "initdb"),
                "-D",
                str(POSTGRES_DATA),
                "-U",
                "cra",
                "--auth-local=trust",
                "--auth-host=scram-sha-256",
                f"--pwfile={password_file}",
                "--encoding=UTF8",
                "--locale=C",
            ]
        )
        password_file.unlink()
    if not _postgres_status(bin_dir):
        _run(
            [
                str(bin_dir / "pg_ctl"),
                "-D",
                str(POSTGRES_DATA),
                "-l",
                str(LOGS["postgres"]),
                "-o",
                f"-h 127.0.0.1 -p {POSTGRES_PORT}",
                "-w",
                "start",
            ],
            timeout=60,
        )
    environment = _database_env()
    environment["PGPASSWORD"] = "local-synthetic-only"
    exists = _run(
        [
            str(bin_dir / "psql"),
            "-h",
            "127.0.0.1",
            "-p",
            str(POSTGRES_PORT),
            "-U",
            "cra",
            "-d",
            "postgres",
            "-Atc",
            "SELECT 1 FROM pg_database WHERE datname='cra_local'",
        ],
        env=environment,
    ).stdout.strip()
    if exists != "1":
        _run(
            [
                str(bin_dir / "createdb"),
                "-h",
                "127.0.0.1",
                "-p",
                str(POSTGRES_PORT),
                "-U",
                "cra",
                "cra_local",
            ],
            env=environment,
        )


def find_node() -> Path:
    candidates = [shutil.which("node")]
    candidates.extend(
        str(path)
        for path in sorted(
            (Path.home() / ".cache" / "codex-runtimes").glob(
                "*/dependencies/node/bin/node"
            )
        )
    )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    raise RuntimeError(
        "Node.js was not found. Install Node 24.22.2 or reopen the Codex app."
    )


def ensure_web_dependencies(node: Path) -> Path:
    vite = ROOT / "web" / "node_modules" / "vite" / "bin" / "vite.js"
    if vite.is_file():
        return vite
    npm = node.parent / "npm"
    if not npm.is_file():
        raise RuntimeError(
            "web/node_modules is missing and npm was not found. "
            "Install Node 24.22.2, then run `npm --prefix web ci`."
        )
    _run([str(npm), "--prefix", "web", "ci"], timeout=300)
    if not vite.is_file():
        raise RuntimeError("Vite was not installed")
    return vite


def _read_pid(name: str) -> int | None:
    path = PID_FILES[name]
    try:
        value = int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    try:
        os.kill(value, 0)
    except OSError:
        path.unlink(missing_ok=True)
        return None
    return value


def _start_process(
    name: str,
    command: list[str],
    environment: dict[str, str],
) -> int:
    existing = _read_pid(name)
    if existing:
        return existing
    RUNTIME.mkdir(parents=True, exist_ok=True)
    LOGS[name].parent.mkdir(parents=True, exist_ok=True)
    with LOGS[name].open("ab") as log:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )
    PID_FILES[name].write_text(str(process.pid), encoding="utf-8")
    return process.pid


def _stop_process(name: str) -> None:
    pid = _read_pid(name)
    if pid is None:
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass
    for _ in range(30):
        try:
            os.kill(pid, 0)
        except OSError:
            break
        time.sleep(0.2)
    else:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    PID_FILES[name].unlink(missing_ok=True)


def _url_ready(url: str) -> bool:
    import httpx2

    try:
        response = httpx2.get(url, timeout=2)
        return 200 <= response.status_code < 400
    except Exception:
        return False


def wait_http(url: str, timeout: int = 60) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _url_ready(url):
            return
        time.sleep(0.5)
    raise TimeoutError(f"service did not become ready: {url}")


def start(*, open_browser: bool) -> int:
    postgres_bin = ensure_postgres()
    start_postgres(postgres_bin)
    environment = _database_env()
    _run(
        [str(ROOT / ".venv/bin/alembic"), "upgrade", "head"],
        env=environment,
        timeout=120,
    )
    _run(
        [str(ROOT / ".venv/bin/python"), "tools/seed_synthetic.py"],
        env=environment,
        timeout=60,
    )
    _start_process(
        "api",
        [
            str(ROOT / ".venv/bin/uvicorn"),
            "cra_app.main:app",
            "--app-dir",
            "backend",
            "--host",
            "127.0.0.1",
            "--port",
            str(API_PORT),
        ],
        environment,
    )
    _start_process(
        "worker",
        [
            str(ROOT / ".venv/bin/python"),
            "-m",
            "cra_app.documents.worker",
        ],
        environment,
    )
    wait_http(f"{API_URL}/health/ready")
    _run(
        [
            str(ROOT / ".venv/bin/python"),
            "tools/seed_local_experience.py",
            API_URL,
        ],
        env=environment,
        timeout=180,
    )
    node = find_node()
    vite = ensure_web_dependencies(node)
    _start_process(
        "web",
        [
            str(node),
            str(vite),
            "web",
            "--config",
            "web/vite.config.ts",
            "--host",
            "127.0.0.1",
            "--port",
            str(WEB_PORT),
            "--strictPort",
        ],
        environment,
    )
    wait_http(WEB_URL)
    print(
        json.dumps(
            {
                "status": "local synthetic experience ready",
                "url": WEB_URL,
                "identity_entry": "点击“进入合成工作台”",
                "study_selector": "合成监查演示项目 / S01",
                "api": f"{API_URL}/health/ready",
                "data_boundary": "synthetic only; loopback only",
                "capabilities": f"{API_URL}/capabilities",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if open_browser:
        webbrowser.open(WEB_URL)
    return 0


def status() -> int:
    postgres_bin = _postgres_bin()
    api_pid = _read_pid("api")
    worker_pid = _read_pid("worker")
    web_pid = _read_pid("web")
    capabilities = None
    if _url_ready(f"{API_URL}/health/ready"):
        try:
            import httpx2

            capabilities = httpx2.get(
                f"{API_URL}/capabilities", timeout=5
            ).json()
        except Exception:
            capabilities = None
    payload = {
        "url": WEB_URL,
        "postgres": _postgres_status(postgres_bin) if postgres_bin.is_dir() else False,
        "api": {"pid": api_pid, "ready": _url_ready(f"{API_URL}/health/ready")},
        "worker": {"pid": worker_pid},
        "web": {"pid": web_pid, "ready": _url_ready(WEB_URL)},
        "capabilities": capabilities,
        "data_boundary": "synthetic only; loopback only",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    ready = all(
        (
            payload["postgres"],
            payload["api"]["ready"],
            worker_pid is not None,
            payload["web"]["ready"],
        )
    )
    return 0 if ready else 1


def stop() -> int:
    _stop_process("web")
    _stop_process("worker")
    _stop_process("api")
    bin_dir = _postgres_bin()
    if bin_dir.is_dir() and _postgres_status(bin_dir):
        _run(
            [
                str(bin_dir / "pg_ctl"),
                "-D",
                str(POSTGRES_DATA),
                "-m",
                "fast",
                "-w",
                "stop",
            ],
            timeout=60,
        )
    print(json.dumps({"status": "stopped", "data_retained": True}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        nargs="?",
        choices=("start", "stop", "status", "open"),
        default="start",
    )
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    if not (ROOT / ".venv" / "bin" / "python").is_file():
        raise RuntimeError(
            "Python environment is missing. Run `uv sync --frozen --group dev`."
        )
    if args.command == "start":
        return start(open_browser=not args.no_open)
    if args.command == "stop":
        return stop()
    if args.command == "status":
        return status()
    webbrowser.open(WEB_URL)
    print(WEB_URL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
