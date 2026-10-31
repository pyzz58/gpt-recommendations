from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import AgentRoleConfig
from medical_one_person.application.errors import (
    ConflictingOperationError,
    NotFoundError,
    ReviewPolicyError,
)
from medical_one_person.domain.audits import (
    AnalysisAuditPacket,
    AuditEvaluationFixture,
    AuditEvaluationView,
    AuditEvidenceItem,
    AuditFindingSpec,
    AuditFindingStatus,
    AuditReviewResult,
    AuditState,
    AuditTargetType,
    ClaimAuditPacket,
    DeliverableAuditPacket,
    EvaluationMetrics,
)
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    AnalysisReview,
    AnalysisRun,
    AuditEvaluation,
    AuditFinding,
    AuditRun,
    Citation,
    ClaimVersion,
    EvidenceLink,
    ExternalDeliverable,
    KnowledgeChunk,
    KnowledgeDocumentVersion,
    Project,
    ProjectEvent,
    Task,
    User,
)


class AuditTargetView(BaseModel):
    target_type: AuditTargetType
    target_id: UUID
    label: str
    detail: str


class AuditFindingView(BaseModel):
    id: UUID
    code: str
    severity: str
    category: str
    message: str
    evidence_refs: list[str]
    affected_objects: list[dict[str, str]]
    status: AuditFindingStatus
    resolution: str | None
    created_at: datetime


class AuditRunView(BaseModel):
    id: UUID
    project_id: UUID
    target_type: AuditTargetType
    target_id: UUID
    linked_task_id: UUID | None
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
    findings: list[AuditFindingView]
    created_at: datetime


class AuditWorkspaceView(BaseModel):
    targets: list[AuditTargetView]
    reviews: list[AuditRunView]
    evaluations: list[AuditEvaluationView]
    limitations: list[str]


