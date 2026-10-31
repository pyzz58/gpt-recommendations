from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import AgentRoleConfig
from medical_one_person.application.errors import (
    ConflictingOperationError,
    NotFoundError,
    PlanStateError,
    ReviewPolicyError,
    RevisionConflictError,
)
from medical_one_person.application.readiness import require_no_active_audit_blockers
from medical_one_person.application.tasks import (
    require_current_task_inputs,
    resolve_task_inputs,
)
from medical_one_person.domain.opportunities import Track
from medical_one_person.domain.plans import (
    FindingSeverity,
    PlanNodeSpec,
    PlanSpec,
    PlanStatus,
    ReviewDecision,
    ReviewFinding,
)
from medical_one_person.domain.projects import ProjectStage, ProjectStatus
from medical_one_person.domain.tasks import TaskState
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    CommandReceipt,
    Decision,
    Job,
    Opportunity,
    OutboxMessage,
    Plan,
    PlanNode,
    Project,
    ProjectEvent,
    ProjectVersion,
    Task,
    TaskDependency,
    TaskReview,
    TaskVersion,
    User,
)
from medical_one_person.infrastructure.workflows import WorkflowRegistry


class PlanNodeView(BaseModel):
    node_id: UUID
    task_id: UUID
    node_key: str
    order_index: int
    task_type: str
    goal: str
    assignee_role: str
    task_state: str
    task_revision: int
    dependencies: list[str]
    reviewer_roles: list[str]


class PlanView(BaseModel):
    id: UUID
    project_id: UUID
    plan_version: int
    status: PlanStatus
    revision: int
    title: str
    objective: str
    source_decision_id: UUID
    workflow_track: Track | None
    workflow_id: str | None
    workflow_version: int | None
    workflow_sha256: str | None
    stage_id: str | None
    pause_reason: str | None
    max_rework_rounds: int
    nodes: list[PlanNodeView]
    reviews: list[TaskReviewSummary]
    created_at: datetime
    updated_at: datetime
    activated_at: datetime | None
    paused_at: datetime | None
    stopped_at: datetime | None


class TaskReviewSummary(BaseModel):
    review_id: UUID
    task_id: UUID
    reviewer_role: str
    decision: ReviewDecision
    review_round: int
    summary: str
    findings: list[ReviewFinding]
    created_at: datetime


class PlanDispatchItem(BaseModel):
    task_id: UUID
    node_key: str
    assignee_role: str
    task_state: TaskState
    task_revision: int


class PlanDispatchView(BaseModel):
    plan_id: UUID
    plan_revision: int
    dispatched: list[PlanDispatchItem]


class TaskReviewView(BaseModel):
    review_id: UUID
    plan_id: UUID
    task_id: UUID
    decision: ReviewDecision
    review_round: int
    task_state: TaskState
    task_revision: int
    unlocked_task_ids: list[UUID]
    plan_status: PlanStatus


class PlanReceiptPayload(BaseModel):
    plan_id: UUID


