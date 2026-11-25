from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import logging
import os
import signal
import socket
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import load_role_configs
from medical_one_person.application.policy_bundles import PolicyBundleService
from medical_one_person.application.worker_loop import WorkerLoop
from medical_one_person.config import get_settings
from medical_one_person.infrastructure.db.engine import create_database_engine
from medical_one_person.infrastructure.db.models import Workspace
from medical_one_person.infrastructure.runtime_health import (
    WORKER_HEARTBEAT_SECONDS,
    remove_worker_heartbeat,
    write_worker_heartbeat,
)
from medical_one_person.providers import build_model_provider

logger = logging.getLogger(__name__)


def parse_workspace_id(value: str | None) -> UUID | None:
    return UUID(value) if value else None


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
    PolicyBundleService(
        session_factory,
        settings=settings,
    ).require_runtime_ready(workspace_id=workspace_id)
    theory_hash = hashlib.sha256(settings.theory_path.read_bytes()).hexdigest()
    worker_id = f"{socket.gethostname()}:{os.getpid()}"
    provider = build_model_provider(settings)
    if not provider.capabilities().structured_output:
        raise RuntimeError(
            f"Model provider {provider.provider_id} is not configured for structured output"
        )
    write_worker_heartbeat(settings.run_root, worker_id=worker_id)
    loop_runner = WorkerLoop(
        session_factory,
        provider,
        roles,
        theory_hash=theory_hash,
        worker_id=worker_id,
    )
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for name in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(name, stop.set)

    async def heartbeat() -> None:
        while not stop.is_set():
            try:
                write_worker_heartbeat(settings.run_root, worker_id=worker_id)
            except OSError:
                logger.exception(
                    "Worker heartbeat could not be persisted; stopping the worker"
                )
                stop.set()
                return
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(
                    stop.wait(),
                    timeout=WORKER_HEARTBEAT_SECONDS,
                )

    heartbeat_task = asyncio.create_task(heartbeat())
    print(f"medical-one-person mock worker started: {worker_id}", flush=True)
    consecutive_errors = 0
    try:
        while not stop.is_set():
            try:
                result = await asyncio.to_thread(
                    loop_runner.run_once,
                    workspace_id=workspace_id,
                )
            except Exception:
                consecutive_errors += 1
                delay = min(
                    max(poll_seconds, 0.1) * (2 ** min(consecutive_errors - 1, 5)),
                    30.0,
                )
                logger.exception(
                    "Worker iteration failed; retrying in %.1f seconds",
                    delay,
                )
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), timeout=delay)
                continue
            consecutive_errors = 0
            if result.failure_code:
                logger.error(
                    "Task job %s failed with %s; continuing",
                    result.failed_job_id,
                    result.failure_code,
                )
            if result.claimed_job_id is None:
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), timeout=poll_seconds)
    finally:
        stop.set()
        heartbeat_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat_task
        remove_worker_heartbeat(settings.run_root, worker_id=worker_id)
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
            workspace_id=parse_workspace_id(args.workspace_id),
            poll_seconds=max(args.poll_seconds, 0.1),
        )
    )