class AuditService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        roles: dict[str, AgentRoleConfig],
        evaluation_fixture_path: Path,
    ) -> None:
        self._session_factory = session_factory
        self._roles = roles
        self._fixture_path = evaluation_fixture_path

    def workspace(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
    ) -> AuditWorkspaceView:
        with self._session_factory.begin() as session:
            actor, project = _context(session, project_id, actor_user_id)
            claims = session.scalars(
                select(ClaimVersion)
                .where(ClaimVersion.project_id == project.id)
                .order_by(ClaimVersion.created_at.desc())
            ).all()
            analyses = session.scalars(
                select(AnalysisRun)
                .where(AnalysisRun.project_id == project.id)
                .order_by(AnalysisRun.created_at.desc())
            ).all()
            deliverables = session.scalars(
                select(ExternalDeliverable)
                .where(ExternalDeliverable.project_id == project.id)
                .order_by(ExternalDeliverable.created_at.desc())
            ).all()
            runs = session.scalars(
                select(AuditRun)
                .where(AuditRun.project_id == project.id)
                .order_by(AuditRun.created_at.desc())
            ).all()
            evaluations = session.scalars(
                select(AuditEvaluation)
                .where(AuditEvaluation.project_id == project.id)
                .order_by(AuditEvaluation.created_at.desc())
            ).all()
            return AuditWorkspaceView(
                targets=[
                    *[
                        AuditTargetView(
                            target_type=AuditTargetType.CLAIM_VERSION,
                            target_id=item.id,
                            label=item.statement[:160],
                            detail=f"{item.status} · {item.directness}",
                        )
                        for item in claims
                    ],
                    *[
                        AuditTargetView(
                            target_type=AuditTargetType.ANALYSIS_RUN,
                            target_id=item.id,
                            label=f"分析运行 v{item.analysis_version}",
                            detail=item.result.get("method", "unknown"),
                        )
                        for item in analyses
                    ],
                    *[
                        AuditTargetView(
                            target_type=AuditTargetType.EXTERNAL_DELIVERABLE,
                            target_id=item.id,
                            label=item.title,
                            detail=f"{item.kind} · {item.state}",
                        )
                        for item in deliverables
                    ],
                ],
                reviews=[_review_view(session, run) for run in runs],
                evaluations=[_evaluation_view(item) for item in evaluations],
                limitations=[
                    "A25/A26 reviews use deterministic rules on a stored project packet; "
                    "they are not live model or human expert reviews.",
                    "Synthetic evaluation measures detector regression only, not "
                    "scientific judgment quality.",
                ],
            )

    def create_review(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        target_type: AuditTargetType,
        target_id: UUID,
        reviewer_role: str,
        producer_role: str | None,
        linked_task_id: UUID | None = None,
        idempotency_key: str,
    ) -> AuditRunView:
        reviewer = self._roles.get(reviewer_role)
        if (
            reviewer is None
            or reviewer_role not in {"A25", "A26"}
            or not reviewer.independent_context
        ):
            raise ReviewPolicyError("Audit requires an independent A25 or A26 role contract")
        if producer_role is not None and producer_role == reviewer_role:
            raise ReviewPolicyError("The producing role cannot review its own output")
        if producer_role is not None and producer_role not in self._roles:
            raise ReviewPolicyError("Producer role is not configured")
        packet, target_sha256 = self._build_packet(
            project_id=project_id,
            actor_user_id=actor_user_id,
            target_type=target_type,
            target_id=target_id,
        )
        result = _review_packet(target_type, packet, reviewer_role)
        request_hash = _digest(
            {
                "target_type": target_type.value,
                "target_id": str(target_id),
                "reviewer_role": reviewer_role,
                "producer_role": producer_role,
                "linked_task_id": str(linked_task_id) if linked_task_id else None,
            }
        )
        with self._session_factory.begin() as session:
            actor, project = _context(session, project_id, actor_user_id)
            _lock_project(session, project)
            if linked_task_id is not None:
                task = session.scalar(
                    select(Task).where(
                        Task.id == linked_task_id,
                        Task.project_id == project.id,
                    )
                )
                if task is None:
                    raise NotFoundError("Linked task not found")
            existing = session.scalar(
                select(AuditRun)
                .where(
                    AuditRun.project_id == project.id,
                    AuditRun.idempotency_key == idempotency_key,
                )
                .with_for_update()
            )
            if existing is not None:
                if existing.request_hash != request_hash:
                    raise ConflictingOperationError(
                        "Audit idempotency key was reused with different parameters"
                    )
                return _review_view(session, existing)
            version = (
                session.scalar(
                    select(func.max(AuditRun.review_version)).where(
                        AuditRun.project_id == project.id,
                        AuditRun.target_type == target_type.value,
                        AuditRun.target_id == target_id,
                        AuditRun.reviewer_role == reviewer_role,
                    )
                )
                or 0
            ) + 1
            now = datetime.now(UTC)
            run = AuditRun(
                id=uuid4(),
                workspace_id=actor.workspace_id,
                project_id=project.id,
                target_type=target_type.value,
                target_id=target_id,
                linked_task_id=linked_task_id,
                target_sha256=target_sha256,
                input_sha256=_digest(packet),
                reviewer_role=reviewer_role,
                producer_role=producer_role,
                method="deterministic_rules.v1",
                state=result.state.value,
                downstream_blocked=result.downstream_blocked,
                summary=result.summary,
                review_version=version,
                input_snapshot=packet,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                created_by_user_id=actor.id,
                created_at=now,
            )
            session.add(run)
            session.flush()
            for finding in result.findings:
                session.add(
                    AuditFinding(
                        id=uuid4(),
                        workspace_id=actor.workspace_id,
                        project_id=project.id,
                        audit_id=run.id,
                        code=finding.code,
                        severity=finding.severity,
                        category=finding.category,
                        message=finding.message,
                        evidence_refs=finding.evidence_refs,
                        affected_objects=finding.affected_objects,
                        status=AuditFindingStatus.OPEN.value,
                        created_at=now,
                    )
                )
            if target_type == AuditTargetType.CLAIM_VERSION and result.state == AuditState.BLOCKED:
                claim = session.get(ClaimVersion, target_id)
                if claim is not None and claim.status != "stale":
                    claim.status = "disputed"
            _event(
                session,
                project=project,
                actor=actor,
                audit=run,
                event_type="audit.review_completed",
                now=now,
                payload={
                    "target_type": target_type.value,
                    "target_id": str(target_id),
                    "reviewer_role": reviewer_role,
                    "state": result.state.value,
                    "finding_codes": [item.code for item in result.findings],
                },
            )
            session.flush()
            return _review_view(session, run)

    def resolve_finding(
        self,
        *,
        project_id: UUID,
        audit_id: UUID,
        finding_id: UUID,
        actor_user_id: UUID,
        status: AuditFindingStatus,
        resolution: str,
    ) -> AuditFindingView:
        if status == AuditFindingStatus.OPEN:
            raise ValueError("Use resolved or accepted_risk when recording a disposition")
        if not resolution.strip():
            raise ValueError("Finding resolution requires a reason")
        with self._session_factory.begin() as session:
            actor, project = _context(session, project_id, actor_user_id)
            _lock_project(session, project)
            run = session.scalar(
                select(AuditRun).where(
                    AuditRun.id == audit_id,
                    AuditRun.project_id == project.id,
                )
            )
            if run is None:
                raise NotFoundError("Audit review not found")
            finding = session.scalar(
                select(AuditFinding)
                .where(
                    AuditFinding.id == finding_id,
                    AuditFinding.audit_id == run.id,
                    AuditFinding.project_id == project.id,
                )
                .with_for_update()
            )
            if finding is None:
                raise NotFoundError("Audit finding not found")
            if finding.status == AuditFindingStatus.RESOLVED.value:
                if finding.resolution != resolution:
                    raise ConflictingOperationError("Resolved finding cannot be rewritten")
                return _finding_view(finding)
            now = datetime.now(UTC)
            finding.status = status.value
            finding.resolution = resolution
            finding.resolved_by_user_id = actor.id
            finding.resolved_at = now
            _event(
                session,
                project=project,
                actor=actor,
                audit=run,
                event_type="audit.finding_disposition_recorded",
                now=now,
                payload={
                    "finding_id": str(finding.id),
                    "status": status.value,
                    "code": finding.code,
                },
            )
            return _finding_view(finding)

    def run_evaluation(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
    ) -> AuditEvaluationView:
        fixture_content = self._fixture_path.read_bytes()
        fixture = AuditEvaluationFixture.model_validate_json(fixture_content)
        true_positives = 0
        false_positives = 0
        false_negatives = 0
        case_results: list[dict[str, Any]] = []
        for case in fixture.cases:
            result = _review_packet(case.target_type, case.packet, case.reviewer_role)
            predicted = {finding.code for finding in result.findings}
            expected = set(case.expected_codes)
            matched = predicted & expected
            unexpected = predicted - expected
            missed = expected - predicted
            true_positives += len(matched)
            false_positives += len(unexpected)
            false_negatives += len(missed)
            case_results.append(
                {
                    "case_id": case.case_id,
                    "reviewer_role": case.reviewer_role,
                    "expected_codes": sorted(expected),
                    "predicted_codes": sorted(predicted),
                    "matched_codes": sorted(matched),
                    "unexpected_codes": sorted(unexpected),
                    "missed_codes": sorted(missed),
                }
            )
        precision_denominator = true_positives + false_positives
        recall_denominator = true_positives + false_negatives
        metrics = EvaluationMetrics(
            cases=len(fixture.cases),
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
            precision=(
                true_positives / precision_denominator if precision_denominator else 1.0
            ),
            recall=true_positives / recall_denominator if recall_denominator else 1.0,
        )
        limitations = [
            "Synthetic regression fixture only; no real scientific labels or expert consensus.",
            "Measures deterministic rule detection, not model reasoning quality.",
            "Does not establish that unseen medical claims will be found.",
        ]
        with self._session_factory.begin() as session:
            actor, project = _context(session, project_id, actor_user_id)
            row = AuditEvaluation(
                id=uuid4(),
                workspace_id=actor.workspace_id,
                project_id=project.id,
                fixture_name=fixture.name,
                fixture_sha256=hashlib.sha256(fixture_content).hexdigest(),
                cases=metrics.cases,
                metrics=metrics.model_dump(mode="json"),
                case_results=case_results,
                limitations=limitations,
                created_by_user_id=actor.id,
                created_at=datetime.now(UTC),
            )
            session.add(row)
            session.flush()
            return _evaluation_view(row)

    def _build_packet(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        target_type: AuditTargetType,
        target_id: UUID,
    ) -> tuple[dict[str, Any], str]:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            if target_type == AuditTargetType.CLAIM_VERSION:
                claim = session.scalar(
                    select(ClaimVersion).where(
                        ClaimVersion.id == target_id,
                        ClaimVersion.project_id == project.id,
                    )
                )
                if claim is None:
                    raise NotFoundError("Claim version not found")
                links = session.scalars(
                    select(EvidenceLink)
                    .where(
                        EvidenceLink.claim_version_id == claim.id,
                        EvidenceLink.project_id == project.id,
                    )
                    .order_by(EvidenceLink.created_at)
                ).all()
                evidence: list[AuditEvidenceItem] = []
                for link in links:
                    citation = session.get(Citation, link.citation_id)
                    chunk = session.get(KnowledgeChunk, citation.chunk_id) if citation else None
                    version = (
                        session.get(KnowledgeDocumentVersion, citation.version_id)
                        if citation
                        else None
                    )
                    if citation is None or chunk is None or version is None:
                        raise NotFoundError("Claim evidence citation is incomplete")
                    evidence.append(
                        AuditEvidenceItem(
                            citation_id=str(citation.id),
                            excerpt=citation.quoted_excerpt,
                            source_excerpt=chunk.text,
                            citation_sha256=citation.content_sha256,
                            citation_review_status=citation.review_status,
                            source_evidence_status=version.evidence_status,
                            stance=cast(
                                Literal["supports", "refutes", "context"],
                                link.stance,
                            ),
                        )
                    )
                packet = ClaimAuditPacket(
                    statement=claim.statement,
                    status=claim.status,
                    directness=claim.directness,
                    species_or_population=claim.species_or_population,
                    sample_size=claim.sample_size,
                    evidence=evidence,
                    negative_evidence_checked=any(
                        item.stance in {"refutes", "context"} for item in evidence
                    ),
                ).model_dump(mode="json")
                return packet, _digest(packet)
            if target_type == AuditTargetType.ANALYSIS_RUN:
                analysis = session.scalar(
                    select(AnalysisRun).where(
                        AnalysisRun.id == target_id,
                        AnalysisRun.project_id == project.id,
                    )
                )
                if analysis is None:
                    raise NotFoundError("Analysis run not found")
                review = session.scalar(
                    select(AnalysisReview)
                    .where(AnalysisReview.analysis_id == analysis.id)
                    .order_by(AnalysisReview.created_at.desc())
                    .limit(1)
                )
                packet = AnalysisAuditPacket(
                    method=analysis.result.get("method", "unknown"),
                    result=analysis.result,
                    chart=analysis.chart_spec,
                    output_sha256=analysis.output_sha256,
                    latest_review_decision=review.decision if review else None,
                    limitations=[
                        str(item) for item in analysis.result.get("limitations", [])
                    ],
                    exploratory=bool(analysis.result.get("exploratory", False)),
                ).model_dump(mode="json")
                return packet, _digest(packet)
            deliverable = session.scalar(
                select(ExternalDeliverable).where(
                    ExternalDeliverable.id == target_id,
                    ExternalDeliverable.project_id == project.id,
                )
            )
            if deliverable is None:
                raise NotFoundError("External deliverable not found")
            packet = DeliverableAuditPacket(
                title=deliverable.title,
                kind=deliverable.kind,
                state=deliverable.state,
                knowledge_version_id=(
                    str(deliverable.knowledge_version_id)
                    if deliverable.knowledge_version_id
                    else None
                ),
                manifest=deliverable.manifest,
                missing_items=deliverable.missing_items,
                reviewer_role=deliverable.reviewer_role,
                expected_items=deliverable.expected_items,
            ).model_dump(mode="json")
            return packet, _digest(packet)