class PlanService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        roles: dict[str, AgentRoleConfig],
        workflows: WorkflowRegistry | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._roles = roles
        self._workflows = workflows

    def submit_plan(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        source_decision_id: UUID,
        spec: PlanSpec,
        idempotency_key: str,
    ) -> PlanView:
        if not idempotency_key.strip():
            raise ValueError("Plan idempotency key is required")
        request_hash = _digest(
            {
                "project_id": str(project_id),
                "source_decision_id": str(source_decision_id),
                "spec": spec.model_dump(mode="json"),
            }
        )
        route = f"plans.submit:{project_id}"
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _locked_project(session, project_id, actor.workspace_id)
            receipt = _find_receipt(session, actor.id, route, idempotency_key)
            if receipt is not None:
                return self._replay_receipt(session, receipt, request_hash)
            _validate_plan_roles(spec, self._roles)
            decision = _validate_source_decision(session, project.id, source_decision_id)
            workflow_sha256 = _validate_spec_workflow(
                spec,
                selected_track=_decision_track(session, decision),
                workflows=self._workflows,
            )
            now = datetime.now(UTC)
            plan_version = (
                session.scalar(
                    select(func.max(Plan.plan_version)).where(Plan.project_id == project.id)
                )
                or 0
            ) + 1
            plan = Plan(
                id=uuid4(),
                workspace_id=project.workspace_id,
                project_id=project.id,
                plan_version=plan_version,
                status=PlanStatus.DRAFT.value,
                revision=1,
                title=spec.title,
                objective=spec.objective,
                source_decision_id=source_decision_id,
                workflow_track=(
                    spec.workflow_track.value if spec.workflow_track is not None else None
                ),
                workflow_id=spec.workflow_id,
                workflow_version=spec.workflow_version,
                workflow_sha256=workflow_sha256,
                stage_id=spec.stage_id,
                pause_reason=None,
                max_nodes=20,
                max_rework_rounds=spec.max_rework_rounds,
                created_by_user_id=actor.id,
                created_at=now,
                updated_at=now,
            )
            session.add(plan)
            session.flush()

            tasks_by_key: dict[str, Task] = {}
            for order_index, node_spec in enumerate(_topological_nodes(spec)):
                task_id = uuid4()
                dependency_tasks = [tasks_by_key[key] for key in node_spec.depends_on]
                task_state = TaskState.READY if not dependency_tasks else TaskState.NEEDS_INPUT
                input_refs = list(
                    dict.fromkeys(
                        [
                            f"decision:{source_decision_id}",
                            *node_spec.input_refs,
                        ]
                    )
                )
                input_snapshot, input_snapshot_sha256 = resolve_task_inputs(
                    session,
                    project_id=project.id,
                    input_version=node_spec.input_version,
                    input_refs=input_refs,
                    captured_at=now,
                )
                task = Task(
                    id=task_id,
                    workspace_id=project.workspace_id,
                    project_id=project.id,
                    dedupe_key=_digest(
                        {
                            "plan_id": str(plan.id),
                            "node_key": node_spec.key,
                            "task_type": node_spec.task_type,
                            "assignee_role": node_spec.assignee_role,
                        }
                    ),
                    task_type=node_spec.task_type,
                    purpose=node_spec.purpose,
                    assignee_role=node_spec.assignee_role,
                    role_version=node_spec.role_version,
                    input_version=node_spec.input_version,
                    input_refs=input_refs,
                    input_validity="current",
                    input_snapshot=input_snapshot,
                    input_snapshot_sha256=input_snapshot_sha256,
                    input_invalidated_at=None,
                    input_invalidated_reason=None,
                    input_invalidated_by=[],
                    goal=node_spec.goal,
                    deliverable_schema=node_spec.deliverable_schema,
                    acceptance_policy=node_spec.acceptance_policy,
                    mode=node_spec.mode,
                    state=task_state.value,
                    revision=1,
                    max_attempts=node_spec.max_attempts,
                    created_by_user_id=actor.id,
                    created_at=now,
                    updated_at=now,
                )
                session.add(task)
                session.flush()
                for dependency in dependency_tasks:
                    session.add(
                        TaskDependency(
                            id=uuid4(),
                            workspace_id=project.workspace_id,
                            project_id=project.id,
                            task_id=task.id,
                            depends_on_task_id=dependency.id,
                        )
                    )
                _append_task_version(session, task, now)
                _append_event(
                    session,
                    project_id=project.id,
                    workspace_id=project.workspace_id,
                    event_type="task.created",
                    object_type="task",
                    object_id=task.id,
                    object_revision=task.revision,
                    actor_user_id=actor.id,
                    payload={
                        "state": task.state,
                        "plan_id": str(plan.id),
                        "node_key": node_spec.key,
                    },
                    now=now,
                )
                session.add(
                    PlanNode(
                        id=uuid4(),
                        workspace_id=project.workspace_id,
                        project_id=project.id,
                        plan_id=plan.id,
                        task_id=task.id,
                        node_key=node_spec.key,
                        order_index=order_index,
                        created_at=now,
                    )
                )
                tasks_by_key[node_spec.key] = task

            _append_event(
                session,
                project_id=project.id,
                workspace_id=project.workspace_id,
                event_type="plan.submitted",
                object_type="plan",
                object_id=plan.id,
                object_revision=plan.revision,
                actor_user_id=actor.id,
                payload={
                    "plan_version": plan.plan_version,
                    "node_count": len(spec.nodes),
                    "source_decision_id": str(source_decision_id),
                },
                now=now,
            )
            session.add(
                CommandReceipt(
                    id=uuid4(),
                    actor_user_id=actor.id,
                    route=route,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    response_payload=PlanReceiptPayload(plan_id=plan.id).model_dump(mode="json"),
                    resource_id=plan.id,
                    created_at=now,
                )
            )
            session.flush()
            return self._detail(session, plan)

    def activate_plan(
        self,
        *,
        project_id: UUID,
        plan_id: UUID,
        actor_user_id: UUID,
        expected_revision: int,
    ) -> PlanView:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _locked_project(session, project_id, actor.workspace_id)
            plan = _locked_plan(session, plan_id, project.id)
            _expect_plan_revision(plan, expected_revision)
            if plan.status != PlanStatus.DRAFT.value:
                raise PlanStateError("Only a draft plan can be activated")
            decision = _validate_source_decision(session, project.id, plan.source_decision_id)
            _validate_existing_plan_workflow(
                plan,
                selected_track=_decision_track(session, decision),
                workflows=self._workflows,
            )
            nodes = self._plan_tasks(session, plan.id, project.id)
            if not nodes or len(nodes) > plan.max_nodes:
                raise PlanStateError("Plan node count is outside the configured bound")
            _validate_materialized_plan(session, plan, nodes, self._roles)
            now = datetime.now(UTC)
            plan.status = PlanStatus.ACTIVE.value
            plan.revision += 1
            plan.updated_at = now
            plan.activated_at = now
            _set_project_state(
                session,
                project,
                stage=ProjectStage.PLANNED,
                status=ProjectStatus.ACTIVE,
                actor_user_id=actor.id,
                now=now,
            )
            _append_event(
                session,
                project_id=project.id,
                workspace_id=project.workspace_id,
                event_type="plan.activated",
                object_type="plan",
                object_id=plan.id,
                object_revision=plan.revision,
                actor_user_id=actor.id,
                payload={"plan_version": plan.plan_version},
                now=now,
            )
            session.flush()
            return self._detail(session, plan)

    def dispatch_plan(
        self,
        *,
        project_id: UUID,
        plan_id: UUID,
        actor_user_id: UUID,
        expected_revision: int,
    ) -> PlanDispatchView:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _locked_project(session, project_id, actor.workspace_id)
            plan = _locked_plan(session, plan_id, project.id)
            _expect_plan_revision(plan, expected_revision)
            if plan.status != PlanStatus.ACTIVE.value:
                raise PlanStateError("Only an active plan can be dispatched")
            now = datetime.now(UTC)
            nodes = self._plan_tasks(session, plan.id, project.id)
            dependency_map = _dependency_map(session, project.id)
            tasks_by_id = {task.id: task for task in nodes}
            dispatched: list[PlanDispatchItem] = []
            for task in nodes:
                if task.state not in {
                    TaskState.READY.value,
                    TaskState.REWORK.value,
                }:
                    continue
                require_current_task_inputs(task, session=session)
                require_no_active_audit_blockers(
                    session,
                    project_id=project.id,
                    task_id=task.id,
                )
                dependencies = dependency_map.get(task.id, [])
                if any(
                    tasks_by_id[dependency_id].state != TaskState.ACCEPTED.value
                    for dependency_id in dependencies
                ):
                    continue
                task.state = TaskState.QUEUED.value
                task.revision += 1
                task.updated_at = now
                _append_task_version(session, task, now)
                session.add(
                    OutboxMessage(
                        id=uuid4(),
                        workspace_id=task.workspace_id,
                        project_id=task.project_id,
                        task_id=task.id,
                        unique_key=f"task:{task.id}:queue:{task.revision}",
                        event_type="task.queue_requested",
                        payload={
                            "task_id": str(task.id),
                            "plan_id": str(plan.id),
                            "deliverable_schema": task.deliverable_schema,
                        },
                        state="pending",
                        attempts=0,
                        available_at=now,
                        created_at=now,
                    )
                )
                _append_event(
                    session,
                    project_id=project.id,
                    workspace_id=project.workspace_id,
                    event_type="task.queued",
                    object_type="task",
                    object_id=task.id,
                    object_revision=task.revision,
                    actor_user_id=actor.id,
                    payload={"state": task.state, "plan_id": str(plan.id)},
                    now=now,
                )
                key = _node_key(session, plan.id, task.id)
                dispatched.append(
                    PlanDispatchItem(
                        task_id=task.id,
                        node_key=key,
                        assignee_role=task.assignee_role,
                        task_state=TaskState(task.state),
                        task_revision=task.revision,
                    )
                )
            if dispatched:
                plan.revision += 1
                plan.updated_at = now
                _append_event(
                    session,
                    project_id=project.id,
                    workspace_id=project.workspace_id,
                    event_type="plan.dispatched",
                    object_type="plan",
                    object_id=plan.id,
                    object_revision=plan.revision,
                    actor_user_id=actor.id,
                    payload={"task_ids": [str(item.task_id) for item in dispatched]},
                    now=now,
                )
            session.flush()
            return PlanDispatchView(
                plan_id=plan.id,
                plan_revision=plan.revision,
                dispatched=dispatched,
            )

    def review_task(
        self,
        *,
        project_id: UUID,
        plan_id: UUID,
        task_id: UUID,
        actor_user_id: UUID,
        expected_revision: int,
        reviewer_role: str,
        decision: ReviewDecision,
        summary: str,
        findings: list[ReviewFinding],
        idempotency_key: str,
    ) -> TaskReviewView:
        if not summary.strip() or not idempotency_key.strip():
            raise ValueError("Review summary and idempotency key are required")
        request_hash = _digest(
            {
                "task_id": str(task_id),
                "expected_revision": expected_revision,
                "reviewer_role": reviewer_role,
                "decision": decision.value,
                "summary": summary,
                "findings": [item.model_dump(mode="json") for item in findings],
            }
        )
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _locked_project(session, project_id, actor.workspace_id)
            plan = _locked_plan(session, plan_id, project.id)
            existing = session.scalar(
                select(TaskReview).where(
                    TaskReview.plan_id == plan.id,
                    TaskReview.idempotency_key == idempotency_key,
                )
            )
            if existing is not None:
                if existing.request_hash != request_hash:
                    raise ConflictingOperationError(
                        "Review idempotency key was reused with different parameters"
                    )
                task = session.get(Task, existing.task_id)
                if task is None:
                    raise NotFoundError("Task not found for review replay")
                return TaskReviewView.model_validate(existing.result_payload)
            if plan.status not in {PlanStatus.ACTIVE.value, PlanStatus.PAUSED.value}:
                raise PlanStateError("Plan is not open for review")
            task = session.scalar(
                select(Task)
                .join(PlanNode, PlanNode.task_id == Task.id)
                .where(
                    Task.id == task_id,
                    PlanNode.plan_id == plan.id,
                    Task.project_id == project.id,
                )
                .with_for_update()
            )
            if task is None:
                raise NotFoundError("Plan task not found")
            if task.revision != expected_revision:
                raise RevisionConflictError("Task revision conflict")
            if task.state != TaskState.SUBMITTED.value:
                raise PlanStateError("Only a submitted task can be reviewed")
            require_current_task_inputs(task, session=session)
            require_no_active_audit_blockers(
                session,
                project_id=project.id,
                task_id=task.id,
            )
            _validate_reviewer(task, reviewer_role, self._roles)
            critical = any(item.severity == FindingSeverity.CRITICAL for item in findings)
            if critical and decision != ReviewDecision.CHANGES_REQUESTED:
                raise ReviewPolicyError("A critical finding requires changes_requested")
            reviewed_version = session.scalar(
                select(TaskVersion).where(
                    TaskVersion.task_id == task.id,
                    TaskVersion.task_revision == expected_revision,
                )
            )
            if reviewed_version is None:
                raise NotFoundError("Reviewed task version not found")
            previous_reviews = int(
                session.scalar(
                    select(func.count())
                    .select_from(TaskReview)
                    .where(TaskReview.task_id == task.id)
                )
                or 0
            )
            previous_changes = int(
                session.scalar(
                    select(func.count())
                    .select_from(TaskReview)
                    .where(
                        TaskReview.task_id == task.id,
                        TaskReview.decision == ReviewDecision.CHANGES_REQUESTED.value,
                    )
                )
                or 0
            )
            now = datetime.now(UTC)
            review = TaskReview(
                id=uuid4(),
                workspace_id=project.workspace_id,
                project_id=project.id,
                plan_id=plan.id,
                task_id=task.id,
                task_version_id=reviewed_version.id,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                reviewer_user_id=actor.id,
                reviewer_role=reviewer_role,
                decision=decision.value,
                review_round=previous_reviews + 1,
                summary=summary,
                findings=[item.model_dump(mode="json") for item in findings],
                result_payload={},
                created_at=now,
            )
            session.add(review)

            unlocked: list[UUID] = []
            if decision == ReviewDecision.ACCEPTED:
                _transition_task(
                    session,
                    task,
                    TaskState.ACCEPTED,
                    event_type="task.accepted",
                    actor_user_id=actor.id,
                    payload={"review_id": str(review.id)},
                    now=now,
                )
                unlocked = self._unlock_ready_tasks(
                    session,
                    plan=plan,
                    project=project,
                    actor_user_id=actor.id,
                    now=now,
                )
                for unlocked_task_id in unlocked:
                    self._queue_for_worker(
                        session,
                        project=project,
                        task_id=unlocked_task_id,
                        operation="unlocked",
                        actor_user_id=actor.id,
                        now=now,
                    )
                nodes = self._plan_tasks(session, plan.id, project.id)
                if nodes and all(item.state == TaskState.ACCEPTED.value for item in nodes):
                    plan.status = PlanStatus.COMPLETED.value
                    plan.revision += 1
                    plan.updated_at = now
                    _append_event(
                        session,
                        project_id=project.id,
                        workspace_id=project.workspace_id,
                        event_type="plan.completed",
                        object_type="plan",
                        object_id=plan.id,
                        object_revision=plan.revision,
                        actor_user_id=actor.id,
                        payload={"accepted_tasks": len(nodes)},
                        now=now,
                    )
            elif decision == ReviewDecision.CHANGES_REQUESTED:
                if previous_changes >= plan.max_rework_rounds:
                    _transition_task(
                        session,
                        task,
                        TaskState.PAUSED,
                        event_type="task.iteration_limit_reached",
                        actor_user_id=actor.id,
                        payload={
                            "review_id": str(review.id),
                            "max_rework_rounds": plan.max_rework_rounds,
                        },
                        now=now,
                    )
                    _pause_plan(
                        session,
                        plan=plan,
                        project=project,
                        actor_user_id=actor.id,
                        reason="iteration_limit",
                        now=now,
                    )
                else:
                    _transition_task(
                        session,
                        task,
                        TaskState.REWORK,
                        event_type="task.changes_requested",
                        actor_user_id=actor.id,
                        payload={"review_id": str(review.id)},
                        now=now,
                    )
                    self._queue_for_worker(
                        session,
                        project=project,
                        task_id=task.id,
                        operation=f"rework:{review.id}",
                        actor_user_id=actor.id,
                        now=now,
                    )
            else:
                _append_event(
                    session,
                    project_id=project.id,
                    workspace_id=project.workspace_id,
                    event_type="task.review_disputed",
                    object_type="task",
                    object_id=task.id,
                    object_revision=task.revision,
                    actor_user_id=actor.id,
                    payload={"review_id": str(review.id)},
                    now=now,
                )
            result = TaskReviewView(
                review_id=review.id,
                plan_id=plan.id,
                task_id=task.id,
                decision=decision,
                review_round=review.review_round,
                task_state=TaskState(task.state),
                task_revision=task.revision,
                unlocked_task_ids=unlocked,
                plan_status=PlanStatus(plan.status),
            )
            review.result_payload = result.model_dump(mode="json")
            session.flush()
            return result

    def _queue_for_worker(
        self,
        session: Session,
        *,
        project: Project,
        task_id: UUID,
        operation: str,
        actor_user_id: UUID,
        now: datetime,
    ) -> None:
        task = session.get(Task, task_id)
        if task is None:
            raise NotFoundError("Task not found for worker queue")
        if task.state == TaskState.READY.value:
            _transition_task(
                session,
                task,
                TaskState.QUEUED,
                event_type="task.auto_queued",
                actor_user_id=actor_user_id,
                payload={"operation": operation},
                now=now,
            )
        session.add(
            OutboxMessage(
                id=uuid4(),
                workspace_id=project.workspace_id,
                project_id=project.id,
                task_id=task.id,
                unique_key=f"task:{task.id}:worker:{task.revision}:{operation}",
                event_type="task.queue_requested",
                payload={
                    "task_id": str(task.id),
                    "deliverable_schema": task.deliverable_schema,
                    "input_snapshot_sha256": task.input_snapshot_sha256,
                },
                state="pending",
                attempts=0,
                available_at=now,
                created_at=now,
            )
        )

    def pause_plan(
        self,
        *,
        project_id: UUID,
        plan_id: UUID,
        actor_user_id: UUID,
        expected_revision: int,
        reason: str,
    ) -> PlanView:
        if not reason.strip():
            raise ValueError("Pause reason is required")
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _locked_project(session, project_id, actor.workspace_id)
            plan = _locked_plan(session, plan_id, project.id)
            _expect_plan_revision(plan, expected_revision)
            if plan.status != PlanStatus.ACTIVE.value:
                raise PlanStateError("Only an active plan can be paused")
            now = datetime.now(UTC)
            _pause_plan(
                session,
                plan=plan,
                project=project,
                actor_user_id=actor.id,
                reason="manual",
                now=now,
            )
            session.flush()
            return self._detail(session, plan)

    def resume_plan(
        self,
        *,
        project_id: UUID,
        plan_id: UUID,
        actor_user_id: UUID,
        expected_revision: int,
        additional_rework_rounds: int = 0,
    ) -> PlanView:
        if additional_rework_rounds < 0:
            raise ValueError("Additional rework rounds cannot be negative")
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _locked_project(session, project_id, actor.workspace_id)
            plan = _locked_plan(session, plan_id, project.id)
            _expect_plan_revision(plan, expected_revision)
            if plan.status != PlanStatus.PAUSED.value:
                raise PlanStateError("Only a paused plan can be resumed")
            if plan.pause_reason == "iteration_limit":
                if additional_rework_rounds < 1:
                    raise PlanStateError("Resume requires an explicit additional rework allowance")
                plan.max_rework_rounds = min(
                    10,
                    plan.max_rework_rounds + additional_rework_rounds,
                )
            now = datetime.now(UTC)
            tasks = self._plan_tasks(session, plan.id, project.id)
            dependencies = _dependency_map(session, project.id)
            tasks_by_id = {task.id: task for task in tasks}
            for task in tasks:
                if task.state != TaskState.PAUSED.value:
                    continue
                dependencies_accepted = all(
                    tasks_by_id[dependency_id].state == TaskState.ACCEPTED.value
                    for dependency_id in dependencies.get(task.id, [])
                )
                next_state = (
                    TaskState.REWORK
                    if plan.pause_reason == "iteration_limit"
                    else (TaskState.READY if dependencies_accepted else TaskState.NEEDS_INPUT)
                )
                _transition_task(
                    session,
                    task,
                    next_state,
                    event_type="task.resumed",
                    actor_user_id=actor.id,
                    payload={"plan_id": str(plan.id)},
                    now=now,
                )
            plan.status = PlanStatus.ACTIVE.value
            plan.pause_reason = None
            plan.paused_at = now
            plan.revision += 1
            plan.updated_at = now
            _set_project_state(
                session,
                project,
                stage=ProjectStage.ACTIVE,
                status=ProjectStatus.ACTIVE,
                actor_user_id=actor.id,
                now=now,
            )
            _append_event(
                session,
                project_id=project.id,
                workspace_id=project.workspace_id,
                event_type="plan.resumed",
                object_type="plan",
                object_id=plan.id,
                object_revision=plan.revision,
                actor_user_id=actor.id,
                payload={
                    "max_rework_rounds": plan.max_rework_rounds,
                    "additional_rework_rounds": additional_rework_rounds,
                },
                now=now,
            )
            session.flush()
            return self._detail(session, plan)

    def stop_plan(
        self,
        *,
        project_id: UUID,
        plan_id: UUID,
        actor_user_id: UUID,
        expected_revision: int,
        reason: str,
    ) -> PlanView:
        if not reason.strip():
            raise ValueError("Stop reason is required")
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _locked_project(session, project_id, actor.workspace_id)
            plan = _locked_plan(session, plan_id, project.id)
            _expect_plan_revision(plan, expected_revision)
            if plan.status not in {
                PlanStatus.DRAFT.value,
                PlanStatus.ACTIVE.value,
                PlanStatus.PAUSED.value,
            }:
                raise PlanStateError("Plan cannot be stopped from its current state")
            now = datetime.now(UTC)
            tasks = self._plan_tasks(session, plan.id, project.id)
            running_task_ids = [task.id for task in tasks if task.state == TaskState.RUNNING.value]
            for task in tasks:
                if task.state in {
                    TaskState.DRAFT.value,
                    TaskState.NEEDS_INPUT.value,
                    TaskState.READY.value,
                    TaskState.QUEUED.value,
                    TaskState.REWORK.value,
                    TaskState.PAUSED.value,
                }:
                    _transition_task(
                        session,
                        task,
                        TaskState.CANCELLED,
                        event_type="task.cancelled",
                        actor_user_id=actor.id,
                        payload={"reason": reason, "plan_stopped": True},
                        now=now,
                    )
            _cancel_unstarted_work(session, plan.id, project.id, now)
            plan.status = PlanStatus.STOPPED.value
            plan.pause_reason = None
            plan.revision += 1
            plan.stopped_at = now
            plan.updated_at = now
            _set_project_state(
                session,
                project,
                stage=ProjectStage.STOPPED,
                status=ProjectStatus.STOPPED,
                actor_user_id=actor.id,
                now=now,
            )
            _append_event(
                session,
                project_id=project.id,
                workspace_id=project.workspace_id,
                event_type="plan.stopped",
                object_type="plan",
                object_id=plan.id,
                object_revision=plan.revision,
                actor_user_id=actor.id,
                payload={
                    "reason": reason,
                    "running_task_ids": [str(task_id) for task_id in running_task_ids],
                },
                now=now,
            )
            session.flush()
            return self._detail(session, plan)

    def list_plans(self, *, project_id: UUID, actor_user_id: UUID) -> list[PlanView]:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            _project(session, project_id, actor.workspace_id)
            plans = session.scalars(
                select(Plan).where(Plan.project_id == project_id).order_by(Plan.plan_version.desc())
            ).all()
            return [self._detail(session, plan) for plan in plans]

    def get_plan(
        self,
        *,
        project_id: UUID,
        plan_id: UUID,
        actor_user_id: UUID,
    ) -> PlanView:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            _project(session, project_id, actor.workspace_id)
            plan = session.scalar(
                select(Plan).where(Plan.id == plan_id, Plan.project_id == project_id)
            )
            if plan is None:
                raise NotFoundError("Plan not found")
            return self._detail(session, plan)

    def _detail(self, session: Session, plan: Plan) -> PlanView:
        nodes = session.scalars(
            select(PlanNode).where(PlanNode.plan_id == plan.id).order_by(PlanNode.order_index)
        ).all()
        tasks = {
            task.id: task
            for task in session.scalars(select(Task).where(Task.project_id == plan.project_id))
        }
        dependencies = _dependency_map(session, plan.project_id)
        key_by_task = {node.task_id: node.node_key for node in nodes}
        node_views = [
            PlanNodeView(
                node_id=node.id,
                task_id=node.task_id,
                node_key=node.node_key,
                order_index=node.order_index,
                task_type=tasks[node.task_id].task_type,
                goal=tasks[node.task_id].goal,
                assignee_role=tasks[node.task_id].assignee_role,
                task_state=tasks[node.task_id].state,
                task_revision=tasks[node.task_id].revision,
                dependencies=[
                    key_by_task[task_id] for task_id in dependencies.get(node.task_id, [])
                ],
                reviewer_roles=self._roles[tasks[node.task_id].assignee_role].reviewers,
            )
            for node in nodes
        ]
        reviews = session.scalars(
            select(TaskReview)
            .where(TaskReview.plan_id == plan.id)
            .order_by(TaskReview.created_at, TaskReview.review_round)
        ).all()
        return PlanView(
            id=plan.id,
            project_id=plan.project_id,
            plan_version=plan.plan_version,
            status=PlanStatus(plan.status),
            revision=plan.revision,
            title=plan.title,
            objective=plan.objective,
            source_decision_id=plan.source_decision_id,
            workflow_track=(
                Track(plan.workflow_track) if plan.workflow_track is not None else None
            ),
            workflow_id=plan.workflow_id,
            workflow_version=plan.workflow_version,
            workflow_sha256=plan.workflow_sha256,
            stage_id=plan.stage_id,
            pause_reason=plan.pause_reason,
            max_rework_rounds=plan.max_rework_rounds,
            nodes=node_views,
            reviews=[
                TaskReviewSummary(
                    review_id=review.id,
                    task_id=review.task_id,
                    reviewer_role=review.reviewer_role,
                    decision=ReviewDecision(review.decision),
                    review_round=review.review_round,
                    summary=review.summary,
                    findings=[ReviewFinding.model_validate(item) for item in review.findings],
                    created_at=review.created_at,
                )
                for review in reviews
            ],
            created_at=plan.created_at,
            updated_at=plan.updated_at,
            activated_at=plan.activated_at,
            paused_at=plan.paused_at,
            stopped_at=plan.stopped_at,
        )

    def _plan_tasks(self, session: Session, plan_id: UUID, project_id: UUID) -> list[Task]:
        return list(
            session.scalars(
                select(Task)
                .join(PlanNode, PlanNode.task_id == Task.id)
                .where(
                    PlanNode.plan_id == plan_id,
                    Task.project_id == project_id,
                )
                .order_by(PlanNode.order_index)
                .with_for_update()
            ).all()
        )

    def _unlock_ready_tasks(
        self,
        session: Session,
        *,
        plan: Plan,
        project: Project,
        actor_user_id: UUID,
        now: datetime,
    ) -> list[UUID]:
        tasks = self._plan_tasks(session, plan.id, project.id)
        dependencies = _dependency_map(session, project.id)
        tasks_by_id = {task.id: task for task in tasks}
        unlocked: list[UUID] = []
        changed = True
        while changed:
            changed = False
            for task in tasks:
                if task.state != TaskState.NEEDS_INPUT.value:
                    continue
                task_dependencies = dependencies.get(task.id, [])
                if task_dependencies and all(
                    tasks_by_id[dependency_id].state == TaskState.ACCEPTED.value
                    for dependency_id in task_dependencies
                ):
                    _transition_task(
                        session,
                        task,
                        TaskState.READY,
                        event_type="task.unblocked",
                        actor_user_id=actor_user_id,
                        payload={"plan_id": str(plan.id)},
                        now=now,
                    )
                    unlocked.append(task.id)
                    changed = True
        return unlocked

    def _replay_receipt(
        self,
        session: Session,
        receipt: CommandReceipt,
        request_hash: str,
    ) -> PlanView:
        if receipt.request_hash != request_hash:
            raise ConflictingOperationError(
                "Plan idempotency key was reused with different parameters"
            )
        payload = PlanReceiptPayload.model_validate(receipt.response_payload)
        plan = session.get(Plan, payload.plan_id)
        if plan is None:
            raise NotFoundError("Plan from receipt not found")
        return self._detail(session, plan)


