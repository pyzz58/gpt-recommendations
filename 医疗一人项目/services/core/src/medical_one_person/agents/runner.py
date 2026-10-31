from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import AgentRoleConfig
from medical_one_person.agents.context import AgentContext
from medical_one_person.agents.contracts import AgentDelivery
from medical_one_person.application.errors import (
    AgentConfigurationError,
    AgentExecutionFailure,
    AgentOutputValidationError,
    LeaseConflictError,
)
from medical_one_person.application.scheduling import JobQueue
from medical_one_person.application.tasks import TaskService
from medical_one_person.domain.tasks import JobClaim, JobState, TaskState
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    AgentInstance,
    AgentRun,
    Job,
    PolicyBundle,
    Project,
    Task,
    TaskReview,
)
from medical_one_person.providers.base import (
    ModelProvider,
    StructuredGenerationRequest,
)


@dataclass(frozen=True)
class TaskExecutionView:
    id: UUID
    workspace_id: UUID
    project_id: UUID
    goal: str
    input_refs: tuple[str, ...]
    input_version: str
    purpose: str
    revision: int
    input_snapshot_sha256: str
    policy_bundle_id: str
    policy_theory_hash: str
    review_id: UUID | None
    review_feedback: tuple[str, ...]
    previous_output: dict[str, Any] | None


@dataclass(frozen=True)
class ExistingRunView:
    id: UUID
    state: str
    output: dict[str, Any] | None


