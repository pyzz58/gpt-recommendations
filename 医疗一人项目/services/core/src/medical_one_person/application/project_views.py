from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import AgentRoleConfig
from medical_one_person.application.errors import NotFoundError
from medical_one_person.domain.projects import ProjectSnapshot, ProjectStage, ProjectStatus
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    AgentInstance,
    AgentRun,
    Decision,
    KnowledgeDocumentVersion,
    Opportunity,
    Project,
    ProjectEvent,
    Task,
    TaskDependency,
    User,
)

OPEN_TASK_STATES = (
    "draft",
    "needs_input",
    "ready",
    "queued",
    "running",
    "submitted",
    "rework",
    "waiting_external",
    "paused",
    "failed",
)
ACTION_TASK_STATES = ("needs_input", "submitted", "rework", "failed")


class ProjectListItem(BaseModel):
    project: ProjectSnapshot
    open_tasks: int
    documents: int
    opportunities: int


class ProjectCounts(BaseModel):
    tasks: int
    open_tasks: int
    documents: int
    opportunities: int
    active_agents: int


class ActionRequired(BaseModel):
    kind: str
    object_id: UUID
    title: str
    detail: str
    state: str


class OpportunitySummary(BaseModel):
    id: UUID
    title: str
    track: str
    status: str
    current_version: int
    revision: int


class EventView(BaseModel):
    event_id: UUID
    project_seq: int
    project_id: UUID
    type: str
    object_type: str
    object_id: UUID
    object_revision: int
    actor_user_id: UUID | None
    payload: dict[str, Any]
    correlation_id: UUID
    occurred_at: datetime


class ProjectOverview(BaseModel):
    project: ProjectSnapshot
    counts: ProjectCounts
    current_direction: OpportunitySummary | None
    current_selection_decision_id: UUID | None
    opportunities: list[OpportunitySummary]
    action_required: list[ActionRequired]
    recent_events: list[EventView]


class TaskView(BaseModel):
    id: UUID
    task_type: str
    purpose: str
    assignee_role: str
    goal: str
    state: str
    mode: str
    revision: int
    input_version: str
    input_refs: list[str]
    input_validity: str
    input_snapshot_sha256: str | None
    policy_bundle_id: str | None
    input_invalidated_at: datetime | None
    input_invalidated_reason: str | None
    deliverable_schema: str
    acceptance_policy: str
    dependencies: list[UUID]
    created_at: datetime
    updated_at: datetime


class AgentRunSummary(BaseModel):
    id: UUID
    state: str
    mode: str
    provider_id: str
    model_id: str
    policy_bundle_id: str | None
    created_at: datetime
    ended_at: datetime | None


class AgentSceneView(BaseModel):
    role_id: str
    name: str
    version: int
    reports_to: list[str]
    responsibilities: list[str]
    deliverable_types: list[str]
    scene_state: str
    instance_state: str
    latest_task_id: UUID | None
    latest_task_goal: str | None
    latest_task_state: str | None
    latest_run: AgentRunSummary | None
    updated_at: datetime | None


