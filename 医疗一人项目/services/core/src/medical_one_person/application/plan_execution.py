from __future__ import annotations

import hashlib
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import AgentRoleConfig
from medical_one_person.agents.runner import AgentRunner
from medical_one_person.application.errors import NotFoundError, PlanStateError
from medical_one_person.application.scheduling import JobQueue, OutboxDispatcher
from medical_one_person.domain.tasks import TaskState
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    AgentRun,
    Plan,
    PlanNode,
    Project,
    Task,
    User,
)
from medical_one_person.providers import FakeModelProvider


class ExecutedTaskView(BaseModel):
    task_id: UUID
    role_id: str
    task_state: TaskState
    run_id: UUID
    run_state: str


class PlanExecutionView(BaseModel):
    plan_id: UUID
    executed: list[ExecutedTaskView]


class MockPlanExecutor:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        roles: dict[str, AgentRoleConfig],
        *,
        theory_hash: str,
    ) -> None:
        self._session_factory = session_factory
        self._roles = roles
        self._theory_hash = theory_hash

    def execute_ready(
        self,
        *,
        project_id: UUID,
        plan_id: UUID,
        actor_user_id: UUID,
        max_tasks: int = 4,
    ) -> PlanExecutionView:
        if not 1 <= max_tasks <= 10:
            raise ValueError("max_tasks must be between 1 and 10")
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(
                session,
                workspace_id=actor.workspace_id,
                user_id=actor.id,
            )
            project = session.get(Project, project_id)
            plan = session.scalar(
                select(Plan).where(Plan.id == plan_id, Plan.project_id == project_id)
            )
            if project is None or plan is None:
                raise NotFoundError("Plan not found")
            if plan.status != "active":
                raise PlanStateError("Only an active plan can execute mock tasks")
            task_ids = list(
                session.scalars(
                    select(PlanNode.task_id).where(
                        PlanNode.plan_id == plan.id,
                        PlanNode.project_id == project.id,
                    )
                )
            )
            workspace_id = actor.workspace_id

        OutboxDispatcher(self._session_factory).dispatch_once(
            workspace_id=workspace_id,
        )
        queue = JobQueue(self._session_factory)
        runner = AgentRunner(
            self._session_factory,
            FakeModelProvider(),
            self._roles,
            theory_hash=self._theory_hash,
            job_queue=queue,
        )
        executed: list[ExecutedTaskView] = []
        for index in range(max_tasks):
            claim = queue.claim(
                workspace_id=workspace_id,
                worker_id=f"w11-mock-{hashlib.sha256(plan_id.bytes).hexdigest()[:8]}-{index}",
                lease_seconds=60,
                task_ids=set(task_ids),
            )
            if claim is None:
                break
            delivery = runner.run_claim(claim)
            with self._session_factory.begin() as session:
                set_rls_context(
                    session,
                    workspace_id=workspace_id,
                    user_id=actor_user_id,
                )
                task = session.get(Task, claim.task_id)
                run = session.scalar(
                    select(AgentRun)
                    .where(
                        AgentRun.task_id == claim.task_id,
                        AgentRun.role_id == delivery.role_id,
                    )
                    .order_by(AgentRun.created_at.desc())
                    .limit(1)
                )
                if task is None or run is None:
                    raise NotFoundError("Executed task or run not found")
                executed.append(
                    ExecutedTaskView(
                        task_id=task.id,
                        role_id=delivery.role_id,
                        task_state=TaskState(task.state),
                        run_id=run.id,
                        run_state=run.state,
                    )
                )
        return PlanExecutionView(plan_id=plan_id, executed=executed)


def _owner(session: Session, actor_user_id: UUID) -> User:
    actor = session.get(User, actor_user_id)
    if actor is None:
        raise NotFoundError("User not found")
    if not actor.is_owner:
        raise PermissionError("Only the verified workspace owner can execute plans")
    return actor
