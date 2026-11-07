from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.errors import (
    NotFoundError,
    TaskDependencyError,
    TaskNotReadyError,
)
from medical_one_person.application.readiness import require_no_active_audit_blockers
from medical_one_person.domain.tasks import InputValidity, TaskSnapshot, TaskState
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    AnalysisRun,
    Citation,
    ClaimVersion,
    Decision,
    ExternalDeliverable,
    KnowledgeDocumentVersion,
    OutboxMessage,
    PolicyBundle,
    Project,
    ProjectEvent,
    Task,
    TaskDependency,
    TaskVersion,
    User,
)


class TaskService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_task(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        task_type: str,
        purpose: str,
        assignee_role: str,
        role_version: str,
        input_version: str,
        input_refs: Sequence[str],
        goal: str,
        deliverable_schema: str,
        acceptance_policy: str,
        mode: str = "mock",
        max_attempts: int = 3,
        dependencies: Sequence[UUID] = (),
        policy_bundle_id: str | None = None,
    ) -> TaskSnapshot:
        if mode != "mock":
            raise ValueError("W04 only permits mock/free task scheduling")
        if not input_refs:
            raise ValueError("Task input_refs cannot be empty")
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        required_text = {
            "task_type": task_type,
            "purpose": purpose,
            "assignee_role": assignee_role,
            "role_version": role_version,
            "input_version": input_version,
            "goal": goal,
            "deliverable_schema": deliverable_schema,
            "acceptance_policy": acceptance_policy,
        }
        if any(not value.strip() for value in required_text.values()):
            raise ValueError("Task contract fields cannot be empty")

        dedupe_key = _digest(
            {
                "project_id": str(project_id),
                "task_type": task_type,
                "purpose": purpose,
                "assignee_role": assignee_role,
                "role_version": role_version,
                "input_version": input_version,
                "input_refs": list(input_refs),
                "deliverable_schema": deliverable_schema,
            }
        )
        now = datetime.now(UTC)
        with self._session_factory.begin() as session:
            actor = self._actor(session, actor_user_id)
            self._set_context(session, actor)
            project = self._project(
                session,
                project_id,
                actor.workspace_id,
                for_update=True,
            )
            bundle_id = policy_bundle_id or project.policy_bundle_id
            if not bundle_id:
                raise TaskNotReadyError("Project has no active policy bundle")
            bundle = session.get(PolicyBundle, bundle_id)
            if bundle is None or bundle.workspace_id != project.workspace_id:
                raise TaskNotReadyError("Task policy bundle is unknown")
            input_snapshot, input_snapshot_sha256 = resolve_task_inputs(
                session,
                project_id=project.id,
                input_version=input_version,
                input_refs=input_refs,
                captured_at=now,
            )
            existing = session.scalar(
                select(Task).where(
                    Task.project_id == project.id,
                    Task.dedupe_key == dedupe_key,
                )
            )
            if existing is not None:
                return _task_snapshot(existing)

            dependency_tasks = self._dependency_tasks(
                session,
                project.id,
                dependency_ids=dependencies,
                task_id=None,
            )
            state = (
                TaskState.READY
                if all(task.state == TaskState.ACCEPTED.value for task in dependency_tasks)
                else TaskState.NEEDS_INPUT
            )
            task = Task(
                id=uuid4(),
                workspace_id=project.workspace_id,
                project_id=project.id,
                dedupe_key=dedupe_key,
                task_type=task_type,
                purpose=purpose,
                assignee_role=assignee_role,
                role_version=role_version,
                policy_bundle_id=bundle.id,
                input_version=input_version,
                input_refs=list(input_refs),
                input_validity=InputValidity.CURRENT.value,
                input_snapshot=input_snapshot,
                input_snapshot_sha256=input_snapshot_sha256,
                input_invalidated_at=None,
                input_invalidated_reason=None,
                input_invalidated_by=[],
                goal=goal,
                deliverable_schema=deliverable_schema,
                acceptance_policy=acceptance_policy,
                mode=mode,
                state=state.value,
                revision=1,
                max_attempts=max_attempts,
                created_by_user_id=actor.id,
                created_at=now,
                updated_at=now,
            )
            session.add(task)
            session.flush()
            for upstream in dependency_tasks:
                session.add(
                    TaskDependency(
                        id=uuid4(),
                        workspace_id=project.workspace_id,
                        project_id=project.id,
                        task_id=task.id,
                        depends_on_task_id=upstream.id,
                    )
                )
            self._append_version(session, task, now)
            self._append_event(
                session,
                task,
                actor.id,
                event_type="task.created",
                payload={"state": task.state, "dedupe_key": task.dedupe_key},
                now=now,
            )
            session.flush()
            return _task_snapshot(task)

    def add_dependency(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        task_id: UUID,
        depends_on_task_id: UUID,
    ) -> None:
        if task_id == depends_on_task_id:
            raise TaskDependencyError("A task cannot depend on itself")
        with self._session_factory.begin() as session:
            actor = self._actor(session, actor_user_id)
            self._set_context(session, actor)
            project = session.scalar(
                select(Project).where(Project.id == project_id).with_for_update()
            )
            if project is None:
                raise NotFoundError("Project not found")
            loaded = self._dependency_tasks(
                session,
                project_id,
                dependency_ids=(depends_on_task_id,),
                task_id=task_id,
            )
            tasks_by_id = {item.id: item for item in loaded}
            task = tasks_by_id[task_id]
            upstream = tasks_by_id[depends_on_task_id]
            if task.state not in {
                TaskState.DRAFT.value,
                TaskState.NEEDS_INPUT.value,
                TaskState.READY.value,
            }:
                raise TaskDependencyError(
                    "Queued or completed tasks cannot accept new dependencies"
                )
            if session.scalar(
                select(TaskDependency).where(
                    TaskDependency.task_id == task_id,
                    TaskDependency.depends_on_task_id == depends_on_task_id,
                )
            ):
                return
            if self._path_exists(session, project_id, start=depends_on_task_id, target=task_id):
                raise TaskDependencyError("Dependency would create a cycle")
            session.add(
                TaskDependency(
                    id=uuid4(),
                    workspace_id=actor.workspace_id,
                    project_id=project_id,
                    task_id=task_id,
                    depends_on_task_id=depends_on_task_id,
                )
            )
            if upstream.state != TaskState.ACCEPTED.value and task.state == TaskState.READY.value:
                now = datetime.now(UTC)
                task.state = TaskState.NEEDS_INPUT.value
                task.revision += 1
                task.updated_at = now
                self._append_version(session, task, now)
                self._append_event(
                    session,
                    task,
                    actor.id,
                    event_type="task.dependency_added",
                    payload={"depends_on_task_id": str(upstream.id)},
                    now=now,
                )

    def enqueue(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        task_id: UUID,
    ) -> TaskSnapshot:
        with self._session_factory.begin() as session:
            actor = self._actor(session, actor_user_id)
            self._set_context(session, actor)
            project = session.scalar(
                select(Project).where(Project.id == project_id).with_for_update()
            )
            if project is None:
                raise NotFoundError("Project not found")
            task = session.scalar(
                select(Task)
                .where(Task.id == task_id, Task.project_id == project_id)
                .with_for_update()
            )
            if task is None:
                raise NotFoundError("Task not found")
            require_current_task_inputs(task, session=session)
            require_no_active_audit_blockers(
                session,
                project_id=project_id,
                task_id=task.id,
            )
            if task.state == TaskState.QUEUED.value:
                return _task_snapshot(task)
            if task.state != TaskState.READY.value:
                raise TaskNotReadyError("Task is not ready to queue")
            if task.mode != "mock":
                raise TaskNotReadyError("Live task budget enforcement is not configured")
            dependencies = session.scalars(
                select(TaskDependency).where(TaskDependency.task_id == task.id)
            ).all()
            for dependency in dependencies:
                upstream = session.get(Task, dependency.depends_on_task_id)
                if upstream is None or upstream.state != TaskState.ACCEPTED.value:
                    raise TaskNotReadyError("All dependencies must be accepted")
            if not task.input_refs:
                raise TaskNotReadyError("Task input references are missing")

            now = datetime.now(UTC)
            task.state = TaskState.QUEUED.value
            task.revision += 1
            task.updated_at = now
            self._append_version(session, task, now)
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
                        "deliverable_schema": task.deliverable_schema,
                    },
                    state="pending",
                    attempts=0,
                    available_at=now,
                    created_at=now,
                )
            )
            self._append_event(
                session,
                task,
                actor.id,
                event_type="task.queued",
                payload={"state": task.state},
                now=now,
            )
            session.flush()
            return _task_snapshot(task)

    def submit_for_review(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        task_id: UUID,
        expected_revision: int,
    ) -> TaskSnapshot:
        with self._session_factory.begin() as session:
            actor = self._actor(session, actor_user_id)
            self._set_context(session, actor)
            session.scalar(select(Project).where(Project.id == project_id).with_for_update())
            task = session.scalar(
                select(Task)
                .where(Task.id == task_id, Task.project_id == project_id)
                .with_for_update()
            )
            if task is None:
                raise NotFoundError("Task not found")
            if task.revision != expected_revision:
                raise TaskNotReadyError("Task revision conflict")
            if task.state != TaskState.RUNNING.value:
                raise TaskNotReadyError("Only a running task can be submitted")
            require_current_task_inputs(task, session=session)
            now = datetime.now(UTC)
            task.state = TaskState.SUBMITTED.value
            task.revision += 1
            task.updated_at = now
            self._append_version(session, task, now)
            self._append_event(
                session,
                task,
                actor.id,
                event_type="task.submitted",
                payload={"state": task.state, "accepted": False},
                now=now,
            )
            session.flush()
            return _task_snapshot(task)

    def submit_by_worker(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        task_id: UUID,
        expected_revision: int,
    ) -> TaskSnapshot:
        """Record worker output without impersonating the task's human creator."""

        with self._session_factory.begin() as session:
            set_rls_context(session, workspace_id=workspace_id, user_id=None)
            project = session.scalar(
                select(Project).where(Project.id == project_id).with_for_update()
            )
            if project is None:
                raise NotFoundError("Project not found")
            task = session.scalar(
                select(Task)
                .where(Task.id == task_id, Task.project_id == project_id)
                .with_for_update()
            )
            if task is None:
                raise NotFoundError("Task not found")
            if task.revision != expected_revision:
                raise TaskNotReadyError("Task revision conflict")
            if task.state != TaskState.RUNNING.value:
                raise TaskNotReadyError("Only a running task can be submitted")
            require_current_task_inputs(task, session=session)
            now = datetime.now(UTC)
            task.state = TaskState.SUBMITTED.value
            task.revision += 1
            task.updated_at = now
            self._append_version(session, task, now)
            self._append_event(
                session,
                task,
                None,
                event_type="task.submitted",
                payload={"state": task.state, "accepted": False, "actor": "worker"},
                now=now,
            )
            session.flush()
            return _task_snapshot(task)

    def invalidate_dependents(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        upstream_task_id: UUID,
    ) -> list[UUID]:
        with self._session_factory.begin() as session:
            actor = self._actor(session, actor_user_id)
            self._set_context(session, actor)
            session.scalar(select(Project).where(Project.id == project_id).with_for_update())
            now = datetime.now(UTC)
            direct_dependents = list(
                session.scalars(
                    select(TaskDependency.task_id).where(
                        TaskDependency.project_id == project_id,
                        TaskDependency.depends_on_task_id == upstream_task_id,
                    )
                ).all()
            )
            invalidated = invalidate_task_inputs(
                session,
                project_id=project_id,
                task_ids=direct_dependents,
                actor_user_id=actor.id,
                reason=f"UPSTREAM_TASK_CHANGED:{upstream_task_id}",
                now=now,
            )
            session.flush()
            return invalidated

    def revise_inputs(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        task_id: UUID,
        expected_revision: int,
        input_version: str,
        input_refs: Sequence[str],
    ) -> TaskSnapshot:
        if not input_version.strip() or not input_refs:
            raise ValueError("Revised task inputs require a version and references")
        now = datetime.now(UTC)
        with self._session_factory.begin() as session:
            actor = self._actor(session, actor_user_id)
            self._set_context(session, actor)
            project = session.scalar(
                select(Project).where(Project.id == project_id).with_for_update()
            )
            if project is None:
                raise NotFoundError("Project not found")
            task = session.scalar(
                select(Task)
                .where(Task.id == task_id, Task.project_id == project_id)
                .with_for_update()
            )
            if task is None:
                raise NotFoundError("Task not found")
            snapshot, snapshot_sha256 = resolve_task_inputs(
                session,
                project_id=project_id,
                input_version=input_version,
                input_refs=input_refs,
                captured_at=now,
            )
            if task.revision != expected_revision:
                raise TaskNotReadyError("Task revision conflict")
            if task.state in {
                TaskState.ACCEPTED.value,
                TaskState.CANCELLED.value,
                TaskState.RUNNING.value,
                TaskState.SUBMITTED.value,
            }:
                raise TaskNotReadyError(
                    "Accepted or in-flight task history is immutable; create a new task revision"
                )
            dependencies = session.scalars(
                select(Task)
                .join(TaskDependency, TaskDependency.depends_on_task_id == Task.id)
                .where(TaskDependency.task_id == task.id)
            ).all()
            dependencies_current = all(
                dependency.state == TaskState.ACCEPTED.value
                and dependency.input_validity == InputValidity.CURRENT.value
                for dependency in dependencies
            )
            task.input_version = input_version
            if not project.policy_bundle_id:
                raise TaskNotReadyError("Project has no active policy bundle")
            task.policy_bundle_id = project.policy_bundle_id
            task.input_refs = list(input_refs)
            task.input_snapshot = snapshot
            task.input_snapshot_sha256 = snapshot_sha256
            task.input_validity = InputValidity.CURRENT.value
            task.input_invalidated_at = None
            task.input_invalidated_reason = None
            task.input_invalidated_by = []
            task.state = (
                TaskState.READY.value if dependencies_current else TaskState.NEEDS_INPUT.value
            )
            task.revision += 1
            task.updated_at = now
            self._append_version(session, task, now)
            self._append_event(
                session,
                task,
                actor.id,
                event_type="task.inputs_revised",
                payload={
                    "input_version": input_version,
                    "input_snapshot_sha256": snapshot_sha256,
                    "state": task.state,
                },
                now=now,
            )
            session.flush()
            return _task_snapshot(task)

    @staticmethod
    def _actor(session: Session, actor_user_id: UUID) -> User:
        actor = session.get(User, actor_user_id)
        if actor is None:
            raise NotFoundError("Project not found")
        return actor

    @staticmethod
    def _set_context(session: Session, actor: User) -> None:
        set_rls_context(
            session,
            workspace_id=actor.workspace_id,
            user_id=actor.id,
        )

    @staticmethod
    def _project(
        session: Session,
        project_id: UUID,
        workspace_id: UUID,
        *,
        for_update: bool = False,
    ) -> Project:
        query = select(Project).where(Project.id == project_id)
        if for_update:
            query = query.with_for_update()
        project = session.scalar(query)
        if project is None or project.workspace_id != workspace_id:
            raise NotFoundError("Project not found")
        return project

    @staticmethod
    def _dependency_tasks(
        session: Session,
        project_id: UUID,
        *,
        dependency_ids: Sequence[UUID],
        task_id: UUID | None,
    ) -> list[Task]:
        unique_ids = set(dependency_ids)
        if not unique_ids:
            return []
        tasks = list(
            session.scalars(
                select(Task).where(
                    Task.project_id == project_id,
                    Task.id.in_(unique_ids),
                )
            ).all()
        )
        if len(tasks) != len(unique_ids):
            raise TaskDependencyError("Dependency task was not found in the project")
        if task_id is not None and task_id not in {task.id for task in tasks}:
            task = session.get(Task, task_id)
            if task is None or task.project_id != project_id:
                raise NotFoundError("Task not found")
            tasks.append(task)
        return tasks

    @staticmethod
    def _path_exists(
        session: Session,
        project_id: UUID,
        *,
        start: UUID,
        target: UUID,
    ) -> bool:
        edges = session.execute(
            select(
                TaskDependency.task_id,
                TaskDependency.depends_on_task_id,
            ).where(TaskDependency.project_id == project_id)
        ).all()
        graph: dict[UUID, set[UUID]] = {}
        for task_id, upstream_id in edges:
            graph.setdefault(task_id, set()).add(upstream_id)
        stack = [start]
        seen: set[UUID] = set()
        while stack:
            current = stack.pop()
            if current == target:
                return True
            if current in seen:
                continue
            seen.add(current)
            stack.extend(graph.get(current, set()))
        return False

    @staticmethod
    def _append_version(session: Session, task: Task, now: datetime) -> None:
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
                policy_bundle_id=task.policy_bundle_id,
                created_at=now,
            )
        )

    @staticmethod
    def _append_event(
        session: Session,
        task: Task,
        actor_user_id: UUID | None,
        *,
        event_type: str,
        payload: Mapping[str, object],
        now: datetime,
    ) -> None:
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
                actor_user_id=actor_user_id,
                object_type="task",
                object_id=task.id,
                object_revision=task.revision,
                payload=dict(payload),
                correlation_id=uuid4(),
                created_at=now,
            )
        )


