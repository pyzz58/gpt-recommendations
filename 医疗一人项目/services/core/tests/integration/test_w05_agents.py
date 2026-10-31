from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import load_role_configs
from medical_one_person.agents.runner import AgentRunner
from medical_one_person.application.errors import AgentOutputValidationError
from medical_one_person.application.projects import ProjectService
from medical_one_person.application.scheduling import JobQueue, OutboxDispatcher
from medical_one_person.application.tasks import TaskService
from medical_one_person.infrastructure.bootstrap import bootstrap_local_owner
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    AgentInstance,
    AgentRun,
    Job,
    Task,
)
from medical_one_person.providers.base import (
    ModelUsage,
    ProviderCapabilities,
    StructuredGenerationRequest,
    StructuredGenerationResponse,
)
from medical_one_person.providers.fake import FakeModelProvider


def _roles():
    path = Path(__file__).resolve().parents[4] / "config" / "agents" / "roles.yaml"
    return load_role_configs(path)


def _project_and_task(
    session_factory: sessionmaker[Session],
    *,
    role_id: str,
    purpose: str,
):
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name=f"W05 {role_id} 项目",
        scope="W05独立岗位上下文测试。",
        idempotency_key=f"create-w05-{role_id}",
    )
    task = TaskService(session_factory).create_task(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_type=f"{role_id}.synthetic",
        purpose=purpose,
        assignee_role=role_id,
        role_version="1",
        input_version=f"v1:{purpose}",
        input_refs=[f"fixture:{purpose}"],
        goal="生成明确的模拟岗位交付。",
        deliverable_schema="agent_delivery.v1",
        acceptance_policy="independent_review.v1",
        mode="mock",
    )
    return identity, project, task


def test_runner_persists_independent_outputs_without_auto_acceptance(
    session_factory: sessionmaker[Session],
) -> None:
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="四岗独立输出项目",
        scope="验证首席、运营、质量和反证意见分别保存。",
        idempotency_key="create-four-role-project",
    )
    task_service = TaskService(session_factory)
    role_ids = ("A02", "A03", "A25", "A26")
    tasks = []
    for role_id in role_ids:
        task = task_service.create_task(
            project_id=project.id,
            actor_user_id=identity.owner_user_id,
            task_type=f"{role_id}.synthetic",
            purpose=f"purpose-{role_id}",
            assignee_role=role_id,
            role_version="1",
            input_version=f"v1:{role_id}",
            input_refs=[f"fixture:{role_id}"],
            goal="生成模拟岗位意见。",
            deliverable_schema="agent_delivery.v1",
            acceptance_policy="independent_review.v1",
            mode="mock",
        )
        tasks.append(task)
        task_service.enqueue(
            project_id=project.id,
            actor_user_id=identity.owner_user_id,
            task_id=task.id,
        )

    OutboxDispatcher(session_factory).dispatch_once(workspace_id=identity.workspace_id)
    queue = JobQueue(session_factory)
    runner = AgentRunner(
        session_factory,
        FakeModelProvider(),
        _roles(),
        theory_hash="a" * 64,
        job_queue=queue,
    )
    deliveries = []
    while claim := queue.claim(
        workspace_id=identity.workspace_id,
        worker_id="worker-w05",
    ):
        deliveries.append(runner.run_claim(claim))

    assert sorted(delivery.role_id for delivery in deliveries) == sorted(role_ids)
    assert all(delivery.mode == "mock" for delivery in deliveries)
    independent = {delivery.role_id: delivery.independent_review for delivery in deliveries}
    assert independent == {
        "A02": False,
        "A03": False,
        "A25": True,
        "A26": True,
    }

    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        instances = session.scalars(select(AgentInstance).order_by(AgentInstance.role_id)).all()
        runs = session.scalars(select(AgentRun).order_by(AgentRun.role_id)).all()
        stored_tasks = session.scalars(select(Task).order_by(Task.assignee_role)).all()
        jobs = session.scalars(select(Job)).all()
    assert [instance.role_id for instance in instances] == list(role_ids)
    assert len({instance.context_namespace for instance in instances}) == 4
    assert sorted(run.role_id for run in runs) == sorted(role_ids)
    assert [run.state for run in runs] == ["succeeded"] * 4
    assert all(run.output is not None for run in runs)
    assert [task.state for task in stored_tasks] == ["submitted"] * 4
    assert all(job.state == "succeeded" for job in jobs)