class WorkspaceReader:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        roles: dict[str, AgentRoleConfig],
    ) -> None:
        self._session_factory = session_factory
        self._roles = roles

    def list_projects(self, *, actor_user_id: UUID) -> list[ProjectListItem]:
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            projects = session.scalars(
                select(Project)
                .where(Project.workspace_id == actor.workspace_id)
                .order_by(Project.updated_at.desc(), Project.id)
            ).all()
            return [
                ProjectListItem(
                    project=_project_snapshot(project),
                    open_tasks=int(
                        session.scalar(
                            select(func.count())
                            .select_from(Task)
                            .where(
                                Task.project_id == project.id,
                                Task.state.in_(OPEN_TASK_STATES),
                            )
                        )
                        or 0
                    ),
                    documents=int(
                        session.scalar(
                            select(func.count())
                            .select_from(KnowledgeDocumentVersion)
                            .where(
                                KnowledgeDocumentVersion.project_id == project.id,
                                KnowledgeDocumentVersion.version_status == "current",
                                KnowledgeDocumentVersion.access_state == "active",
                            )
                        )
                        or 0
                    ),
                    opportunities=int(
                        session.scalar(
                            select(func.count())
                            .select_from(Opportunity)
                            .where(Opportunity.project_id == project.id)
                        )
                        or 0
                    ),
                )
                for project in projects
            ]

    def get_project(self, *, actor_user_id: UUID, project_id: UUID) -> ProjectSnapshot:
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            return _project_snapshot(project)

    def overview(self, *, actor_user_id: UUID, project_id: UUID) -> ProjectOverview:
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            tasks = session.scalars(
                select(Task).where(Task.project_id == project.id).order_by(Task.updated_at.desc())
            ).all()
            documents = int(
                session.scalar(
                    select(func.count())
                    .select_from(KnowledgeDocumentVersion)
                    .where(
                        KnowledgeDocumentVersion.project_id == project.id,
                        KnowledgeDocumentVersion.version_status == "current",
                        KnowledgeDocumentVersion.access_state == "active",
                    )
                )
                or 0
            )
            opportunities = session.scalars(
                select(Opportunity)
                .where(Opportunity.project_id == project.id)
                .order_by(Opportunity.updated_at.desc())
            ).all()
            active_agents = int(
                session.scalar(
                    select(func.count())
                    .select_from(AgentInstance)
                    .where(
                        AgentInstance.project_id == project.id,
                        AgentInstance.status == "active",
                    )
                )
                or 0
            )
            events = session.scalars(
                select(ProjectEvent)
                .where(ProjectEvent.project_id == project.id)
                .order_by(ProjectEvent.project_seq.desc())
                .limit(12)
            ).all()
            open_tasks = [task for task in tasks if task.state in OPEN_TASK_STATES]
            action_tasks = [task for task in tasks if task.state in ACTION_TASK_STATES]
            actions = [
                ActionRequired(
                    kind="task",
                    object_id=task.id,
                    title=task.goal,
                    detail=f"{task.assignee_role} · {task.task_type}",
                    state=task.state,
                )
                for task in action_tasks
            ]
            selected = next(
                (item for item in opportunities if item.status == "selected"),
                None,
            )
            current_decision = session.scalar(
                select(Decision)
                .where(
                    Decision.project_id == project.id,
                    Decision.kind == "opportunity_selection",
                )
                .order_by(Decision.effective_at.desc(), Decision.created_at.desc())
                .limit(1)
            )
            return ProjectOverview(
                project=_project_snapshot(project),
                counts=ProjectCounts(
                    tasks=len(tasks),
                    open_tasks=len(open_tasks),
                    documents=documents,
                    opportunities=len(opportunities),
                    active_agents=active_agents,
                ),
                current_direction=(
                    _opportunity_summary(selected) if selected is not None else None
                ),
                current_selection_decision_id=(
                    current_decision.id
                    if current_decision is not None and selected is not None
                    else None
                ),
                opportunities=[_opportunity_summary(item) for item in opportunities],
                action_required=actions,
                recent_events=[_event_view(item) for item in events],
            )

    def list_tasks(self, *, actor_user_id: UUID, project_id: UUID) -> list[TaskView]:
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            tasks = session.scalars(
                select(Task).where(Task.project_id == project.id).order_by(Task.updated_at.desc())
            ).all()
            dependencies = session.execute(
                select(TaskDependency.task_id, TaskDependency.depends_on_task_id).where(
                    TaskDependency.project_id == project.id
                )
            ).all()
            dependency_map: dict[UUID, list[UUID]] = {}
            for task_id, upstream_id in dependencies:
                dependency_map.setdefault(task_id, []).append(upstream_id)
            return [_task_view(task, dependency_map.get(task.id, [])) for task in tasks]

    def list_agents(
        self,
        *,
        actor_user_id: UUID,
        project_id: UUID,
    ) -> list[AgentSceneView]:
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            tasks = session.scalars(
                select(Task).where(Task.project_id == project.id).order_by(Task.updated_at.desc())
            ).all()
            instances = {
                item.role_id: item
                for item in session.scalars(
                    select(AgentInstance).where(AgentInstance.project_id == project.id)
                )
            }
            runs = session.execute(
                select(AgentRun, AgentInstance)
                .join(AgentInstance, AgentInstance.id == AgentRun.agent_instance_id)
                .where(AgentRun.project_id == project.id)
                .order_by(AgentRun.created_at.desc())
            ).all()
            latest_task: dict[str, Task] = {}
            for task_row in tasks:
                latest_task.setdefault(task_row.assignee_role, task_row)
            latest_run: dict[str, AgentRun] = {}
            for run_record, instance_record in runs:
                latest_run.setdefault(instance_record.role_id, run_record)

            result: list[AgentSceneView] = []
            for role_id in sorted(self._roles):
                role = self._roles[role_id]
                latest_task_row = latest_task.get(role_id)
                instance_row = instances.get(role_id)
                run_row = latest_run.get(role_id)
                result.append(
                    AgentSceneView(
                        role_id=role.role_id,
                        name=role.name,
                        version=role.version,
                        reports_to=role.reports_to,
                        responsibilities=role.responsibilities,
                        deliverable_types=role.deliverable_types,
                        scene_state=(
                            latest_task_row.state if latest_task_row is not None else "unassigned"
                        ),
                        instance_state=(
                            instance_row.status if instance_row is not None else "inactive"
                        ),
                        latest_task_id=(
                            latest_task_row.id if latest_task_row is not None else None
                        ),
                        latest_task_goal=(
                            latest_task_row.goal if latest_task_row is not None else None
                        ),
                        latest_task_state=(
                            latest_task_row.state if latest_task_row is not None else None
                        ),
                        latest_run=(
                            AgentRunSummary(
                                id=run_row.id,
                                state=run_row.state,
                                mode=run_row.mode,
                                provider_id=run_row.provider_id,
                                model_id=run_row.model_id,
                                policy_bundle_id=run_row.policy_bundle_id,
                                created_at=run_row.created_at,
                                ended_at=run_row.ended_at,
                            )
                            if run_row is not None
                            else None
                        ),
                        updated_at=(
                            latest_task_row.updated_at if latest_task_row is not None else None
                        ),
                    )
                )
            return result

    def events(
        self,
        *,
        actor_user_id: UUID,
        project_id: UUID,
        after: int,
        limit: int = 100,
    ) -> list[EventView]:
        if after < 0:
            raise ValueError("Event cursor cannot be negative")
        if not 1 <= limit <= 500:
            raise ValueError("Event limit must be between 1 and 500")
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            rows = session.scalars(
                select(ProjectEvent)
                .where(
                    ProjectEvent.project_id == project.id,
                    ProjectEvent.project_seq > after,
                )
                .order_by(ProjectEvent.project_seq)
                .limit(limit)
            ).all()
            return [_event_view(item) for item in rows]


