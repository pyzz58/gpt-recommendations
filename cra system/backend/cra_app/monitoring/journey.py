"""Read-only aggregation for the four-stage monitoring journey."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from cra_app.edc_import.service import EDCImportService
from cra_app.issues.service import IssueService, aggregate_action_status
from cra_app.laboratory.service import LaboratoryService
from cra_app.monitoring.service import MonitoringService, WorkbenchData
from cra_app.reports.service import ReportService
from cra_app.safety.service import SafetyService
from cra_app.site_files.service import SiteFileService
from cra_app.subjects.service import SubjectService


@dataclass(frozen=True)
class JourneyStage:
    key: str
    label: str
    status: str
    summary: str
    primary_action: str
    blocking: bool = False


@dataclass(frozen=True)
class MonitoringJourney:
    workbench: WorkbenchData
    stages: tuple[JourneyStage, ...]
    recommended_stage: str
    remaining_issue_ids: tuple[uuid.UUID, ...]
    remaining_issue_numbers: tuple[str, ...]
    urgent_action_count: int
    subject_count: int
    coverage_count: int
    not_checked_count: int
    active_skip_count: int
    laboratory_report_count: int
    edc_snapshot_count: int
    report_draft_count: int
    report_snapshot_count: int
    directory_missing_count: int
    generated_at: datetime
    limitations: tuple[str, ...]
    metrics: dict[str, Any]


class MonitoringJourneyService:
    """Compose existing module facts without introducing a second state store."""

    def __init__(
        self,
        *,
        monitoring: MonitoringService,
        issues: IssueService,
        subjects: SubjectService,
        laboratory: LaboratoryService,
        edc_imports: EDCImportService,
        safety: SafetyService,
        site_files: SiteFileService,
        reports: ReportService,
    ):
        self.monitoring = monitoring
        self.issues = issues
        self.subjects = subjects
        self.laboratory = laboratory
        self.edc_imports = edc_imports
        self.safety = safety
        self.site_files = site_files
        self.reports = reports

    def journey(self, scope, visit_id: uuid.UUID) -> MonitoringJourney:
        workbench = self.monitoring.workbench(scope, visit_id)
        visit = workbench.visit
        issue_details = self.issues.list_issues(
            scope, visit.study_id, visit.site_id
        )
        remaining = [
            item
            for item in issue_details
            if aggregate_action_status(item.actions) != "completed"
        ]
        urgent_count = sum(
            1
            for item in issue_details
            for action in item.actions
            if action.kind == "pd_reporting"
            and action.status not in {"completed", "reported_done"}
        )
        subject_summaries = self.subjects.list_subjects(
            scope, visit.study_id, visit.site_id
        )
        coverage_count = 0
        not_checked_count = 0
        active_skip_count = 0
        safety_alert_count = 0
        for subject in subject_summaries:
            coverage = self.subjects.list_coverage(scope, subject.subject.id)
            coverage_count += len(coverage)
            not_checked_count += sum(
                1 for item in coverage if item.status == "not_checked"
            )
            active_skip_count += sum(
                1
                for item in self.subjects.list_check_decisions(
                    scope, subject.subject.id
                )
                if item.state == "active"
            )
            for assessment in self.safety.list_assessments(
                scope, visit.study_id, visit.site_id, subject.subject.id
            ):
                safety_alert_count += len(assessment.timely_alerts)
        urgent_count += safety_alert_count
        lab_reports = self.laboratory.list_reports(
            scope, visit.study_id, visit.site_id
        )
        edc_snapshots = self.edc_imports.list_snapshots(
            scope, visit.study_id, visit.site_id
        )
        report_drafts = self.reports.list_drafts(
            scope, visit.study_id, visit.site_id
        )
        report_snapshots = self.reports.list_snapshots(
            scope, visit.study_id, visit.site_id
        )
        directory_refs = self.site_files.site_file_status(
            scope, visit.study_id, visit.site_id
        )
        directory_missing_count = sum(
            1
            for directory in directory_refs
            for item in directory.items
            if item.applicability_status == "required"
            and item.acquisition_status != "provided"
        )
        selected_count = len(workbench.selected_issue_ids)
        previsit_status = (
            "complete"
            if selected_count or not remaining
            else "ready_to_choose"
        )
        carryover_status = "attention" if remaining else "complete"
        subject_status = (
            "recorded"
            if subject_summaries and coverage_count
            else "not_started"
        )
        handover_status = (
            "snapshot_ready"
            if report_snapshots
            else "draft_ready"
            if report_drafts
            else "not_started"
        )
        if not selected_count and remaining:
            recommended = "previsit"
        elif remaining:
            recommended = "carryover_review"
        elif subject_summaries:
            recommended = "subject_review"
        else:
            recommended = "handover"
        stages = (
            JourneyStage(
                key="previsit",
                label="1. 访前准备",
                status=previsit_status,
                summary=(
                    f"已选择{selected_count}项遗留；完整未完清单{len(remaining)}项。"
                ),
                primary_action="选择本次要沟通的遗留事项并生成访视信",
            ),
            JourneyStage(
                key="carryover_review",
                label="2. 遗留复核",
                status=carryover_status,
                summary=(
                    f"仍有{len(remaining)}项未完遗留；"
                    f"紧急待核实{urgent_count}项。"
                ),
                primary_action="到中心逐项展开并确认整改，未完成项保留",
            ),
            JourneyStage(
                key="subject_review",
                label="3. 逐患者核查",
                status=subject_status,
                summary=(
                    f"{len(subject_summaries)}名患者，"
                    f"{coverage_count}项覆盖记录，"
                    f"{not_checked_count}项未核查。"
                ),
                primary_action="按患者核对分层list、检验和后续事项",
                blocking=False,
            ),
            JourneyStage(
                key="handover",
                label="4. 报告与交接",
                status=handover_status,
                summary=(
                    f"{len(report_drafts)}份草稿，"
                    f"{len(report_snapshots)}份快照；"
                    f"目录未见{directory_missing_count}项。"
                ),
                primary_action="确认范围后生成报告/交接，下次继续未完事项",
            ),
        )
        return MonitoringJourney(
            workbench=workbench,
            stages=stages,
            recommended_stage=recommended,
            remaining_issue_ids=tuple(item.issue.id for item in remaining),
            remaining_issue_numbers=tuple(
                item.issue.issue_number for item in remaining
            ),
            urgent_action_count=urgent_count,
            subject_count=len(subject_summaries),
            coverage_count=coverage_count,
            not_checked_count=not_checked_count,
            active_skip_count=active_skip_count,
            laboratory_report_count=len(lab_reports),
            edc_snapshot_count=len(edc_snapshots),
            report_draft_count=len(report_drafts),
            report_snapshot_count=len(report_snapshots),
            directory_missing_count=directory_missing_count,
            generated_at=datetime.now(UTC),
            limitations=(
                "阶段推进只是导航，不创建全局审批锁或临床完成结论。",
                "未核查、unknown和跳过范围不会因进入下一阶段变成正常。",
                "自动检验能力仍以W08/W14的实际支持范围为准。",
            ),
            metrics={
                "remaining_issue_count": len(remaining),
                "urgent_action_count": urgent_count,
                "subject_count": len(subject_summaries),
                "coverage_count": coverage_count,
                "not_checked_count": not_checked_count,
                "active_skip_count": active_skip_count,
                "laboratory_report_count": len(lab_reports),
                "edc_snapshot_count": len(edc_snapshots),
                "report_draft_count": len(report_drafts),
                "report_snapshot_count": len(report_snapshots),
                "directory_missing_count": directory_missing_count,
            },
        )
