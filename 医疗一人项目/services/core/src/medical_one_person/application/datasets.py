from __future__ import annotations

import hashlib
import inspect
import json
import math
import platform
import statistics
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
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
)
from medical_one_person.domain.datasets import (
    AnalysisState,
    CleaningSpec,
    DatasetVersionKind,
    DatasetVersionState,
    StatisticalMethod,
    StatisticalPlanSpec,
)
from medical_one_person.domain.plans import FindingSeverity, ReviewDecision, ReviewFinding
from medical_one_person.infrastructure.artifacts import LocalArtifactStore
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    AnalysisReview,
    AnalysisRun,
    CommandReceipt,
    Dataset,
    DatasetRow,
    DatasetVersion,
    KnowledgeBlob,
    KnowledgeDocumentVersion,
    Project,
    ProjectEvent,
    StatisticalPlan,
    User,
)
from medical_one_person.infrastructure.tables import parse_table

ANALYSIS_CODE_VERSION = "w13-stats.v1"


class DatasetReceiptPayload(BaseModel):
    dataset_id: UUID
    version_id: UUID


class PlanReceiptPayload(BaseModel):
    plan_id: UUID


class AnalysisReceiptPayload(BaseModel):
    analysis_id: UUID


class ReviewReceiptPayload(BaseModel):
    review_id: UUID


class DatasetVersionView(BaseModel):
    id: UUID
    dataset_id: UUID
    version_number: int
    kind: DatasetVersionKind
    state: DatasetVersionState
    source_document_version_id: UUID | None
    parent_version_id: UUID | None
    manifest: dict[str, Any]
    transformation: dict[str, Any] | None
    rows_sha256: str
    row_count: int
    columns: list[str]
    quality_findings: list[dict[str, Any]]
    preview: list[dict[str, Any]]
    created_at: datetime