def _actor(session: Session, actor_user_id: UUID) -> User:
    actor = session.get(User, actor_user_id)
    if actor is None:
        raise NotFoundError("User not found")
    return actor


def _project(session: Session, project_id: UUID, workspace_id: UUID) -> Project:
    project = session.get(Project, project_id)
    if project is None or project.workspace_id != workspace_id:
        raise NotFoundError("Project not found")
    return project


def _project_snapshot(project: Project) -> ProjectSnapshot:
    return ProjectSnapshot(
        id=project.id,
        workspace_id=project.workspace_id,
        name=project.name,
        scope=project.scope,
        stage=ProjectStage(project.stage),
        status=ProjectStatus(project.status),
        revision=project.revision,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _opportunity_summary(opportunity: Opportunity) -> OpportunitySummary:
    return OpportunitySummary(
        id=opportunity.id,
        title=opportunity.title,
        track=opportunity.track,
        status=opportunity.status,
        current_version=opportunity.current_version,
        revision=opportunity.revision,
    )


def _event_view(event: ProjectEvent) -> EventView:
    return EventView(
        event_id=event.id,
        project_seq=event.project_seq,
        project_id=event.project_id,
        type=event.type,
        object_type=event.object_type,
        object_id=event.object_id,
        object_revision=event.object_revision,
        actor_user_id=event.actor_user_id,
        payload=event.payload,
        correlation_id=event.correlation_id,
        occurred_at=event.created_at,
    )


def _task_view(task: Task, dependencies: list[UUID]) -> TaskView:
    return TaskView(
        id=task.id,
        task_type=task.task_type,
        purpose=task.purpose,
        assignee_role=task.assignee_role,
        goal=task.goal,
        state=task.state,
        mode=task.mode,
        revision=task.revision,
        input_version=task.input_version,
        input_refs=task.input_refs,
        input_validity=task.input_validity,
        input_snapshot_sha256=task.input_snapshot_sha256,
        policy_bundle_id=task.policy_bundle_id,
        input_invalidated_at=task.input_invalidated_at,
        input_invalidated_reason=task.input_invalidated_reason,
        deliverable_schema=task.deliverable_schema,
        acceptance_policy=task.acceptance_policy,
        dependencies=sorted(dependencies, key=str),
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
