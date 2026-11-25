from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from medical_one_person.config import Settings
from medical_one_person.contracts import DependencyStatus

WORKER_HEARTBEAT_SECONDS = 5
WORKER_STALE_SECONDS = 15


def storage_status(settings: Settings) -> DependencyStatus:
    roots = {
        "artifacts": settings.artifact_root,
        "knowledge-staging": settings.knowledge_staging_root,
        "runs": settings.run_root,
        "backups": settings.backup_root,
        "restore-checks": settings.restore_root,
    }
    try:
        for root in roots.values():
            root.mkdir(parents=True, exist_ok=True, mode=0o700)
            with tempfile.NamedTemporaryFile(
                dir=root,
                prefix=".medical-one-health-",
                delete=True,
            ):
                pass
    except OSError:
        return DependencyStatus(
            status="unavailable",
            detail="One or more project storage roots are not writable",
        )
    return DependencyStatus(
        status="ready",
        detail=(
            f"{len(roots)} project storage roots are writable: "
            + ", ".join(sorted(roots))
        ),
    )


def queue_schema_status(engine: Engine) -> DependencyStatus:
    try:
        with engine.connect() as connection:
            tables = connection.execute(
                text(
                    "SELECT to_regclass('public.outbox'), "
                    "to_regclass('public.jobs')"
                )
            ).one()
    except SQLAlchemyError:
        return DependencyStatus(
            status="unavailable",
            detail="PostgreSQL queue schema could not be inspected",
        )
    if any(table is None for table in tables):
        return DependencyStatus(
            status="unavailable",
            detail="PostgreSQL queue schema is incomplete",
        )
    return DependencyStatus(
        status="ready",
        detail="Outbox and leased-job tables are available",
    )


def worker_status(run_root: Path, *, now: datetime | None = None) -> DependencyStatus:
    heartbeat_root = _heartbeat_root(run_root)
    current = now or datetime.now(UTC)
    active: list[datetime] = []
    invalid = 0
    try:
        paths = sorted(heartbeat_root.glob("*.json"))
    except OSError:
        paths = []
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("state") != "running":
                continue
            updated_at = datetime.fromisoformat(str(payload["updated_at"]).replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError, OSError):
            invalid += 1
            continue
        if current - updated_at <= timedelta(seconds=WORKER_STALE_SECONDS):
            active.append(updated_at)
    if active:
        return DependencyStatus(
            status="ready",
            detail=f"{len(active)} mock worker heartbeat(s) are current",
        )
    detail = (
        f"no mock worker heartbeat was written within {WORKER_STALE_SECONDS} seconds; "
        "jobs may remain queued"
    )
    if invalid:
        detail += f"; {invalid} heartbeat file(s) were invalid"
    return DependencyStatus(status="unavailable", detail=detail)


def write_worker_heartbeat(
    run_root: Path,
    *,
    worker_id: str,
    state: str = "running",
    now: datetime | None = None,
) -> Path:
    heartbeat_root = _heartbeat_root(run_root)
    heartbeat_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = heartbeat_root / (_worker_key(worker_id) + ".json")
    payload: dict[str, Any] = {
        "worker_id": worker_id,
        "pid": os.getpid(),
        "state": state,
        "updated_at": (now or datetime.now(UTC)).isoformat(),
    }
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=heartbeat_root,
        prefix=".heartbeat-",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temp_path, 0o600)
    os.replace(temp_path, target)
    return target


def remove_worker_heartbeat(run_root: Path, *, worker_id: str) -> None:
    target = _heartbeat_root(run_root) / (_worker_key(worker_id) + ".json")
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        if payload.get("worker_id") == worker_id:
            target.unlink()
    except FileNotFoundError:
        return
    except (OSError, ValueError, TypeError):
        return


def _heartbeat_root(run_root: Path) -> Path:
    return run_root / "health" / "workers"


def _worker_key(worker_id: str) -> str:
    return hashlib.sha256(worker_id.encode("utf-8")).hexdigest()
