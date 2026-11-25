from __future__ import annotations

import hashlib
import json
import re
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.errors import (
    ConflictingOperationError,
    NotFoundError,
)
from medical_one_person.domain.artifacts import ArtifactMode, ArtifactOrigin
from medical_one_person.domain.exports import (
    ExportFormat,
    ExportState,
    ExportTemplate,
    ReportCalculation,
    ReportReview,
    ReportSection,
    ReportSource,
    ReportTable,
    StructuredReport,
)
from medical_one_person.infrastructure.artifacts import LocalArtifactStore
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    AnalysisReview,
    AnalysisRun,
    Artifact,
    ArtifactExport,
    ArtifactVersion,
    Dataset,
    DatasetRow,
    DatasetVersion,
    Project,
    ProjectEvent,
    StatisticalPlan,
    User,
)
from medical_one_person.infrastructure.exports.engine import (
    ExportValidationError,
    OfficeExportEngine,
)
from medical_one_person.infrastructure.exports.renderer import (
    OfficeRenderer,
    OfficeRendererError,
    OfficeRendererUnavailable,
    OfficeRuntimeStatus,
)
from medical_one_person.infrastructure.exports.templates import ExportTemplateRegistry


class ExportRuntimeUnavailable(Exception):
    pass


@dataclass(frozen=True)
class ExportFile:
    content: bytes
    filename: str
    media_type: str


@dataclass(frozen=True)
class ReportSnapshot:
    report: StructuredReport
    rows: list[dict[str, Any]]
    input_sha256: str


class ArtifactExportView(BaseModel):
    id: UUID
    project_id: UUID
    analysis_id: UUID
    artifact_version_id: UUID | None
    version: int | None
    filename: str
    format: ExportFormat
    media_type: str
    template_id: str
    template_version: int
    mode: str
    data_origin: str
    state: ExportState
    validation_status: str
    revision: int
    art_sha256: str | None
    size_bytes: int | None
    preview_pdf_sha256: str | None
    preview_png_sha256: str | None
    page_count: int | None
    validation: dict[str, Any]
    source_sha256: str
    report_sha256: str
    error_code: str | None
    error_message: str | None
    download_url: str | None
    preview_pdf_url: str | None
    preview_png_url: str | None
    created_at: datetime
    completed_at: datetime | None


