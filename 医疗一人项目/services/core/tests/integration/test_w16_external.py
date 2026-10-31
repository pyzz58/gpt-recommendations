from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.errors import PlanStateError
from medical_one_person.application.external import ExternalService
from medical_one_person.application.projects import ProjectService
from medical_one_person.domain.external import (
    CommercialEvidenceType,
    ContactSpec,
    ContractSpec,
    ContractState,
    ContractTransitionSpec,
    DeliverableKind,
    DeliverableReceiptSpec,
    DeliverableReviewSpec,
    DeliverableSpec,
    EngagementScope,
    EngagementSpec,
    ExpertSpec,
    ExternalAuthorizationSpec,
    ExternalEngagementState,
    FinancialEventType,
    OrganizationSpec,
    PatentStatus,
    ProfessionalRecordKind,
    ProfessionalRecordSpec,
    ProfessionalRecordState,
    ProviderType,
    QuoteSpec,
    QuoteState,
    SourceTier,
    VerificationState,
)
from medical_one_person.infrastructure.artifacts import LocalArtifactStore
from medical_one_person.infrastructure.bootstrap import bootstrap_local_owner
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    ExternalContract,
    ExternalDeliverable,
    ExternalEngagement,
    ExternalQuote,
    KnowledgeBlob,
    KnowledgeDocument,
    KnowledgeDocumentVersion,
    Library,
)


def _knowledge_version(
    session_factory: sessionmaker[Session],
    store: LocalArtifactStore,
    *,
    workspace_id,
    project_id,
    actor_user_id,
    filename: str,
    content: bytes,
) -> KnowledgeDocumentVersion:
    stored = store.put(content)
    now = datetime.now(UTC)
    with session_factory.begin() as session:
        set_rls_context(session, workspace_id=workspace_id, user_id=actor_user_id)
        library = Library(
            id=uuid4(),
            workspace_id=workspace_id,
            project_id=project_id,
            scope="project_private",
            name=f"W16 evidence {uuid4()}",
            acl_revision=1,
            created_at=now,
        )
        session.add(library)
        session.flush()
        blob = KnowledgeBlob(
            id=uuid4(),
            workspace_id=workspace_id,
            content_hash=stored.sha256,
            size_bytes=stored.size_bytes,
            media_type="application/pdf",
            object_key=stored.object_key,
            ref_count=1,
            created_at=now,
        )
        session.add(blob)
        session.flush()
        document = KnowledgeDocument(
            id=uuid4(),
            workspace_id=workspace_id,
            library_id=library.id,
            title=filename,
            document_kind="pdf",
            current_version_id=None,
            revision=1,
            created_at=now,
        )
        session.add(document)
        session.flush()
        version = KnowledgeDocumentVersion(
            id=uuid4(),
            workspace_id=workspace_id,
            project_id=project_id,
            library_id=library.id,
            document_id=document.id,
            blob_id=blob.id,
            version_label="v1",
            filename=filename,
            media_type="application/pdf",
            size_bytes=stored.size_bytes,
            content_hash=stored.sha256,
            origin="external_provider",
            data_origin="synthetic_test",
            confidentiality="project_private",
            cloud_policy="local_only",
            source_at=now,
            ingested_at=now,
            ingest_state="stored",
            evidence_status="unreviewed",
            version_status="current",
            access_state="active",
        )
        session.add(version)
        session.flush()
        document.current_version_id = version.id
        return version


def _scope() -> EngagementScope:
    return EngagementScope(
        scientific_question="合成样本的探索性检测何时能回答技术可行性问题？",
        decision_impact="决定是否继续准备真实方法学验证。",
        input_requirements=["合成样本清单", "拟议方法"],
        deliverables=["原始数据", "检测报告"],
        method_and_quality=["记录方法版本、质控和偏差"],
        rights_and_confidentiality=["仅项目私有", "不得公开原始数据"],
        acceptance_responsibility="A25记录资料完整性，A26保留科学异议",
        target_start=date.today(),
        target_end=date.today() + timedelta(days=30),
        budget_lower=Decimal("1000.00"),
        budget_upper=Decimal("3000.00"),
        currency="CNY",
    )


