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
from medical_one_person.domain.tasks import TaskSnapshot, TaskState
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    OutboxMessage,
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
                input_version=input_version,
                input_refs=list(input_refs),
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
            session.scalar(select(Project).where(Project.id == project_id).with_for_update())
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
            session.scalar(select(Project).where(Project.id == project_id).with_for_update())
            task = session.scalar(
                select(Task)
                .where(Task.id == task_id, Task.project_id == project_id)
                .with_for_update()
            )
            if task is None:
                raise NotFoundError("Task not found")
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
            frontier = [upstream_task_id]
            visited: set[UUID] = set()
            invalidated: list[UUID] = []
            now = datetime.now(UTC)
            while frontier:
                upstream_id = frontier.pop()
                if upstream_id in visited:
                    continue
                visited.add(upstream_id)
                dependents = session.scalars(
                    select(Task)
                    .join(TaskDependency, TaskDependency.task_id == Task.id)
                    .where(
                        TaskDependency.project_id == project_id,
                        TaskDependency.depends_on_task_id == upstream_id,
                    )
                    .with_for_update()
                ).all()
                for dependent in dependents:
                    frontier.append(dependent.id)
                    if dependent.state in {
                        TaskState.ACCEPTED.value,
                        TaskState.CANCELLED.value,
                    }:
                        continue
                    if dependent.state != TaskState.NEEDS_INPUT.value:
                        dependent.state = TaskState.NEEDS_INPUT.value
                        dependent.revision += 1
                        dependent.updated_at = now
                        self._append_version(session, dependent, now)
                        self._append_event(
                            session,
                            dependent,
                            actor.id,
                            event_type="task.upstream_changed",
                            payload={"upstream_task_id": str(upstream_id)},
                            now=now,
                        )
                    invalidated.append(dependent.id)
            session.flush()
            return invalidated

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
                role_version=task.role_version,
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
    )
