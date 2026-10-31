"""Procrastinate worker entrypoint for document parsing."""
from __future__ import annotations

import argparse
import uuid

from procrastinate import App, PsycopgConnector

from cra_app.documents.service import DocumentService
from cra_app.documents.storage import build_private_storage
from cra_app.platform.jobs import ProcrastinateQueue
from cra_app.shared.config import get_settings
from cra_app.shared.db import build_engine, build_session_factory


def build_worker_app(
    service: DocumentService, database_url: str
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
        service = DocumentService(
            sessions,
            storage=build_private_storage(settings),
            queue=queue,
            max_upload_bytes=settings.max_upload_bytes,
        )
        worker = build_worker_app(service, settings.sqlalchemy_url())
        worker.run_worker(
            queues=["documents"],
            concurrency=1,
            wait=not args.once,
        )
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