def _digest(value: Mapping[str, object]) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _task_snapshot(task: Task) -> TaskSnapshot:
    return TaskSnapshot(
        id=task.id,
        workspace_id=task.workspace_id,
        project_id=task.project_id,
        state=TaskState(task.state),
        revision=task.revision,
        mode=task.mode,
        input_validity=InputValidity(task.input_validity),
        input_snapshot_sha256=task.input_snapshot_sha256,
        policy_bundle_id=task.policy_bundle_id,
    )


def build_task_input_snapshot(
    input_version: str,
    input_refs: Sequence[str],
    *,
    captured_at: datetime,
) -> tuple[dict[str, object], str]:
    snapshot: dict[str, object] = {
        "input_version": input_version,
        "captured_at": captured_at.isoformat(),
        "refs": [
            {
                "ref": ref,
                "declared_version": input_version,
                "ref_sha256": hashlib.sha256(ref.encode("utf-8")).hexdigest(),
            }
            for ref in input_refs
        ],
    }
    return snapshot, _digest(
        {
            "input_version": input_version,
            "refs": snapshot["refs"],
        }
    )


def require_current_task_inputs(task: Task, *, session: Session | None = None) -> None:
    if task.input_validity != InputValidity.CURRENT.value:
        raise TaskNotReadyError(
            f"Task input validity is {task.input_validity}; revise inputs before continuing"
        )
    if (
        task.input_snapshot.get("input_version") != task.input_version
        or [
            item.get("ref")
            for item in task.input_snapshot.get("refs", [])
            if isinstance(item, dict)
        ]
        != task.input_refs
    ):
        raise TaskNotReadyError("Task snapshot does not match current task inputs")
    if session is not None:
        _snapshot, current_hash = resolve_task_inputs(
            session,
            project_id=task.project_id,
            input_version=task.input_version,
            input_refs=task.input_refs,
            captured_at=datetime.fromisoformat(str(task.input_snapshot["captured_at"])),
        )
        if current_hash != task.input_snapshot_sha256:
            raise TaskNotReadyError("Resolved task inputs changed without a new revision")
    elif (
        not task.input_snapshot_sha256
        or _digest(
            {
                "input_version": task.input_snapshot["input_version"],
                "refs": task.input_snapshot["refs"],
            }
        )
        != task.input_snapshot_sha256
    ):
        raise TaskNotReadyError("Task input snapshot hash is missing or does not match")