def _review_packet(
    target_type: AuditTargetType,
    packet: dict[str, Any],
    reviewer_role: str,
) -> AuditReviewResult:
    if target_type == AuditTargetType.CLAIM_VERSION:
        return _review_claim(ClaimAuditPacket.model_validate(packet), reviewer_role)
    if target_type == AuditTargetType.ANALYSIS_RUN:
        return _review_analysis(AnalysisAuditPacket.model_validate(packet), reviewer_role)
    return _review_deliverable(
        DeliverableAuditPacket.model_validate(packet),
        reviewer_role,
    )


def _review_claim(packet: ClaimAuditPacket, reviewer_role: str) -> AuditReviewResult:
    findings: list[AuditFindingSpec] = []
    evidence_ids = [item.citation_id for item in packet.evidence]
    if packet.status in {"supported", "contradicted", "conflicted"} and not packet.evidence:
        findings.append(
            _finding(
                "CLAIM_MISSING_EVIDENCE",
                "critical",
                "evidence",
                "A supported or conflicted claim has no linked citation.",
            )
        )
    if packet.status == "stale":
        findings.append(
            _finding(
                "STALE_CLAIM_VERSION",
                "critical",
                "version",
                "Claim version is stale and cannot support current decisions.",
            )
        )
    for item in packet.evidence:
        if hashlib.sha256(item.excerpt.encode("utf-8")).hexdigest() != item.citation_sha256:
            findings.append(
                _finding(
                    "CITATION_HASH_MISMATCH",
                    "critical",
                    "citation",
                    "Citation excerpt hash does not match its recorded digest.",
                    [item.citation_id],
                )
            )
        if item.excerpt not in item.source_excerpt:
            findings.append(
                _finding(
                    "CITATION_EXCERPT_NOT_IN_SOURCE",
                    "critical",
                    "citation",
                    "Quoted citation text is not present in the stored source passage.",
                    [item.citation_id],
                )
            )
    if reviewer_role == "A25":
        if any(item.citation_review_status != "verified" for item in packet.evidence):
            findings.append(
                _finding(
                    "CITATION_UNREVIEWED",
                    "major",
                    "citation",
                    "At least one citation is not scope-verified.",
                    evidence_ids,
                )
            )
        if any(item.source_evidence_status == "needs_review" for item in packet.evidence):
            findings.append(
                _finding(
                    "SOURCE_SCOPE_NEEDS_REVIEW",
                    "major",
                    "source",
                    "A source version remains marked needs_review.",
                    evidence_ids,
                )
            )
    if reviewer_role == "A26":
        contradictory = [item for item in packet.evidence if item.stance == "refutes"]
        if contradictory and packet.status == "supported":
            findings.append(
                _finding(
                    "CONTRADICTION_IGNORED",
                    "critical",
                    "counter_evidence",
                    "Refuting evidence is linked while the claim remains "
                    "unconditionally supported.",
                    [item.citation_id for item in contradictory],
                )
            )
        if (
            packet.status in {"supported", "contradicted", "conflicted"}
            and not packet.negative_evidence_checked
        ):
            findings.append(
                _finding(
                    "NEGATIVE_EVIDENCE_NOT_CHECKED",
                    "major",
                    "counter_evidence",
                    "No negative or contextual evidence review is recorded.",
                    evidence_ids,
                )
            )
        if _contains_overclaim(packet.statement) and (
            packet.directness != "direct"
            or not any(item.stance == "supports" for item in packet.evidence)
        ):
            findings.append(
                _finding(
                    "OVERCLAIM_WITHOUT_DIRECT_SUPPORT",
                    "critical",
                    "interpretation",
                    "Claim uses an absolute regulatory, efficacy or safety term "
                    "without direct support.",
                    evidence_ids,
                )
            )
        if packet.status == "supported" and packet.directness == "unknown":
            findings.append(
                _finding(
                    "DIRECTNESS_NOT_JUSTIFIED",
                    "major",
                    "inference",
                    "A supported claim has unknown directness.",
                    evidence_ids,
                )
            )
        if packet.status == "supported" and not packet.species_or_population:
            findings.append(
                _finding(
                    "CLAIM_SCOPE_MISSING",
                    "major",
                    "scope",
                    "Supported claim does not state the species or population.",
                    evidence_ids,
                )
            )
        if (
            packet.status == "supported"
            and packet.sample_size is None
            and re.search(r"降低|增加|改善|减少|优于|有效", packet.statement)
        ):
            findings.append(
                _finding(
                    "SAMPLE_SIZE_MISSING",
                    "major",
                    "sample",
                    "Effect claim lacks a recorded sample size.",
                    evidence_ids,
                )
            )
    return _finish(findings, "claim")


