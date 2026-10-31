from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import os
import signal
import socket
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import load_role_configs
from medical_one_person.application.worker_loop import WorkerLoop
from medical_one_person.config import get_settings
from medical_one_person.infrastructure.db.engine import create_database_engine
from medical_one_person.infrastructure.db.models import Workspace
from medical_one_person.providers import FakeModelProvider


async def run(*, workspace_id: UUID | None, poll_seconds: float) -> None:
    settings = get_settings()
    roles = load_role_configs(settings.agent_config_path)
    engine = create_database_engine(settings.database_url)
    session_factory: sessionmaker[Session] = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )
    if workspace_id is None:
        with session_factory.begin() as session:
            workspace_ids = list(session.scalars(select(Workspace.id)))
        if len(workspace_ids) != 1:
            raise RuntimeError(
                "Set --workspace-id when the database does not contain exactly one workspace"
            )
        workspace_id = workspace_ids[0]
    theory_hash = hashlib.sha256(settings.theory_path.read_bytes()).hexdigest()
    worker_id = f"{socket.gethostname()}:{os.getpid()}"
    loop_runner = WorkerLoop(
        session_factory,
        FakeModelProvider(),
        roles,
        theory_hash=theory_hash,
        worker_id=worker_id,
    )
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for name in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(name, stop.set)

    print(f"medical-one-person mock worker started: {worker_id}")
    try:
        while not stop.is_set():
            result = await asyncio.to_thread(
                loop_runner.run_once,
                workspace_id=workspace_id,
            )
            if result.claimed_job_id is None:
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), timeout=poll_seconds)
    finally:
        engine.dispose()
        print(f"medical-one-person mock worker stopped: {worker_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workspace-id",
        default=os.getenv("MEDICAL_ONE_WORKSPACE_ID") or None,
    )
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    args = parser.parse_args()
    asyncio.run(
        run(
            workspace_id=UUID(args.workspace_id),
            poll_seconds=max(args.poll_seconds, 0.1),
        )
    )
