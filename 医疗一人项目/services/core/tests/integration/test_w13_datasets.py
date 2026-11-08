from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import load_role_configs
from medical_one_person.application.datasets import DatasetService
from medical_one_person.application.errors import ReviewPolicyError
from medical_one_person.application.projects import ProjectService
from medical_one_person.domain.datasets import (
    CleaningSpec,
    StatisticalMethod,
    StatisticalPlanSpec,
)
from medical_one_person.domain.plans import (
    FindingSeverity,
    ReviewDecision,
    ReviewFinding,
)
from medical_one_person.infrastructure.artifacts import LocalArtifactStore
from medical_one_person.infrastructure.bootstrap import bootstrap_local_owner
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    AnalysisReview,
    AnalysisRun,
    Dataset,
)
from medical_one_person.infrastructure.knowledge.upload import UploadService

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _setup(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
):
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="W13合成统计项目",
        scope="验证不可变数据版本、清理、统计计划和复核。",
        idempotency_key="create-w13-project",
    )
    store = LocalArtifactStore(tmp_path / "objects")
    uploads = UploadService(
        session_factory,
        store,
        tmp_path / "staging",
        max_file_bytes=1024 * 1024,
        max_batch_bytes=2 * 1024 * 1024,
        chunk_size=64 * 1024,
    )
    uploads.ensure_private_library(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
    )
    content = (PROJECT_ROOT / "fixtures" / "dataset-study-example.csv").read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    started = uploads.create_session(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        filename="synthetic-dataset.csv",
        expected_bytes=len(content),
        media_type_hint="text/csv",
        expected_sha256=digest,
    )
    uploads.put_part(
        session_id=started.session_id,
        actor_user_id=identity.owner_user_id,
        offset=0,
        content=content,
        client_sha256=digest,
    )
    committed = uploads.commit(
        session_id=started.session_id,
        actor_user_id=identity.owner_user_id,
    )
    roles = load_role_configs(PROJECT_ROOT / "config" / "agents" / "roles.yaml")
    return (
        identity,
        project,
        committed.version_id,
        DatasetService(session_factory, store, roles),
    )


