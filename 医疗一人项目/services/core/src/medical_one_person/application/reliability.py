from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.errors import NotFoundError
from medical_one_person.domain.reliability import (
    ReliabilityEvaluationView,
    ReliabilityFinding,
    ReliabilityMetrics,
    ReliabilityProjectView,
)
from medical_one_person.domain.tasks import TaskState
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    AgentRun,
    AuditFinding,
    BudgetLedgerEntry,
    BudgetReservation,
    Job,
    MailSendAttempt,
    PolicyImpact,
    PolicyMigrationOperation,
    Project,
    ReliabilityEvaluation,
    SkillRun,
    Task,
    TaskAttempt,
    ToolAuditEvent,
    User,
)

OPEN_TASK_STATES = {
    TaskState.DRAFT.value,
    TaskState.NEEDS_INPUT.value,
    TaskState.READY.value,
    TaskState.QUEUED.value,
    TaskState.RUNNING.value,
    TaskState.SUBMITTED.value,
    TaskState.REWORK.value,
    TaskState.WAITING_EXTERNAL.value,
    TaskState.PAUSED.value,
}


class ReliabilityService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def evaluate(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        performance_threshold_ms: float = 500.0,
    ) -> ReliabilityEvaluationView:
        now = datetime.now(UTC)
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(
                session,
                workspace_id=actor.workspace_id,
                user_id=actor.id,
            )
            project = _project(session, project_id, actor.workspace_id)
            tasks = session.scalars(
                select(Task).where(Task.project_id == project.id).order_by(Task.id)
            ).all()
            task_ids = {task.id for task in tasks}
            jobs = session.scalars(
                select(Job).where(Job.project_id == project.id)
            ).all()
            attempts = session.scalars(
                select(TaskAttempt).where(TaskAttempt.project_id == project.id)
            ).all()
            agent_runs = session.scalars(
                select(AgentRun).where(AgentRun.project_id == project.id)
            ).all()
            skill_runs = session.scalars(
                select(SkillRun).where(SkillRun.project_id == project.id)
            ).all()
            tool_audits = session.scalars(
                select(ToolAuditEvent).where(
                    ToolAuditEvent.project_id == project.id
                )
            ).all()
            reservations = session.scalars(
                select(BudgetReservation).where(
                    BudgetReservation.project_id == project.id
                )
            ).all()
            mail_attempts = session.scalars(
                select(MailSendAttempt).where(
                    MailSendAttempt.project_id == project.id
                )
            ).all()
            open_findings = list(
                session.scalars(
                    select(AuditFinding).where(
                        AuditFinding.project_id == project.id,
                        AuditFinding.status.in_(["open", "accepted_risk"]),
                    )
                ).all()
            )
            impacts = int(
                session.scalar(
                    select(func.count())
                    .select_from(PolicyImpact)
                    .where(PolicyImpact.project_id == project.id)
                )
                or 0
            )
            migrations = int(
                session.scalar(
                    select(func.count())
                    .select_from(PolicyMigrationOperation)
                    .where(PolicyMigrationOperation.project_id == project.id)
                )
                or 0
            )
            spent = session.scalar(
                select(func.coalesce(func.sum(BudgetLedgerEntry.spent_delta), 0)).where(
                    BudgetLedgerEntry.project_id == project.id
                )
            )
            durations: list[float] = []
            for _ in range(12):
                started = time.perf_counter()
                session.scalars(
                    select(Task.id)
                    .where(Task.project_id == project.id)
                    .order_by(Task.updated_at.desc())
                    .limit(100)
                ).all()
                durations.append((time.perf_counter() - started) * 1000)
            p95 = sorted(durations)[max(0, int(len(durations) * 0.95) - 1)]
            findings: list[ReliabilityFinding] = []
            for job in jobs:
                if job.state == "running" and (
                    job.lease_until is None or job.lease_until <= now
                ):
                    findings.append(
                        _finding("EXPIRED_RUNNING_LEASE", "critical", "job", job.id)
                    )
            for task in tasks:
                if not task.policy_bundle_id:
                    findings.append(
                        _finding("TASK_POLICY_BUNDLE_MISSING", "critical", "task", task.id)
                    )
                if (
                    task.input_validity != "current"
                    and task.state in {TaskState.QUEUED.value, TaskState.RUNNING.value}
                ):
                    findings.append(
                        _finding("INVALID_INPUT_IN_FLIGHT", "critical", "task", task.id)
                    )
                if task.revision < 1:
                    findings.append(
                        _finding("TASK_REVISION_INVALID", "critical", "task", task.id)
                    )
            for attempt in attempts:
                if attempt.task_id not in task_ids:
                    findings.append(
                        _finding(
                            "ATTEMPT_TASK_CHAIN_MISSING",
                            "critical",
                            "attempt",
                            attempt.id,
                        )
                    )
                if (
                    attempt.state == "running"
                    and not any(
                        job.id == attempt.job_id
                        and job.state == "running"
                        and job.fence_token == attempt.fence_token
                        for job in jobs
                    )
                ):
                    findings.append(
                        _finding(
                            "ATTEMPT_JOB_CHAIN_MISSING",
                            "critical",
                            "attempt",
                            attempt.id,
                        )
                    )
            job_by_id = {job.id: job for job in jobs}
            for run in agent_runs:
                if run.task_id not in task_ids or run.job_id not in job_by_id:
                    findings.append(
                        _finding("AGENT_RUN_CHAIN_MISSING", "critical", "run", run.id)
                    )
                if not run.policy_bundle_id:
                    findings.append(
                        _finding("AGENT_RUN_POLICY_MISSING", "critical", "run", run.id)
                    )
                if (
                    run.state == "succeeded"
                    and run.job_id in job_by_id
                    and job_by_id[run.job_id].state
                    not in {"succeeded", "queued", "running"}
                ):
                    findings.append(
                        _finding(
                            "SUCCEEDED_RUN_JOB_FAILED",
                            "critical",
                            "run",
                            run.id,
                        )
                    )
            for skill_run in skill_runs:
                if (
                    skill_run.task_id not in task_ids
                    or not skill_run.policy_bundle_id
                ):
                    findings.append(
                        _finding(
                            "SKILL_RUN_CHAIN_MISSING",
                            "critical",
                            "skill_run",
                            skill_run.id,
                        )
                    )
            for audit in tool_audits:
                if (
                    audit.state == "authorized"
                    and audit.created_at < now - timedelta(minutes=5)
                ):
                    findings.append(
                        _finding(
                            "TOOL_AUDIT_UNSETTLED",
                            "major",
                            "tool_audit",
                            audit.id,
                        )
                    )
            for reservation in reservations:
                if reservation.state == "uncertain":
                    findings.append(
                        _finding(
                            "BUDGET_OUTCOME_UNCERTAIN",
                            "critical",
                            "budget_reservation",
                            reservation.id,
                        )
                    )
            for mail_attempt in mail_attempts:
                if mail_attempt.state == "outcome_unknown":
                    findings.append(
                        _finding(
                            "EXTERNAL_SEND_OUTCOME_UNKNOWN",
                            "critical",
                            "mail_attempt",
                            mail_attempt.id,
                        )
                    )
            for finding in open_findings:
                if finding.severity == "critical" or finding.status == "open":
                    findings.append(
                        _finding(
                            "AUDIT_FINDING_UNRESOLVED",
                            "critical" if finding.severity == "critical" else "major",
                            "audit_finding",
                            finding.id,
                        )
                    )
            if p95 > performance_threshold_ms:
                findings.append(
                    ReliabilityFinding(
                        code="TASK_LIST_P95_OVER_BUDGET",
                        severity="major",
                        object_type="project",
                        object_id=str(project.id),
                        detail=(
                            f"Task list p95 {p95:.1f}ms exceeds "
                            f"{performance_threshold_ms:.1f}ms"
                        ),
                    )
                )
            metrics = ReliabilityMetrics(
                tasks=len(tasks),
                open_tasks=sum(task.state in OPEN_TASK_STATES for task in tasks),
                jobs=len(jobs),
                running_jobs=sum(job.state == "running" for job in jobs),
                expired_leases=sum(
                    job.state == "running"
                    and (job.lease_until is None or job.lease_until <= now)
                    for job in jobs
                ),
                attempts=len(attempts),
                agent_runs=len(agent_runs),
                succeeded_agent_runs=sum(run.state == "succeeded" for run in agent_runs),
                skill_runs=len(skill_runs),
                tool_audits=len(tool_audits),
                unresolved_tool_audits=sum(
                    audit.state == "authorized" for audit in tool_audits
                ),
                policy_impact_count=impacts,
                migrated_policy_count=migrations,
                budget_reserved=str(
                    sum(
                        (
                            item.amount
                            for item in reservations
                            if item.state in {"reserved", "uncertain"}
                        ),
                        Decimal("0"),
                    )
                ),
                budget_spent=str(spent or Decimal("0")),
                uncertain_budget_reservations=sum(
                    item.state == "uncertain" for item in reservations
                ),
                outcome_unknown_mail_attempts=sum(
                    item.state == "outcome_unknown" for item in mail_attempts
                ),
                open_audit_findings=len(open_findings),
                task_list_p95_ms=round(p95, 3),
            )
            limitations = [
                "Synthetic/local measurements only; no production load or "
                "external service latency.",
                "Error injection covers selected database and mock-adapter failure "
                "paths, not every host failure.",
                "A passed reliability report does not prove scientific validity or "
                "real-world execution.",
            ]
            evaluation = ReliabilityEvaluation(
                id=uuid4(),
                workspace_id=project.workspace_id,
                project_id=project.id,
                policy_bundle_id=project.policy_bundle_id,
                status="blocked" if findings else "passed",
                metrics=metrics.model_dump(mode="json"),
                findings=[item.model_dump(mode="json") for item in findings],
                limitations=limitations,
                created_by_user_id=actor.id,
                created_at=now,
            )
            session.add(evaluation)
            session.flush()
            return _evaluation_view(evaluation)

    def project_view(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
    ) -> ReliabilityProjectView:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(
                session,
                workspace_id=actor.workspace_id,
                user_id=actor.id,
            )
            project = _project(session, project_id, actor.workspace_id)
            latest = session.scalar(
                select(ReliabilityEvaluation)
                .where(ReliabilityEvaluation.project_id == project.id)
                .order_by(ReliabilityEvaluation.created_at.desc())
                .limit(1)
            )
            return ReliabilityProjectView(
                project_id=str(project.id),
                latest=_evaluation_view(latest) if latest is not None else None,
                evidence={
                    "project_revision": project.revision,
                    "policy_bundle_id": project.policy_bundle_id,
                    "thresholds": {
                        "task_list_p95_ms": 500,
                    },
                },
            )