def _review_analysis(packet: AnalysisAuditPacket, reviewer_role: str) -> AuditReviewResult:
    findings: list[AuditFindingSpec] = []
    expected_hash = _digest({"result": packet.result, "chart": packet.chart})
    if expected_hash != packet.output_sha256:
        findings.append(
            _finding(
                "ANALYSIS_HASH_MISMATCH",
                "critical",
                "reproducibility",
                "Analysis result/chart digest does not match the stored output hash.",
            )
        )
    if reviewer_role == "A25":
        if packet.latest_review_decision != "accepted":
            findings.append(
                _finding(
                    "ANALYSIS_REVIEW_NOT_ACCEPTED",
                    "critical",
                    "review",
                    "Analysis has no latest accepted review record.",
                )
            )
        if not packet.limitations:
            findings.append(
                _finding(
                    "ANALYSIS_LIMITATIONS_MISSING",
                    "major",
                    "reporting",
                    "Analysis output has no explicit limitations.",
                )
            )
    elif packet.method not in {
        "descriptive_continuous",
        "two_group_mean_difference",
        "proportion_wilson",
    }:
        findings.append(
            _finding(
                "ANALYSIS_METHOD_UNSUPPORTED",
                "critical",
                "method",
                "Analysis method is outside the reviewed deterministic method set.",
            )
        )
    return _finish(findings, "analysis")