class ArtifactExportService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        store: LocalArtifactStore,
        renderer: OfficeRenderer,
        templates: ExportTemplateRegistry,
        *,
        mode: ArtifactMode,
        pdf_font_path: Path | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._store = store
        self._renderer = renderer
        self._engine = OfficeExportEngine(renderer, pdf_font_path=pdf_font_path)
        self._templates = templates
        self._mode = mode

    def runtime_status(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
    ) -> OfficeRuntimeStatus:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            _project(session, project_id, actor.workspace_id)
        return self._renderer.status()

    def list_exports(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
    ) -> list[ArtifactExportView]:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            exports = session.scalars(
                select(ArtifactExport)
                .where(ArtifactExport.project_id == project.id)
                .order_by(ArtifactExport.created_at.desc())
            ).all()
            return [_export_view(session, export) for export in exports]

    def create_export(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        analysis_id: UUID,
        export_format: ExportFormat,
        template_id: str | None,
        title: str | None,
        idempotency_key: str,
    ) -> ArtifactExportView:
        if not idempotency_key.strip():
            raise ValueError("Idempotency key is required")
        template = self._resolve_template(export_format, template_id)
        snapshot = self._report_snapshot(
            project_id=project_id,
            actor_user_id=actor_user_id,
            analysis_id=analysis_id,
        )
        report = snapshot.report
        if title is not None and title.strip():
            report = report.model_copy(update={"title": title.strip()})
        report_sha256 = _digest(report.model_dump(mode="json"))
        request_hash = _digest(
            {
                "analysis_id": str(analysis_id),
                "format": export_format.value,
                "template_id": template.template_id,
                "template_version": template.version,
                "title": report.title,
                "mode": self._mode.value,
            }
        )
        filename = (
            f"{_safe_filename(report.title)}-analysis-v"
            f"{_analysis_version(snapshot.report)}.{export_format.value}"
        )
        export_id = self._claim(
            project_id=project_id,
            actor_user_id=actor_user_id,
            analysis_id=analysis_id,
            export_format=export_format,
            template=template,
            report=report,
            filename=filename,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            input_sha256=snapshot.input_sha256,
            report_sha256=report_sha256,
        )
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            claimed = session.get(ArtifactExport, export_id)
            if claimed is None:
                raise NotFoundError("Export record not found")
            if claimed.state == ExportState.SUCCEEDED.value:
                return _export_view(session, claimed)

        try:
            with tempfile.TemporaryDirectory(prefix="medical-one-export-") as temporary:
                workdir = Path(temporary)
                generated = self._engine.generate(
                    report=report,
                    rows=snapshot.rows,
                    export_format=export_format,
                    workdir=workdir,
                )
                output = self._store.put_path(generated.file_path)
                preview_pdf = self._store.put(generated.preview.pdf_bytes)
                preview_png = self._store.put(generated.preview.first_page_png)
        except OfficeRendererUnavailable as exc:
            self._mark_failed(
                export_id,
                actor_user_id,
                "OFFICE_RUNTIME_UNAVAILABLE",
                str(exc),
            )
            raise ExportRuntimeUnavailable(str(exc)) from exc
        except (ExportValidationError, OfficeRendererError) as exc:
            self._mark_failed(
                export_id,
                actor_user_id,
                "EXPORT_VALIDATION_FAILED",
                str(exc),
            )
            raise ValueError(f"Export validation failed: {exc}") from exc
        except Exception as exc:
            self._mark_failed(
                export_id,
                actor_user_id,
                "EXPORT_GENERATION_FAILED",
                str(exc),
            )
            raise

        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            export = session.scalar(
                select(ArtifactExport)
                .where(
                    ArtifactExport.id == export_id,
                    ArtifactExport.project_id == project.id,
                )
                .with_for_update()
            )
            if export is None:
                raise NotFoundError("Export record not found")
            if export.state == ExportState.SUCCEEDED.value:
                return _export_view(session, export)
            now = datetime.now(UTC)
            artifact = session.scalar(
                select(Artifact).where(
                    Artifact.project_id == project.id,
                    Artifact.title == f"{report.title}（{export_format.value.upper()}）",
                )
            )
            if artifact is None:
                artifact = Artifact(
                    id=uuid4(),
                    workspace_id=project.workspace_id,
                    project_id=project.id,
                    title=f"{report.title}（{export_format.value.upper()}）",
                    created_by_user_id=actor.id,
                    created_at=now,
                )
                session.add(artifact)
                session.flush()
            current_version = session.scalar(
                select(func.max(ArtifactVersion.version)).where(
                    ArtifactVersion.artifact_id == artifact.id
                )
            )
            artifact_version = ArtifactVersion(
                id=uuid4(),
                project_id=project.id,
                artifact_id=artifact.id,
                version=(current_version or 0) + 1,
                media_type=export_format.media_type,
                object_key=output.object_key,
                sha256=output.sha256,
                size_bytes=output.size_bytes,
                mode=self._mode.value,
                raw_or_derived=ArtifactOrigin.DERIVED.value,
                validation_status="passed",
                producer="office.export.w14.v1",
                created_at=now,
            )
            session.add(artifact_version)
            session.flush()
            export.artifact_version_id = artifact_version.id
            export.state = ExportState.SUCCEEDED.value
            export.validation_status = "passed"
            export.validation = generated.validation
            export.preview_pdf_object_key = preview_pdf.object_key
            export.preview_pdf_sha256 = preview_pdf.sha256
            export.preview_pdf_size_bytes = preview_pdf.size_bytes
            export.preview_png_object_key = preview_png.object_key
            export.preview_png_sha256 = preview_png.sha256
            export.preview_png_size_bytes = preview_png.size_bytes
            export.page_count = generated.preview.page_count
            export.error_code = None
            export.error_message = None
            export.revision += 1
            export.completed_at = now
            session.flush()
            _append_event(
                session,
                project=project,
                actor_user_id=actor.id,
                event_type="artifact.export_completed",
                object_id=export.id,
                object_revision=export.revision,
                payload={
                    "analysis_id": str(export.analysis_id),
                    "artifact_version_id": str(artifact_version.id),
                    "format": export_format.value,
                    "sha256": artifact_version.sha256,
                    "template_id": template.template_id,
                    "template_version": template.version,
                    "validation_status": "passed",
                },
                now=now,
            )
            return _export_view(session, export)

    def read_output(
        self,
        *,
        project_id: UUID,
        export_id: UUID,
        actor_user_id: UUID,
    ) -> ExportFile:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            _project(session, project_id, actor.workspace_id)
            export = _export(session, project_id, export_id)
            if export.state != ExportState.SUCCEEDED.value or not export.artifact_version_id:
                raise NotFoundError("Completed export not found")
            version = session.get(ArtifactVersion, export.artifact_version_id)
            if version is None or version.project_id != project_id:
                raise NotFoundError("Export artifact version not found")
            content = self._store.read(version.object_key, version.sha256)
            return ExportFile(
                content=content,
                filename=export.filename,
                media_type=export.media_type,
            )

    def read_preview(
        self,
        *,
        project_id: UUID,
        export_id: UUID,
        actor_user_id: UUID,
        png: bool,
    ) -> bytes:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            _project(session, project_id, actor.workspace_id)
            export = _export(session, project_id, export_id)
            if export.state != ExportState.SUCCEEDED.value:
                raise NotFoundError("Export preview not found")
            if png:
                assert export.preview_png_object_key is not None
                assert export.preview_png_sha256 is not None
                return self._store.read(
                    export.preview_png_object_key,
                    export.preview_png_sha256,
                )
            assert export.preview_pdf_object_key is not None
            assert export.preview_pdf_sha256 is not None
            return self._store.read(
                export.preview_pdf_object_key,
                export.preview_pdf_sha256,
            )

    def _resolve_template(
        self,
        export_format: ExportFormat,
        template_id: str | None,
    ) -> ExportTemplate:
        if template_id is None:
            return self._templates.default_for(export_format)
        matches = [
            template
            for template in self._templates.templates
            if template.template_id == template_id
        ]
        if not matches:
            raise ValueError("Export template is not registered")
        if matches[0].format != export_format:
            raise ValueError("Export template format does not match the requested format")
        return matches[0]

    def _claim(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        analysis_id: UUID,
        export_format: ExportFormat,
        template: ExportTemplate,
        report: StructuredReport,
        filename: str,
        idempotency_key: str,
        request_hash: str,
        input_sha256: str,
        report_sha256: str,
    ) -> UUID:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            existing = session.scalar(
                select(ArtifactExport)
                .where(
                    ArtifactExport.project_id == project.id,
                    ArtifactExport.idempotency_key == idempotency_key,
                )
                .with_for_update()
            )
            now = datetime.now(UTC)
            if existing is not None:
                if existing.request_hash != request_hash:
                    raise ConflictingOperationError(
                        "Export idempotency key was reused with different parameters"
                    )
                if existing.state == ExportState.SUCCEEDED.value:
                    return existing.id
                if existing.state == ExportState.RUNNING.value:
                    raise ConflictingOperationError("Export is already running")
                existing.state = ExportState.RUNNING.value
                existing.revision += 1
                existing.validation_status = "not_checked"
                existing.validation = {}
                existing.error_code = None
                existing.error_message = None
                existing.completed_at = None
                return existing.id
            export = ArtifactExport(
                id=uuid4(),
                workspace_id=project.workspace_id,
                project_id=project.id,
                analysis_id=analysis_id,
                artifact_version_id=None,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                input_sha256=input_sha256,
                report_sha256=report_sha256,
                format=export_format.value,
                media_type=export_format.media_type,
                filename=filename,
                template_id=template.template_id,
                template_version=template.version,
                mode=self._mode.value,
                data_origin=report.data_origin,
                state=ExportState.RUNNING.value,
                validation_status="not_checked",
                revision=1,
                structured_content=report.model_dump(mode="json"),
                validation={},
                created_by_user_id=actor.id,
                created_at=now,
            )
            session.add(export)
            session.flush()
            _append_event(
                session,
                project=project,
                actor_user_id=actor.id,
                event_type="artifact.export_started",
                object_id=export.id,
                object_revision=export.revision,
                payload={
                    "analysis_id": str(analysis_id),
                    "format": export_format.value,
                    "template_id": template.template_id,
                    "template_version": template.version,
                },
                now=now,
            )
            return export.id

    def _report_snapshot(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        analysis_id: UUID,
    ) -> ReportSnapshot:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            analysis = session.scalar(
                select(AnalysisRun).where(
                    AnalysisRun.id == analysis_id,
                    AnalysisRun.project_id == project.id,
                )
            )
            if analysis is None:
                raise NotFoundError("Analysis run not found")
            if analysis.state != "succeeded":
                raise ValueError("Only a succeeded analysis can be exported")
            plan = session.get(StatisticalPlan, analysis.plan_id)
            version = session.get(DatasetVersion, analysis.dataset_version_id)
            if plan is None or version is None or plan.project_id != project.id:
                raise NotFoundError("Analysis source not found")
            dataset = session.get(Dataset, version.dataset_id)
            review = session.scalar(
                select(AnalysisReview)
                .where(AnalysisReview.analysis_id == analysis.id)
                .order_by(AnalysisReview.created_at.desc())
                .limit(1)
            )
            if dataset is None or review is None:
                raise ValueError("An accepted owner-recorded review is required before export")
            if review.decision != "accepted":
                raise ValueError("The latest analysis review must be accepted before export")
            rows = [
                item.row_data
                for item in session.scalars(
                    select(DatasetRow)
                    .where(DatasetRow.dataset_version_id == analysis.dataset_version_id)
                    .order_by(DatasetRow.row_index)
                ).all()
            ]
            synthetic = _declared_synthetic(session, version)
            data_origin: Literal["synthetic", "unknown"] = (
                "synthetic" if synthetic is True else "unknown"
            )
            method = analysis.result.get("method")
            if method not in {
                "descriptive_continuous",
                "two_group_mean_difference",
                "proportion_wilson",
            }:
                raise ValueError("Analysis method is not supported by W14 export")
            if method == "descriptive_continuous":
                reported_value = float(analysis.result["mean"])
                reported_n = int(analysis.result["n"])
            elif method == "two_group_mean_difference":
                reported_value = float(analysis.result["difference"])
                groups = analysis.result.get("groups", {})
                reported_n = sum(int(value["n"]) for value in groups.values())
            else:
                reported_value = float(analysis.result["proportion"])
                reported_n = int(analysis.result["n"])
            input_sha256 = _digest(
                {
                    "analysis_input_sha256": analysis.input_sha256,
                    "analysis_output_sha256": analysis.output_sha256,
                    "dataset_rows_sha256": version.rows_sha256,
                    "plan_id": str(plan.id),
                    "plan_version": plan.plan_version,
                    "review_id": str(review.id),
                    "review_result_sha256": review.result_sha256,
                    "code_sha256": analysis.code_sha256,
                }
            )
            method_label = {
                "descriptive_continuous": "连续终点描述统计",
                "two_group_mean_difference": "两组均值差（正态近似区间）",
                "proportion_wilson": "二分比例 Wilson 区间",
            }[method]
            result_summary = _result_summary(method, analysis.result, plan.unit)
            limitations = _dedupe(
                [
                    *plan.limitations,
                    "导出校验只覆盖文件打开、结构、重算和渲染，不证明研究设计正确。",
                    "复核是 owner 记录的岗位合同，不等于 W17 独立 Agent 或真人专家审查。",
                    "合成数据或用户声明不能代替真实研究数据与外部专业判断。",
                ]
            )
            report = StructuredReport(
                title=f"{dataset.title}｜分析报告",
                subtitle="基于版本化数据、预设统计计划和已接受复核记录",
                data_origin=data_origin,
                mode=self._mode.value,
                created_at=analysis.created_at,
                question=plan.question,
                method=method_label,
                result_summary=result_summary,
                chart=analysis.chart_spec,
                sections=[
                    ReportSection(
                        heading="研究问题",
                        paragraphs=[plan.question],
                        bullets=[
                            f"分析集：{plan.analysis_set}",
                            f"主要终点：{plan.endpoint_column}",
                            (
                                f"分组列：{plan.group_column or '不适用'}"
                                f"；预期组：{', '.join(plan.expected_groups) or '不适用'}"
                            ),
                            f"探索性分析：{'是' if plan.exploratory else '否'}",
                        ],
                    ),
                    ReportSection(
                        heading="方法与来源",
                        paragraphs=[
                            (
                                f"使用预设分析版本 v{plan.plan_version} 和 "
                                f"{method_label}。生成时固定数据行哈希、分析输出哈希与代码哈希。"
                            )
                        ],
                        bullets=[
                            f"缺失策略：{plan.missing_policy}",
                            f"单位：{plan.unit or '未指定'}",
                            "两组均值差未计算 p 值；区间不等于因果或优效证明。",
                        ],
                    ),
                    ReportSection(
                        heading="结果",
                        paragraphs=[
                            "；".join(f"{label}：{value}" for label, value in result_summary)
                        ],
                        bullets=[
                            "结果来自 W13 确定性分析运行，可回到原始分析记录。",
                            f"分析输出 SHA-256：{analysis.output_sha256}",
                        ],
                    ),
                    ReportSection(
                        heading="复核与限制",
                        paragraphs=[
                            (
                                f"{review.reviewer_role} 记录复核决定 "
                                f"{review.decision}：{review.summary}"
                            )
                        ],
                        bullets=limitations,
                    ),
                ],
                tables=[
                    ReportTable(
                        title="统计结果",
                        columns=["指标", "结果"],
                        rows=[[label, value] for label, value in result_summary],
                    ),
                    ReportTable(
                        title="来源版本",
                        columns=["类别", "对象", "版本", "SHA-256"],
                        rows=[
                            [
                                "分析运行",
                                str(analysis.id),
                                str(analysis.analysis_version),
                                analysis.output_sha256,
                            ],
                            [
                                "数据版本",
                                str(version.id),
                                str(version.version_number),
                                version.rows_sha256,
                            ],
                        ],
                    ),
                ],
                sources=[
                    ReportSource(
                        kind="project",
                        object_id=str(project.id),
                        label=f"项目：{project.name}",
                        version=str(project.revision),
                    ),
                    ReportSource(
                        kind="dataset",
                        object_id=str(dataset.id),
                        label=f"数据集：{dataset.title}",
                        version=str(dataset.revision),
                    ),
                    ReportSource(
                        kind="dataset_version",
                        object_id=str(version.id),
                        label="不可变数据版本",
                        version=f"v{version.version_number}",
                        sha256=version.rows_sha256,
                    ),
                    ReportSource(
                        kind="statistical_plan",
                        object_id=str(plan.id),
                        label="预设统计计划",
                        version=f"v{plan.plan_version}",
                    ),
                    ReportSource(
                        kind="analysis_run",
                        object_id=str(analysis.id),
                        label="确定性分析运行",
                        version=f"v{analysis.analysis_version}",
                        sha256=analysis.output_sha256,
                    ),
                    ReportSource(
                        kind="analysis_review",
                        object_id=str(review.id),
                        label=f"复核记录 {review.reviewer_role}",
                        version=review.decision,
                        sha256=review.result_sha256,
                    ),
                    ReportSource(
                        kind="code",
                        object_id=analysis.code_version,
                        label="分析代码版本",
                        version=analysis.code_version,
                        sha256=analysis.code_sha256,
                    ),
                ],
                limitations=limitations,
                review=ReportReview(
                    review_id=str(review.id),
                    reviewer_role=cast(
                        Literal["A14", "A25", "A26"],
                        review.reviewer_role,
                    ),
                    decision="accepted",
                    summary=review.summary,
                    reviewed_at=review.created_at,
                ),
                calculation=ReportCalculation(
                    method=method,
                    endpoint_column=plan.endpoint_column,
                    group_column=plan.group_column,
                    expected_groups=plan.expected_groups,
                    reported_value=reported_value,
                    reported_n=reported_n,
                    unit=plan.unit,
                ),
            )
            return ReportSnapshot(
                report=report,
                rows=rows,
                input_sha256=input_sha256,
            )

    def _mark_failed(
        self,
        export_id: UUID,
        actor_user_id: UUID,
        code: str,
        message: str,
    ) -> None:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(
                session,
                workspace_id=actor.workspace_id,
                user_id=actor.id,
            )
            export = session.scalar(
                select(ArtifactExport)
                .where(ArtifactExport.id == export_id)
                .with_for_update()
            )
            if export is None:
                return
            export.state = ExportState.FAILED.value
            export.validation_status = "failed"
            export.validation = {
                "status": "failed",
                "checks": [],
                "error_code": code,
                "error_message": message,
            }
            export.error_code = code
            export.error_message = message[:10_000]
            export.revision += 1
            export.completed_at = datetime.now(UTC)


