from __future__ import annotations

from datetime import UTC, datetime, timedelta

from medical_one_person.config import Settings
from medical_one_person.infrastructure.runtime_health import (
    remove_worker_heartbeat,
    storage_status,
    worker_status,
    write_worker_heartbeat,
)


def test_storage_status_proves_all_runtime_roots_are_writable(tmp_path) -> None:
    settings = Settings(
        artifact_root=tmp_path / "artifacts",
        knowledge_staging_root=tmp_path / "knowledge",
        run_root=tmp_path / "runs",
        backup_root=tmp_path / "backups",
        restore_root=tmp_path / "restore",
    )

    status = storage_status(settings)

    assert status.status == "ready"
    for name in ("artifacts", "knowledge", "runs", "backups", "restore"):
        assert (tmp_path / name).is_dir()


def test_worker_heartbeat_is_fresh_then_expires_and_can_be_removed(tmp_path) -> None:
    now = datetime(2026, 11, 1, 0, 0, tzinfo=UTC)
    write_worker_heartbeat(
        tmp_path,
        worker_id="test-host:123",
        now=now,
    )

    assert worker_status(tmp_path, now=now + timedelta(seconds=5)).status == "ready"
    assert (
        worker_status(tmp_path, now=now + timedelta(seconds=16)).status
        == "unavailable"
    )

    remove_worker_heartbeat(tmp_path, worker_id="test-host:123")
    assert worker_status(tmp_path, now=now).status == "unavailable"
