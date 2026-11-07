from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import load_role_configs
from medical_one_person.agents.runner import AgentRunner
from medical_one_person.application.budgets import BudgetService
from medical_one_person.application.errors import BudgetExceededError
from medical_one_person.application.projects import ProjectService
from medical_one_person.application.reliability import ReliabilityService
from medical_one_person.application.scheduling import JobQueue, OutboxDispatcher
from medical_one_person.application.tasks import TaskService
from medical_one_person.config import Settings
from medical_one_person.contracts import DependencyStatus
from medical_one_person.infrastructure.bootstrap import bootstrap_local_owner
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import Job
from medical_one_person.main import create_app
from medical_one_person.providers import FakeModelProvider

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _project_and_task(
    session_factory: sessionmaker[Session],
    *,
    suffix: str,
    purpose: str,
):
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name=f"W20可靠性{suffix}",
        scope="验证全链审计、预算上界、性能和故障恢复。",
        idempotency_key=f"w20-project-{suffix}",
    )
    task = TaskService(session_factory).create_task(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_type="reliability.verification",
        purpose=purpose,
        assignee_role="A02",
        role_version="1",
        input_version="v1",
        input_refs=[f"fixture:{purpose}"],
        goal="验证W20可靠性门。",
        deliverable_schema="agent_delivery.v1",
        acceptance_policy="independent_review.v1",
    )
    return identity, project, task


def test_reliability_report_passes_complete_mock_chain(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project, task = _project_and_task(
        session_factory,
        suffix="通过",
        purpose="complete-chain",
    )
    tasks = TaskService(session_factory)
    tasks.enqueue(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_id=task.id,
    )
    OutboxDispatcher(session_factory).dispatch_once(workspace_id=identity.workspace_id)
    queue = JobQueue(session_factory)
    claim = queue.claim(
        workspace_id=identity.workspace_id,
        worker_id="w20-complete",
    )
    assert claim is not None
    budgets = BudgetService(session_factory)
    budget = budgets.create(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        name="w20",
        currency="USD",
        limit_amount=Decimal("10"),
    )
    reservation = budgets.reserve(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        budget_id=budget.id,
        amount=Decimal("2"),
        operation_key="w20-complete-reserve",
        task_id=task.id,
        job_id=claim.job_id,
    )
    runner = AgentRunner(
        session_factory,
        FakeModelProvider(),
        load_role_configs(PROJECT_ROOT / "config" / "agents" / "roles.yaml"),
        theory_hash="0" * 64,
        job_queue=queue,
    )
    runner.run_claim(claim)
    budgets.settle(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        reservation_id=reservation.id,
        actual_amount=Decimal("1.25"),
        ledger_key="w20-complete-settle",
    )

    report = ReliabilityService(session_factory).evaluate(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
    )
    assert report.status == "passed"
    assert report.findings == []
    assert report.metrics.succeeded_agent_runs == 1
    assert report.metrics.budget_spent == "1.250000"
    assert report.metrics.uncertain_budget_reservations == 0
    assert report.metrics.task_list_p95_ms < 500


def test_reliability_report_blocks_expired_lease_and_uncertain_cost(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project, task = _project_and_task(
        session_factory,
        suffix="阻断",
        purpose="expired-and-uncertain",
    )
    tasks = TaskService(session_factory)
    tasks.enqueue(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_id=task.id,
    )
    OutboxDispatcher(session_factory).dispatch_once(workspace_id=identity.workspace_id)
    queue = JobQueue(session_factory)
    claim = queue.claim(
        workspace_id=identity.workspace_id,
        worker_id="w20-blocked",
    )
    assert claim is not None
    with session_factory.begin() as session:
        set_rls_context(session, workspace_id=identity.workspace_id, user_id=None)
        job = session.get(Job, claim.job_id)
        assert job is not None
        job.lease_until = datetime.now(UTC) - timedelta(seconds=1)
    budgets = BudgetService(session_factory)
    budget = budgets.create(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        name="w20",
        currency="USD",
        limit_amount=Decimal("10"),
    )
    reservation = budgets.reserve(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        budget_id=budget.id,
        amount=Decimal("3"),
        operation_key="w20-uncertain-reserve",
        task_id=task.id,
        job_id=claim.job_id,
    )
    budgets.mark_uncertain(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        reservation_id=reservation.id,
    )

    report = ReliabilityService(session_factory).evaluate(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
    )
    codes = {finding.code for finding in report.findings}
    assert report.status == "blocked"
    assert "EXPIRED_RUNNING_LEASE" in codes
    assert "BUDGET_OUTCOME_UNCERTAIN" in codes
    assert report.metrics.expired_leases == 1
    assert report.metrics.uncertain_budget_reservations == 1


def test_budget_upper_bound_under_parallel_reservations(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project, _task = _project_and_task(
        session_factory,
        suffix="预算压力",
        purpose="parallel-budget",
    )
    budgets = BudgetService(session_factory)
    budget = budgets.create(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        name="stress",
        currency="USD",
        limit_amount=Decimal("20"),
    )

    def reserve(index: int) -> bool:
        try:
            budgets.reserve(
                project_id=project.id,
                actor_user_id=identity.owner_user_id,
                budget_id=budget.id,
                amount=Decimal("1"),
                operation_key=f"stress-{index}",
            )
        except BudgetExceededError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=12) as executor:
        outcomes = list(executor.map(reserve, range(30)))
    assert sum(outcomes) == 20
    assert sum(not item for item in outcomes) == 10


def test_w20_reliability_api_persists_report(
    session_factory: sessionmaker[Session],
    app_database_url: str,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_mode="mock",
        environment="development",
        database_url=app_database_url,
        artifact_root=tmp_path / "artifacts",
        knowledge_staging_root=tmp_path / "staging",
        run_root=tmp_path / "runs",
    )
    app = create_app(
        database_checker=lambda: DependencyStatus(
            status="ready",
            detail="W20 API integration",
        ),
        settings_override=settings,
        session_factory_override=session_factory,
    )
    client = TestClient(app, base_url="http://127.0.0.1:3000")
    assert client.post("/api/v1/system/local-session").status_code == 200
    project = client.post(
        "/api/v1/projects",
        headers={"Idempotency-Key": "w20-api-project"},
        json={"name": "W20 API可靠性", "scope": "验证可靠性报告API。"},
    )
    assert project.status_code == 201, project.text
    evaluated = client.post(
        f"/api/v1/projects/{project.json()['id']}/reliability/evaluate"
    )
    assert evaluated.status_code == 201, evaluated.text
    assert evaluated.json()["status"] == "passed"
    latest = client.get(f"/api/v1/projects/{project.json()['id']}/reliability")
    assert latest.status_code == 200
    assert latest.json()["latest"]["id"] == evaluated.json()["id"]


def test_w20_reliability_table_uses_forced_rls(database: Engine) -> None:
    with database.connect() as connection:
        policies = connection.scalar(
            text("SELECT count(*) FROM pg_policies WHERE schemaname = 'public'")
        )
        table = connection.execute(
            text(
                """
                SELECT relrowsecurity, relforcerowsecurity
                FROM pg_class
                WHERE oid = 'reliability_evaluations'::regclass
                """
            )
        ).one()
    assert policies == 84
    assert table.relrowsecurity and table.relforcerowsecurity