def _owner(session: Session, actor_user_id: UUID) -> User:
    actor = session.get(User, actor_user_id)
    if actor is None:
        raise NotFoundError("User not found")
    if not actor.is_owner:
        raise PermissionError("Only the verified workspace owner can manage exports")
    return actor


def _project(session: Session, project_id: UUID, workspace_id: UUID) -> Project:
    project = session.get(Project, project_id)
    if project is None or project.workspace_id != workspace_id:
        raise NotFoundError("Project not found")
    return project


def _export(
    session: Session,
    project_id: UUID,
    export_id: UUID,
) -> ArtifactExport:
    export = session.scalar(
        select(ArtifactExport).where(
            ArtifactExport.id == export_id,
            ArtifactExport.project_id == project_id,
        )
    )
    if export is None:
        raise NotFoundError("Artifact export not found")
    return export


def _export_view(session: Session, export: ArtifactExport) -> ArtifactExportView:
    version = (
        session.get(ArtifactVersion, export.artifact_version_id)
        if export.artifact_version_id
        else None
    )
    base = f"/api/v1/projects/{export.project_id}/artifact-exports/{export.id}"
    return ArtifactExportView(
        id=export.id,
        project_id=export.project_id,
        analysis_id=export.analysis_id,
        artifact_version_id=export.artifact_version_id,
        version=version.version if version else None,
        filename=export.filename,
        format=ExportFormat(export.format),
        media_type=export.media_type,
        template_id=export.template_id,
        template_version=export.template_version,
        mode=export.mode,
        data_origin=export.data_origin,
        state=ExportState(export.state),
        validation_status=export.validation_status,
        revision=export.revision,
        art_sha256=version.sha256 if version else None,
        size_bytes=version.size_bytes if version else None,
        preview_pdf_sha256=export.preview_pdf_sha256,
        preview_png_sha256=export.preview_png_sha256,
        page_count=export.page_count,
        validation=export.validation,
        source_sha256=export.input_sha256,
        report_sha256=export.report_sha256,
        error_code=export.error_code,
        error_message=export.error_message,
        download_url=f"{base}/download" if version else None,
        preview_pdf_url=f"{base}/preview.pdf" if version else None,
        preview_png_url=f"{base}/preview.png" if version else None,
        created_at=export.created_at,
        completed_at=export.completed_at,
    )


