from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AuditTargetType(StrEnum):
    CLAIM_VERSION = "claim_version"
    ANALYSIS_RUN = "analysis_run"
    EXTERNAL_DELIVERABLE = "external_deliverable"


class AuditState(StrEnum):
    PASSED = "passed"
    CHANGES_REQUESTED = "changes_requested"
    BLOCKED = "blocked"


class AuditFindingStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    ACCEPTED_RISK = "accepted_risk"


class AuditCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(min_length=1, max_length=100)
    reviewer_role: Literal["A25", "A26"]
    target_type: AuditTargetType
    expected_codes: list[str]
    packet: dict[str, Any]


class AuditEvaluationFixture(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    name: str
    cases: list[AuditCase] = Field(min_length=1)


class AuditEvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    citation_id: str
    excerpt: str
    source_excerpt: str
    citation_sha256: str
    citation_review_status: str
    source_evidence_status: str
    stance: Literal["supports", "refutes", "context"]


class ClaimAuditPacket(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    statement: str
    status: str
    directness: str
    species_or_population: str | None
    sample_size: int | None
    evidence: list[AuditEvidenceItem]
    negative_evidence_checked: bool


class AnalysisAuditPacket(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    method: str
    result: dict[str, Any]
    chart: dict[str, Any]
    output_sha256: str
    latest_review_decision: str | None
    limitations: list[str]
    exploratory: bool


class DeliverableAuditPacket(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str
    kind: str
    state: str
    knowledge_version_id: str | None
    manifest: dict[str, Any]
    missing_items: list[str]
    reviewer_role: str | None
    expected_items: list[str]


class AuditFindingSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    severity: Literal["critical", "major", "minor"]
    category: str
    message: str
    evidence_refs: list[str] = Field(default_factory=list)
    affected_objects: list[dict[str, str]] = Field(default_factory=list)


class AuditReviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    findings: list[AuditFindingSpec]
    state: AuditState
    downstream_blocked: bool
    summary: str


class AuditReviewView(BaseModel):
    id: str
    project_id: str
    target_type: AuditTargetType
    target_id: str
    target_sha256: str
    input_sha256: str
    reviewer_role: str
    producer_role: str | None
    method: str
    state: AuditState
    downstream_blocked: bool
    summary: str
    review_version: int
    input_snapshot: dict[str, Any]
    findings: list[dict[str, Any]]
    created_at: datetime


class EvaluationMetrics(BaseModel):
    cases: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float


class AuditEvaluationView(BaseModel):
    id: str
    fixture_name: str
    fixture_sha256: str
    metrics: EvaluationMetrics
    case_results: list[dict[str, Any]]
    limitations: list[str]
    created_at: datetime