def _review_deliverable(
    packet: DeliverableAuditPacket,
    reviewer_role: str,
) -> AuditReviewResult:
    findings: list[AuditFindingSpec] = []
    if packet.state == "accepted":
        if not packet.knowledge_version_id:
            findings.append(
                _finding(
                    "RAW_ORIGINAL_MISSING",
                    "critical",
                    "delivery",
                    "Deliverable is accepted without an original document version.",
                )
            )
        if packet.missing_items:
            findings.append(
                _finding(
                    "MISSING_ITEMS_ACCEPTED",
                    "critical",
                    "delivery",
                    "Deliverable is accepted while required items remain missing.",
                )
            )
        if packet.reviewer_role not in {"A25", "A26"}:
            findings.append(
                _finding(
                    "COMPLETENESS_REVIEW_MISSING",
                    "major",
                    "review",
                    "Accepted deliverable has no A25/A26 review record.",
                )
            )
        if "content_sha256" not in packet.manifest:
            findings.append(
                _finding(
                    "MANIFEST_HASH_MISSING",
                    "major",
                    "provenance",
                    "Accepted deliverable manifest has no content hash.",
                )
            )
    if (
        reviewer_role == "A26"
        and packet.kind == "raw_data"
        and packet.state == "accepted"
        and "content_sha256" not in packet.manifest
    ):
        findings.append(
            _finding(
                "RAW_DATA_HASH_MISSING",
                "critical",
                "reproducibility",
                "Raw data acceptance has no recorded source hash.",
            )
        )
    return _finish(findings, "deliverable")


