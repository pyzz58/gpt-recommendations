from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.errors import LeaseConflictError
from medical_one_person.domain.tasks import (
    AttemptState,
    JobClaim,
    JobState,
    TaskState,
)
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    Job,
    OutboxMessage,
    Plan,
    PlanNode,
    Project,
    ProjectEvent,
    Task,
    TaskAttempt,
    TaskVersion,
)


class OutboxDispatcher:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def dispatch_once(self, *, workspace_id: UUID, limit: int = 10) -> list[UUID]:
        if limit < 1:
            raise ValueError("Dispatch limit must be positive")
        created_job_ids: list[UUID] = []
        with self._session_factory.begin() as session:
            set_rls_context(session, workspace_id=workspace_id, user_id=None)
            now = datetime.now(UTC)
            messages = session.scalars(
                select(OutboxMessage)
                .where(
                    OutboxMessage.workspace_id == workspace_id,
                    OutboxMessage.state == "pending",
                    OutboxMessage.available_at <= now,
                )
                .order_by(OutboxMessage.available_at, OutboxMessage.created_at)
                .with_for_update(skip_locked=True)
                .limit(limit)
            ).all()
            for message in messages:
                job_key = f"job:{message.unique_key}"
                job = session.scalar(
                    select(Job).where(
                        Job.project_id == message.project_id,
                        Job.job_key == job_key,
                    )
                )
                if job is None:
                    task = session.get(Task, message.task_id)
                    job = Job(
                        id=uuid4(),
                        workspace_id=message.workspace_id,
                        project_id=message.project_id,
                        task_id=message.task_id,
                        job_key=job_key,
                        job_type=message.event_type,
                        payload=dict(message.payload),
                        state=JobState.QUEUED.value,
                        priority=100,
                        available_at=now,
                        fence_token=0,
                        attempts=0,
                        max_attempts=task.max_attempts if task is not None else 1,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(job)
                    session.flush()
                    created_job_ids.append(job.id)
                message.state = "dispatched"
                message.attempts += 1
                message.dispatched_at = now
        return created_job_ids


class JobQueue:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def claim(
        self,
        *,
        workspace_id: UUID,
        worker_id: str,
        lease_seconds: int = 30,
        task_ids: set[UUID] | None = None,
    ) -> JobClaim | None:
        if not worker_id.strip():
            raise ValueError("Worker identifier cannot be empty")
        if lease_seconds < 1:
            raise ValueError("Lease duration must be positive")
        if task_ids is not None and not task_ids:
            return None
        self.recover_expired(workspace_id=workspace_id)
        now = datetime.now(UTC)
        with self._session_factory.begin() as session:
            set_rls_context(session, workspace_id=workspace_id, user_id=None)
            query = (
                select(Job)
                .where(
                    Job.workspace_id == workspace_id,
                    Job.state == JobState.QUEUED.value,
                    Job.available_at <= now,
                )
                .order_by(Job.priority, Job.available_at, Job.created_at)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if task_ids is not None:
                query = query.where(Job.task_id.in_(task_ids))
            job = session.scalar(query)
            if job is None:
                return None
            session.scalar(select(Project).where(Project.id == job.project_id).with_for_update())
            task = session.scalar(select(Task).where(Task.id == job.task_id).with_for_update())
            if task is None:
                job.state = JobState.FAILED.value
                job.last_error_code = "TASK_MISSING"
                job.finished_at = now
                return None
            plan_status = session.scalar(
                select(Plan.status)
                .join(PlanNode, PlanNode.plan_id == Plan.id)
                .where(PlanNode.task_id == task.id)
            )
            if plan_status is not None and plan_status != "active":
                job.state = JobState.CANCELLED.value
                job.last_error_code = "PLAN_NOT_ACTIVE"
                job.finished_at = now
                job.updated_at = now
                return None
            if task.state not in {TaskState.QUEUED.value, TaskState.REWORK.value}:
                job.state = JobState.CANCELLED.value
                job.last_error_code = "TASK_NOT_CLAIMABLE"
                job.finished_at = now
                return None

            job.state = JobState.RUNNING.value
            job.lease_owner = worker_id
            job.lease_until = now + timedelta(seconds=lease_seconds)
            job.fence_token += 1
            job.attempts += 1
            job.updated_at = now
            task_revision = _transition_task(
                session,
                task,
                TaskState.RUNNING,
                event_type="task.running",
                now=now,
            )
            session.add(
                TaskAttempt(
                    id=uuid4(),
                    workspace_id=job.workspace_id,
                    project_id=job.project_id,
                    task_id=job.task_id,
                    job_id=job.id,
                    attempt_number=job.attempts,
                    worker_id=worker_id,
                    fence_token=job.fence_token,
                    state=AttemptState.RUNNING.value,
                    started_at=now,
                )
            )
            session.flush()
            return JobClaim(
                job_id=job.id,
                workspace_id=job.workspace_id,
                project_id=job.project_id,
                task_id=job.task_id,
                worker_id=worker_id,
                fence_token=job.fence_token,
                attempt_number=job.attempts,
                task_revision=task_revision,
                payload=dict(job.payload),
            )

    def heartbeat(
        self,
        *,
        workspace_id: UUID,
        claim: JobClaim,
        lease_seconds: int = 30,
    ) -> bool:
        if lease_seconds < 1:
            raise ValueError("Lease duration must be positive")
        now = datetime.now(UTC)
        with self._session_factory.begin() as session:
            set_rls_context(session, workspace_id=workspace_id, user_id=None)
            job = session.scalar(select(Job).where(Job.id == claim.job_id).with_for_update())
            if not _owns_active_lease(job, claim, now):
                return False
            assert job is not None and job.lease_until is not None
            job.lease_until = now + timedelta(seconds=lease_seconds)
            job.updated_at = now
            return True

    def complete(
        self,
        *,
        workspace_id: UUID,
        claim: JobClaim,
    ) -> None:
        now = datetime.now(UTC)
        with self._session_factory.begin() as session:
            set_rls_context(session, workspace_id=workspace_id, user_id=None)
            job = session.scalar(select(Job).where(Job.id == claim.job_id).with_for_update())
            if not _owns_active_lease(job, claim, now):
                raise LeaseConflictError("Job lease is expired or owned by another worker")
            assert job is not None
            attempt = _attempt_for_claim(session, claim)
            if attempt is None:
                raise LeaseConflictError("Attempt does not match the current fence")
            attempt.state = AttemptState.SUCCEEDED.value
            attempt.finished_at = now
            job.state = JobState.SUCCEEDED.value
            job.lease_owner = None
            job.lease_until = None
            job.updated_at = now
            job.finished_at = now

    def fail(
        self,
        *,
        workspace_id: UUID,
        claim: JobClaim,
        error_code: str,
        retryable: bool,
        retry_delay_seconds: int = 0,
    ) -> str:
        if retry_delay_seconds < 0:
            raise ValueError("Retry delay cannot be negative")
        now = datetime.now(UTC)
        with self._session_factory.begin() as session:
            set_rls_context(session, workspace_id=workspace_id, user_id=None)
            job = session.scalar(select(Job).where(Job.id == claim.job_id).with_for_update())
            if not _owns_active_lease(job, claim, now):
                raise LeaseConflictError("Job lease is expired or owned by another worker")
            assert job is not None
            attempt = _attempt_for_claim(session, claim)
            if attempt is None:
                raise LeaseConflictError("Attempt does not match the current fence")
            attempt.state = AttemptState.FAILED.value
            attempt.error_code = error_code[:100]
            attempt.finished_at = now
            job.last_error_code = error_code[:100]
            job.updated_at = now
            session.scalar(select(Project).where(Project.id == job.project_id).with_for_update())
            task = session.scalar(select(Task).where(Task.id == job.task_id).with_for_update())
            if task is None:
                job.state = JobState.FAILED.value
                job.finished_at = now
                return job.state
            if retryable and job.attempts < job.max_attempts:
                job.state = JobState.QUEUED.value
                job.available_at = now + timedelta(seconds=retry_delay_seconds)
                job.lease_owner = None
                job.lease_until = None
                _transition_task(
                    session,
                    task,
                    TaskState.QUEUED,
                    event_type="task.retry_queued",
                    now=now,
                )
                return job.state
            job.state = JobState.DEAD.value if retryable else JobState.FAILED.value
            job.lease_owner = None
            job.lease_until = None
            job.finished_at = now
            _transition_task(
                session,
                task,
                TaskState.FAILED,
                event_type="task.failed",
                now=now,
            )
            return job.state

    def recover_expired(self, *, workspace_id: UUID) -> int:
        now = datetime.now(UTC)
        recovered = 0
        with self._session_factory.begin() as session:
            set_rls_context(session, workspace_id=workspace_id, user_id=None)
            jobs = session.scalars(
                select(Job)
                .where(
                    Job.workspace_id == workspace_id,
                    Job.state == JobState.RUNNING.value,
                    Job.lease_until < now,
                )
                .order_by(Job.lease_until)
                .with_for_update(skip_locked=True)
            ).all()
            for job in jobs:
                attempt = session.scalar(
                    select(TaskAttempt)
                    .where(
                        TaskAttempt.job_id == job.id,
                        TaskAttempt.fence_token == job.fence_token,
                        TaskAttempt.state == AttemptState.RUNNING.value,
                    )
                    .with_for_update()
                )
                if attempt is not None:
                    attempt.state = AttemptState.INTERRUPTED.value
                    attempt.error_code = "LEASE_EXPIRED"
                    attempt.finished_at = now
                job.lease_owner = None
                job.lease_until = None
                job.updated_at = now
                session.scalar(
                    select(Project).where(Project.id == job.project_id).with_for_update()
                )
                task = session.scalar(select(Task).where(Task.id == job.task_id).with_for_update())
                if retry_possible := job.attempts < job.max_attempts:
                    job.state = JobState.QUEUED.value
                    job.available_at = now
                    if task is not None:
                        _transition_task(
                            session,
                            task,
                            TaskState.QUEUED,
                            event_type="task.lease_recovered",
                            now=now,
                        )
                else:
                    job.state = JobState.DEAD.value
                    job.finished_at = now
                    if task is not None:
                        _transition_task(
                            session,
                            task,
                            TaskState.FAILED,
                            event_type="task.failed",
                            now=now,
                        )
                recovered += 1 if retry_possible else 0
        return recovered


def _owns_active_lease(job: Job | None, claim: JobClaim, now: datetime) -> bool:
    return (
        job is not None
        and job.state == JobState.RUNNING.value
        and job.lease_owner == claim.worker_id
        and job.fence_token == claim.fence_token
        and job.lease_until is not None
        and job.lease_until > now
    )


def _attempt_for_claim(session: Session, claim: JobClaim) -> TaskAttempt | None:
    return session.scalar(
        select(TaskAttempt)
        .where(
            TaskAttempt.job_id == claim.job_id,
            TaskAttempt.attempt_number == claim.attempt_number,
            TaskAttempt.fence_token == claim.fence_token,
            TaskAttempt.state == AttemptState.RUNNING.value,
        )
        .with_for_update()
    )


def _transition_task(
    session: Session,
    task: Task,
    state: TaskState,
    *,
    event_type: str,
    now: datetime,
) -> int:
    session.scalar(select(Project).where(Project.id == task.project_id).with_for_update())
    task.state = state.value
    task.revision += 1
    task.updated_at = now
    session.add(
        TaskVersion(
            id=uuid4(),
            workspace_id=task.workspace_id,
            project_id=task.project_id,
            task_id=task.id,
            task_revision=task.revision,
            state=task.state,
            input_version=task.input_version,
            role_version=task.role_version,
            created_at=now,
        )
    )
    last_sequence = session.scalar(
        select(ProjectEvent.project_seq)
        .where(ProjectEvent.project_id == task.project_id)
        .order_by(ProjectEvent.project_seq.desc())
        .limit(1)
    )
    session.add(
        ProjectEvent(
            id=uuid4(),
            workspace_id=task.workspace_id,
            project_id=task.project_id,
            project_seq=(last_sequence or 0) + 1,
            type=event_type,
            actor_user_id=None,
            object_type="task",
            object_id=task.id,
            object_revision=task.revision,
            payload={"state": task.state},
            correlation_id=uuid4(),
            created_at=now,
        )
    )
    return task.revision