def _owner(session: Session, actor_user_id: UUID) -> User:
    actor = session.get(User, actor_user_id)
    if actor is None:
        raise NotFoundError("Actor not found")
    if not actor.is_owner:
        raise PermissionError("Only the verified workspace owner can evaluate reliability")
    return actor


def _project(session: Session, project_id: UUID, workspace_id: UUID) -> Project:
    project = session.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.workspace_id == workspace_id,
        )
    )
    if project is None:
        raise NotFoundError("Project not found")
    return project


def _finding(
    code: str,
    severity: str,
    object_type: str,
    object_id: UUID,
    detail: str | None = None,
) -> ReliabilityFinding:
    return ReliabilityFinding(
        code=code,
        severity=severity,
        object_type=object_type,
        object_id=str(object_id),
        detail=detail or code.replace("_", " ").lower(),
    )


def _evaluation_view(item: ReliabilityEvaluation) -> ReliabilityEvaluationView:
    return ReliabilityEvaluationView(
        id=str(item.id),
        project_id=str(item.project_id),
        policy_bundle_id=item.policy_bundle_id,
        status=item.status,
        metrics=ReliabilityMetrics.model_validate(item.metrics),
        findings=[ReliabilityFinding.model_validate(row) for row in item.findings],
        limitations=list(item.limitations),
        created_at=item.created_at,
    )