def _current_engagement(
    service: ExternalService,
    *,
    project_id,
    actor_user_id,
    engagement_id,
):
    workspace = service.workspace(
        project_id=project_id,
        actor_user_id=actor_user_id,
    )
    return next(item for item in workspace.engagements if item.id == engagement_id)


def test_w16_external_engagement_quote_contract_receipt_and_acceptance(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="W16外部合作项目",
        scope="验证外部合作、报价、合同与原始交付状态。",
        idempotency_key="w16-project",
    )
    store = LocalArtifactStore(tmp_path / "w16-artifacts")
    quote_document = _knowledge_version(
        session_factory,
        store,
        workspace_id=identity.workspace_id,
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        filename="synthetic-quote.pdf",
        content=b"%PDF-1.7\nsynthetic quote\n",
    )
    contract_document = _knowledge_version(
        session_factory,
        store,
        workspace_id=identity.workspace_id,
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        filename="synthetic-signed-contract.pdf",
        content=b"%PDF-1.7\nsynthetic signed contract\n",
    )
    raw_document = _knowledge_version(
        session_factory,
        store,
        workspace_id=identity.workspace_id,
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        filename="synthetic-raw-results.csv",
        content=b"sample,result\nA,1\n",
    )
    service = ExternalService(session_factory)
    organization = service.create_organization(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        spec=OrganizationSpec(
            name="合成检测机构",
            provider_type=ProviderType.CENTRAL_LAB,
            capability_summary="仅用于W16合同测试，不代表真实机构。",
            source_refs=["fixture:w16-provider-confirmation"],
            verification_state=VerificationState.VERIFIED,
        ),
        idempotency_key="w16-org",
    )
    contact = service.create_contact(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        spec=ContactSpec(
            organization_id=organization.id,
            name="合成联系人",
            role="项目接口",
            email="contact@example.test",
            source_refs=["fixture:w16-contact"],
            verification_state=VerificationState.VERIFIED,
        ),
    )
    assert contact.verification_state == VerificationState.VERIFIED
    expert = service.create_expert(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        spec=ExpertSpec(
            name="合成统计专家",
            expertise="合成统计方法审查",
            public_source_refs=["fixture:w16-expert"],
            contact_email="expert@example.test",
        ),
        idempotency_key="w16-expert",
    )
    assert expert.state.value == "candidate"

    engagement = service.create_engagement(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        spec=EngagementSpec(
            organization_id=organization.id,
            title="合成方法学验证工作包",
            scope=_scope(),
        ),
        idempotency_key="w16-engagement",
    )
    for target in (
        ExternalEngagementState.SCOPE_READY,
        ExternalEngagementState.REQUESTED,
    ):
        engagement = service.transition_engagement(
            project_id=project.id,
            engagement_id=engagement.id,
            actor_user_id=identity.owner_user_id,
            expected_revision=engagement.revision,
            state=target,
        )
    quote = service.create_quote(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        spec=QuoteSpec(
            engagement_id=engagement.id,
            amount=Decimal("2000.00"),
            currency="CNY",
            tax_included=False,
            shipping_included=None,
            assumptions=["样本由项目方提供"],
            excluded_work=["复测费用"],
            valid_until=date.today() + timedelta(days=14),
            document_version_id=quote_document.id,
            state=QuoteState.ACCEPTED,
        ),
        idempotency_key="w16-quote",
    )
    assert quote.document_version_id == quote_document.id
    comparison = service.compare_quotes(
        project_id=project.id,
        engagement_id=engagement.id,
        actor_user_id=identity.owner_user_id,
    )
    assert len(comparison.comparable) == 1
    assert any("shipping" in warning for warning in comparison.warnings)

    contract = service.create_contract(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        spec=ContractSpec(
            engagement_id=engagement.id,
            quote_id=quote.id,
            title="合成外部服务合同",
            terms_summary="仅为测试记录，不是已签真实合同。",
            document_version_id=contract_document.id,
        ),
        idempotency_key="w16-contract",
    )
    assert contract.state == ContractState.DRAFT
    signed = service.transition_contract(
        project_id=project.id,
        contract_id=contract.id,
        actor_user_id=identity.owner_user_id,
        spec=ContractTransitionSpec(
            expected_revision=contract.revision,
            state=ContractState.SIGNED,
            internal_signed=True,
            external_signed=True,
            document_version_id=contract_document.id,
            reason="合成双方签署样本文档已登记。",
        ),
    )
    assert signed.state == ContractState.SIGNED

    authorization = service.create_authorization(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        spec=ExternalAuthorizationSpec(
            engagement_id=engagement.id,
            action_scope="仅登记合成测试执行状态，不联系或付款。",
            amount_max=Decimal("2500.00"),
            currency="CNY",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        ),
        idempotency_key="w16-external-auth",
    )
    assert authorization.state.value == "active"
    engagement = _current_engagement(
        service,
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        engagement_id=engagement.id,
    )
    engagement = service.transition_engagement(
        project_id=project.id,
        engagement_id=engagement.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=engagement.revision,
        state=ExternalEngagementState.EXECUTING,
    )
    assert engagement.state == ExternalEngagementState.EXECUTING

    deliverable = service.create_deliverable(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        spec=DeliverableSpec(
            engagement_id=engagement.id,
            title="合成原始检测结果",
            kind=DeliverableKind.RAW_DATA,
            expected_items=["样本清单", "原始结果", "方法版本"],
        ),
        idempotency_key="w16-deliverable",
    )
    assert deliverable.state.value == "expected"
    received = service.receive_deliverable(
        project_id=project.id,
        deliverable_id=deliverable.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=deliverable.revision,
        spec=DeliverableReceiptSpec(
            knowledge_version_id=raw_document.id,
            manifest={"format": "csv", "synthetic": True},
            missing_items=[],
            summary="合成原始结果已登记，不代表真实实验结果。",
        ),
    )
    assert received.state.value == "received"
    accepted = service.review_deliverable(
        project_id=project.id,
        deliverable_id=received.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=received.revision,
        spec=DeliverableReviewSpec(
            decision="accepted",
            reviewer_role="A25",
            summary="合成交付完整性合同通过，不证明科学结果成立。",
        ),
    )
    assert accepted.state.value == "accepted"
    engagement = _current_engagement(
        service,
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        engagement_id=engagement.id,
    )
    assert engagement.state == ExternalEngagementState.UNDER_REVIEW
    engagement = service.transition_engagement(
        project_id=project.id,
        engagement_id=engagement.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=engagement.revision,
        state=ExternalEngagementState.ACCEPTED,
    )
    engagement = _current_engagement(
        service,
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        engagement_id=engagement.id,
    )
    engagement = service.transition_engagement(
        project_id=project.id,
        engagement_id=engagement.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=engagement.revision,
        state=ExternalEngagementState.CLOSED,
    )
    assert engagement.state == ExternalEngagementState.CLOSED

    workspace = service.workspace(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
    )
    assert len(workspace.organizations) == 1
    assert len(workspace.quotes) == 1
    assert len(workspace.contracts) == 1
    assert len(workspace.deliverables) == 1