def _validate_plan_roles(
    spec: PlanSpec,
    roles: dict[str, AgentRoleConfig],
) -> None:
    for node in spec.nodes:
        role = roles.get(node.assignee_role)
        if role is None:
            raise ReviewPolicyError(f"Plan role {node.assignee_role} is not configured")
        if node.role_version != str(role.version):
            raise ReviewPolicyError(f"Plan role version for {node.assignee_role} is not active")


def _decision_track(session: Session, decision: Decision) -> Track:
    opportunity = session.get(Opportunity, decision.selected_opportunity_id)
    if opportunity is None:
        raise PlanStateError("Selected opportunity is missing")
    return Track(opportunity.track)


def _validate_spec_workflow(
    spec: PlanSpec,
    *,
    selected_track: Track,
    workflows: WorkflowRegistry | None,
) -> str | None:
    if spec.workflow_id is None:
        return None
    if workflows is None:
        raise PlanStateError("Workflow registry is not configured")
    assert spec.workflow_track is not None
    assert spec.workflow_version is not None
    assert spec.stage_id is not None
    if spec.workflow_track != selected_track:
        raise PlanStateError("Plan workflow track does not match selected opportunity")
    workflow = workflows.get(spec.workflow_track)
    if workflow.workflow_id != spec.workflow_id or workflow.version != spec.workflow_version:
        raise PlanStateError("Plan workflow id/version is not active")
    stage = next(
        (item for item in workflow.stages if item.stage_id == spec.stage_id),
        None,
    )
    if stage is None:
        raise PlanStateError("Plan workflow stage is not defined")
    expected = {node.key: node for node in stage.plan_nodes}
    actual = {node.key: node for node in spec.nodes}
    if set(expected) != set(actual):
        raise PlanStateError("Plan nodes do not match the workflow stage template")
    for key, configured in expected.items():
        node = actual[key]
        if (
            node.assignee_role != configured.assignee_role
            or set(node.depends_on) != set(configured.depends_on)
            or node.task_type != configured.task_type
        ):
            raise PlanStateError(f"Plan node {key} does not match the workflow stage template")
    return workflows.fingerprint(spec.workflow_track)