def _append_event(
    session: Session,
    *,
    project: Project,
    actor_user_id: UUID,
    event_type: str,
    object_id: UUID,
    object_revision: int,
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
            object_type="artifact_export",
            object_id=object_id,
            object_revision=object_revision,
            payload=payload,
            correlation_id=uuid4(),
            created_at=now,
        )
    )


def _result_summary(
    method: str,
    result: dict[str, Any],
    unit: str | None,
) -> list[tuple[str, str]]:
    suffix = f" {unit}" if unit else ""
    if method == "descriptive_continuous":
        return [
            ("样本量", str(result["n"])),
            ("均值", f"{_format_number(result['mean'])}{suffix}"),
            ("中位数", f"{_format_number(result['median'])}{suffix}"),
            ("标准差", _format_optional(result.get("sd"), suffix)),
            (
                "正态近似置信区间",
                f"{_format_optional(result.get('ci_lower'))}—"
                f"{_format_optional(result.get('ci_upper'))}{suffix}",
            ),
        ]
    if method == "two_group_mean_difference":
        summary = [
            (
                "组间均值差",
                f"{_format_number(result['difference'])}{suffix}",
            )
        ]
        for group, values in result.get("groups", {}).items():
            summary.append(
                (f"{group}（n={values['n']}）", f"{_format_number(values['mean'])}{suffix}")
            )
        summary.append(
            (
                "正态近似置信区间",
                f"{_format_optional(result.get('ci_lower'))}—"
                f"{_format_optional(result.get('ci_upper'))}{suffix}",
            )
        )
        return summary
    return [
        ("样本量", str(result["n"])),
        ("成功数", str(result["successes"])),
        ("比例", _format_number(result["proportion"])),
        (
            "Wilson 置信区间",
            f"{_format_optional(result.get('ci_lower'))}—"
            f"{_format_optional(result.get('ci_upper'))}",
        ),
    ]


def _format_number(value: Any) -> str:
    return f"{float(value):.6g}"


def _format_optional(value: Any, suffix: str = "") -> str:
    return f"{_format_number(value)}{suffix}" if value is not None else "不可计算"


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _safe_filename(value: str) -> str:
    normalized = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", value, flags=re.UNICODE)
    normalized = normalized.strip("-_.")[:140]
    return normalized or "analysis-report"


def _declared_synthetic(session: Session, version: DatasetVersion) -> bool | None:
    current = version
    visited: set[UUID] = set()
    while current.id not in visited:
        visited.add(current.id)
        declared = current.manifest.get("synthetic")
        if isinstance(declared, bool):
            return declared
        if current.parent_version_id is None:
            return None
        parent = session.get(DatasetVersion, current.parent_version_id)
        if parent is None or parent.project_id != version.project_id:
            return None
        current = parent
    return None


def _analysis_version(report: StructuredReport) -> int:
    source = next(item for item in report.sources if item.kind == "analysis_run")
    return int(source.version.removeprefix("v"))


def _digest(value: Any) -> str:
    content = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(content).hexdigest()
