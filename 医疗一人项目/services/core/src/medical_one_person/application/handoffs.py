"""Resolve reviewed deliveries, never a worker's unaccepted completion claim."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from medical_one_person.application.errors import TaskNotReadyError
from medical_one_person.application.readiness import require_no_active_audit_blockers
from medical_one_person.infrastructure.db.models import AgentRun, Task, TaskReview


def payload_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def submitted_run(session: Session, task: Task) -> AgentRun:
    run = session.scalar(
        select(AgentRun)
        .where(
            AgentRun.project_id == task.project_id,
            AgentRun.task_id == task.id,
            AgentRun.state == "succeeded",
        )
        .order_by(AgentRun.created_at.desc())
        .limit(1)
    )
    if (
        run is None
        or not run.output
        or run.role_id != task.assignee_role
        or run.input_snapshot.get("input_refs") != task.input_refs
        or run.input_snapshot.get("goal") != task.goal
        or run.policy_bundle_id != task.policy_bundle_id
    ):
        raise TaskNotReadyError("Current task has no matching successful delivery to review")
    latest_return = session.scalar(
        select(TaskReview)
        .where(
            TaskReview.task_id == task.id,
            TaskReview.decision == "changes_requested",
        )
        .order_by(TaskReview.review_round.desc())
        .limit(1)
    )
    if latest_return is not None and f"review_id={latest_return.id}" not in run.input_snapshot.get(
        "review_feedback", []
    ):
        raise TaskNotReadyError("Delivery predates the latest rework feedback")
    return run


def accepted_run_payload(session: Session, *, project_id: UUID, run_id: UUID) -> dict[str, Any]:
    # Local import avoids a module cycle with the typed task-input resolver.
    from medical_one_person.application.tasks import require_current_task_inputs

    run = session.scalar(
        select(AgentRun).where(
            AgentRun.id == run_id,
            AgentRun.project_id == project_id,
        )
    )
    if run is None or run.state != "succeeded" or not run.output:
        raise TaskNotReadyError("Agent delivery is unavailable in this project")
    task = session.get(Task, run.task_id)
    if task is None or task.state != "accepted":
        raise TaskNotReadyError("Agent delivery has not been accepted")
    require_current_task_inputs(task, session=session)
    require_no_active_audit_blockers(session, project_id=project_id, task_id=task.id)
    reviews = session.scalars(
        select(TaskReview)
        .where(
            TaskReview.project_id == project_id,
            TaskReview.task_id == task.id,
        )
        .order_by(TaskReview.review_round)
    ).all()
    if not reviews or reviews[-1].decision != "accepted":
        raise TaskNotReadyError("Agent delivery has no current acceptance review")
    review = reviews[-1]
    if review.result_payload.get("delivery_run_id") != str(run.id):
        raise TaskNotReadyError("Review does not bind this delivery version")
    if review.result_payload.get("delivery_sha256") != payload_hash(run.output):
        raise TaskNotReadyError("Reviewed delivery content changed")
    return {
        "run_id": str(run.id),
        "task_id": str(task.id),
        "goal": task.goal,
        "role_id": run.role_id,
        "mode": run.mode,
        "review_id": str(review.id),
        "task_version_id": str(review.task_version_id),
        "delivery_sha256": payload_hash(run.output),
        "delivery": run.output,
        "reviews": [
            {
                "review_id": str(item.id),
                "reviewer_role": item.reviewer_role,
                "decision": item.decision,
                "summary": item.summary,
                "findings": item.findings,
            }
            for item in reviews
        ],
    }