def _validate_existing_plan_workflow(
    plan: Plan,
    *,
    selected_track: Track,
    workflows: WorkflowRegistry | None,
) -> None:
    if plan.workflow_id is None:
        return
    if workflows is None:
        raise PlanStateError("Workflow registry is not configured")
    assert plan.workflow_track is not None
    assert plan.workflow_version is not None
    if Track(plan.workflow_track) != selected_track:
        raise PlanStateError("Plan workflow track no longer matches selected opportunity")
    workflow = workflows.get(selected_track)
    if (
        workflow.workflow_id != plan.workflow_id
        or workflow.version != plan.workflow_version
        or workflows.fingerprint(selected_track) != plan.workflow_sha256
    ):
        raise PlanStateError("Workflow configuration changed after plan submission")
    if not any(stage.stage_id == plan.stage_id for stage in workflow.stages):
        raise PlanStateError("Plan workflow stage is no longer defined")


def _topological_nodes(spec: PlanSpec) -> list[PlanNodeSpec]:
    by_key = {node.key: node for node in spec.nodes}
    dependencies = {node.key: set(node.depends_on) for node in spec.nodes}
    ordered: list[PlanNodeSpec] = []
    while dependencies:
        ready = [node_key for node_key in dependencies if not dependencies[node_key]]
        if not ready:
            raise ValueError("Plan dependencies must not contain a cycle")
        for node_key in sorted(ready):
            ordered.append(by_key[node_key])
            dependencies.pop(node_key)
        for remaining in dependencies.values():
            remaining.difference_update(ready)
    return ordered