def _finish(findings: list[AuditFindingSpec], target_label: str) -> AuditReviewResult:
    severities = {item.severity for item in findings}
    if "critical" in severities:
        state = AuditState.BLOCKED
        blocked = True
    elif "major" in severities:
        state = AuditState.CHANGES_REQUESTED
        blocked = True
    else:
        state = AuditState.PASSED
        blocked = False
    summary = (
        f"{target_label} review passed with no blocking findings."
        if not findings
        else (
            f"{target_label} review found {len(findings)} issue(s): "
            + ", ".join(item.code for item in findings)
        )
    )
    return AuditReviewResult(
        findings=findings,
        state=state,
        downstream_blocked=blocked,
        summary=summary,
    )


def _finding(
    code: str,
    severity: str,
    category: str,
    message: str,
    evidence_refs: list[str] | None = None,
) -> AuditFindingSpec:
    return AuditFindingSpec(
        code=code,
        severity=severity,  # type: ignore[arg-type]
        category=category,
        message=message,
        evidence_refs=evidence_refs or [],
        affected_objects=[],
    )


def _contains_overclaim(statement: str) -> bool:
    return bool(
        re.search(
            r"已获批|可治愈|保证安全|绝对安全|已证明有效|证明.{0,8}有效|批准用于",
            statement,
        )
    )


