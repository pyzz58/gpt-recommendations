"""Procrastinate worker entrypoint for document parsing."""
from __future__ import annotations

import argparse
import uuid

from procrastinate import App, PsycopgConnector

from cra_app.documents.service import DocumentService
from cra_app.documents.storage import build_private_storage
from cra_app.edc_import.service import EDCImportService
from cra_app.governance.service import GovernanceService, ScopeContext
from cra_app.issues.service import IssueService
from cra_app.laboratory.service import LaboratoryService
from cra_app.platform.jobs import ProcrastinateQueue
from cra_app.providers.case_analysis import build_case_analysis_provider
from cra_app.providers.lab_ocr import RoutedLabProvider
from cra_app.rules.common_policy import load_common_policy_set
from cra_app.rules.service import RuleService
from cra_app.safety.service import SafetyService
from cra_app.shared.config import get_settings
from cra_app.shared.db import build_engine, build_session_factory
from cra_app.subjects.service import SubjectService


def build_worker_app(
    service: DocumentService,
    database_url: str,
    laboratory_service: LaboratoryService | None = None,
    safety_service: SafetyService | None = None,
) -> App:
    conninfo = database_url.replace(
        "postgresql+psycopg://", "postgresql://"
    )
    app = App(connector=PsycopgConnector(conninfo=conninfo))

    @app.task(
        name=ProcrastinateQueue.TASK_NAME,
        queue="documents",
        retry=2,
        pass_context=True,
    )
    def parse_document(context, job_id: str) -> None:
        service.process_job(
            uuid.UUID(job_id),
            worker_id=f"procrastinate:{context.job.id}",
        )

    if laboratory_service is not None:

        @app.task(
            name=ProcrastinateQueue.LAB_TASK_NAME,
            queue="laboratory",
            retry=2,
            pass_context=True,
        )
        def recognize_laboratory(context, job_id: str) -> None:
            with laboratory_service.session_factory() as session:
                from cra_app.laboratory.models import LabRecognitionJob

                job = session.get(LabRecognitionJob, uuid.UUID(job_id))
                if job is None:
                    raise ValueError("laboratory recognition job was not found")
                scope = ScopeContext(
                    actor_id=job.actor_id,
                    tenant_id=job.tenant_id,
                    authentication_source=job.authentication_source,
                    platform_roles=frozenset(job.platform_roles),
                )
            laboratory_service.process_recognition_job(
                scope,
                uuid.UUID(job_id),
                worker_id=f"procrastinate:{context.job.id}",
            )

    if safety_service is not None:

        @app.task(
            name=ProcrastinateQueue.SAFETY_TASK_NAME,
            queue="safety",
            retry=2,
            pass_context=True,
        )
        def analyze_safety(context, job_id: str) -> None:
            safety_service.process_provider_job(
                uuid.UUID(job_id),
                worker_id=f"procrastinate:{context.job.id}",
            )

    return app


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once",
        action="store_true",
        help="process currently available jobs then exit",
    )
    args = parser.parse_args()
    settings = get_settings()
    engine = build_engine(settings.sqlalchemy_url())
    try:
        sessions = build_session_factory(engine)
        queue = ProcrastinateQueue(settings.sqlalchemy_url())
        queue.ensure_schema()
        governance = GovernanceService(sessions)
        service = DocumentService(
            sessions,
            storage=build_private_storage(settings),
            queue=queue,
            governance=governance,
            max_upload_bytes=settings.max_upload_bytes,
        )
        issues = IssueService(
            sessions, governance=governance, documents=service
        )
        edc_imports = EDCImportService(
            sessions, documents=service, governance=governance
        )
        laboratory = LaboratoryService(
            sessions,
            documents=service,
            edc_imports=edc_imports,
            issues=issues,
            governance=governance,
            provider=RoutedLabProvider(
                ocr_provider=settings.ocr_provider
            ),
        )
        rules = RuleService(
            sessions,
            governance=governance,
            common_policy_set=load_common_policy_set(
                settings.common_policy_path
            ),
        )
        subjects = SubjectService(
            sessions, governance=governance, rules=rules
        )
        safety = SafetyService(
            sessions,
            governance=governance,
            rules=rules,
            subjects=subjects,
            issues=issues,
            laboratory=laboratory,
            provider=build_case_analysis_provider(
                settings.resolved_analysis_provider()
            ),
            provider_data_classification=(
                settings.resolved_analysis_data_classification()
            ),
            queue=queue,
        )
        worker = build_worker_app(
            service, settings.sqlalchemy_url(), laboratory, safety
        )
        worker.run_worker(
            queues=["documents", "laboratory", "safety"],
            concurrency=1,
            wait=not args.once,
        )
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
