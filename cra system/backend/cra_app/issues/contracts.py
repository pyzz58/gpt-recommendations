"""Validated commands and shared value objects for issue and carryover workflows."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ActionKind = Literal[
    "pd_reporting",
    "edc_correction",
    "document_supply",
    "medical_clarification",
    "query_followup",
    "other",
]
ActionStatus = Literal["open", "reported_done", "completed", "needs_correction"]
SourceKind = Literal[
    "manual", "monitoring_report", "track", "text", "legacy", "other"
]
QueryState = Literal["draft", "formal"]
MonitoringStage = Literal[
    "previsit", "carryover_review", "subject_review", "closeout", "handover"
]


class IssueContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ActionCreate(IssueContract):
    action_key: str | None = Field(
        default=None, pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$"
    )
    kind: ActionKind
    requirement: str | None = Field(default=None, max_length=4000)
    due_on: date | None = None
    deadline_source: str | None = Field(default=None, max_length=500)
    deadline_source_refs: list[dict[str, Any]] = Field(
        default_factory=list, max_length=50
    )

    @model_validator(mode="after")
    def validate_deadline(self) -> "ActionCreate":
        if self.due_on is not None and not (
            self.deadline_source and self.deadline_source.strip()
        ):
            raise ValueError("due_on requires an explicit deadline_source")
        return self


class CreateIssueCommand(IssueContract):
    expected_revision: Literal[0] = 0
    idempotency_key: str = Field(min_length=1, max_length=128)
    site_id: uuid.UUID
    subject_id: uuid.UUID | None = None
    issue_number: str | None = Field(default=None, max_length=64)
    original_finding: str | None = Field(default=None, max_length=10000)
    location: str | None = Field(default=None, max_length=2000)
    recommendation: str | None = Field(default=None, max_length=5000)
    recommendation_sources: list[Any] = Field(default_factory=list, max_length=100)
    reported_correction: str | None = Field(default=None, max_length=10000)
    known_progress: str | None = Field(default=None, max_length=10000)
    source_kind: SourceKind = "manual"
    source_document_version_id: uuid.UUID | None = None
    source_anchor_id: uuid.UUID | None = None
    source_original_key: str | None = Field(default=None, max_length=512)
    source_refs: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    actions: list[ActionCreate] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_identifiable_issue(self) -> "CreateIssueCommand":
        if not any(
            value and value.strip()
            for value in (
                self.issue_number,
                self.original_finding,
                self.reported_correction,
            )
        ):
            raise ValueError(
                "an issue needs an original number or some source finding"
            )
        keys = [
            action.action_key
            for action in self.actions
            if action.action_key is not None
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("action keys must be unique")
        return self


class AddActionCommand(IssueContract):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    action: ActionCreate


class ActionTarget(IssueContract):
    action_id: uuid.UUID
    expected_revision: int = Field(ge=1)


class ConfirmCorrectedCommand(IssueContract):
    idempotency_key: str = Field(min_length=1, max_length=128)
    actions: list[ActionTarget] = Field(min_length=1, max_length=100)
    optional_note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_distinct_actions(self) -> "ConfirmCorrectedCommand":
        ids = [item.action_id for item in self.actions]
        if len(ids) != len(set(ids)):
            raise ValueError("action_ids must be unique")
        return self


class ConfirmReportedCommand(IssueContract):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    user_statement: str = Field(min_length=1, max_length=2000)
    optional_note: str | None = Field(default=None, max_length=2000)


class ReopenActionCommand(IssueContract):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=2000)


class RecordReplyCommand(IssueContract):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    statement: str = Field(min_length=1, max_length=10000)


class CreateQueryLinkCommand(IssueContract):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    query_state: QueryState
    external_system: str | None = Field(default=None, max_length=64)
    external_query_number: str | None = Field(default=None, max_length=128)
    opened_on: date | None = None
    due_on: date | None = None
    deadline_source: str | None = Field(default=None, max_length=500)
    deadline_source_refs: list[dict[str, Any]] = Field(
        default_factory=list, max_length=50
    )
    replied_on: date | None = None
    reply_summary: str | None = Field(default=None, max_length=10000)

    @model_validator(mode="after")
    def validate_query_evidence(self) -> "CreateQueryLinkCommand":
        if self.query_state == "formal" and (
            not self.external_query_number
            or not self.external_query_number.strip()
            or self.opened_on is None
        ):
            raise ValueError(
                "formal Query requires external number and actual opened date; "
                "save an incomplete item as draft"
            )
        if self.due_on is not None and not (
            self.deadline_source and self.deadline_source.strip()
        ):
            raise ValueError("due_on requires an explicit deadline_source")
        if (
            self.replied_on is not None
            and self.opened_on is not None
            and self.replied_on < self.opened_on
        ):
            raise ValueError("replied_on cannot precede opened_on")
        return self


class CreateMonitoringVisitCommand(IssueContract):
    expected_revision: Literal[0] = 0
    idempotency_key: str = Field(min_length=1, max_length=128)
    site_id: uuid.UUID
    stage: MonitoringStage = "carryover_review"
    title: str = Field(min_length=1, max_length=255)
    scope_note: str | None = Field(default=None, max_length=5000)


class UpdateMonitoringScopeCommand(IssueContract):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    scope_note: str | None = Field(default=None, max_length=5000)
    status: Literal["draft", "in_progress", "completed"] | None = None


class SelectPrevisitIssuesCommand(IssueContract):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    issue_ids: list[uuid.UUID] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def validate_unique_issue_ids(self) -> "SelectPrevisitIssuesCommand":
        if len(self.issue_ids) != len(set(self.issue_ids)):
            raise ValueError("issue_ids must be unique")
        return self


class PreviewCarryoverDocumentCommand(IssueContract):
    expected_revision: Literal[0] = 0
    idempotency_key: str = Field(min_length=1, max_length=128)
    site_id: uuid.UUID


class PreviewCarryoverTextCommand(IssueContract):
    expected_revision: Literal[0] = 0
    idempotency_key: str = Field(min_length=1, max_length=128)
    site_id: uuid.UUID
    source_label: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1, max_length=1_000_000)


class CarryoverCandidateCorrection(IssueContract):
    candidate_id: uuid.UUID
    issue_number: str | None = Field(default=None, max_length=64)
    original_finding: str | None = Field(default=None, max_length=10000)
    location: str | None = Field(default=None, max_length=2000)
    recommendation: str | None = Field(default=None, max_length=5000)
    known_progress: str | None = Field(default=None, max_length=10000)
    actions: list[ActionCreate] | None = None
    skip: bool = False


class ConfirmCarryoverImportCommand(IssueContract):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    corrections: list[CarryoverCandidateCorrection] = Field(
        default_factory=list, max_length=500
    )

    @model_validator(mode="after")
    def validate_unique_candidates(self) -> "ConfirmCarryoverImportCommand":
        ids = [item.candidate_id for item in self.corrections]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate corrections must be unique")
        return self
