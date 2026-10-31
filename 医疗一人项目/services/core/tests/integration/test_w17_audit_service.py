"""W17 audit service integration requirements."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import load_role_configs
from medical_one_person.application.audits import AuditService
from medical_one_person.application.datasets import DatasetService
from medical_one_person.application.errors import (
    ConflictingOperationError,
    NotFoundError,
    ReviewPolicyError,
)
from medical_one_person.application.external import ExternalService
from medical_one_person.application.knowledge import (
    CitationService,
    ClaimService,
    KnowledgeIndexService,
    KnowledgeSearchService,
    KnowledgeVersionService,
)
from medical_one_person.application.knowledge_ingestion import KnowledgeIngestionService
from medical_one_person.application.projects import ProjectService
from medical_one_person.application.tasks import TaskService
from medical_one_person.domain.audits import (
    AuditFindingStatus,
    AuditState,
    AuditTargetType,
)
from medical_one_person.domain.datasets import (
    CleaningSpec,
    StatisticalMethod,
    StatisticalPlanSpec,
)
from medical_one_person.domain.external import (
    DeliverableKind,
    DeliverableSpec,
    EngagementScope,
    EngagementSpec,
    OrganizationSpec,
    ProviderType,
    VerificationState,
)
from medical_one_person.domain.plans import ReviewDecision
from medical_one_person.infrastructure.artifacts import LocalArtifactStore
from medical_one_person.infrastructure.bootstrap import bootstrap_local_owner
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    AnalysisRun,
    AuditEvaluation,
    AuditFinding,
    AuditRun,
    ClaimVersion,
    ExternalDeliverable,
)
from medical_one_person.infrastructure.knowledge.parsers import DocumentParser
from medical_one_person.infrastructure.knowledge.upload import UploadService

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _upload(
    uploads: UploadService,
    identity,
    project_id,
    *,
    filename: str,
    content: bytes,
    media_type: str,
):
    digest = hashlib.sha256(content).hexdigest()
    started = uploads.create_session(
        project_id=project_id,
        actor_user_id=identity.owner_user_id,
        filename=filename,
        expected_bytes=len(content),
        media_type_hint=media_type,
        expected_sha256=digest,
    )
    uploads.put_part(
        session_id=started.session_id,
        actor_user_id=identity.owner_user_id,
        offset=0,
        content=content,
        client_sha256=digest,
    )
    return uploads.commit(
        session_id=started.session_id,
        actor_user_id=identity.owner_user_id,
    )


def _seed_claim(
    identity,
    project,
    task,
    store: LocalArtifactStore,
    uploads: UploadService,
    session_factory: sessionmaker[Session],
):
    content = (
        "合成研究记录：犬模型疼痛评分下降。\n"
        "阴性结果：功能改善未观察到。\n"
    ).encode()
    version = _upload(
        uploads,
        identity,
        project.id,
        filename="w17-synthetic-study.txt",
        content=content,
        media_type="text/plain",
    )
    KnowledgeIngestionService(session_factory, store, DocumentParser()).process(
        workspace_id=identity.workspace_id,
        job_id=version.job_id,
    )
    KnowledgeIndexService(
        session_factory,
        chunk_chars=80,
        overlap_chars=10,
    ).index_version(
        workspace_id=identity.workspace_id,
        version_id=version.version_id,
    )
    hit = KnowledgeSearchService(session_factory).search(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        task_id=task.id,
        query="犬模型 疼痛",
    ).hits[0]
    KnowledgeVersionService(session_factory).record_source_review(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        version_id=version.version_id,
        scope="W17合成引文核查范围",
        outcome="verified_scope",
        evidence_refs=[str(hit.chunk_id)],
    )
    citation = CitationService(session_factory).create(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        task_id=task.id,
        chunk_id=hit.chunk_id,
        quoted_excerpt=hit.excerpt,
    )
    claims = ClaimService(session_factory)
    unreviewed = claims.create(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        statement="合成药物可能降低犬疼痛评分。",
        species_or_population="犬",
        sample_size=24,
        directness="direct",
    )
    claims.link_evidence(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        claim_version_id=unreviewed.version_id,
        citation_id=citation.id,
        stance="supports",
    )
    contradictory = claims.create(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        statement="合成药物降低了犬疼痛评分。",
        species_or_population="犬",
        sample_size=24,
        directness="direct",
    )
    claims.link_evidence(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        claim_version_id=contradictory.version_id,
        citation_id=citation.id,
        stance="refutes",
    )
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        version_row = session.get(ClaimVersion, contradictory.version_id)
        assert version_row is not None
        version_row.status = "supported"
    return citation, unreviewed, contradictory


def _seed_analysis(
    identity,
    project,
    roles,
    store: LocalArtifactStore,
    uploads: UploadService,
    session_factory: sessionmaker[Session],
) -> AnalysisRun:
    content = (PROJECT_ROOT / "fixtures" / "dataset-study-example.csv").read_bytes()
    version = _upload(
        uploads,
        identity,
        project.id,
        filename="w17-synthetic.csv",
        content=content,
        media_type="text/csv",
    )
    service = DatasetService(session_factory, store, roles)
    raw = service.import_table(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        document_version_id=version.version_id,
        title="W17合成统计",
        source_label="synthetic-w17",
        synthetic=True,
        sheet_name=None,
        idempotency_key="w17-dataset-import",
    )
    derived = service.derive_version(
        project_id=project.id,
        dataset_id=raw.id,
        actor_user_id=identity.owner_user_id,
        parent_version_id=raw.current_version.id,
        spec=CleaningSpec(
            select_columns=["group", "score", "response"],
            numeric_columns=["score"],
            rename_columns={},
            drop_missing_columns=["score"],
            rationale="W17只使用主要终点完整的合成行。",
        ),
        idempotency_key="w17-dataset-clean",
    )
    plan = service.create_plan(
        project_id=project.id,
        dataset_version_id=derived.current_version.id,
        actor_user_id=identity.owner_user_id,
        spec=StatisticalPlanSpec(
            question="W17合成两组均值差是多少？",
            endpoint_column="score",
            method=StatisticalMethod.TWO_GROUP_MEAN_DIFFERENCE,
            group_column="group",
            analysis_set="主要终点完整行",
            missing_policy="fail_if_missing",
            unit="score",
            alpha=0.05,
            expected_groups=["control", "treatment"],
            limitations=["未计算p值", "合成数据"],
            exploratory=False,
        ),
        idempotency_key="w17-stat-plan",
    )
    analysis = service.run_analysis(
        project_id=project.id,
        plan_id=plan.id,
        actor_user_id=identity.owner_user_id,
        idempotency_key="w17-stat-run",
    )
    service.review_analysis(
        project_id=project.id,
        analysis_id=analysis.id,
        actor_user_id=identity.owner_user_id,
        reviewer_role="A14",
        decision=ReviewDecision.ACCEPTED,
        summary="W17合成统计方法合同复核。",
        findings=[],
        idempotency_key="w17-stat-review",
    )
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        row = session.get(AnalysisRun, analysis.id)
        assert row is not None
        row.output_sha256 = "0" * 64
        return row


def _seed_deliverable(
    identity,
    project,
    session_factory: sessionmaker[Session],
) -> ExternalDeliverable:
    service = ExternalService(session_factory)
    organization = service.create_organization(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        spec=OrganizationSpec(
            name="W17合成CRO记录",
            provider_type=ProviderType.CRO,
            capability_summary="仅用于审计合同合成测试，未联系。",
            source_refs=["fixture:w17-provider"],
            verification_state=VerificationState.VERIFIED,
        ),
        idempotency_key="w17-org",
    )
    engagement = service.create_engagement(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        spec=EngagementSpec(
            organization_id=organization.id,
            title="W17合成交付工作包",
            scope=EngagementScope(
                scientific_question="合成问题能否回答审计阻断？",
                decision_impact="仅验证内部审计流程。",
                input_requirements=["合成方案"],
                deliverables=["原始数据"],
                method_and_quality=["记录方法与偏差"],
                rights_and_confidentiality=["项目私有"],
                acceptance_responsibility="A25/A26合同复核",
            ),
        ),
        idempotency_key="w17-engagement",
    )
    deliverable = service.create_deliverable(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        spec=DeliverableSpec(
            engagement_id=engagement.id,
            title="W17缺失原件的已接受原始数据",
            kind=DeliverableKind.RAW_DATA,
            expected_items=["原始数据", "方法记录"],
        ),
        idempotency_key="w17-deliverable",
    )
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        row = session.get(ExternalDeliverable, deliverable.id)
        assert row is not None
        row.state = "accepted"
        row.knowledge_version_id = None
        row.manifest = {}
        row.reviewer_role = None
        return row


def test_w17_audit_reviews_block_reverse_evidence_and_preserve_history(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    identity = bootstrap_local_owner(session_factory)
    projects = ProjectService(session_factory)
    project = projects.create_project(
        actor_user_id=identity.owner_user_id,
        name="W17审计项目",
        scope="验证独立审计合同、阻断和合成评测。",
        idempotency_key="w17-project",
    )
    other_project = projects.create_project(
        actor_user_id=identity.owner_user_id,
        name="W17隔离项目",
        scope="仅验证跨项目目标拒绝。",
        idempotency_key="w17-other-project",
    )
    task = TaskService(session_factory).create_task(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_type="evidence.review",
        purpose="w17-citation",
        assignee_role="A26",
        role_version="1",
        input_version="v1",
        input_refs=["fixture:w17-audit"],
        goal="生成W17审计引用。",
        deliverable_schema="audit_report.v1",
        acceptance_policy="independent_review.v1",
    )
    roles = load_role_configs(PROJECT_ROOT / "config" / "agents" / "roles.yaml")
    store = LocalArtifactStore(tmp_path / "objects")
    uploads = UploadService(
        session_factory,
        store,
        tmp_path / "staging",
        max_file_bytes=2 * 1024 * 1024,
        max_batch_bytes=4 * 1024 * 1024,
        chunk_size=64 * 1024,
    )
    uploads.ensure_private_library(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
    )
    _, unreviewed, contradictory = _seed_claim(
        identity,
        project,
        task,
        store,
        uploads,
        session_factory,
    )
    analysis = _seed_analysis(
        identity,
        project,
        roles,
        store,
        uploads,
        session_factory,
    )
    deliverable = _seed_deliverable(identity, project, session_factory)
    service = AuditService(
        session_factory,
        roles,
        PROJECT_ROOT / "fixtures" / "w17-audit-cases.json",
    )

    a25 = service.create_review(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        target_type=AuditTargetType.CLAIM_VERSION,
        target_id=unreviewed.version_id,
        reviewer_role="A25",
        producer_role="A02",
        idempotency_key="w17-a25-claim",
    )
    assert a25.state == AuditState.CHANGES_REQUESTED
    assert a25.downstream_blocked is True
    assert [finding.code for finding in a25.findings] == ["CITATION_UNREVIEWED"]
    assert a25.reviewer_role == "A25"
    assert a25.producer_role == "A02"
    assert len(a25.target_sha256) == 64
    assert a25.input_snapshot["statement"] == "合成药物可能降低犬疼痛评分。"
    assert service.create_review(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        target_type=AuditTargetType.CLAIM_VERSION,
        target_id=unreviewed.version_id,
        reviewer_role="A25",
        producer_role="A02",
        idempotency_key="w17-a25-claim",
    ) == a25
    with pytest.raises(ConflictingOperationError, match="different parameters"):
        service.create_review(
            project_id=project.id,
            actor_user_id=identity.owner_user_id,
            target_type=AuditTargetType.CLAIM_VERSION,
            target_id=unreviewed.version_id,
            reviewer_role="A26",
            producer_role="A02",
            idempotency_key="w17-a25-claim",
        )
    with pytest.raises(ReviewPolicyError, match="own output"):
        service.create_review(
            project_id=project.id,
            actor_user_id=identity.owner_user_id,
            target_type=AuditTargetType.CLAIM_VERSION,
            target_id=unreviewed.version_id,
            reviewer_role="A25",
            producer_role="A25",
            idempotency_key="w17-self-review",
        )
    with pytest.raises(NotFoundError, match="Claim version not found"):
        service.create_review(
            project_id=other_project.id,
            actor_user_id=identity.owner_user_id,
            target_type=AuditTargetType.CLAIM_VERSION,
            target_id=unreviewed.version_id,
            reviewer_role="A25",
            producer_role="A02",
            idempotency_key="w17-cross-project",
        )

    a26 = service.create_review(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        target_type=AuditTargetType.CLAIM_VERSION,
        target_id=contradictory.version_id,
        reviewer_role="A26",
        producer_role="A02",
        idempotency_key="w17-a26-claim",
    )
    assert a26.state == AuditState.BLOCKED
    assert a26.downstream_blocked is True
    assert [finding.code for finding in a26.findings] == ["CONTRADICTION_IGNORED"]
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        claim = session.get(ClaimVersion, contradictory.version_id)
        assert claim is not None and claim.status == "disputed"

    analysis_review = service.create_review(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        target_type=AuditTargetType.ANALYSIS_RUN,
        target_id=analysis.id,
        reviewer_role="A25",
        producer_role="A15",
        idempotency_key="w17-analysis",
    )
    assert analysis_review.state == AuditState.BLOCKED
    assert [item.code for item in analysis_review.findings] == [
        "ANALYSIS_HASH_MISMATCH"
    ]

    deliverable_review = service.create_review(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        target_type=AuditTargetType.EXTERNAL_DELIVERABLE,
        target_id=deliverable.id,
        reviewer_role="A26",
        producer_role="A22",
        idempotency_key="w17-deliverable",
    )
    assert deliverable_review.state == AuditState.BLOCKED
    assert {item.code for item in deliverable_review.findings} == {
        "COMPLETENESS_REVIEW_MISSING",
        "MANIFEST_HASH_MISSING",
        "RAW_DATA_HASH_MISSING",
        "RAW_ORIGINAL_MISSING",
    }

    finding = a25.findings[0]
    resolved = service.resolve_finding(
        project_id=project.id,
        audit_id=a25.id,
        finding_id=finding.id,
        actor_user_id=identity.owner_user_id,
        status=AuditFindingStatus.RESOLVED,
        resolution="已补记引文核查，原审计结论保留。",
    )
    assert resolved.status == AuditFindingStatus.RESOLVED
    with pytest.raises(ConflictingOperationError, match="cannot be rewritten"):
        service.resolve_finding(
            project_id=project.id,
            audit_id=a25.id,
            finding_id=finding.id,
            actor_user_id=identity.owner_user_id,
            status=AuditFindingStatus.ACCEPTED_RISK,
            resolution="尝试改写已解决缺陷。",
        )
    rerun = service.create_review(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        target_type=AuditTargetType.CLAIM_VERSION,
        target_id=unreviewed.version_id,
        reviewer_role="A25",
        producer_role="A02",
        idempotency_key="w17-a25-claim-rerun",
    )
    assert rerun.review_version == 2
    assert rerun.state == AuditState.CHANGES_REQUESTED
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        original = session.get(AuditRun, a25.id)
        original_finding = session.get(AuditFinding, finding.id)
        assert original is not None
        assert original.state == "changes_requested"
        assert original.input_snapshot == a25.input_snapshot
        assert original_finding is not None
        assert original_finding.status == "resolved"
        assert original_finding.resolution == "已补记引文核查，原审计结论保留。"

    evaluation = service.run_evaluation(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
    )
    assert evaluation.metrics.cases == 7
    assert evaluation.metrics.true_positives == 6
    assert evaluation.metrics.false_positives == 0
    assert evaluation.metrics.false_negatives == 0
    assert evaluation.metrics.precision == 1.0
    assert evaluation.metrics.recall == 1.0
    assert any("Synthetic" in item for item in evaluation.limitations)
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        assert session.get(AuditEvaluation, evaluation.id) is not None

    workspace = service.workspace(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
    )
    assert {item.target_type for item in workspace.targets} == {
        AuditTargetType.ANALYSIS_RUN,
        AuditTargetType.CLAIM_VERSION,
        AuditTargetType.EXTERNAL_DELIVERABLE,
    }
    assert len(workspace.reviews) == 5
    assert len(workspace.evaluations) == 1
    assert any("not live model or human expert reviews" in item for item in workspace.limitations)


def test_w17_tables_are_forced_through_workspace_rls(database: Engine) -> None:
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
                    'audit_runs',
                    'audit_findings',
                    'audit_evaluations'
                  )
                ORDER BY c.relname
                """
            )
        ).all()
    assert policies == 79
    assert len(tables) == 3
    assert all(row.relrowsecurity and row.relforcerowsecurity for row in tables)
