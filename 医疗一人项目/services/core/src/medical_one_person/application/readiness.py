from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from medical_one_person.application.errors import ReviewPolicyError
from medical_one_person.infrastructure.db.models import AuditFinding, AuditRun


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
    blockers: list[AuditBlocker] = []
    for run in latest.values():
        affected = run.linked_task_id == task_id or (
            target_ids is not None and run.target_id in target_ids
        )
        if not affected or run.state == "passed":
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