def resolve_task_inputs(
    session: Session,
    *,
    project_id: UUID,
    input_version: str,
    input_refs: Sequence[str],
    captured_at: datetime,
) -> tuple[dict[str, object], str]:
    from medical_one_person.application.handoffs import delivery_resolution

    with delivery_resolution():
        return _resolve_task_inputs(
            session,
            project_id=project_id,
            input_version=input_version,
            input_refs=input_refs,
            captured_at=captured_at,
        )


def _resolve_task_inputs(
    session: Session,
    *,
    project_id: UUID,
    input_version: str,
    input_refs: Sequence[str],
    captured_at: datetime,
) -> tuple[dict[str, object], str]:
    entries: list[dict[str, object]] = []
    for ref in input_refs:
        if not ref.strip():
            raise TaskNotReadyError("Task input reference cannot be empty")
        kind, separator, value = ref.partition(":")
        entry: dict[str, object] = {
            "ref": ref,
            "kind": kind if separator else "opaque",
            "declared_version": input_version,
            "ref_sha256": hashlib.sha256(ref.encode("utf-8")).hexdigest(),
            "resolution_status": "declared_only",
            "object_id": None,
            "object_version": None,
            "content_sha256": None,
            "access_state": "not_applicable",
        }
        identifier: UUID | None = None
        strict_typed = {
            "document",
            "citation",
            "claim",
            "analysis",
            "deliverable",
            "decision",
            "agent_run",
        }
        if not separator:
            value = ref
            entry["resolution_status"] = "opaque_string"
        elif kind in strict_typed:
            try:
                identifier = UUID(value)
            except ValueError as exc:
                raise TaskNotReadyError(f"{kind} input reference must contain a UUID") from exc
        elif not value.strip():
            raise TaskNotReadyError(f"{kind} input reference must contain a value")
        elif kind == "opaque":
            entry["resolution_status"] = "opaque_string"
        elif kind not in {"fixture", "workflow"}:
            raise TaskNotReadyError(f"Unsupported task input reference type: {kind}")

        if kind == "fixture" and separator:
            entry["resolution_status"] = "synthetic_fixture"
        elif kind == "workflow" and separator:
            entry["resolution_status"] = "configuration_reference"
        elif kind == "decision" and identifier is not None:
            decision = session.scalar(
                select(Decision).where(
                    Decision.id == identifier,
                    Decision.project_id == project_id,
                )
            )
            if decision is None:
                raise TaskNotReadyError("Decision input reference is outside the project")
            entry.update(
                {
                    "resolution_status": "resolved",
                    "object_id": str(decision.id),
                    "object_version": str(decision.selected_opportunity_version),
                    "content_sha256": hashlib.sha256(
                        json.dumps(
                            {
                                "selected": decision.selected,
                                "reason": decision.reason,
                                "scope": decision.scope,
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        ).encode("utf-8")
                    ).hexdigest(),
                    "access_state": "active",
                }
            )
        elif kind == "agent_run" and identifier is not None:
            from medical_one_person.application.handoffs import accepted_run_payload, payload_hash

            payload = accepted_run_payload(session, project_id=project_id, run_id=identifier)
            entry.update(
                {
                    "resolution_status": "resolved",
                    "object_id": payload["task_id"],
                    "object_version": payload["run_id"],
                    "content_sha256": payload_hash(payload),
                    "access_state": "accepted",
                }
            )
        elif kind == "document" and identifier is not None:
            version = session.scalar(
                select(KnowledgeDocumentVersion).where(
                    KnowledgeDocumentVersion.id == identifier,
                    KnowledgeDocumentVersion.project_id == project_id,
                )
            )
            if version is None:
                raise TaskNotReadyError("Document input version is unavailable in the project")
            if version.version_status != "current":
                raise TaskNotReadyError(
                    f"Document input version is {version.version_status}, not current"
                )
            if version.access_state != "active":
                raise TaskNotReadyError(
                    f"Document input version is {version.access_state}, not accessible"
                )
            entry.update(
                {
                    "resolution_status": "resolved",
                    "object_id": str(version.document_id),
                    "object_version": str(version.id),
                    "content_sha256": version.content_hash,
                    "access_state": version.access_state,
                }
            )
        elif kind == "citation" and identifier is not None:
            citation = session.scalar(
                select(Citation).where(
                    Citation.id == identifier,
                    Citation.project_id == project_id,
                )
            )
            if citation is None:
                raise TaskNotReadyError("Citation input is unavailable in the project")
            if citation.review_status in {"invalid", "disputed"}:
                raise TaskNotReadyError(f"Citation input review status is {citation.review_status}")
            version = session.scalar(
                select(KnowledgeDocumentVersion).where(
                    KnowledgeDocumentVersion.id == citation.version_id,
                    KnowledgeDocumentVersion.project_id == project_id,
                )
            )
            if version is None:
                raise TaskNotReadyError(
                    "Citation input source version is unavailable in the project"
                )
            if version.version_status != "current":
                raise TaskNotReadyError(
                    f"Citation source version is {version.version_status}, not current"
                )
            if version.access_state != "active":
                raise TaskNotReadyError(
                    f"Citation source version is {version.access_state}, not accessible"
                )
            entry.update(
                {
                    "resolution_status": "resolved",
                    "object_id": str(citation.id),
                    "object_version": str(citation.version_id),
                    "content_sha256": citation.content_sha256,
                    "access_state": "active",
                }
            )
        elif kind == "claim" and identifier is not None:
            claim = session.scalar(
                select(ClaimVersion).where(
                    ClaimVersion.id == identifier,
                    ClaimVersion.project_id == project_id,
                )
            )
            if claim is None:
                raise TaskNotReadyError("Claim input is unavailable in the project")
            if claim.status in {"stale", "disputed"}:
                raise TaskNotReadyError(f"Claim input status is {claim.status}")
            entry.update(
                {
                    "resolution_status": "resolved",
                    "object_id": str(claim.claim_id),
                    "object_version": str(claim.id),
                    "content_sha256": hashlib.sha256(claim.statement.encode("utf-8")).hexdigest(),
                    "access_state": claim.status,
                }
            )
        elif kind == "analysis" and identifier is not None:
            analysis = session.scalar(
                select(AnalysisRun).where(
                    AnalysisRun.id == identifier,
                    AnalysisRun.project_id == project_id,
                )
            )
            if analysis is None:
                raise TaskNotReadyError("Analysis input is unavailable in the project")
            if analysis.state != "succeeded":
                raise TaskNotReadyError(f"Analysis input state is {analysis.state}")
            entry.update(
                {
                    "resolution_status": "resolved",
                    "object_id": str(analysis.id),
                    "object_version": str(analysis.analysis_version),
                    "content_sha256": analysis.output_sha256,
                    "access_state": analysis.state,
                }
            )
        elif kind == "deliverable" and identifier is not None:
            deliverable = session.scalar(
                select(ExternalDeliverable).where(
                    ExternalDeliverable.id == identifier,
                    ExternalDeliverable.project_id == project_id,
                )
            )
            if deliverable is None:
                raise TaskNotReadyError("Deliverable input is unavailable in the project")
            if deliverable.state not in {"received", "under_review", "accepted"}:
                raise TaskNotReadyError(f"Deliverable input state is {deliverable.state}")
            entry.update(
                {
                    "resolution_status": "resolved",
                    "object_id": str(deliverable.id),
                    "object_version": str(deliverable.revision),
                    "content_sha256": hashlib.sha256(
                        json.dumps(
                            deliverable.manifest,
                            ensure_ascii=False,
                            sort_keys=True,
                        ).encode("utf-8")
                    ).hexdigest(),
                    "access_state": deliverable.state,
                }
            )
        entries.append(entry)
    semantic = {
        "input_version": input_version,
        "refs": entries,
    }
    snapshot: dict[str, object] = {
        **semantic,
        "captured_at": captured_at.isoformat(),
    }
    return snapshot, _digest(semantic)


def invalidate_task_inputs(
    session: Session,
    *,
    project_id: UUID,
    task_ids: Sequence[UUID],
    actor_user_id: UUID | None,
    reason: str,
    now: datetime,
) -> list[UUID]:
    frontier = list(dict.fromkeys(task_ids))
    visited: set[UUID] = set()
    invalidated: list[UUID] = []
    while frontier:
        current_id = frontier.pop(0)
        if current_id in visited:
            continue
        visited.add(current_id)
        task = session.scalar(
            select(Task)
            .where(Task.id == current_id, Task.project_id == project_id)
            .with_for_update()
        )
        if task is None or task.state == TaskState.CANCELLED.value:
            continue
        if task.input_validity != InputValidity.STALE.value:
            task.state = TaskState.NEEDS_INPUT.value
            task.input_validity = InputValidity.STALE.value
            task.input_invalidated_at = now
            task.input_invalidated_reason = reason
            task.input_invalidated_by = [reason]
            task.revision += 1
            task.updated_at = now
            TaskService._append_version(session, task, now)
            TaskService._append_event(
                session,
                task,
                actor_user_id,
                event_type="task.input_invalidated",
                payload={
                    "state": task.state,
                    "input_validity": task.input_validity,
                    "reason": reason,
                },
                now=now,
            )
            invalidated.append(task.id)
        frontier.extend(
            session.scalars(
                select(TaskDependency.task_id).where(
                    TaskDependency.project_id == project_id,
                    TaskDependency.depends_on_task_id == task.id,
                )
            ).all()
        )
    return invalidated