def test_dataset_manifest_cleaning_statistics_and_review(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    identity, project, document_version_id, service = _setup(
        session_factory,
        tmp_path,
    )
    imported = service.import_table(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        document_version_id=document_version_id,
        title="合成研究数据",
        source_label="synthetic-fixture",
        synthetic=True,
        sheet_name=None,
        idempotency_key="w13-import",
    )
    assert imported.current_version.kind == "raw"
    assert imported.current_version.manifest["synthetic"] is True
    assert imported.current_version.row_count == 7
    assert imported.current_version.columns == ["group", "score", "response", "visit"]
    assert any(
        item["code"] == "MISSING_VALUES" and item["column"] == "score"
        for item in imported.current_version.quality_findings
    )
    replay = service.import_table(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        document_version_id=document_version_id,
        title="合成研究数据",
        source_label="synthetic-fixture",
        synthetic=True,
        sheet_name=None,
        idempotency_key="w13-import",
    )
    assert replay == imported

    cleaning = CleaningSpec(
        select_columns=["group", "score", "response"],
        numeric_columns=["score"],
        rename_columns={},
        drop_missing_columns=["score"],
        rationale="删除缺少主要终点的行，保留原始版本。",
    )
    derived = service.derive_version(
        project_id=project.id,
        dataset_id=imported.id,
        actor_user_id=identity.owner_user_id,
        parent_version_id=imported.current_version.id,
        spec=cleaning,
        idempotency_key="w13-clean",
    )
    assert derived.current_version.version_number == 2
    assert derived.current_version.kind == "derived"
    assert derived.current_version.row_count == 6
    assert derived.versions[0].parent_version_id == imported.current_version.id
    assert derived.versions[1].row_count == 7

    descriptive_spec = StatisticalPlanSpec(
        question="主要连续终点的描述性分布是什么？",
        endpoint_column="score",
        method=StatisticalMethod.DESCRIPTIVE_CONTINUOUS,
        group_column=None,
        analysis_set="清理版本中主要终点完整的所有行",
        missing_policy="fail_if_missing",
        unit="score",
        alpha=0.05,
        expected_groups=[],
        limitations=["合成数据", "正态区间仅作方法演示"],
        exploratory=False,
    )
    descriptive_plan = service.create_plan(
        project_id=project.id,
        dataset_version_id=derived.current_version.id,
        actor_user_id=identity.owner_user_id,
        spec=descriptive_spec,
        idempotency_key="w13-descriptive-plan",
    )
    descriptive = service.run_analysis(
        project_id=project.id,
        plan_id=descriptive_plan.id,
        actor_user_id=identity.owner_user_id,
        idempotency_key="w13-descriptive-run",
    )
    assert descriptive.result["n"] == 6
    assert descriptive.result["mean"] == pytest.approx(14.5)
    assert descriptive.result["median"] == pytest.approx(14.5)
    assert descriptive.chart_spec["kind"] == "summary_interval"
    assert descriptive.code_sha256
    assert descriptive.input_sha256
    assert descriptive.output_sha256
    replay_run = service.run_analysis(
        project_id=project.id,
        plan_id=descriptive_plan.id,
        actor_user_id=identity.owner_user_id,
        idempotency_key="w13-descriptive-run",
    )
    assert replay_run == descriptive

    group_spec = StatisticalPlanSpec(
        question="两组连续终点均值差是多少？",
        endpoint_column="score",
        method=StatisticalMethod.TWO_GROUP_MEAN_DIFFERENCE,
        group_column="group",
        analysis_set="清理版本中主要终点完整的所有行",
        missing_policy="fail_if_missing",
        unit="score",
        alpha=0.05,
        expected_groups=["control", "treatment"],
        limitations=["未计算p值", "正态近似仅用于合成示例"],
        exploratory=False,
    )
    group_plan = service.create_plan(
        project_id=project.id,
        dataset_version_id=derived.current_version.id,
        actor_user_id=identity.owner_user_id,
        spec=group_spec,
        idempotency_key="w13-group-plan",
    )
    group = service.run_analysis(
        project_id=project.id,
        plan_id=group_plan.id,
        actor_user_id=identity.owner_user_id,
        idempotency_key="w13-group-run",
    )
    assert group.result["difference"] == pytest.approx(-5.0)
    assert group.result["p_value"] is None
    assert group.chart_spec["kind"] == "group_means"

    proportion_spec = StatisticalPlanSpec(
        question="响应比例是多少？",
        endpoint_column="response",
        method=StatisticalMethod.PROPORTION_WILSON,
        group_column=None,
        analysis_set="清理版本中响应完整的所有行",
        missing_policy="fail_if_missing",
        unit=None,
        alpha=0.05,
        expected_groups=[],
        limitations=["Wilson区间仅用于合成示例"],
        exploratory=True,
    )
    proportion_plan = service.create_plan(
        project_id=project.id,
        dataset_version_id=derived.current_version.id,
        actor_user_id=identity.owner_user_id,
        spec=proportion_spec,
        idempotency_key="w13-proportion-plan",
    )
    proportion = service.run_analysis(
        project_id=project.id,
        plan_id=proportion_plan.id,
        actor_user_id=identity.owner_user_id,
        idempotency_key="w13-proportion-run",
    )
    assert proportion.result["successes"] == 3
    assert proportion.result["proportion"] == pytest.approx(0.5)

    with pytest.raises(ReviewPolicyError, match="critical"):
        service.review_analysis(
            project_id=project.id,
            analysis_id=descriptive.id,
            actor_user_id=identity.owner_user_id,
            reviewer_role="A14",
            decision=ReviewDecision.ACCEPTED,
            summary="critical缺陷不能接受。",
            findings=[
                ReviewFinding(
                    code="WRONG_ENDPOINT",
                    severity=FindingSeverity.CRITICAL,
                    message="合成检查发现终点口径错误。",
                    evidence_refs=[],
                )
            ],
            idempotency_key="w13-critical-review",
        )
    reviewed = service.review_analysis(
        project_id=project.id,
        analysis_id=descriptive.id,
        actor_user_id=identity.owner_user_id,
        reviewer_role="A14",
        decision=ReviewDecision.ACCEPTED,
        summary="合成统计结果与方法假设已人工检查。",
        findings=[],
        idempotency_key="w13-accept-review",
    )
    assert reviewed.decision == ReviewDecision.ACCEPTED

    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        assert session.scalar(select(func.count()).select_from(Dataset)) == 1
        assert session.scalar(select(func.count()).select_from(AnalysisRun)) == 3
        assert session.scalar(select(func.count()).select_from(AnalysisReview)) == 1


def test_w13_tables_are_forced_through_workspace_rls(database: Engine) -> None:
    with database.connect() as connection:
        policies = connection.scalar(
            text("SELECT count(*) FROM pg_policies WHERE schemaname = 'public'")
        )
        tables = connection.execute(
            text(
                """
                SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
                FROM pg_class AS c
                JOIN pg_namespace AS n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relname IN (
                    'datasets',
                    'dataset_versions',
                    'dataset_rows',
                    'statistical_plans',
                    'analysis_runs',
                    'analysis_reviews'
                  )
                ORDER BY c.relname
                """
            )
        ).all()
    assert policies == 85
    assert len(tables) == 6
    assert all(row.relrowsecurity and row.relforcerowsecurity for row in tables)