def test_w16_professional_records_keep_domains_and_facts_separate(
    session_factory: sessionmaker[Session],
) -> None:
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="W16专业记录项目",
        scope="验证注册、专利、财务与商业记录。",
        idempotency_key="w16-professional-project",
    )
    service = ExternalService(session_factory)
    regulatory = service.create_professional_record(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        spec=ProfessionalRecordSpec(
            kind=ProfessionalRecordKind.REGULATORY,
            state=ProfessionalRecordState.OFFICIAL_CONFIRMED,
            title="合成市场官方分类问题",
            source_tier=SourceTier.OFFICIAL,
            source_title="合成测试来源",
            source_ref="fixture:w16-regulatory",
            checked_at=date.today(),
            market="合成市场",
            product_scope="合成IVD项目",
            facts=["已核对测试来源，不代表真实适用性"],
            limitations=["只适用于测试范围"],
        ),
        idempotency_key="w16-reg-record",
    )
    assert regulatory.market == "合成市场"
    patent = service.create_professional_record(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        spec=ProfessionalRecordSpec(
            kind=ProfessionalRecordKind.PATENT,
            state=ProfessionalRecordState.INFORMATION_ONLY,
            title="合成专利检索",
            source_tier=SourceTier.OFFICIAL,
            source_ref="fixture:w16-patent",
            checked_at=date.today(),
            jurisdiction="CN",
            patent_status=PatentStatus.PROVISIONAL,
            application_number="SYNTHETIC-APP-001",
            limitations=["临时申请不等于授权"],
        ),
        idempotency_key="w16-patent",
    )
    assert patent.patent_status == "provisional"
    commitment = service.create_professional_record(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        spec=ProfessionalRecordSpec(
            kind=ProfessionalRecordKind.FINANCIAL,
            title="合成预算承诺",
            source_tier=SourceTier.USER_STATEMENT,
            source_ref="fixture:w16-commitment",
            financial_event_type=FinancialEventType.COMMITMENT,
            amount=Decimal("2000.00"),
            currency="CNY",
        ),
        idempotency_key="w16-commitment",
    )
    assert commitment.financial_event_type == "commitment"
    business = service.create_professional_record(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        spec=ProfessionalRecordSpec(
            kind=ProfessionalRecordKind.COMMERCIAL,
            title="合成需求假说",
            source_tier=SourceTier.NONE,
            commercial_evidence_type=CommercialEvidenceType.UNKNOWN,
            limitations=["尚无真实访谈"],
        ),
        idempotency_key="w16-commercial",
    )
    assert business.commercial_evidence_type == "unknown"
    with pytest.raises(ValueError, match="source reference"):
        ProfessionalRecordSpec(
            kind=ProfessionalRecordKind.COMMERCIAL,
            title="无来源访谈",
            source_tier=SourceTier.NONE,
            commercial_evidence_type=CommercialEvidenceType.VERIFIED_INTERVIEW,
        )

    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        assert session.scalar(select(func.count()).select_from(ExternalQuote)) == 0
        assert session.scalar(select(func.count()).select_from(ExternalContract)) == 0
        assert session.scalar(select(func.count()).select_from(ExternalDeliverable)) == 0


