"""Synthetic PostgreSQL/API diagnostics for laboratory job idempotence and recovery."""
from __future__ import annotations
import importlib.util
import json
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "cra_recheck_existing_laboratory", ROOT / "tests/integration/test_laboratory.py"
)
_existing = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _existing
_spec.loader.exec_module(_existing)
engine = _existing.engine
queue = _existing.queue
session_factory = _existing.session_factory
settings = _existing.settings
services = _existing.services
application = _existing.application
api = _existing.api

from cra_app.governance.service import ScopeContext
from cra_app.laboratory.models import LabRecognitionJob

def emit(case, expected, observed, reproduced):
    print("CRA_RECHECK_RESULT=" + json.dumps({
        "case": case, "original_finding": "CRA-REV-20261101-08",
        "expected_correct_behavior": expected, "observed": observed,
        "finding_reproduced": bool(reproduced), "acceptance_passed": False,
        "evidence_kind": "actual_laboratory_service_or_public_API_with_PostgreSQL",
        "reviewed_source_commit": "5148684064a57e50077dd32d02e76b57b2221fc4",
    }, ensure_ascii=False, default=str))

def test_completed_recognition_reexecution_is_not_a_noop(api, services):
    report = _existing._upload_lab(api, services, key="recheck-completed-job")
    service = api.app.state.laboratory_service
    real_provider = service.provider
    calls = []
    class CountingProvider:
        enabled = True
        name = "review-counter"
        version = "1"
        def recognize(self, *args, **kwargs):
            calls.append(1)
            return real_provider.recognize(*args, **kwargs)
    service.provider = CountingProvider()
    scope = ScopeContext(actor_id="synthetic-cra-a", tenant_id="synthetic-tenant",
                         authentication_source="trusted-test")
    caught = None
    try:
        service.process_recognition_job(
            scope, uuid.UUID(report["recognition_job_id"]),
            worker_id="synthetic-redelivery",
        )
    except Exception as exc:
        caught = type(exc).__name__
    finally:
        service.provider = real_provider
    current = service.report_detail(scope, uuid.UUID(report["id"]))
    reproduced = bool(calls) and (
        caught is not None or current.report.revision != report["revision"]
        or len(current.observations) != report["observations_count"]
    )
    emit("completed_job_reexecuted",
         "A repeated delivery of a succeeded job returns the existing result without inference, duplicate rows, or another completion audit.",
         {"provider_calls_on_redelivery": len(calls), "exception_type": caught,
          "revision_before": report["revision"], "revision_after": current.report.revision,
          "observation_count_after": len(current.observations)}, reproduced)
    assert reproduced, "Diagnostic assumption changed; reassess rather than declaring this finding reproduced."

def test_expired_running_recognition_cannot_be_retried_through_api(api, services, session_factory):
    artifact = _existing.LAB_PDF
    uploaded = api.post(
        f"/api/v1/studies/{services['study']}/lab-reports",
        files={"file": (artifact.name, artifact.read_bytes(), "application/pdf")},
        data={"site_id": str(services["sites"]["site_a"]),
              "title": "Synthetic expired recognition lease", "version_label": "v1"},
        headers={**_existing._csrf(api), "Idempotency-Key": "recheck-expired-lease"},
    )
    assert uploaded.status_code == 202
    report = uploaded.json()
    with session_factory() as session:
        job = session.get(LabRecognitionJob, uuid.UUID(report["recognition_job_id"]))
        assert job is not None
        job.status = "running"
        job.attempts = 1
        job.lease_owner = "synthetic-dead-worker"
        job.lease_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        session.commit()
    retried = api.post(
        f"/api/v1/lab-reports/{report['id']}/retry-recognition",
        headers=_existing._csrf(api),
    )
    reproduced = retried.status_code == 409
    emit("expired_running_job_retry_denied",
         "An explicitly retried job whose lease expired can be safely requeued after fencing the old attempt; an unexpired active lease stays protected.",
         {"retry_status": retried.status_code, "retry_body": retried.json(),
          "lease_was_expired": True}, reproduced)
    assert reproduced, "Diagnostic assumption changed; reassess rather than declaring this finding reproduced."