def _validate_materialized_plan(
    session: Session,
    plan: Plan,
    tasks: list[Task],
    roles: dict[str, AgentRoleConfig],
) -> None:
    for task in tasks:
        role = roles.get(task.assignee_role)
        if role is None or task.role_version != str(role.version):
            raise PlanStateError("Plan task role/version is not active")
        if task.mode != "mock":
            raise PlanStateError("Only mock/free plans can be activated")
    dependencies = _dependency_map(session, plan.project_id)
    task_ids = {task.id for task in tasks}
    for task_id in task_ids:
        dependency_ids = dependencies.get(task_id, [])
        if any(dependency_id not in task_ids for dependency_id in dependency_ids):
            raise PlanStateError("Plan dependency points outside the plan")


def _validate_reviewer(
    task: Task,
    reviewer_role: str,
    roles: dict[str, AgentRoleConfig],
) -> None:
    producer_role = roles.get(task.assignee_role)
    reviewer = roles.get(reviewer_role)
    if producer_role is None or reviewer is None:
        raise ReviewPolicyError("Reviewer role is not configured")
    if reviewer_role == task.assignee_role or reviewer_role not in producer_role.reviewers:
        raise ReviewPolicyError(
            "Reviewer must be a designated independent role for the producing role"
        )
    if not reviewer.independent_context:
        raise ReviewPolicyError("Designated reviewer is not an independent context role")