class DatasetView(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    revision: int
    current_version: DatasetVersionView
    versions: list[DatasetVersionView]
    created_at: datetime
    updated_at: datetime


class StatisticalPlanView(BaseModel):
    id: UUID
    project_id: UUID
    dataset_version_id: UUID
    plan_version: int
    question: str
    endpoint_column: str
    method: StatisticalMethod
    group_column: str | None
    analysis_set: str
    missing_policy: str
    unit: str | None
    alpha: float
    expected_groups: list[str]
    limitations: list[str]
    exploratory: bool
    created_at: datetime


class AnalysisRunView(BaseModel):
    id: UUID
    project_id: UUID
    dataset_version_id: UUID
    plan_id: UUID
    analysis_version: int
    code_version: str
    code_sha256: str
    environment: dict[str, Any]
    random_seed: int
    state: AnalysisState
    result: dict[str, Any]
    chart_spec: dict[str, Any]
    input_sha256: str
    output_sha256: str
    error_code: str | None
    created_at: datetime
    latest_review: AnalysisReviewView | None = None


class AnalysisReviewView(BaseModel):
    id: UUID
    analysis_id: UUID
    decision: ReviewDecision
    reviewer_role: str
    summary: str
    findings: list[ReviewFinding]
    result_sha256: str
    created_at: datetime


class DatasetService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        store: LocalArtifactStore,
        roles: dict[str, AgentRoleConfig],
    ) -> None:
        self._session_factory = session_factory
        self._store = store
        self._roles = roles

    def import_table(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        document_version_id: UUID,
        title: str,
        source_label: str,
        synthetic: bool,
        sheet_name: str | None,
        idempotency_key: str,
    ) -> DatasetView:
        if not title.strip() or not source_label.strip() or not idempotency_key.strip():
            raise ValueError("Dataset title, source label and idempotency key are required")
        request_hash = _digest(
            {
                "document_version_id": str(document_version_id),
                "title": title,
                "source_label": source_label,
                "synthetic": synthetic,
                "sheet_name": sheet_name,
            }
        )
        route = f"datasets.import:{project_id}"
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _locked_project(session, project_id, actor.workspace_id)
            receipt = _find_receipt(session, actor.id, route, idempotency_key)
            if receipt is not None:
                return self._replay_dataset(session, receipt, request_hash)
            row = session.execute(
                select(KnowledgeDocumentVersion, KnowledgeBlob)
                .join(
                    KnowledgeBlob,
                    KnowledgeBlob.id == KnowledgeDocumentVersion.blob_id,
                )
                .where(
                    KnowledgeDocumentVersion.id == document_version_id,
                    KnowledgeDocumentVersion.project_id == project.id,
                    KnowledgeDocumentVersion.access_state == "active",
                )
            ).one_or_none()
            if row is None:
                raise NotFoundError("Source document version not found")
            source, blob = row
            content = self._store.read(blob.object_key, blob.content_hash)
            parsed = parse_table(
                content,
                filename=source.filename,
                media_type=source.media_type,
                sheet_name=sheet_name,
            )
            now = datetime.now(UTC)
            rows_sha256 = _digest(parsed.rows)
            dataset = Dataset(
                id=uuid4(),
                workspace_id=project.workspace_id,
                project_id=project.id,
                title=title,
                current_version_id=None,
                revision=1,
                created_by_user_id=actor.id,
                created_at=now,
                updated_at=now,
            )
            session.add(dataset)
            session.flush()
            version = DatasetVersion(
                id=uuid4(),
                workspace_id=project.workspace_id,
                project_id=project.id,
                dataset_id=dataset.id,
                version_number=1,
                kind=DatasetVersionKind.RAW.value,
                state=DatasetVersionState.READY.value,
                source_document_version_id=source.id,
                parent_version_id=None,
                manifest={
                    "filename": source.filename,
                    "content_sha256": source.content_hash,
                    "media_type": source.media_type,
                    "size_bytes": source.size_bytes,
                    "document_version_id": str(source.id),
                    "sheet_name": parsed.sheet_name,
                    "source_label": source_label,
                    "synthetic": synthetic,
                    "received_at": source.ingested_at.isoformat(),
                    "registered_at": now.isoformat(),
                    "expected_files": 1,
                    "data_dictionary": parsed.columns,
                    "missing_files": [],
                },
                transformation=None,
                rows_sha256=rows_sha256,
                row_count=len(parsed.rows),
                columns=parsed.columns,
                quality_findings=parsed.quality_findings,
                created_by_user_id=actor.id,
                created_at=now,
            )
            session.add(version)
            session.flush()
            dataset.current_version_id = version.id
            _insert_rows(
                session,
                project=project,
                version=version,
                rows=parsed.rows,
            )
            session.add(
                CommandReceipt(
                    id=uuid4(),
                    actor_user_id=actor.id,
                    route=route,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    response_payload=DatasetReceiptPayload(
                        dataset_id=dataset.id,
                        version_id=version.id,
                    ).model_dump(mode="json"),
                    resource_id=dataset.id,
                    created_at=now,
                )
            )
            _append_event(
                session,
                project=project,
                event_type="dataset.imported",
                object_type="dataset_version",
                object_id=version.id,
                object_revision=1,
                actor_user_id=actor.id,
                payload={
                    "dataset_id": str(dataset.id),
                    "row_count": version.row_count,
                    "synthetic": synthetic,
                },
                now=now,
            )
            return self._dataset_view(session, dataset)

    def derive_version(
        self,
        *,
        project_id: UUID,
        dataset_id: UUID,
        actor_user_id: UUID,
        parent_version_id: UUID,
        spec: CleaningSpec,
        idempotency_key: str,
    ) -> DatasetView:
        if not idempotency_key.strip():
            raise ValueError("Derivation idempotency key is required")
        request_hash = _digest(
            {
                "dataset_id": str(dataset_id),
                "parent_version_id": str(parent_version_id),
                "spec": spec.model_dump(mode="json"),
            }
        )
        route = f"datasets.derive:{dataset_id}"
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _locked_project(session, project_id, actor.workspace_id)
            dataset = _dataset(session, dataset_id, project.id, for_update=True)
            receipt = _find_receipt(session, actor.id, route, idempotency_key)
            if receipt is not None:
                return self._replay_dataset(session, receipt, request_hash)
            parent = _dataset_version(session, parent_version_id, dataset.id)
            if parent.state != DatasetVersionState.READY.value:
                raise PlanStateError("Only a ready dataset version can be transformed")
            missing = set(spec.select_columns) - set(parent.columns)
            if missing:
                raise ValueError(f"Selected columns do not exist: {sorted(missing)}")
            source_rows = _dataset_rows(session, parent.id)
            derived_rows = _derive_rows(source_rows, spec)
            if not derived_rows:
                raise ValueError("Cleaning removed every row")
            now = datetime.now(UTC)
            version_number = (
                session.scalar(
                    select(func.max(DatasetVersion.version_number)).where(
                        DatasetVersion.dataset_id == dataset.id
                    )
                )
                or 0
            ) + 1
            columns = [spec.rename_columns.get(column, column) for column in spec.select_columns]
            version = DatasetVersion(
                id=uuid4(),
                workspace_id=project.workspace_id,
                project_id=project.id,
                dataset_id=dataset.id,
                version_number=version_number,
                kind=DatasetVersionKind.DERIVED.value,
                state=DatasetVersionState.READY.value,
                source_document_version_id=None,
                parent_version_id=parent.id,
                manifest={
                    "parent_version_id": str(parent.id),
                    "parent_rows_sha256": parent.rows_sha256,
                    "source_document_version_id": str(parent.source_document_version_id),
                    "data_dictionary": columns,
                },
                transformation=spec.model_dump(mode="json"),
                rows_sha256=_digest(derived_rows),
                row_count=len(derived_rows),
                columns=columns,
                quality_findings=[
                    {
                        "code": "DERIVED_VERSION",
                        "parent_version_id": str(parent.id),
                        "rows_before": parent.row_count,
                        "rows_after": len(derived_rows),
                    }
                ],
                created_by_user_id=actor.id,
                created_at=now,
            )
            session.add(version)
            session.flush()
            _insert_rows(
                session,
                project=project,
                version=version,
                rows=derived_rows,
            )
            dataset.current_version_id = version.id
            dataset.revision += 1
            dataset.updated_at = now
            session.add(
                CommandReceipt(
                    id=uuid4(),
                    actor_user_id=actor.id,
                    route=route,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    response_payload=DatasetReceiptPayload(
                        dataset_id=dataset.id,
                        version_id=version.id,
                    ).model_dump(mode="json"),
                    resource_id=dataset.id,
                    created_at=now,
                )
            )
            _append_event(
                session,
                project=project,
                event_type="dataset.version_derived",
                object_type="dataset_version",
                object_id=version.id,
                object_revision=version_number,
                actor_user_id=actor.id,
                payload={
                    "parent_version_id": str(parent.id),
                    "row_count": version.row_count,
                },
                now=now,
            )
            return self._dataset_view(session, dataset)

    def create_plan(
        self,
        *,
        project_id: UUID,
        dataset_version_id: UUID,
        actor_user_id: UUID,
        spec: StatisticalPlanSpec,
        idempotency_key: str,
    ) -> StatisticalPlanView:
        if not idempotency_key.strip():
            raise ValueError("Statistical plan idempotency key is required")
        request_hash = _digest(
            {
                "dataset_version_id": str(dataset_version_id),
                "spec": spec.model_dump(mode="json"),
            }
        )
        route = f"statistics.plan:{dataset_version_id}"
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _locked_project(session, project_id, actor.workspace_id)
            receipt = _find_receipt(session, actor.id, route, idempotency_key)
            if receipt is not None:
                payload = PlanReceiptPayload.model_validate(receipt.response_payload)
                if receipt.request_hash != request_hash:
                    raise ConflictingOperationError(
                        "Plan idempotency key was reused with different parameters"
                    )
                plan = session.get(StatisticalPlan, payload.plan_id)
                if plan is None:
                    raise NotFoundError("Statistical plan from receipt not found")
                return _plan_view(plan)
            version = _version_in_project(
                session,
                dataset_version_id,
                project.id,
            )
            if version.state != DatasetVersionState.READY.value:
                raise PlanStateError("Statistical plan requires a ready dataset version")
            rows = _dataset_rows(session, version.id)
            _validate_plan_columns(spec, version.columns, rows)
            plan_version = (
                session.scalar(
                    select(func.max(StatisticalPlan.plan_version)).where(
                        StatisticalPlan.dataset_version_id == version.id
                    )
                )
                or 0
            ) + 1
            now = datetime.now(UTC)
            plan = StatisticalPlan(
                id=uuid4(),
                workspace_id=project.workspace_id,
                project_id=project.id,
                dataset_version_id=version.id,
                plan_version=plan_version,
                question=spec.question,
                endpoint_column=spec.endpoint_column,
                method=spec.method.value,
                group_column=spec.group_column,
                analysis_set=spec.analysis_set,
                missing_policy=spec.missing_policy,
                unit=spec.unit,
                alpha=Decimal(str(spec.alpha)),
                expected_groups=spec.expected_groups,
                limitations=spec.limitations,
                exploratory=spec.exploratory,
                created_by_user_id=actor.id,
                created_at=now,
            )
            session.add(plan)
            session.flush()
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
            _append_event(
                session,
                project=project,
                event_type="analysis.plan_created",
                object_type="statistical_plan",
                object_id=plan.id,
                object_revision=plan_version,
                actor_user_id=actor.id,
                payload={"method": plan.method, "dataset_version_id": str(version.id)},
                now=now,
            )
            return _plan_view(plan)

    def run_analysis(
        self,
        *,
        project_id: UUID,
        plan_id: UUID,
        actor_user_id: UUID,
        idempotency_key: str,
    ) -> AnalysisRunView:
        if not idempotency_key.strip():
            raise ValueError("Analysis idempotency key is required")
        request_hash = _digest({"plan_id": str(plan_id), "code_version": ANALYSIS_CODE_VERSION})
        route = f"statistics.run:{plan_id}"
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _locked_project(session, project_id, actor.workspace_id)
            receipt = _find_receipt(session, actor.id, route, idempotency_key)
            if receipt is not None:
                if receipt.request_hash != request_hash:
                    raise ConflictingOperationError(
                        "Analysis idempotency key was reused with different parameters"
                    )
                payload = AnalysisReceiptPayload.model_validate(receipt.response_payload)
                analysis = session.get(AnalysisRun, payload.analysis_id)
                if analysis is None:
                    raise NotFoundError("Analysis from receipt not found")
                return self._analysis_view(session, analysis)
            plan = _plan_in_project(session, plan_id, project.id)
            version = _version_in_project(
                session,
                plan.dataset_version_id,
                project.id,
            )
            rows = _dataset_rows(session, version.id)
            result, chart = _calculate_analysis(plan, rows)
            result_hash = _digest({"result": result, "chart": chart})
            code_hash = hashlib.sha256(
                inspect.getsource(_calculate_analysis).encode("utf-8")
            ).hexdigest()
            input_hash = _digest(
                {
                    "dataset_version_id": str(version.id),
                    "rows_sha256": version.rows_sha256,
                    "plan_id": str(plan.id),
                    "code_version": ANALYSIS_CODE_VERSION,
                    "code_sha256": code_hash,
                }
            )
            analysis_version = (
                session.scalar(
                    select(func.max(AnalysisRun.analysis_version)).where(
                        AnalysisRun.plan_id == plan.id
                    )
                )
                or 0
            ) + 1
            now = datetime.now(UTC)
            analysis = AnalysisRun(
                id=uuid4(),
                workspace_id=project.workspace_id,
                project_id=project.id,
                dataset_version_id=version.id,
                plan_id=plan.id,
                analysis_version=analysis_version,
                code_version=ANALYSIS_CODE_VERSION,
                code_sha256=code_hash,
                environment={
                    "python": platform.python_version(),
                    "implementation": platform.python_implementation(),
                },
                random_seed=0,
                state=AnalysisState.SUCCEEDED.value,
                result=result,
                chart_spec=chart,
                input_sha256=input_hash,
                output_sha256=result_hash,
                error_code=None,
                created_by_user_id=actor.id,
                created_at=now,
            )
            session.add(analysis)
            session.flush()
            session.add(
                CommandReceipt(
                    id=uuid4(),
                    actor_user_id=actor.id,
                    route=route,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    response_payload=AnalysisReceiptPayload(analysis_id=analysis.id).model_dump(
                        mode="json"
                    ),
                    resource_id=analysis.id,
                    created_at=now,
                )
            )
            _append_event(
                session,
                project=project,
                event_type="analysis.succeeded",
                object_type="analysis",
                object_id=analysis.id,
                object_revision=analysis_version,
                actor_user_id=actor.id,
                payload={
                    "plan_id": str(plan.id),
                    "dataset_version_id": str(version.id),
                    "output_sha256": result_hash,
                },
                now=now,
            )
            return self._analysis_view(session, analysis)

    def review_analysis(
        self,
        *,
        project_id: UUID,
        analysis_id: UUID,
        actor_user_id: UUID,
        reviewer_role: str,
        decision: ReviewDecision,
        summary: str,
        findings: list[ReviewFinding],
        idempotency_key: str,
    ) -> AnalysisReviewView:
        if not summary.strip() or not idempotency_key.strip():
            raise ValueError("Review summary and idempotency key are required")
        request_hash = _digest(
            {
                "analysis_id": str(analysis_id),
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
            existing = session.scalar(
                select(AnalysisReview).where(
                    AnalysisReview.analysis_id == analysis_id,
                    AnalysisReview.idempotency_key == idempotency_key,
                )
            )
            if existing is not None:
                if existing.request_hash != request_hash:
                    raise ConflictingOperationError(
                        "Review idempotency key was reused with different parameters"
                    )
                return _review_view(existing)
            analysis = session.scalar(
                select(AnalysisRun)
                .where(
                    AnalysisRun.id == analysis_id,
                    AnalysisRun.project_id == project.id,
                )
                .with_for_update()
            )
            if analysis is None:
                raise NotFoundError("Analysis not found")
            reviewer = self._roles.get(reviewer_role)
            if reviewer is None or reviewer_role not in {"A14", "A25", "A26"}:
                raise ReviewPolicyError("Analysis review requires A14, A25 or A26 configured role")
            critical = any(item.severity == FindingSeverity.CRITICAL for item in findings)
            if critical and decision != ReviewDecision.CHANGES_REQUESTED:
                raise ReviewPolicyError("A critical finding requires changes_requested")
            now = datetime.now(UTC)
            review = AnalysisReview(
                id=uuid4(),
                workspace_id=project.workspace_id,
                project_id=project.id,
                analysis_id=analysis.id,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                reviewer_user_id=actor.id,
                reviewer_role=reviewer_role,
                decision=decision.value,
                summary=summary,
                findings=[item.model_dump(mode="json") for item in findings],
                result_sha256=analysis.output_sha256,
                created_at=now,
            )
            session.add(review)
            session.flush()
            _append_event(
                session,
                project=project,
                event_type="analysis.reviewed",
                object_type="analysis",
                object_id=analysis.id,
                object_revision=analysis.analysis_version,
                actor_user_id=actor.id,
                payload={
                    "review_id": str(review.id),
                    "decision": decision.value,
                    "reviewer_role": reviewer_role,
                },
                now=now,
            )
            return _review_view(review)

    def list_datasets(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
    ) -> list[DatasetView]:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            datasets = session.scalars(
                select(Dataset)
                .where(Dataset.project_id == project.id)
                .order_by(Dataset.updated_at.desc())
            ).all()
            return [self._dataset_view(session, dataset) for dataset in datasets]

    def get_dataset(
        self,
        *,
        project_id: UUID,
        dataset_id: UUID,
        actor_user_id: UUID,
    ) -> DatasetView:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            dataset = _dataset(session, dataset_id, project.id)
            return self._dataset_view(session, dataset)

    def list_analyses(
        self,
        *,
        project_id: UUID,
        dataset_version_id: UUID | None,
        actor_user_id: UUID,
    ) -> list[AnalysisRunView]:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            statement = select(AnalysisRun).where(AnalysisRun.project_id == project.id)
            if dataset_version_id is not None:
                statement = statement.where(AnalysisRun.dataset_version_id == dataset_version_id)
            analyses = session.scalars(statement.order_by(AnalysisRun.created_at.desc())).all()
            return [self._analysis_view(session, analysis) for analysis in analyses]

    def _dataset_view(self, session: Session, dataset: Dataset) -> DatasetView:
        if dataset.current_version_id is None:
            raise RuntimeError("Dataset has no current version")
        current = _dataset_version(session, dataset.current_version_id, dataset.id)
        versions = session.scalars(
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset.id)
            .order_by(DatasetVersion.version_number.desc())
        ).all()
        return DatasetView(
            id=dataset.id,
            project_id=dataset.project_id,
            title=dataset.title,
            revision=dataset.revision,
            current_version=_version_view(session, current),
            versions=[_version_view(session, version) for version in versions],
            created_at=dataset.created_at,
            updated_at=dataset.updated_at,
        )

    def _analysis_view(
        self,
        session: Session,
        analysis: AnalysisRun,
    ) -> AnalysisRunView:
        review = session.scalar(
            select(AnalysisReview)
            .where(AnalysisReview.analysis_id == analysis.id)
            .order_by(AnalysisReview.created_at.desc())
            .limit(1)
        )
        return AnalysisRunView(
            id=analysis.id,
            project_id=analysis.project_id,
            dataset_version_id=analysis.dataset_version_id,
            plan_id=analysis.plan_id,
            analysis_version=analysis.analysis_version,
            code_version=analysis.code_version,
            code_sha256=analysis.code_sha256,
            environment=analysis.environment,
            random_seed=analysis.random_seed,
            state=AnalysisState(analysis.state),
            result=analysis.result,
            chart_spec=analysis.chart_spec,
            input_sha256=analysis.input_sha256,
            output_sha256=analysis.output_sha256,
            error_code=analysis.error_code,
            created_at=analysis.created_at,
            latest_review=_review_view(review) if review is not None else None,
        )

    def _replay_dataset(
        self,
        session: Session,
        receipt: CommandReceipt,
        request_hash: str,
    ) -> DatasetView:
        if receipt.request_hash != request_hash:
            raise ConflictingOperationError(
                "Dataset idempotency key was reused with different parameters"
            )
        payload = DatasetReceiptPayload.model_validate(receipt.response_payload)
        dataset = session.get(Dataset, payload.dataset_id)
        if dataset is None:
            raise NotFoundError("Dataset from receipt not found")
        return self._dataset_view(session, dataset)


def _owner(session: Session, actor_user_id: UUID) -> User:
    actor = session.get(User, actor_user_id)
    if actor is None:
        raise NotFoundError("User not found")
    if not actor.is_owner:
        raise PermissionError("Only the verified workspace owner can manage datasets")
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


def _dataset(
    session: Session,
    dataset_id: UUID,
    project_id: UUID,
    *,
    for_update: bool = False,
) -> Dataset:
    statement = select(Dataset).where(
        Dataset.id == dataset_id,
        Dataset.project_id == project_id,
    )
    if for_update:
        statement = statement.with_for_update()
    dataset = session.scalar(statement)
    if dataset is None:
        raise NotFoundError("Dataset not found")
    return dataset


def _dataset_version(
    session: Session,
    version_id: UUID,
    dataset_id: UUID,
) -> DatasetVersion:
    version = session.scalar(
        select(DatasetVersion).where(
            DatasetVersion.id == version_id,
            DatasetVersion.dataset_id == dataset_id,
        )
    )
    if version is None:
        raise NotFoundError("Dataset version not found")
    return version


def _version_in_project(
    session: Session,
    version_id: UUID,
    project_id: UUID,
) -> DatasetVersion:
    version = session.scalar(
        select(DatasetVersion).where(
            DatasetVersion.id == version_id,
            DatasetVersion.project_id == project_id,
        )
    )
    if version is None:
        raise NotFoundError("Dataset version not found")
    return version


def _plan_in_project(
    session: Session,
    plan_id: UUID,
    project_id: UUID,
) -> StatisticalPlan:
    plan = session.scalar(
        select(StatisticalPlan).where(
            StatisticalPlan.id == plan_id,
            StatisticalPlan.project_id == project_id,
        )
    )
    if plan is None:
        raise NotFoundError("Statistical plan not found")
    return plan


def _dataset_rows(session: Session, version_id: UUID) -> list[dict[str, Any]]:
    rows = session.execute(
        select(DatasetRow.row_data)
        .where(DatasetRow.dataset_version_id == version_id)
        .order_by(DatasetRow.row_index)
    ).all()
    return [row.row_data for row in rows]


def _insert_rows(
    session: Session,
    *,
    project: Project,
    version: DatasetVersion,
    rows: list[dict[str, Any]],
) -> None:
    for index, row in enumerate(rows):
        session.add(
            DatasetRow(
                id=uuid4(),
                workspace_id=project.workspace_id,
                project_id=project.id,
                dataset_version_id=version.id,
                row_index=index,
                row_data=row,
            )
        )
    session.flush()


def _derive_rows(
    source_rows: list[dict[str, Any]],
    spec: CleaningSpec,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in source_rows:
        if any(row.get(column) is None for column in spec.drop_missing_columns):
            continue
        transformed: dict[str, Any] = {}
        invalid_numeric = False
        for column in spec.select_columns:
            output_name = spec.rename_columns.get(column, column)
            value = row.get(column)
            if column in spec.numeric_columns and value is not None:
                try:
                    value = _to_float(value)
                except ValueError as exc:
                    raise ValueError(
                        f"Column {column} contains non-numeric value: {value!r}"
                    ) from exc
                if not math.isfinite(value):
                    invalid_numeric = True
            transformed[output_name] = value
        if invalid_numeric:
            raise ValueError("Cleaning produced a non-finite numeric value")
        result.append(transformed)
    return result


def _validate_plan_columns(
    spec: StatisticalPlanSpec,
    columns: list[str],
    rows: list[dict[str, Any]],
) -> None:
    if spec.endpoint_column not in columns:
        raise ValueError("Endpoint column is not present in the dataset version")
    if spec.group_column and spec.group_column not in columns:
        raise ValueError("Group column is not present in the dataset version")
    if spec.method != StatisticalMethod.PROPORTION_WILSON:
        for row in rows:
            value = row.get(spec.endpoint_column)
            if value is not None:
                _to_float(value)


def _calculate_analysis(
    plan: StatisticalPlan,
    rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    endpoint = plan.endpoint_column
    excluded = 0
    values: list[float] = []
    for row in rows:
        raw = row.get(endpoint)
        if raw is None:
            excluded += 1
            if plan.missing_policy == "fail_if_missing":
                raise ValueError("Endpoint contains missing values under fail_if_missing")
            continue
        if plan.method == StatisticalMethod.PROPORTION_WILSON:
            number = _to_binary(raw)
        else:
            number = _to_float(raw)
        values.append(number)
    if not values:
        raise ValueError("No endpoint observations remain")

    if plan.method == StatisticalMethod.DESCRIPTIVE_CONTINUOUS.value:
        ordered = sorted(values)
        mean = statistics.fmean(values)
        sd = statistics.stdev(values) if len(values) >= 2 else None
        half_width = (
            statistics.NormalDist().inv_cdf(1 - float(plan.alpha) / 2) * sd / math.sqrt(len(values))
            if sd is not None
            else None
        )
        summary = {
            "method": plan.method,
            "n": len(values),
            "excluded_endpoint_missing": excluded,
            "mean": mean,
            "median": statistics.median(values),
            "sd": sd,
            "q1": _quantile(ordered, 0.25),
            "q3": _quantile(ordered, 0.75),
            "minimum": ordered[0],
            "maximum": ordered[-1],
            "ci_lower": mean - half_width if half_width is not None else None,
            "ci_upper": mean + half_width if half_width is not None else None,
            "ci_method": "normal_approximation",
            "unit": plan.unit,
            "exploratory": plan.exploratory,
            "limitations": plan.limitations,
        }
        chart = {
            "kind": "summary_interval",
            "label": endpoint,
            "value": mean,
            "lower": summary["ci_lower"],
            "upper": summary["ci_upper"],
            "unit": plan.unit,
        }
        return summary, chart

    if plan.method == StatisticalMethod.TWO_GROUP_MEAN_DIFFERENCE.value:
        assert plan.group_column is not None
        groups: dict[str, list[float]] = {group: [] for group in plan.expected_groups}
        for row in rows:
            raw_endpoint = row.get(endpoint)
            raw_group = row.get(plan.group_column)
            if raw_endpoint is None:
                continue
            group = str(raw_group)
            if group not in groups:
                raise ValueError(f"Unexpected group value: {group}")
            groups[group].append(_to_float(raw_endpoint))
        first, second = plan.expected_groups
        if len(groups[first]) < 2 or len(groups[second]) < 2:
            raise ValueError("Each group needs at least two observations")
        mean_first = statistics.fmean(groups[first])
        mean_second = statistics.fmean(groups[second])
        variance_first = statistics.variance(groups[first])
        variance_second = statistics.variance(groups[second])
        standard_error = math.sqrt(
            variance_first / len(groups[first]) + variance_second / len(groups[second])
        )
        difference = mean_first - mean_second
        half_width = statistics.NormalDist().inv_cdf(1 - float(plan.alpha) / 2) * standard_error
        result = {
            "method": plan.method,
            "groups": {
                first: {"n": len(groups[first]), "mean": mean_first},
                second: {"n": len(groups[second]), "mean": mean_second},
            },
            "difference": difference,
            "standard_error": standard_error,
            "ci_lower": difference - half_width,
            "ci_upper": difference + half_width,
            "ci_method": "normal_approximation",
            "p_value": None,
            "unit": plan.unit,
            "exploratory": plan.exploratory,
            "limitations": plan.limitations,
        }
        chart = {
            "kind": "group_means",
            "labels": [first, second],
            "values": [mean_first, mean_second],
            "unit": plan.unit,
        }
        return result, chart

    successes = int(sum(values))
    count = len(values)
    proportion = successes / count
    z = statistics.NormalDist().inv_cdf(1 - float(plan.alpha) / 2)
    denominator = 1 + z * z / count
    center = (proportion + z * z / (2 * count)) / denominator
    margin = (
        z
        * math.sqrt(proportion * (1 - proportion) / count + z * z / (4 * count * count))
        / denominator
    )
    result = {
        "method": plan.method,
        "n": count,
        "successes": successes,
        "proportion": proportion,
        "ci_lower": center - margin,
        "ci_upper": center + margin,
        "ci_method": "wilson",
        "exploratory": plan.exploratory,
        "limitations": plan.limitations,
    }
    chart = {
        "kind": "proportion_interval",
        "label": endpoint,
        "value": proportion,
        "lower": result["ci_lower"],
        "upper": result["ci_upper"],
    }
    return result, chart


def _to_float(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("Boolean is not a continuous numeric value")
    try:
        number = float(value)
    except (TypeError, ValueError, InvalidOperation) as exc:
        raise ValueError(f"Not numeric: {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError("Non-finite numeric value")
    return number


def _to_binary(value: Any) -> float:
    if value is True or value == 1 or value == "1":
        return 1.0
    if value is False or value == 0 or value == "0":
        return 0.0
    raise ValueError(f"Proportion endpoint must be binary: {value!r}")


def _quantile(ordered: list[float], probability: float) -> float:
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _version_view(session: Session, version: DatasetVersion) -> DatasetVersionView:
    preview = [
        row.row_data
        for row in session.scalars(
            select(DatasetRow)
            .where(DatasetRow.dataset_version_id == version.id)
            .order_by(DatasetRow.row_index)
            .limit(5)
        )
    ]
    return DatasetVersionView(
        id=version.id,
        dataset_id=version.dataset_id,
        version_number=version.version_number,
        kind=DatasetVersionKind(version.kind),
        state=DatasetVersionState(version.state),
        source_document_version_id=version.source_document_version_id,
        parent_version_id=version.parent_version_id,
        manifest=version.manifest,
        transformation=version.transformation,
        rows_sha256=version.rows_sha256,
        row_count=version.row_count,
        columns=version.columns,
        quality_findings=version.quality_findings,
        preview=preview,
        created_at=version.created_at,
    )


def _plan_view(plan: StatisticalPlan) -> StatisticalPlanView:
    return StatisticalPlanView(
        id=plan.id,
        project_id=plan.project_id,
        dataset_version_id=plan.dataset_version_id,
        plan_version=plan.plan_version,
        question=plan.question,
        endpoint_column=plan.endpoint_column,
        method=StatisticalMethod(plan.method),
        group_column=plan.group_column,
        analysis_set=plan.analysis_set,
        missing_policy=plan.missing_policy,
        unit=plan.unit,
        alpha=float(plan.alpha),
        expected_groups=plan.expected_groups,
        limitations=plan.limitations,
        exploratory=plan.exploratory,
        created_at=plan.created_at,
    )


def _review_view(review: AnalysisReview) -> AnalysisReviewView:
    return AnalysisReviewView(
        id=review.id,
        analysis_id=review.analysis_id,
        decision=ReviewDecision(review.decision),
        reviewer_role=review.reviewer_role,
        summary=review.summary,
        findings=[ReviewFinding.model_validate(item) for item in review.findings],
        result_sha256=review.result_sha256,
        created_at=review.created_at,
    )


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


def _append_event(
    session: Session,
    *,
    project: Project,
    event_type: str,
    object_type: str,
    object_id: UUID,
    object_revision: int,
    actor_user_id: UUID,
    payload: dict[str, Any],
    now: datetime,
) -> None:
    last_sequence = session.scalar(
        select(ProjectEvent.project_seq)
        .where(ProjectEvent.project_id == project.id)
        .order_by(ProjectEvent.project_seq.desc())
        .limit(1)
    )
    session.add(
        ProjectEvent(
            id=uuid4(),
            workspace_id=project.workspace_id,
            project_id=project.id,
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


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
