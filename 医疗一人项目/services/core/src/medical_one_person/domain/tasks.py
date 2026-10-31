from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class TaskState(StrEnum):
    DRAFT = "draft"
    NEEDS_INPUT = "needs_input"
    READY = "ready"
    QUEUED = "queued"
    RUNNING = "running"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REWORK = "rework"
    WAITING_EXTERNAL = "waiting_external"
    PAUSED = "paused"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InputValidity(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    UNDER_REVIEW = "under_review"


class JobState(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEAD = "dead"
    CANCELLED = "cancelled"


class AttemptState(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


@dataclass(frozen=True)
class TaskSnapshot:
    id: UUID
    workspace_id: UUID
    project_id: UUID
    state: TaskState
    revision: int
    mode: str
    input_validity: InputValidity
    input_snapshot_sha256: str | None
    policy_bundle_id: str | None = None


@dataclass(frozen=True)
class JobClaim:
    job_id: UUID
    workspace_id: UUID
    project_id: UUID
    task_id: UUID
    worker_id: str
    fence_token: int
    attempt_number: int
    task_revision: int
    payload: dict[str, object]