def test_all_26_roles_can_be_dispatched_and_produce_schema_valid_output(
    session_factory: sessionmaker[Session],
) -> None:
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="26岗合同项目",
        scope="逐一验证岗位加载、任务派发和模拟结构化输出。",
        idempotency_key="create-all-role-project",
    )
    service = TaskService(session_factory)
    for role_id in sorted(_roles()):
        task = service.create_task(
            project_id=project.id,
            actor_user_id=identity.owner_user_id,
            task_type=f"{role_id}.contract",
            purpose=f"contract-{role_id}",
            assignee_role=role_id,
            role_version="1",
            input_version=f"contract-v1:{role_id}",
            input_refs=[f"fixture:role-contract:{role_id}"],
            goal="生成岗位合同模拟交付。",
            deliverable_schema="agent_delivery.v1",
            acceptance_policy="independent_review.v1",
            mode="mock",
        )
        service.enqueue(
            project_id=project.id,
            actor_user_id=identity.owner_user_id,
            task_id=task.id,
        )

    created_jobs = OutboxDispatcher(session_factory).dispatch_once(
        workspace_id=identity.workspace_id,
        limit=40,
    )
    assert len(created_jobs) == 26
    queue = JobQueue(session_factory)
    runner = AgentRunner(
        session_factory,
        FakeModelProvider(),
        _roles(),
        theory_hash="c" * 64,
        job_queue=queue,
    )
    delivered_roles = []
    while claim := queue.claim(
        workspace_id=identity.workspace_id,
        worker_id="worker-all-roles",
        lease_seconds=60,
    ):
        delivery = runner.run_claim(claim)
        delivered_roles.append(delivery.role_id)

    assert set(delivered_roles) == set(_roles())
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        assert session.scalar(select(func.count()).select_from(AgentInstance)) == 26
        assert session.scalar(select(func.count()).select_from(AgentRun)) == 26
        assert (
            session.scalar(select(func.count()).select_from(Task).where(Task.state == "submitted"))
            == 26
        )


class _WrongRoleProvider(FakeModelProvider):
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_id="wrong-role-fake",
            mode="mock",
            structured_output=True,
            streaming=False,
            max_context_tokens=1000,
        )

    def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResponse:
        response = super().generate_structured(request)
        response.output["role_id"] = "A99"
        return StructuredGenerationResponse(
            provider_id=self.provider_id,
            model_id="wrong-role-fake",
            mode="mock",
            output=response.output,
            usage=ModelUsage(
                input_tokens=1,
                output_tokens=1,
                estimated_cost=Decimal("0"),
                currency="USD",
            ),
            finish_reason="stop",
        )


def test_runner_rejects_wrong_role_and_fails_job_without_acceptance(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project, task = _project_and_task(
        session_factory, role_id="A26", purpose="wrong-role"
    )
    service = TaskService(session_factory)
    service.enqueue(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_id=task.id,
    )
    OutboxDispatcher(session_factory).dispatch_once(workspace_id=identity.workspace_id)
    queue = JobQueue(session_factory)
    claim = queue.claim(workspace_id=identity.workspace_id, worker_id="worker-bad")
    assert claim is not None
    runner = AgentRunner(
        session_factory,
        _WrongRoleProvider(),
        _roles(),
        theory_hash="b" * 64,
        job_queue=queue,
        max_schema_repairs=0,
    )

    with pytest.raises(AgentOutputValidationError):
        runner.run_claim(claim)

    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        stored_task = session.get(Task, task.id)
        run = session.scalar(select(AgentRun))
        job = session.scalar(select(Job))
    assert stored_task is not None and stored_task.state == "failed"
    assert run is not None and run.state == "failed"
    assert job is not None and job.state == "failed"
