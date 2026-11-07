from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import AgentRoleConfig
from medical_one_person.agents.runner import AgentRunner
from medical_one_person.application.errors import (
    AgentExecutionFailure,
    LeaseConflictError,
)
from medical_one_person.application.scheduling import JobQueue, OutboxDispatcher
from medical_one_person.domain.tasks import JobClaim
from medical_one_person.providers.base import ModelProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkerIteration:
    dispatched_jobs: int
    claimed_job_id: UUID | None
    task_id: UUID | None
    recovered_jobs: int
    failed_job_id: UUID | None = None
    failure_code: str | None = None


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
        job_queue: JobQueue | None = None,
        outbox: OutboxDispatcher | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._worker_id = worker_id
        self._outbox = outbox or OutboxDispatcher(session_factory)
        self._queue = job_queue or JobQueue(session_factory)
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
        except AgentExecutionFailure as exc:
            return self._settle_failure(
                workspace_id=workspace_id,
                claim=claim,
                dispatched_jobs=len(dispatched),
                recovered_jobs=recovered,
                error_code=exc.error_code,
                retryable=exc.retryable,
                cause=exc,
            )
        except Exception as exc:
            return self._settle_failure(
                workspace_id=workspace_id,
                claim=claim,
                dispatched_jobs=len(dispatched),
                recovered_jobs=recovered,
                error_code=("WORKER_" + type(exc).__name__.upper())[:100],
                retryable=False,
                cause=exc,
            )
        return WorkerIteration(
            dispatched_jobs=len(dispatched),
            claimed_job_id=claim.job_id,
            task_id=claim.task_id,
            recovered_jobs=recovered,
        )

    def _settle_failure(
        self,
        *,
        workspace_id: UUID,
        claim: JobClaim,
        dispatched_jobs: int,
        recovered_jobs: int,
        error_code: str,
        retryable: bool,
        cause: Exception,
    ) -> WorkerIteration:
        try:
            self._queue.fail(
                workspace_id=workspace_id,
                claim=claim,
                error_code=error_code,
                retryable=retryable,
            )
        except LeaseConflictError:
            logger.warning(
                "Worker lost settlement ownership for job; preserving original failure %s",
                error_code,
                exc_info=(type(cause), cause, cause.__traceback__),
            )
        except Exception as settlement_error:
            logger.exception(
                "Worker could not settle failed job; preserving original failure %s",
                error_code,
            )
            raise settlement_error from cause
        return WorkerIteration(
            dispatched_jobs=dispatched_jobs,
            claimed_job_id=claim.job_id,
            task_id=claim.task_id,
            recovered_jobs=recovered_jobs,
            failed_job_id=claim.job_id,
            failure_code=error_code,
        )