def _validate_source_decision(
    session: Session,
    project_id: UUID,
    source_decision_id: UUID,
) -> Decision:
    decision = session.scalar(
        select(Decision).where(
            Decision.id == source_decision_id,
            Decision.project_id == project_id,
        )
    )
    if decision is None or decision.kind != "opportunity_selection":
        raise PlanStateError("Plan requires a valid opportunity selection decision")
    opportunity = session.get(Opportunity, decision.selected_opportunity_id)
    if (
        opportunity is None
        or opportunity.project_id != project_id
        or opportunity.status != "selected"
    ):
        raise PlanStateError("Selected opportunity is missing or no longer selected")
    return decision


def _actor(session: Session, actor_user_id: UUID) -> User:
    actor = session.get(User, actor_user_id)
    if actor is None:
        raise NotFoundError("User not found")
    return actor


def _owner(session: Session, actor_user_id: UUID) -> User:
    actor = _actor(session, actor_user_id)
    if not actor.is_owner:
        raise PermissionError("Only the verified workspace owner can manage plans")
    return actor


def _project(session: Session, project_id: UUID, workspace_id: UUID) -> Project:
    project = session.get(Project, project_id)
    if project is None or project.workspace_id != workspace_id:
        raise NotFoundError("Project not found")
    return project