def test_w16_execution_requires_quote_contract_and_authorization(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="W16执行门项目",
        scope="验证执行状态不能由文本自证。",
        idempotency_key="w16-execution-project",
    )
    service = ExternalService(session_factory)
    organization = service.create_organization(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        spec=OrganizationSpec(
            name="合成合作方",
            provider_type=ProviderType.CRO,
            capability_summary="测试用合作方记录。",
            source_refs=["fixture:w16-cro"],
            verification_state=VerificationState.VERIFIED,
        ),
        idempotency_key="w16-exec-org",
    )
    engagement = service.create_engagement(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        spec=EngagementSpec(
            organization_id=organization.id,
            title="未授权执行测试",
            scope=_scope(),
        ),
        idempotency_key="w16-exec-engagement",
    )
    engagement = service.transition_engagement(
        project_id=project.id,
        engagement_id=engagement.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=engagement.revision,
        state=ExternalEngagementState.SCOPE_READY,
    )
    engagement = service.transition_engagement(
        project_id=project.id,
        engagement_id=engagement.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=engagement.revision,
        state=ExternalEngagementState.REQUESTED,
    )
    with pytest.raises(PlanStateError, match="Invalid external engagement transition"):
        service.transition_engagement(
            project_id=project.id,
            engagement_id=engagement.id,
            actor_user_id=identity.owner_user_id,
            expected_revision=engagement.revision,
            state=ExternalEngagementState.AUTHORIZED,
        )
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        assert session.scalar(select(func.count()).select_from(ExternalEngagement)) == 1


def test_w16_tables_are_forced_through_rls(database: Engine) -> None:
    with database.connect() as connection:
        policies = connection.scalar(
            text("SELECT count(*) FROM pg_policies WHERE schemaname = 'public'")
        )
        tables = connection.execute(
            text(
                """
                SELECT relname, relrowsecurity, relforcerowsecurity
                FROM pg_class
                WHERE relname IN (
                  'external_organizations',
                  'external_contacts',
                  'external_experts',
                  'external_engagements',
                  'external_quotes',
                  'external_contracts',
                  'external_deliverables',
                  'professional_records',
                  'external_authorizations'
                )
                ORDER BY relname
                """
            )
        ).all()
    assert policies == 79
    assert len(tables) == 9
    assert all(row.relrowsecurity and row.relforcerowsecurity for row in tables)