class AgentRunner:
    """Runs one role context through one job attempt; it never accepts reviews."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        provider: ModelProvider,
        roles: dict[str, AgentRoleConfig],
        *,
        theory_hash: str,
        job_queue: JobQueue | None = None,
        max_schema_repairs: int = 1,
    ) -> None:
        self._session_factory = session_factory
        self._provider = provider
        self._roles = roles
        self._theory_hash = theory_hash
        self._job_queue = job_queue or JobQueue(session_factory)
        self._task_service = TaskService(session_factory)
        self._max_schema_repairs = max_schema_repairs

    def run_claim(self, claim: JobClaim) -> AgentDelivery:
        task, role, instance_id, context = self._prepare_context(claim)
        run_key = _run_key(task, role)

        existing = self._get_existing_run(claim.workspace_id, task.project_id, run_key)
        if existing is not None and existing.state == "succeeded" and existing.output:
            delivery = AgentDelivery.model_validate(existing.output)
            self._validate_delivery(delivery, task, role)
            self._finish_delivery(claim, task.id, delivery)
            return delivery

        run, cached_delivery = self._start_run(
            claim=claim,
            task=task,
            role=role,
            instance_id=instance_id,
            context=context,
            run_key=run_key,
        )
        if cached_delivery is not None:
            self._validate_delivery(cached_delivery, task, role)
            self._finish_delivery(claim, task.id, cached_delivery)
            return cached_delivery
        request = StructuredGenerationRequest(
            role_id=role.role_id,
            role_version=role.version,
            project_id=task.project_id,
            task_id=task.id,
            goal=task.goal,
            input_refs=list(task.input_refs),
            context_sections=context.sections(),
            system_instructions=context.system_instructions(),
            output_schema=role.output_schema,
            delivery_type=role.deliverable_types[0],
            independent_context=role.independent_context,
        )
        validation_error = ""
        response = None
        for repair in range(self._max_schema_repairs + 1):
            try:
                response = self._provider.generate_structured(
                    request.model_copy(update={"repair_feedback": validation_error or None})
                )
                delivery = AgentDelivery.model_validate(response.output)
                self._validate_delivery(delivery, task, role)
                break
            except (ValidationError, AgentOutputValidationError) as exc:
                validation_error = str(exc)[:4000]
                if repair >= self._max_schema_repairs:
                    self._mark_failed(
                        claim=claim,
                        run_id=run,
                        workspace_id=claim.workspace_id,
                        error_code="AGENT_SCHEMA_INVALID",
                    )
                    raise AgentExecutionFailure(
                        "Provider output failed schema/reference validation after repairs",
                        error_code="AGENT_SCHEMA_INVALID",
                        retryable=False,
                    ) from exc
            except Exception as exc:
                self._mark_failed(
                    claim=claim,
                    run_id=run,
                    workspace_id=claim.workspace_id,
                    error_code="PROVIDER_ERROR",
                )
                raise AgentExecutionFailure(
                    "Provider generation failed",
                    error_code="PROVIDER_ERROR",
                    retryable=True,
                ) from exc

        assert response is not None
        self._mark_succeeded(
            claim=claim,
            run_id=run,
            workspace_id=claim.workspace_id,
            delivery=delivery,
            provider_id=response.provider_id,
            model_id=response.model_id,
            usage=response.usage.model_dump(mode="json"),
        )
        self._finish_delivery(claim, task.id, delivery)
        return delivery

    def _prepare_context(
        self, claim: JobClaim
    ) -> tuple[TaskExecutionView, AgentRoleConfig, UUID, AgentContext]:
        with self._session_factory.begin() as session:
            set_rls_context(session, workspace_id=claim.workspace_id, user_id=None)
            task = session.scalar(
                select(Task)
                .where(
                    Task.id == claim.task_id,
                    Task.project_id == claim.project_id,
                )
                .with_for_update()
            )
            if task is None:
                raise AgentConfigurationError("Task not found for job")
            if not task.policy_bundle_id:
                raise AgentConfigurationError("Task has no policy bundle")
            bundle = session.get(PolicyBundle, task.policy_bundle_id)
            if bundle is None or bundle.workspace_id != task.workspace_id:
                raise AgentConfigurationError("Task policy bundle is unavailable")
            role_snapshot = next(
                (
                    item
                    for item in bundle.snapshot.get("components", {}).get("agents", [])
                    if isinstance(item, dict)
                    and item.get("role_id") == task.assignee_role
                ),
                None,
            )
            if role_snapshot is None:
                raise AgentConfigurationError(
                    "Task policy bundle does not contain its role contract"
                )
            role = AgentRoleConfig.model_validate(role_snapshot)
            if task.role_version != str(role.version):
                raise AgentConfigurationError(
                    "Task role version does not match fixed policy bundle"
                )
            current_role = self._roles.get(task.assignee_role)
            if current_role is None:
                raise AgentConfigurationError("Task role is not configured")
            effective_allow = sorted(
                set(role.tools_allow) & set(current_role.tools_allow)
            )
            revoked_tools = sorted(
                set(role.tools_allow) - set(current_role.tools_allow)
            )
            added_denials = sorted(
                set(current_role.tools_deny) - set(role.tools_deny)
            )
            role = role.model_copy(
                update={
                    "tools_allow": effective_allow,
                    "tools_deny": sorted(
                        set(role.tools_deny) | set(current_role.tools_deny)
                    ),
                }
            )
            if task.mode != "mock" or self._provider.capabilities().mode != "mock":
                raise AgentConfigurationError("W05 only permits mock provider execution")

            instance = session.scalar(
                select(AgentInstance).where(
                    AgentInstance.project_id == task.project_id,
                    AgentInstance.role_id == role.role_id,
                    AgentInstance.role_version == role.version,
                )
            )
            if instance is None:
                instance = AgentInstance(
                    id=uuid4(),
                    workspace_id=task.workspace_id,
                    project_id=task.project_id,
                    role_id=role.role_id,
                    role_version=role.version,
                    memory_scope=role.memory_scope,
                    context_namespace=uuid4(),
                    status="active",
                    created_at=datetime.now(UTC),
                )
                session.add(instance)
                session.flush()
            instance_id = instance.id
            project = session.get(Project, task.project_id)
            if project is None:
                raise AgentConfigurationError("Project not found for agent context")
            latest_review = session.scalar(
                select(TaskReview)
                .where(
                    TaskReview.task_id == task.id,
                    TaskReview.decision == "changes_requested",
                )
                .order_by(TaskReview.created_at.desc(), TaskReview.review_round.desc())
                .limit(1)
            )
            previous_run = session.scalar(
                select(AgentRun)
                .where(
                    AgentRun.task_id == task.id,
                    AgentRun.state == "succeeded",
                    AgentRun.output.is_not(None),
                )
                .order_by(AgentRun.created_at.desc())
                .limit(1)
            )
            review_feedback = (
                (
                    f"review_id={latest_review.id}",
                    f"summary={latest_review.summary}",
                    *[
                        (
                            f"finding={item.get('code', 'unknown')}:"
                            f"{item.get('severity', 'unknown')}:"
                            f"{item.get('message', '')}"
                        )
                        for item in latest_review.findings
                    ],
                )
                if latest_review is not None
                else ()
            )
            context = AgentContext(
                role=role,
                project_id=project.id,
                task_id=task.id,
                goal=task.goal,
                input_refs=tuple(task.input_refs),
                project_scope=project.scope,
                policy_bundle_id=bundle.id,
                current_policy_restrictions=tuple(
                    [f"REVOKED_TOOL:{item}" for item in revoked_tools]
                    + [f"CURRENT_DENY:{item}" for item in added_denials]
                ),
                review_feedback=review_feedback,
                previous_output=previous_run.output if previous_run is not None else None,
            )
            execution = TaskExecutionView(
                id=task.id,
                workspace_id=task.workspace_id,
                project_id=task.project_id,
                goal=task.goal,
                input_refs=tuple(task.input_refs),
                input_version=task.input_version,
                purpose=task.purpose,
                revision=task.revision,
                input_snapshot_sha256=task.input_snapshot_sha256 or "",
                policy_bundle_id=bundle.id,
                policy_theory_hash=bundle.theory_sha256,
                review_id=latest_review.id if latest_review is not None else None,
                review_feedback=review_feedback,
                previous_output=previous_run.output if previous_run is not None else None,
            )
            return execution, role, instance_id, context

    def _start_run(
        self,
        *,
        claim: JobClaim,
        task: TaskExecutionView,
        role: AgentRoleConfig,
        instance_id: UUID,
        context: AgentContext,
        run_key: str,
    ) -> tuple[UUID, AgentDelivery | None]:
        now = datetime.now(UTC)
        with self._session_factory.begin() as session:
            set_rls_context(session, workspace_id=claim.workspace_id, user_id=None)
            self._require_active_claim(session, claim)
            persisted = session.scalar(
                select(AgentRun)
                .where(
                    AgentRun.project_id == task.project_id,
                    AgentRun.run_key == run_key,
                )
                .with_for_update()
            )
            if persisted is None:
                run = AgentRun(
                    id=uuid4(),
                    workspace_id=task.workspace_id,
                    project_id=task.project_id,
                    task_id=task.id,
                    job_id=claim.job_id,
                    agent_instance_id=instance_id,
                    run_key=run_key,
                    mode="mock",
                    provider_id=self._provider.provider_id,
                    model_id=self._provider.capabilities().provider_id,
                    role_id=role.role_id,
                    role_version=role.version,
                    theory_hash=task.policy_theory_hash,
                    policy_bundle=role.limits_profile,
                    policy_bundle_id=task.policy_bundle_id,
                    input_snapshot=context.snapshot(),
                    state="running",
                    output_schema=role.output_schema,
                    independent_context=role.independent_context,
                    created_at=now,
                    started_at=now,
                )
                session.add(run)
                session.flush()
                return run.id, None
            if persisted.state == "succeeded" and persisted.output:
                return persisted.id, AgentDelivery.model_validate(persisted.output)
            if persisted.state == "cancelled":
                raise AgentConfigurationError("Cancelled agent run cannot restart")
            persisted.job_id = claim.job_id
            persisted.state = "running"
            persisted.error_code = None
            persisted.input_snapshot = context.snapshot()
            persisted.started_at = now
            persisted.ended_at = None
            return persisted.id, None

    def _mark_succeeded(
        self,
        *,
        claim: JobClaim,
        run_id: UUID,
        workspace_id: UUID,
        delivery: AgentDelivery,
        provider_id: str,
        model_id: str,
        usage: dict[str, object],
    ) -> None:
        with self._session_factory.begin() as session:
            set_rls_context(session, workspace_id=workspace_id, user_id=None)
            self._require_active_claim(session, claim)
            run = session.scalar(
                select(AgentRun).where(AgentRun.id == run_id).with_for_update()
            )
            if run is None:
                raise AgentConfigurationError("Agent run disappeared")
            run.provider_id = provider_id
            run.model_id = model_id
            run.state = "succeeded"
            run.output = delivery.model_dump(mode="json")
            run.usage = usage
            run.ended_at = datetime.now(UTC)

    def _mark_failed(
        self,
        *,
        claim: JobClaim,
        run_id: UUID,
        workspace_id: UUID,
        error_code: str,
    ) -> None:
        with self._session_factory.begin() as session:
            set_rls_context(session, workspace_id=workspace_id, user_id=None)
            self._require_active_claim(session, claim)
            run = session.scalar(
                select(AgentRun).where(AgentRun.id == run_id).with_for_update()
            )
            if run is not None:
                run.state = "failed"
                run.error_code = error_code
                run.ended_at = datetime.now(UTC)

    @staticmethod
    def _require_active_claim(session: Session, claim: JobClaim) -> None:
        job = session.scalar(
            select(Job).where(Job.id == claim.job_id).with_for_update()
        )
        now = datetime.now(UTC)
        if (
            job is None
            or job.state != JobState.RUNNING.value
            or job.lease_owner != claim.worker_id
            or job.fence_token != claim.fence_token
            or job.lease_until is None
            or job.lease_until <= now
        ):
            raise LeaseConflictError(
                "Job lease is expired or owned by another worker"
            )

    def _finish_delivery(self, claim: JobClaim, task_id: UUID, delivery: AgentDelivery) -> None:
        if delivery.task_id != task_id:
            raise AgentOutputValidationError("Delivery task does not match claimed task")
        with self._session_factory.begin() as session:
            set_rls_context(session, workspace_id=claim.workspace_id, user_id=None)
            task = session.get(Task, task_id)
            if task is None:
                raise AgentConfigurationError("Task disappeared")
            task_state = task.state
            task_state = task.state
        if task_state == TaskState.RUNNING.value:
            self._task_service.submit_by_worker(
                workspace_id=claim.workspace_id,
                project_id=claim.project_id,
                task_id=task_id,
                expected_revision=claim.task_revision,
            )
        self._job_queue.complete(workspace_id=claim.workspace_id, claim=claim)

    def _get_existing_run(
        self, workspace_id: UUID, project_id: UUID, run_key: str
    ) -> ExistingRunView | None:
        with self._session_factory.begin() as session:
            set_rls_context(session, workspace_id=workspace_id, user_id=None)
            run = session.scalar(
                select(AgentRun).where(
                    AgentRun.project_id == project_id,
                    AgentRun.run_key == run_key,
                )
            )
            if run is None:
                return None
            return ExistingRunView(id=run.id, state=run.state, output=run.output)

    @staticmethod
    def _validate_delivery(
        delivery: AgentDelivery, task: TaskExecutionView, role: AgentRoleConfig
    ) -> None:
        if delivery.mode != "mock":
            raise AgentOutputValidationError("Mock task returned a non-mock delivery")
        if delivery.role_id != role.role_id or delivery.role_version != role.version:
            raise AgentOutputValidationError("Delivery role/version does not match task")
        if delivery.project_id != task.project_id or delivery.task_id != task.id:
            raise AgentOutputValidationError("Delivery scope does not match task")
        if delivery.independent_review != role.independent_context:
            raise AgentOutputValidationError("Delivery independence marker is invalid")
        input_refs = set(task.input_refs)
        cited_refs = {reference.ref for reference in delivery.evidence_refs}
        fact_refs = {ref for fact in delivery.facts for ref in fact.source_refs}
        if not (cited_refs | fact_refs).issubset(input_refs):
            raise AgentOutputValidationError("Delivery cites references outside task inputs")


def _run_key(task: TaskExecutionView, role: AgentRoleConfig) -> str:
    canonical = (
        f"{task.project_id}:{task.id}:{role.role_id}:{role.version}:"
        f"{task.policy_bundle_id}:{task.input_version}:{task.input_snapshot_sha256}:"
        f"{task.review_id or 'none'}:{task.purpose}"
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