def _locked_project(session: Session, project_id: UUID, workspace_id: UUID) -> Project:
    project = session.scalar(
        select(Project)
        .where(Project.id == project_id, Project.workspace_id == workspace_id)
        .with_for_update()
    )
    if project is None:
        raise NotFoundError("Project not found")
    return project


def _locked_plan(session: Session, plan_id: UUID, project_id: UUID) -> Plan:
    plan = session.scalar(
        select(Plan).where(Plan.id == plan_id, Plan.project_id == project_id).with_for_update()
    )
    if plan is None:
        raise NotFoundError("Plan not found")
    return plan


def _expect_plan_revision(plan: Plan, expected_revision: int) -> None:
    if plan.revision != expected_revision:
        raise RevisionConflictError("Plan revision conflict")


def _find_receipt(
    session: Session,
    actor_user_id: UUID,
    route: str,
    idempotency_key: str,
) -> CommandReceipt | None:
    return session.scalar(
        select(CommandReceipt).where(
            CommandReceipt.actor_user_id == actor_user_id,
            CommandReceipt.route == route,
            CommandReceipt.idempotency_key == idempotency_key,
        )
    )


def _dependency_map(session: Session, project_id: UUID) -> dict[UUID, list[UUID]]:
    rows = session.execute(
        select(TaskDependency.task_id, TaskDependency.depends_on_task_id).where(
            TaskDependency.project_id == project_id
        )
    ).all()
    result: dict[UUID, list[UUID]] = {}
    for task_id, dependency_id in rows:
        result.setdefault(task_id, []).append(dependency_id)
    return result


def _node_key(session: Session, plan_id: UUID, task_id: UUID) -> str:
    name = session.scalar(
        select(PlanNode.node_key).where(
            PlanNode.plan_id == plan_id,
            PlanNode.task_id == task_id,
        )
    )
    if name is None:
        raise NotFoundError("Plan node not found")
    return name


