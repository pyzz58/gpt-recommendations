from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from medical_one_person.application.errors import ReviewPolicyError
from medical_one_person.infrastructure.db.models import (
    AuditFinding,
    AuditRun,
    Task,
    TaskDependency,
)


@dataclass(frozen=True)
class AuditBlocker:
    audit_id: UUID
    target_type: str
    target_id: UUID
    reviewer_role: str
    state: str
    finding_codes: tuple[str, ...]


def active_audit_blockers(
    session: Session,
    *,
    project_id: UUID,
    task_id: UUID | None = None,
    target_ids: set[UUID] | None = None,
) -> list[AuditBlocker]:
    if task_id is None and not target_ids:
        return []
    runs = session.scalars(
        select(AuditRun)
        .where(AuditRun.project_id == project_id)
        .order_by(AuditRun.created_at.desc())
    ).all()
    latest: dict[tuple[str, UUID, str], AuditRun] = {}
    for run in runs:
        key = (run.target_type, run.target_id, run.reviewer_role)
        existing = latest.get(key)
        if existing is None or run.review_version > existing.review_version:
            latest[key] = run
    tasks = session.scalars(
        select(Task).where(Task.project_id == project_id)
    ).all()
    dependencies = session.scalars(
        select(TaskDependency).where(TaskDependency.project_id == project_id)
    ).all()
    downstream: dict[UUID, set[UUID]] = {}
    for dependency in dependencies:
        downstream.setdefault(dependency.depends_on_task_id, set()).add(
            dependency.task_id
        )

    def affected_task_ids(run: AuditRun) -> set[UUID]:
        roots = {
            task.id
            for task in tasks
            if _task_consumes_target(task, run)
        }
        if run.linked_task_id is not None:
            roots.add(run.linked_task_id)
        affected = set(roots)
        frontier = list(roots)
        while frontier:
            upstream = frontier.pop()
            for dependent in downstream.get(upstream, set()):
                if dependent not in affected:
                    affected.add(dependent)
                    frontier.append(dependent)
        return affected

    blockers: list[AuditBlocker] = []
    for run in latest.values():
        task_affected = task_id is not None and task_id in affected_task_ids(run)
        target_affected = (
            target_ids is not None
            and run.target_id in target_ids
        )
        if not (task_affected or target_affected) or run.state == "passed":
            continue
        findings = session.scalars(
            select(AuditFinding).where(AuditFinding.audit_id == run.id)
        ).all()
        unresolved = [
            finding
            for finding in findings
            if finding.status == "open"
            or (finding.severity == "critical" and finding.status == "accepted_risk")
        ]
        if unresolved:
            blockers.append(
                AuditBlocker(
                    audit_id=run.id,
                    target_type=run.target_type,
                    target_id=run.target_id,
                    reviewer_role=run.reviewer_role,
                    state=run.state,
                    finding_codes=tuple(sorted(item.code for item in unresolved)),
                )
            )
    return blockers


def _task_consumes_target(task: Task, run: AuditRun) -> bool:
    refs = task.input_snapshot.get("refs", [])
    if not isinstance(refs, list):
        return False
    target_id = str(run.target_id)
    for item in refs:
        if not isinstance(item, dict):
            continue
        kind = item.get("kind")
        if (
            run.target_type == "claim_version"
            and kind == "claim"
            and item.get("object_version") == target_id
        ):
            return True
        if (
            run.target_type in {"analysis_run", "external_deliverable"}
            and kind
            == (
                "analysis"
                if run.target_type == "analysis_run"
                else "deliverable"
            )
            and item.get("object_id") == target_id
        ):
            return True
    return False


def require_no_active_audit_blockers(
    session: Session,
    *,
    project_id: UUID,
    task_id: UUID | None = None,
    target_ids: set[UUID] | None = None,
) -> None:
    blockers = active_audit_blockers(
        session,
        project_id=project_id,
        task_id=task_id,
        target_ids=target_ids,
    )
    if blockers:
        detail = "; ".join(
            f"{item.reviewer_role}:{item.target_type}:{item.audit_id}:"
            + ",".join(item.finding_codes)
            for item in blockers
        )
        raise ReviewPolicyError("Active audit findings block this action: " + detail)
