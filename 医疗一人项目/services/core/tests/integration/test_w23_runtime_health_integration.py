from __future__ import annotations

from sqlalchemy import Engine

from medical_one_person.infrastructure.runtime_health import queue_schema_status


def test_queue_schema_status_uses_the_live_outbox_and_jobs_tables(
    app_database: Engine,
) -> None:
    status = queue_schema_status(app_database)

    assert status.status == "ready"
    assert "Outbox and leased-job tables" in status.detail
