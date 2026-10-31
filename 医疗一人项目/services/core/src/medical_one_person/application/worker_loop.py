from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import AgentRoleConfig
from medical_one_person.agents.runner import AgentRunner
from medical_one_person.application.scheduling import JobQueue, OutboxDispatcher
from medical_one_person.providers.base import ModelProvider


@dataclass(frozen=True)
class WorkerIteration:
    dispatched_jobs: int
    claimed_job_id: UUID | None
    task_id: UUID | None
    recovered_jobs: int


class WorkerLoop:
    """One deterministic mock worker iteration over durable queue state."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        provider: ModelProvider,
        roles: dict[str, AgentRoleConfig],
        *,
        theory_hash: str,
        worker_id: str,
    ) -> None:
        self._session_factory = session_factory
        self._worker_id = worker_id
        self._outbox = OutboxDispatcher(session_factory)
        self._queue = JobQueue(session_factory)
        self._runner = AgentRunner(
            session_factory,
            provider,
            roles,
            theory_hash=theory_hash,
            job_queue=self._queue,
        )

    def run_once(self, *, workspace_id: UUID) -> WorkerIteration:
        recovered = self._queue.recover_expired(workspace_id=workspace_id)
        dispatched = self._outbox.dispatch_once(workspace_id=workspace_id, limit=10)
        claim = self._queue.claim(
            workspace_id=workspace_id,
            worker_id=self._worker_id,
            lease_seconds=60,
        )
        if claim is None:
            return WorkerIteration(
                dispatched_jobs=len(dispatched),
                claimed_job_id=None,
                task_id=None,
                recovered_jobs=recovered,
            )
        try:
            self._runner.run_claim(claim)
        except Exception as exc:
            self._queue.fail(
                workspace_id=workspace_id,
                claim=claim,
                error_code=type(exc).__name__.upper()[:100],
                retryable=False,
            )
            raise
        return WorkerIteration(
            dispatched_jobs=len(dispatched),
            claimed_job_id=claim.job_id,
            task_id=claim.task_id,
            recovered_jobs=recovered,
        )