def _owner(session: Session, actor_user_id: UUID) -> User:
    actor = session.get(User, actor_user_id)
    if actor is None:
        raise NotFoundError("User not found")
    if not actor.is_owner:
        raise PermissionError("Only the verified workspace owner can run audits")
    return actor


def _project(session: Session, project_id: UUID, workspace_id: UUID) -> Project:
    project = session.get(Project, project_id)
    if project is None or project.workspace_id != workspace_id:
        raise NotFoundError("Project not found")
    return project


def _lock_project(session: Session, project: Project) -> None:
    locked = session.scalar(
        select(Project)
        .where(Project.id == project.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if locked is None:
        raise NotFoundError("Project not found")


def _context(
    session: Session,
    project_id: UUID,
    actor_user_id: UUID,
) -> tuple[User, Project]:
    actor = _owner(session, actor_user_id)
    set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
    return actor, _project(session, project_id, actor.workspace_id)


def _review_view(session: Session, run: AuditRun) -> AuditRunView:
    findings = session.scalars(
        select(AuditFinding)
        .where(AuditFinding.audit_id == run.id)
        .order_by(AuditFinding.created_at, AuditFinding.code)
    ).all()
    return AuditRunView(
        id=run.id,
        project_id=run.project_id,
        target_type=AuditTargetType(run.target_type),
        target_id=run.target_id,
        linked_task_id=run.linked_task_id,
        target_sha256=run.target_sha256,
        input_sha256=run.input_sha256,
        reviewer_role=run.reviewer_role,
        producer_role=run.producer_role,
        method=run.method,
        state=AuditState(run.state),
        downstream_blocked=run.downstream_blocked,
        summary=run.summary,
        review_version=run.review_version,
        input_snapshot=run.input_snapshot,
        findings=[_finding_view(item) for item in findings],
        created_at=run.created_at.astimezone(UTC),
    )


def _finding_view(finding: AuditFinding) -> AuditFindingView:
    return AuditFindingView(
        id=finding.id,
        code=finding.code,
        severity=finding.severity,
        category=finding.category,
        message=finding.message,
        evidence_refs=finding.evidence_refs,
        affected_objects=finding.affected_objects,
        status=AuditFindingStatus(finding.status),
        resolution=finding.resolution,
        created_at=finding.created_at.astimezone(UTC),
    )


def _evaluation_view(row: AuditEvaluation) -> AuditEvaluationView:
    metrics = EvaluationMetrics.model_validate(row.metrics)
    return AuditEvaluationView(
        id=str(row.id),
        fixture_name=row.fixture_name,
        fixture_sha256=row.fixture_sha256,
        metrics=metrics,
        case_results=row.case_results,
        limitations=row.limitations,
        created_at=row.created_at.astimezone(UTC),
    )


def _event(
    session: Session,
    *,
    project: Project,
    actor: User,
    audit: AuditRun,
    event_type: str,
    now: datetime,
    payload: dict[str, Any],
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
            actor_user_id=actor.id,
            object_type="audit_run",
            object_id=audit.id,
            object_revision=audit.review_version,
            payload=payload,
            correlation_id=uuid4(),
            created_at=now,
        )
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()