def _append_task_version(session: Session, task: Task, now: datetime) -> None:
    session.add(
        TaskVersion(
            id=uuid4(),
            workspace_id=task.workspace_id,
            project_id=task.project_id,
            task_id=task.id,
            task_revision=task.revision,
            state=task.state,
            input_version=task.input_version,
            input_validity=task.input_validity,
            input_snapshot=task.input_snapshot,
            input_snapshot_sha256=task.input_snapshot_sha256,
            input_invalidated_at=task.input_invalidated_at,
            input_invalidated_reason=task.input_invalidated_reason,
            input_invalidated_by=task.input_invalidated_by,
            role_version=task.role_version,
            created_at=now,
        )
    )


def _transition_task(
    session: Session,
    task: Task,
    state: TaskState,
    *,
    event_type: str,
    actor_user_id: UUID | None,
    payload: dict[str, Any],
    now: datetime,
) -> None:
    task.state = state.value
    task.revision += 1
    task.updated_at = now
    _append_task_version(session, task, now)
    _append_event(
        session,
        project_id=task.project_id,
        workspace_id=task.workspace_id,
        event_type=event_type,
        object_type="task",
        object_id=task.id,
        object_revision=task.revision,
        actor_user_id=actor_user_id,
        payload={"state": task.state, **payload},
        now=now,
    )


def _append_event(
    session: Session,
    *,
    project_id: UUID,
    workspace_id: UUID,
    event_type: str,
    object_type: str,
    object_id: UUID,
    object_revision: int,
    actor_user_id: UUID | None,
    payload: dict[str, Any],
    now: datetime,
) -> None:
    last_sequence = session.scalar(
        select(ProjectEvent.project_seq)
        .where(ProjectEvent.project_id == project_id)
        .order_by(ProjectEvent.project_seq.desc())
        .limit(1)
    )
    session.add(
        ProjectEvent(
            id=uuid4(),
            workspace_id=workspace_id,
            project_id=project_id,
            project_seq=(last_sequence or 0) + 1,
            type=event_type,
            actor_user_id=actor_user_id,
            object_type=object_type,
            object_id=object_id,
            object_revision=object_revision,
            payload=payload,
            correlation_id=uuid4(),
            created_at=now,
        )
    )


def _set_project_state(
    session: Session,
    project: Project,
    *,
    stage: ProjectStage,
    status: ProjectStatus,
    actor_user_id: UUID,
    now: datetime,
) -> None:
    if project.stage == stage.value and project.status == status.value:
        return
    project.stage = stage.value
    project.status = status.value
    project.revision += 1
    project.updated_at = now
    session.add(
        ProjectVersion(
            id=uuid4(),
            workspace_id=project.workspace_id,
            project_id=project.id,
            project_revision=project.revision,
            name=project.name,
            scope=project.scope,
            stage=project.stage,
            status=project.status,
            charter_version=project.charter_version,
            policy_bundle_id=project.policy_bundle_id,
            changed_by_user_id=actor_user_id,
            created_at=now,
        )
    )
    _append_event(
        session,
        project_id=project.id,
        workspace_id=project.workspace_id,
        event_type="project.state_changed",
        object_type="project",
        object_id=project.id,
        object_revision=project.revision,
        actor_user_id=actor_user_id,
        payload={"stage": project.stage, "status": project.status},
        now=now,
    )


def _pause_plan(
    session: Session,
    *,
    plan: Plan,
    project: Project,
    actor_user_id: UUID,
    reason: str,
    now: datetime,
) -> None:
    plan.status = PlanStatus.PAUSED.value
    plan.pause_reason = reason
    plan.paused_at = now
    plan.revision += 1
    plan.updated_at = now
    tasks = session.scalars(
        select(Task)
        .join(PlanNode, PlanNode.task_id == Task.id)
        .where(
            PlanNode.plan_id == plan.id,
            Task.project_id == project.id,
            Task.state == TaskState.QUEUED.value,
        )
        .with_for_update()
    ).all()
    for task in tasks:
        _transition_task(
            session,
            task,
            TaskState.PAUSED,
            event_type="task.paused",
            actor_user_id=actor_user_id,
            payload={"plan_id": str(plan.id), "reason": reason},
            now=now,
        )
    _cancel_unstarted_work(session, plan.id, project.id, now)
    _set_project_state(
        session,
        project,
        stage=ProjectStage.PAUSED,
        status=ProjectStatus.PAUSED,
        actor_user_id=actor_user_id,
        now=now,
    )
    _append_event(
        session,
        project_id=project.id,
        workspace_id=project.workspace_id,
        event_type="plan.paused",
        object_type="plan",
        object_id=plan.id,
        object_revision=plan.revision,
        actor_user_id=actor_user_id,
        payload={"reason": reason},
        now=now,
    )


def _cancel_unstarted_work(
    session: Session,
    plan_id: UUID,
    project_id: UUID,
    now: datetime,
) -> None:
    task_ids = list(
        session.scalars(
            select(PlanNode.task_id).where(
                PlanNode.plan_id == plan_id,
                PlanNode.project_id == project_id,
            )
        )
    )
    if not task_ids:
        return
    outbox_messages = session.scalars(
        select(OutboxMessage)
        .where(
            OutboxMessage.task_id.in_(task_ids),
            OutboxMessage.state == "pending",
        )
        .with_for_update()
    ).all()
    for message in outbox_messages:
        message.state = "failed"
    jobs = session.scalars(
        select(Job).where(Job.task_id.in_(task_ids), Job.state == "queued").with_for_update()
    ).all()
    for job in jobs:
        job.state = "cancelled"
        job.finished_at = now
        job.updated_at = now


def _digest(value: dict[str, Any]) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
