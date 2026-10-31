"""Authorized safety analysis with deterministic rules and grounded language."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from cra_app.governance.models import AuditEvent, IdempotencyRecord
from cra_app.governance.service import (
    GovernanceService,
    IdempotencyConflict,
    ScopeContext,
)
from cra_app.issues.contracts import ActionCreate, CreateIssueCommand
from cra_app.issues.service import IssueDetail, IssueService
from cra_app.laboratory.service import ComparisonDetail, LaboratoryService
from cra_app.platform.jobs import digest_payload
from cra_app.providers.case_analysis import (
    CaseAnalysisProvider,
    CaseModelResult,
    DisabledCaseAnalysisProvider,
)
from cra_app.rules.contracts import FactValue, RuleNode
from cra_app.rules.service import (
    ApplicabilityItem,
    ApplicabilityOutcome,
    ApplicableRuleQuery,
    RuleService,
)
from cra_app.safety.contracts import (
    CreateSafetyAssessmentCommand,
    CraSafetyReviewCommand,
    LinkSafetyIssuesCommand,
    MedicalSafetyResponseCommand,
    SafetyDimension,
)
from cra_app.safety.grounding import validate_model_explanation
from cra_app.safety.models import (
    MedicalSafetyResponse,
    SafetyAssessment,
    SafetyCraReview,
    SafetyDimensionResult,
    SafetyIssueLink,
)
from cra_app.shared.output_contract import (
    Claim,
    InputRevision,
    NotCheckedItem,
    OutputCapability,
    OutputEnvelope,
    OutputScope,
    SourceRef,
    UnknownItem,
)
from cra_app.subjects.contracts import CheckDecisionCommand
from cra_app.subjects.models import ClinicalFact
from cra_app.subjects.service import (
    CheckDecision,
    SubjectService,
    SubjectSummary,
    TimelineItem,
)


class SafetyError(Exception):
    pass


class SafetyNotFound(SafetyError):
    pass


class SafetyValidationError(SafetyError):
    pass


class SafetyConflict(SafetyError):
    pass


DIMENSIONS: tuple[SafetyDimension, ...] = (
    "ae_collection",
    "grade",
    "seriousness",
    "relatedness",
    "expectedness",
    "aesi",
    "dlt",
    "protocol_deviation",
    "reporting_timeliness",
)
DIMENSION_LABELS = {
    "ae_collection": "AE收集",
    "grade": "分级",
    "seriousness": "严重性/SAE",
    "relatedness": "相关性",
    "expectedness": "预期性",
    "aesi": "AESI",
    "dlt": "DLT",
    "protocol_deviation": "方案偏离",
    "reporting_timeliness": "及时报告",
}
DIMENSION_TOKENS = {
    "ae_collection": ("AE-COLLECTION", "AE-COLLECT", "ADVERSE-EVENT"),
    "grade": ("GRADE", "CTCAE", "TOXICITY"),
    "seriousness": ("SERIOUSNESS", "SERIOUS", "SAE"),
    "relatedness": ("RELATEDNESS", "RELATED", "CAUSALITY"),
    "expectedness": ("EXPECTEDNESS", "EXPECT", "IB-"),
    "aesi": ("AESI",),
    "dlt": ("DLT",),
    "protocol_deviation": ("PROTOCOL-DEVIATION", "PD-"),
    "reporting_timeliness": ("TIMELINESS", "TIME-ANCHOR", "REPORTING-TIME"),
}
AE_DIMENSIONS: tuple[SafetyDimension, ...] = (
    "ae_collection",
    "grade",
    "seriousness",
    "relatedness",
    "expectedness",
    "aesi",
    "dlt",
    "reporting_timeliness",
)


@dataclass(frozen=True)
class DimensionDraft:
    dimension: SafetyDimension
    status: str
    label: str
    candidate_values: tuple[str, ...]
    rationale: str | None
    uncertainties: tuple[str, ...]
    rule_version_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    source_refs: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class QuestionDraft:
    question_key: str
    dimension: SafetyDimension
    question: str
    reason: str
    priority: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class TimelyAlertDraft:
    alert_key: str
    title: str
    detail: str
    dimensions: tuple[SafetyDimension, ...]
    evidence_ids: tuple[str, ...]
    event_date: date
    awareness_date: date | None
    entry_date: date | None
    reported_date: date | None
    deadline_status: str
    not_a_final_reportability_decision: bool = True


@dataclass(frozen=True)
class FactSnapshot:
    fact: ClinicalFact
    evidence_id: str
    deterministic: bool


@dataclass(frozen=True)
class AssessmentDetail:
    assessment: SafetyAssessment
    dimensions: tuple[SafetyDimensionResult, ...]
    cra_reviews: tuple[SafetyCraReview, ...]
    medical_responses: tuple[MedicalSafetyResponse, ...]
    issue_link: SafetyIssueLink | None
    replayed: bool = False


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


def _walk_nodes(node: RuleNode) -> Iterable[RuleNode]:
    yield node
    for child in node.children:
        yield from _walk_nodes(child)


def _walk_rule_refs(node: RuleNode):
    for current in _walk_nodes(node):
        yield from current.source_refs
        for branch in current.branches:
            yield from branch.source_refs
        for exception in current.exceptions:
            yield from exception.source_refs


def _rule_matches_dimension(
    rule_key: str, title: str, tree: RuleNode, dimension: SafetyDimension
) -> bool:
    content = " ".join(
        (rule_key, title, tree.node_key, tree.summary)
    ).casefold()
    return any(token.casefold() in content for token in DIMENSION_TOKENS[dimension])


def _requested_dimensions(command: CreateSafetyAssessmentCommand) -> list[SafetyDimension]:
    if command.requested_dimensions:
        return list(command.requested_dimensions)
    if command.event_type == "protocol_deviation":
        return ["protocol_deviation", "reporting_timeliness"]
    return list(AE_DIMENSIONS)


def _json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _fact_dict(fact: ClinicalFact) -> dict[str, Any]:
    return {
        "fact_id": str(fact.id),
        "fact_key": fact.fact_key,
        "revision": fact.revision,
        "repeat_instance": fact.repeat_instance,
        "value": _json_value(fact.value_json),
        "value_raw": fact.value_raw,
        "unit": fact.unit,
        "observed_on": fact.observed_on.isoformat() if fact.observed_on else None,
        "observed_at": fact.observed_at.isoformat() if fact.observed_at else None,
        "precision": fact.precision,
        "source_kind": fact.source_kind,
        "verification_status": fact.verification_status,
        "source_ref": fact.source_ref,
    }


def _source_ref_from_fact(fact: ClinicalFact) -> SourceRef:
    source = fact.source_ref
    source_type = source.get("source_type", "record")
    if source_type not in {
        "document",
        "document_anchor",
        "edc_row",
        "image_region",
        "user_action",
        "record",
        "external_query",
    }:
        source_type = "record"
    return SourceRef(
        source_type=source_type,
        source_id=str(source.get("source_id", fact.id)),
        version=str(fact.revision),
        locator=(
            str(source["locator"]) if source.get("locator") is not None else None
        ),
        quote=(
            str(source["quote"]) if source.get("quote") is not None else None
        ),
    )


def _source_ref_from_rule(item: ApplicabilityItem, ref, index: int) -> SourceRef:
    return SourceRef(
        source_type="document_anchor",
        source_id=str(ref.anchor_id or ref.anchor_key),
        version=(
            str(ref.document_version_id)
            if ref.document_version_id is not None
            else str(item.version.id)
        ),
        locator=ref.locator,
        quote=ref.quote,
    )


def _rule_evidence(
    item: ApplicabilityItem,
) -> tuple[list[dict[str, Any]], list[SourceRef], list[str]]:
    evidence: list[dict[str, Any]] = []
    refs: list[SourceRef] = []
    ids: list[str] = []
    seen: set[str] = set()
    for index, ref in enumerate(_walk_rule_refs(item.tree)):
        key = f"{ref.anchor_id or ref.anchor_key}:{ref.quote}"
        if key in seen:
            continue
        seen.add(key)
        evidence_id = f"RULE:{item.version.id}:{index}"
        source_ref = _source_ref_from_rule(item, ref, index)
        evidence.append(
            {
                "evidence_id": evidence_id,
                "text": ref.quote,
                "kind": "rule",
                "source_ref": source_ref.model_dump(
                    mode="json", exclude_none=True
                ),
            }
        )
        refs.append(source_ref)
        ids.append(evidence_id)
    return evidence, refs, ids


def _failed_dimension(
    dimension: SafetyDimension,
    *,
    reason: str,
    evidence_ids: tuple[str, ...] = (),
    source_refs: tuple[dict[str, Any], ...] = (),
) -> DimensionDraft:
    return DimensionDraft(
        dimension=dimension,
        status="unknown",
        label=DIMENSION_LABELS[dimension],
        candidate_values=(),
        rationale=None,
        uncertainties=(reason,),
        rule_version_ids=(),
        evidence_ids=evidence_ids,
        source_refs=source_refs,
    )


def _missing_fact_question(
    dimension: SafetyDimension, key: str
) -> str:
    prompts = {
        "ae_term": "请确认不良事件或医学事件的原始名称、首次发生时间，以及对应原始记录。",
        "grade_criteria_met": "请核实该事件是否达到项目采用的毒性分级标准，并记录研究者分级和依据。",
        "sae_criteria_met": "请确认该事件是否满足任一SAE严重性标准；分级结论不能替代严重性判断。",
        "relatedness_assessment": "请取得研究者对该事件相关性的独立判断及依据；CRA候选不替代医学结论。",
        "ib_version": "请确认事件发生时项目实际采用的IB或参考安全性信息版本，不得用其他版本替代。",
        "expectedness_assessment": "请记录研究者或医学人员依据采用版本作出的预期性判断及出处。",
        "aesi_list": "请确认适用的AESI清单版本，并核实事件术语是否列入该清单。",
        "dlt_criteria": "请确认方案适用的DLT定义及评估窗口，再核实该事件是否达到DLT条件。",
        "dlt_window": "请确认该事件所处治疗周期和DLT评估窗口的起止依据。",
        "protocol_deviation_suspected": "请说明偏离子项、发生日期、方案要求与实际执行，并确认是否按项目PD路径上报。",
        "safety_awareness_date": "请确认研究者或中心首次知悉该安全事件的日期和时间，并区分事件发生、录入和实际上报时间。",
        "safety_reported_date": "请确认项目要求的实际上报日期、接收方和上报依据；未上报时不要填写已上报。",
    }
    return prompts.get(
        key,
        f"请核实与{DIMENSION_LABELS[dimension]}相关的字段 {key} 及其原始来源。",
    )


class SafetyService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        governance: GovernanceService | None = None,
        rules: RuleService,
        subjects: SubjectService,
        issues: IssueService,
        laboratory: LaboratoryService,
        provider: CaseAnalysisProvider | None = None,
    ):
        self.session_factory = session_factory
        self.governance = governance or GovernanceService(session_factory)
        self.rules = rules
        self.subjects = subjects
        self.issues = issues
        self.laboratory = laboratory
        self.provider = provider or DisabledCaseAnalysisProvider()

    def _authorize_read(
        self, scope: ScopeContext, study_id: uuid.UUID, site_id: uuid.UUID
    ) -> None:
        self.governance.authorize(scope, "read_site", study_id, site_id)

    def _authorize_write(
        self, scope: ScopeContext, study_id: uuid.UUID, site_id: uuid.UUID
    ) -> None:
        self.governance.authorize(scope, "write_site", study_id, site_id)

    @staticmethod
    def _scope_fingerprint(
        scope: ScopeContext, study_id: uuid.UUID, site_id: uuid.UUID
    ) -> str:
        return digest_payload(
            {
                "tenant_id": scope.tenant_id,
                "study_id": str(study_id),
                "site_id": str(site_id),
            }
        )

    def _reserve(
        self,
        session: Session,
        *,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
        command_name: str,
        idempotency_key: str,
        command: dict[str, Any],
    ) -> tuple[IdempotencyRecord, bool]:
        fingerprint = self._scope_fingerprint(scope, study_id, site_id)
        request_digest = digest_payload(
            {
                "command_name": command_name,
                "scope_fingerprint": fingerprint,
                "command": command,
            }
        )
        session.execute(
            pg_insert(IdempotencyRecord)
            .values(
                id=uuid.uuid4(),
                actor_id=scope.actor_id,
                tenant_id=scope.tenant_id,
                study_id=study_id,
                site_id=site_id,
                scope_fingerprint=fingerprint,
                command_name=command_name,
                idempotency_key=idempotency_key,
                request_digest=request_digest,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    "actor_id",
                    "tenant_id",
                    "scope_fingerprint",
                    "command_name",
                    "idempotency_key",
                ]
            )
        )
        record = session.scalar(
            select(IdempotencyRecord)
            .where(
                IdempotencyRecord.actor_id == scope.actor_id,
                IdempotencyRecord.tenant_id == scope.tenant_id,
                IdempotencyRecord.scope_fingerprint == fingerprint,
                IdempotencyRecord.command_name == command_name,
                IdempotencyRecord.idempotency_key == idempotency_key,
            )
            .with_for_update()
        )
        if record is None:
            raise RuntimeError("failed to reserve idempotency key")
        if record.request_digest != request_digest:
            raise IdempotencyConflict(
                "idempotency key was already used with different input"
            )
        return record, record.response_resource_id is not None

    @staticmethod
    def _complete(
        record: IdempotencyRecord, resource_id: uuid.UUID, revision: int
    ) -> None:
        record.response_resource_id = resource_id
        record.response_revision = revision
        record.completed_at = datetime.now(UTC)

    def _load_assessment(
        self, scope: ScopeContext, assessment_id: uuid.UUID
    ) -> SafetyAssessment:
        with self.session_factory() as session:
            assessment = session.scalar(
                select(SafetyAssessment).where(
                    SafetyAssessment.id == assessment_id,
                    SafetyAssessment.tenant_id == scope.tenant_id,
                )
            )
            if assessment is None:
                raise SafetyNotFound("safety assessment was not found")
            self._authorize_read(
                scope, assessment.study_id, assessment.site_id
            )
            return assessment

    def detail(
        self, scope: ScopeContext, assessment_id: uuid.UUID
    ) -> AssessmentDetail:
        assessment = self._load_assessment(scope, assessment_id)
        with self.session_factory() as session:
            dimensions = tuple(
                session.scalars(
                    select(SafetyDimensionResult)
                    .where(
                        SafetyDimensionResult.assessment_id == assessment_id
                    )
                    .order_by(SafetyDimensionResult.dimension)
                )
            )
            reviews = tuple(
                session.scalars(
                    select(SafetyCraReview)
                    .where(SafetyCraReview.assessment_id == assessment_id)
                    .order_by(SafetyCraReview.created_at)
                )
            )
            responses = tuple(
                session.scalars(
                    select(MedicalSafetyResponse)
                    .where(
                        MedicalSafetyResponse.assessment_id == assessment_id
                    )
                    .order_by(MedicalSafetyResponse.created_at)
                )
            )
            issue_link = session.scalar(
                select(SafetyIssueLink).where(
                    SafetyIssueLink.assessment_id == assessment_id
                )
            )
            return AssessmentDetail(
                assessment=assessment,
                dimensions=dimensions,
                cra_reviews=reviews,
                medical_responses=responses,
                issue_link=issue_link,
            )

    def list_assessments(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
        subject_id: uuid.UUID,
    ) -> list[SafetyAssessment]:
        self._authorize_read(scope, study_id, site_id)
        with self.session_factory() as session:
            return list(
                session.scalars(
                    select(SafetyAssessment)
                    .where(
                        SafetyAssessment.tenant_id == scope.tenant_id,
                        SafetyAssessment.study_id == study_id,
                        SafetyAssessment.site_id == site_id,
                        SafetyAssessment.subject_id == subject_id,
                    )
                    .order_by(
                        SafetyAssessment.event_date.desc(),
                        SafetyAssessment.created_at.desc(),
                    )
                )
            )

    def _subject_and_facts(
        self,
        scope: ScopeContext,
        command: CreateSafetyAssessmentCommand,
    ) -> tuple[SubjectSummary, list[TimelineItem], list[FactSnapshot]]:
        summaries = self.subjects.list_subjects(
            scope, command.study_id, command.site_id
        )
        summary = next(
            (
                item
                for item in summaries
                if item.subject.id == command.subject_id
            ),
            None,
        )
        if summary is None:
            raise SafetyNotFound("subject was not found in the authorized site")
        timeline = self.subjects.timeline(scope, command.subject_id)
        current = [item for item in timeline if item.is_current]
        snapshots = [
            FactSnapshot(
                fact=item.fact,
                evidence_id=f"FACT:{item.fact.id}",
                deterministic=item.fact.verification_status
                in {"original_record", "cra_confirmed"},
            )
            for item in current
        ]
        return summary, timeline, snapshots

    @staticmethod
    def _fact_values(
        snapshots: list[FactSnapshot],
    ) -> tuple[dict[str, FactValue], set[str], set[str]]:
        grouped: dict[str, list[FactSnapshot]] = defaultdict(list)
        for snapshot in snapshots:
            grouped[snapshot.fact.fact_key].append(snapshot)
        facts: dict[str, FactValue] = {}
        ambiguous: set[str] = set()
        non_deterministic: set[str] = set()
        for key, items in grouped.items():
            if len(items) != 1:
                ambiguous.add(key)
                continue
            snapshot = items[0]
            if not snapshot.deterministic:
                non_deterministic.add(key)
                continue
            facts[key] = FactValue(
                value=_json_value(snapshot.fact.value_json),
                unit=snapshot.fact.unit,
                precision=snapshot.fact.precision,
            )
        return facts, ambiguous, non_deterministic

    @staticmethod
    def _active_safety_decisions(
        decisions: list[CheckDecision],
    ) -> list[CheckDecision]:
        return [
            item
            for item in decisions
            if item.category == "safety" and item.state == "active"
        ]

    @staticmethod
    def _not_checked_for_dimension(
        dimension: SafetyDimension,
        decisions: list[CheckDecision],
        event_date: date,
    ) -> CheckDecision | None:
        for decision in decisions:
            if (
                decision.scope_start is not None
                and event_date < decision.scope_start
            ):
                continue
            if (
                decision.scope_end is not None
                and event_date > decision.scope_end
            ):
                continue
            if (
                dimension in decision.affected_paths
                or dimension in decision.check_type
                or "assessment" in decision.check_type
            ):
                return decision
        return None

    def _dimension_drafts(
        self,
        *,
        event_date: date,
        requested: list[SafetyDimension],
        rule_outcome: ApplicabilityOutcome,
        facts: dict[str, FactValue],
        ambiguous_fact_keys: set[str],
        non_deterministic_fact_keys: set[str],
        active_decisions: list[CheckDecision],
    ) -> tuple[
        list[DimensionDraft],
        list[QuestionDraft],
        list[TimelyAlertDraft],
        list[dict[str, Any]],
        list[SourceRef],
        list[dict[str, Any]],
        list[str],
    ]:
        dimensions: list[DimensionDraft] = []
        questions: list[QuestionDraft] = []
        alert_drafts: list[TimelyAlertDraft] = []
        rule_inputs: list[dict[str, Any]] = []
        all_source_refs: list[SourceRef] = []
        provider_evidence: list[dict[str, Any]] = []
        unknown_codes: list[str] = []

        for item in rule_outcome.rules:
            evidence, refs, evidence_ids = _rule_evidence(item)
            provider_evidence.extend(evidence)
            all_source_refs.extend(refs)
            rule_inputs.append(
                {
                    "rule_id": str(item.rule.id),
                    "rule_version_id": str(item.version.id),
                    "rule_key": item.rule.rule_key,
                    "title": item.rule.title,
                    "policy_layer": item.rule.policy_layer,
                    "activation_id": str(item.activation_id),
                    "evaluation": item.evaluation.model_dump(mode="json"),
                    "evidence_ids": evidence_ids,
                }
            )

        for dimension in requested:
            skipped = self._not_checked_for_dimension(
                dimension, active_decisions, event_date
            )
            if skipped is not None:
                dimensions.append(
                    DimensionDraft(
                        dimension=dimension,
                        status="not_checked_by_user",
                        label=DIMENSION_LABELS[dimension],
                        candidate_values=(),
                        rationale=(
                            "CRA has explicitly skipped this dependent safety "
                            "path; it is not normal or completed."
                        ),
                        uncertainties=(skipped.reason,),
                        rule_version_ids=(
                            (str(skipped.rule_version_id),)
                            if skipped.rule_version_id
                            else ()
                        ),
                        evidence_ids=(),
                        source_refs=(),
                    )
                )
                continue

            matched = [
                item
                for item in rule_outcome.rules
                if _rule_matches_dimension(
                    item.rule.rule_key,
                    item.rule.title,
                    item.tree,
                    dimension,
                )
            ]
            if not matched:
                dimensions.append(
                    _failed_dimension(
                        dimension,
                        reason=(
                            "applicable project rule for this safety dimension "
                            "is missing or not activated"
                        ),
                    )
                )
                unknown_codes.append(f"rule_missing:{dimension}")
                questions.append(
                    QuestionDraft(
                        question_key=f"rule:{dimension}",
                        dimension=dimension,
                        question=(
                            f"请确认项目适用并已确认的{DIMENSION_LABELS[dimension]}"
                            "规则及启用版本；当前未用其他版本替代。"
                        ),
                        reason="applicable rule missing",
                        priority="normal",
                        evidence_ids=(),
                    )
                )
                continue

            evidence_ids: list[str] = []
            source_refs: list[SourceRef] = []
            version_ids: list[str] = []
            candidate_values: list[str] = []
            uncertainties: list[str] = []
            statuses: list[str] = []
            for item in matched:
                version_ids.append(str(item.version.id))
                evidence, refs, ids = _rule_evidence(item)
                evidence_ids.extend(ids)
                source_refs.extend(refs)
                provider_evidence.extend(evidence)
                all_source_refs.extend(refs)
                statuses.append(item.evaluation.status)
                if item.evaluation.status in {"unknown", "analysis_required"}:
                    uncertainties.extend(
                        item.evaluation.unknowns
                        or ["rule requires manual analysis"]
                    )
                    missing = [
                        key
                        for key in item.tree.required_facts
                        if key not in facts
                    ]
                    uncertainties.extend(
                        f"required fact missing: {key}" for key in missing
                    )
                    for key in missing:
                        question = _missing_fact_question(dimension, key)
                        questions.append(
                            QuestionDraft(
                                question_key=f"{dimension}:{key}",
                                dimension=dimension,
                                question=question,
                                reason=f"required fact `{key}` is unavailable",
                                priority="normal",
                                evidence_ids=tuple(ids),
                            )
                        )
                elif item.evaluation.status in {"applicable", "exception"}:
                    branch_actions = [
                        action
                        for branch in item.evaluation.branches
                        if branch.result == "true"
                        for action in branch.actions
                    ]
                    candidate_values.extend(
                        branch_actions
                        if branch_actions
                        else [item.tree.summary]
                    )
                    if item.evaluation.status == "exception":
                        candidate_values.extend(
                            exception.description
                            for exception, result in zip(
                                item.tree.exceptions,
                                item.evaluation.exceptions,
                                strict=False,
                            )
                            if result.result == "true"
                        )

            evidence_ids = list(dict.fromkeys(evidence_ids))
            version_ids = list(dict.fromkeys(version_ids))
            candidate_values = list(dict.fromkeys(candidate_values))
            uncertainties = list(dict.fromkeys(uncertainties))
            if candidate_values:
                status = "candidate"
                rationale = (
                    "Program evaluation found applicable source-backed "
                    "candidate actions; this is not a final medical judgment."
                )
                questions.append(
                    QuestionDraft(
                        question_key=f"candidate:{dimension}",
                        dimension=dimension,
                        question=(
                            f"针对{DIMENSION_LABELS[dimension]}候选，请核对适用规则、"
                            "原始事实和研究者/医学评估并记录依据；系统候选不替代最终判断。"
                        ),
                        reason="source-backed candidate requires confirmation",
                        priority="normal",
                        evidence_ids=tuple(evidence_ids),
                    )
                )
            elif "unknown" in statuses or "analysis_required" in statuses:
                status = (
                    "analysis_required"
                    if "analysis_required" in statuses
                    else "unknown"
                )
                rationale = (
                    "The deterministic condition remains unknown; no result "
                    "has been inferred."
                )
                unknown_codes.append(f"{status}:{dimension}")
            else:
                status = "not_applicable"
                rationale = (
                    "Applicable structured conditions evaluated false; this "
                    "dimension is not triggered for the stated event."
                )
            if status in {"unknown", "analysis_required"} and not questions:
                for key in (
                    matched[0].tree.required_facts
                    if matched
                    else ["ae_term"]
                ):
                    if key not in facts:
                        questions.append(
                            QuestionDraft(
                                question_key=f"{dimension}:{key}",
                                dimension=dimension,
                                question=_missing_fact_question(dimension, key),
                                reason=f"required fact `{key}` is unknown",
                                priority="normal",
                                evidence_ids=tuple(evidence_ids),
                            )
                        )
            dimensions.append(
                DimensionDraft(
                    dimension=dimension,
                    status=status,
                    label=DIMENSION_LABELS[dimension],
                    candidate_values=tuple(candidate_values),
                    rationale=rationale,
                    uncertainties=tuple(uncertainties),
                    rule_version_ids=tuple(version_ids),
                    evidence_ids=tuple(evidence_ids),
                    source_refs=tuple(
                        ref.model_dump(mode="json") for ref in source_refs
                    ),
                )
            )

        serious = next(
            (item for item in dimensions if item.dimension == "seriousness"),
            None,
        )
        timeliness = next(
            (
                item
                for item in dimensions
                if item.dimension == "reporting_timeliness"
            ),
            None,
        )
        urgency_evidence = []
        urgency_ids: list[str] = []
        for candidate in (serious, timeliness):
            if candidate is None:
                continue
            text = " ".join(candidate.candidate_values).casefold()
            if candidate.status == "candidate" and re.search(
                r"report|notify|timeline|urgent|上报|报告|通知|时限",
                text,
                re.IGNORECASE,
            ):
                urgency_ids.extend(candidate.evidence_ids)
        if urgency_ids:
            def fact_date(key: str) -> date | None:
                fact = facts.get(key)
                if fact is None:
                    return None
                if isinstance(fact.value, date):
                    return fact.value
                try:
                    return date.fromisoformat(str(fact.value)[:10])
                except ValueError:
                    return None

            awareness = fact_date("safety_awareness_date")
            entry = fact_date("safety_entry_date")
            reported = fact_date("safety_reported_date")
            alert_drafts.append(
                TimelyAlertDraft(
                    alert_key="sae-time-anchors",
                    title="候选严重安全事件：立即核对报告时间",
                    detail=(
                        "适用规则触发了SAE/及时报告候选。事件、知悉、录入和"
                        "实际上报日期分别表达；在缺知悉时间或适用时限依据时"
                        "系统不计算超期，也不等待报告签发。"
                    ),
                    dimensions=tuple(
                        item.dimension
                        for item in (serious, timeliness)
                        if item is not None and item.status == "candidate"
                    ),
                    evidence_ids=tuple(dict.fromkeys(urgency_ids)),
                    event_date=event_date,
                    awareness_date=awareness,
                    entry_date=entry,
                    reported_date=reported,
                    deadline_status=(
                        "awareness_time_missing"
                        if awareness is None
                        else "rule_based_deadline_requires_review"
                    ),
                )
            )
            if awareness is None:
                questions.append(
                    QuestionDraft(
                        question_key="timeliness:awareness",
                        dimension="reporting_timeliness",
                        question=(
                            "请确认研究者或中心首次知悉该SAE的日期和时间；"
                            "事件日期已知，但知悉、录入和实际上报分别未补，"
                            "当前不计算报告超期。"
                        ),
                        reason="awareness time is missing",
                        priority="timely",
                        evidence_ids=tuple(dict.fromkeys(urgency_ids)),
                    )
                )
        questions = list(
            {
                item.question_key: item for item in questions
            }.values()
        )
        questions.sort(key=lambda item: (item.priority != "timely", item.question_key))
        for fact_key in sorted(ambiguous_fact_keys):
            unknown_codes.append(f"ambiguous_fact:{fact_key}")
        for fact_key in sorted(non_deterministic_fact_keys):
            unknown_codes.append(f"non_deterministic_fact:{fact_key}")
        return (
            dimensions,
            questions,
            alert_drafts,
            rule_inputs,
            all_source_refs,
            provider_evidence,
            unknown_codes,
        )

    def _lab_questions(
        self,
        scope: ScopeContext,
        command: CreateSafetyAssessmentCommand,
        summary: SubjectSummary,
    ) -> tuple[
        ComparisonDetail | None,
        list[QuestionDraft],
        list[dict[str, Any]],
        list[SourceRef],
    ]:
        if command.lab_comparison_id is None:
            return None, [], [], []
        detail = self.laboratory.comparison_detail(
            scope, command.lab_comparison_id
        )
        if (
            detail.comparison.study_id != command.study_id
            or detail.comparison.site_id != command.site_id
        ):
            raise SafetyValidationError(
                "laboratory comparison is outside the assessment site"
            )
        identifiers = {
            item.external_id for item in summary.identifiers
        }
        fields = [
            field
            for field in detail.fields
            if str(field.matched_identity.get("subject_external_id"))
            in identifiers
        ]
        if not fields:
            raise SafetyValidationError(
                "laboratory comparison does not contain this subject"
            )
        questions = []
        evidence = []
        refs = []
        for field in fields:
            if field.result_status == "agreement":
                continue
            evidence_id = f"LAB:{field.id}"
            questions.append(
                QuestionDraft(
                    question_key=f"lab:{field.id}",
                    dimension="ae_collection",
                    question=(
                        f"请核实检验项目 {field.matched_identity.get('analyte')} "
                        f"的{field.result_status}结果是否构成需要收集的AE线索，"
                        "并核对源报告、EDC和临床意义；数值一致或差异均不等于医学安全结论。"
                    ),
                    reason=(
                        field.reason
                        or "laboratory comparison requires safety review"
                    ),
                    priority="normal",
                    evidence_ids=(evidence_id,),
                )
            )
            evidence.append(
                {
                    "evidence_id": evidence_id,
                    "text": (
                        f"{field.matched_identity.get('analyte')}: "
                        f"{field.source_value} {field.source_unit or ''} vs "
                        f"{field.edc_value} {field.edc_unit or ''}; "
                        f"status={field.result_status}"
                    ),
                    "kind": "laboratory_comparison",
                    "source_ref": SourceRef(
                        source_type="record",
                        source_id=str(field.id),
                        version=str(detail.comparison.revision),
                        locator="laboratory_comparison_field",
                        quote=field.reason,
                    ).model_dump(mode="json", exclude_none=True),
                }
            )
            refs.append(
                SourceRef(
                    source_type="record",
                    source_id=str(field.id),
                    version=str(detail.comparison.revision),
                    locator="laboratory_comparison_field",
                    quote=field.reason,
                )
            )
        return detail, questions, evidence, refs

    def _provider_analysis(
        self,
        *,
        case_id: uuid.UUID,
        facts: list[FactSnapshot],
        dimensions: list[DimensionDraft],
        evidence: list[dict[str, Any]],
    ) -> tuple[CaseModelResult, dict[str, Any]]:
        if not evidence:
            provider_name = getattr(self.provider, "name", "unknown")
            provider_version = getattr(self.provider, "version", "unknown")
            result = CaseModelResult(
                provider_name=provider_name,
                provider_version=provider_version,
                model_version=getattr(self.provider, "model_version", None),
                status="unavailable",
                raw_output=None,
                error="no grounded evidence is available for explanation",
            )
            return result, {
                "accepted": False,
                "explanation": None,
                "evidence_ids": [],
                "source_refs": [],
                "errors": [result.error],
            }
        has_candidate = any(
            item.status == "candidate" for item in dimensions
        )
        has_unknown = any(
            item.status in {"unknown", "analysis_required"}
            for item in dimensions
        )
        allowed_codes = (
            ["candidate_and_unknown_review"]
            if has_candidate and has_unknown
            else ["candidate_review"]
            if has_candidate
            else ["unknown_clarification"]
            if has_unknown
            else ["general_review"]
        )
        request = {
            "case_id": str(case_id),
            "source": "pure_synthetic",
            "facts": [
                {
                    "evidence_id": item.evidence_id,
                    "fact_key": item.fact.fact_key,
                    "value": _json_value(item.fact.value_json),
                }
                for item in facts
            ],
            "dimensions": [
                {
                    "dimension": item.dimension,
                    "status": item.status,
                    "text": (
                        "; ".join(item.candidate_values)
                        or "; ".join(item.uncertainties)
                        or item.label
                    ),
                }
                for item in dimensions
            ],
            "evidence": evidence,
            "allowed_explanation_codes": allowed_codes,
        }
        result = self.provider.analyze_batch([request])[0]
        if result.status != "completed" or not result.raw_output:
            return result, {
                "accepted": False,
                "explanation": None,
                "evidence_ids": [],
                "errors": [result.error or "provider did not return output"],
            }
        grounded = validate_model_explanation(
            result.raw_output,
            allowed_evidence_ids={
                str(item["evidence_id"]) for item in evidence
            },
            allowed_explanation_codes=set(allowed_codes),
        )
        by_evidence_id = {
            str(item["evidence_id"]): item for item in evidence
        }
        source_refs = [
            SourceRef.model_validate(by_evidence_id[evidence_id]["source_ref"])
            for evidence_id in grounded.evidence_ids
            if evidence_id in by_evidence_id
            and by_evidence_id[evidence_id].get("source_ref") is not None
        ]
        return result, {
            "accepted": grounded.accepted,
            "explanation": grounded.explanation,
            "evidence_ids": list(grounded.evidence_ids),
            "source_refs": [
                item.model_dump(mode="json", exclude_none=True)
                for item in source_refs
            ],
            "errors": list(grounded.errors),
            "raw_output": result.raw_output,
        }

    def create(
        self,
        scope: ScopeContext,
        command: CreateSafetyAssessmentCommand,
    ) -> AssessmentDetail:
        self._authorize_write(scope, command.study_id, command.site_id)
        requested = _requested_dimensions(command)
        summary, _timeline, fact_snapshots = self._subject_and_facts(
            scope, command
        )
        facts, ambiguous, non_deterministic = self._fact_values(
            fact_snapshots
        )
        active_decisions = self._active_safety_decisions(
            self.subjects.list_check_decisions(scope, command.subject_id)
        )
        rule_outcome = self.rules.applicable_rules(
            scope,
            ApplicableRuleQuery(
                study_id=command.study_id,
                site_id=command.site_id,
                event_date=command.event_date,
                facts=facts,
            ),
        )
        (
            dimensions,
            questions,
            alerts,
            rule_inputs,
            rule_refs,
            rule_evidence,
            unknown_codes,
        ) = self._dimension_drafts(
            event_date=command.event_date,
            requested=requested,
            rule_outcome=rule_outcome,
            facts=facts,
            ambiguous_fact_keys=ambiguous,
            non_deterministic_fact_keys=non_deterministic,
            active_decisions=active_decisions,
        )
        comparison, lab_questions, lab_evidence, lab_refs = self._lab_questions(
            scope, command, summary
        )
        questions.extend(lab_questions)
        questions = list(
            {item.question_key: item for item in questions}.values()
        )
        questions.sort(key=lambda item: (item.priority != "timely", item.question_key))
        fact_evidence = [
            {
                "evidence_id": item.evidence_id,
                "text": f"{item.fact.fact_key}={item.fact.value_raw}",
                "kind": "fact",
                "source_ref": _source_ref_from_fact(item.fact).model_dump(
                    mode="json", exclude_none=True
                ),
            }
            for item in fact_snapshots
            if item.deterministic
        ]
        all_evidence = [*fact_evidence, *rule_evidence, *lab_evidence]
        assessment_id = uuid.uuid4()
        model_result, provider_output = self._provider_analysis(
            case_id=assessment_id,
            facts=fact_snapshots,
            dimensions=dimensions,
            evidence=all_evidence,
        )
        context_snapshot = {
            "subject_label": summary.subject.deidentified_label,
            "facts": [_fact_dict(item.fact) for item in fact_snapshots],
            "ambiguous_fact_keys": sorted(ambiguous),
            "non_deterministic_fact_keys": sorted(non_deterministic),
            "active_safety_decisions": [
                {
                    "id": str(item.id),
                    "check_type": item.check_type,
                    "reason": item.reason,
                    "missing_keys": item.missing_keys,
                    "affected_paths": item.affected_paths,
                }
                for item in active_decisions
            ],
            "laboratory_comparison_id": (
                str(comparison.comparison.id) if comparison else None
            ),
            "note": command.note,
        }
        provider_status = (
            "completed"
            if provider_output["accepted"]
            else "rejected"
            if model_result.status == "completed"
            else "not_configured"
            if model_result.status == "unavailable"
            else "failed"
        )
        if provider_status in {"rejected", "failed", "not_configured"}:
            unknown_codes.append(f"provider:{provider_status}")
        unknown_items = [
            UnknownItem(
                code=code[:128],
                reason=code.replace("_", " "),
                affected_scope=summary.subject.deidentified_label,
            )
            for code in dict.fromkeys(unknown_codes)
        ]
        unknown_items.extend(
            UnknownItem(
                code=f"dimension_unknown:{item.dimension}",
                reason=(
                    "; ".join(item.uncertainties)
                    or "required safety condition remains unknown"
                )[:1000],
                affected_scope=summary.subject.deidentified_label,
            )
            for item in dimensions
            if item.status in {"unknown", "analysis_required"}
        )
        not_checked = [
            NotCheckedItem(
                code=f"not_checked:{item.dimension}",
                scope=summary.subject.deidentified_label,
                reason=(
                    "; ".join(item.uncertainties)
                    or "CRA explicitly skipped this safety path"
                )[:1000],
                decision_ref=(
                    str(
                        next(
                            (
                                decision.id
                                for decision in active_decisions
                                if item.dimension
                                in decision.affected_paths
                                or item.dimension in decision.check_type
                            ),
                            "",
                        )
                    )
                    or None
                ),
            )
            for item in dimensions
            if item.status == "not_checked_by_user"
        ]
        fact_claims = [
            Claim(
                claim_id=item.evidence_id,
                kind="fact",
                label=item.fact.fact_key,
                value=_json_value(item.fact.value_json),
                verification_status=(
                    "cra_confirmed"
                    if item.fact.verification_status == "cra_confirmed"
                    else "needs_review"
                ),
                source_refs=[_source_ref_from_fact(item.fact)],
                calculation=None,
            )
            for item in fact_snapshots
        ]
        dimension_claims = [
            Claim(
                claim_id=f"DIMENSION:{item.dimension}",
                kind="auto_candidate",
                label=item.label,
                value={
                    "status": item.status,
                    "candidate_values": list(item.candidate_values),
                    "uncertainties": list(item.uncertainties),
                },
                verification_status="needs_review",
                source_refs=[
                    SourceRef.model_validate(ref) for ref in item.source_refs
                ],
                calculation="W04 closed AST plus programmatic dimensions",
            )
            for item in dimensions
        ]
        provider_claim = []
        if provider_output["accepted"]:
            provider_claim.append(
                Claim(
                    claim_id=f"MODEL:{assessment_id}",
                    kind="inference",
                    label="受限模型解释",
                    value=provider_output["explanation"],
                    verification_status="needs_review",
                    source_refs=[
                        SourceRef.model_validate(item)
                        for item in provider_output["source_refs"]
                    ],
                    calculation="language explanation; not a decision source",
                )
            )
        envelope_status = (
            "needs_clarification"
            if questions or unknown_items
            else "ready_to_review"
        )
        envelope = OutputEnvelope(
            output_id=assessment_id,
            purpose="safety_analysis",
            scope=OutputScope(
                tenant_id=scope.tenant_id,
                study_id=command.study_id,
                site_id=command.site_id,
                subject_id=str(command.subject_id),
            ),
            input_revisions=[
                InputRevision(
                    resource_type="clinical_fact",
                    resource_id=str(item.fact.id),
                    revision=item.fact.revision,
                )
                for item in fact_snapshots
            ]
            + [
                InputRevision(
                    resource_type="rule_version",
                    resource_id=str(item.version.id),
                    revision=item.version.version_no,
                    digest=item.version.content_hash,
                )
                for item in rule_outcome.rules
            ]
            + (
                [
                    InputRevision(
                        resource_type="lab_comparison",
                        resource_id=str(comparison.comparison.id),
                        revision=comparison.comparison.revision,
                        digest=comparison.comparison.input_digest,
                    )
                ]
                if comparison
                else []
            ),
            policy_versions=rule_outcome.envelope.policy_versions,
            claims=[*fact_claims, *dimension_claims, *provider_claim],
            evidence_refs=[
                *[_source_ref_from_fact(item.fact) for item in fact_snapshots],
                *rule_refs,
                *lab_refs,
            ],
            unknowns=unknown_items,
            conflicts=rule_outcome.envelope.conflicts,
            not_checked=not_checked,
            capabilities=[
                OutputCapability(
                    capability_id="analyze_case",
                    level=(
                        "validated"
                        if provider_output["accepted"]
                        else "limited"
                    ),
                    validated=bool(provider_output["accepted"]),
                    limitations=[
                        "Synthetic/provider engineering validation only",
                        "Not a final medical judgment",
                        "Missing facts remain unknown",
                    ],
                )
            ],
            status=envelope_status,
            generated_at=datetime.now(UTC),
            actor_id=scope.actor_id,
        )
        assessment_key = _digest(
            {
                "subject_id": str(command.subject_id),
                "event_type": command.event_type,
                "event_date": command.event_date,
                "requested_dimensions": requested,
                "facts": [_fact_dict(item.fact) for item in fact_snapshots],
                "rule_versions": sorted(
                    str(item.version.id) for item in rule_outcome.rules
                ),
                "lab_comparison_id": (
                    str(comparison.comparison.id) if comparison else None
                ),
                "provider": {
                    "name": model_result.provider_name,
                    "version": model_result.provider_version,
                    "model": model_result.model_version,
                },
                "active_safety_decision_ids": sorted(
                    str(item.id) for item in active_decisions
                ),
            }
        )
        try:
            return self._persist_new_assessment(
                scope=scope,
                command=command,
                requested=requested,
                assessment_id=assessment_id,
                assessment_key=assessment_key,
                lab_comparison_id=(
                    comparison.comparison.id if comparison else None
                ),
                context_snapshot=context_snapshot,
                rule_inputs=rule_inputs,
                dimensions=dimensions,
                questions=questions,
                alerts=alerts,
                unknown_items=unknown_items,
                not_checked=not_checked,
                envelope=envelope,
                model_result=model_result,
                provider_status=provider_status,
                provider_output=provider_output,
                existing_key=assessment_key,
            )
        except IntegrityError:
            with self.session_factory() as session:
                existing = session.scalar(
                    select(SafetyAssessment).where(
                        SafetyAssessment.tenant_id == scope.tenant_id,
                        SafetyAssessment.study_id == command.study_id,
                        SafetyAssessment.site_id == command.site_id,
                        SafetyAssessment.assessment_key == assessment_key,
                    )
                )
                if existing is None:
                    raise
                detail = self.detail(scope, existing.id)
                return AssessmentDetail(
                    assessment=detail.assessment,
                    dimensions=detail.dimensions,
                    cra_reviews=detail.cra_reviews,
                    medical_responses=detail.medical_responses,
                    issue_link=detail.issue_link,
                    replayed=True,
                )

    def _persist_new_assessment(
        self,
        *,
        scope: ScopeContext,
        command: CreateSafetyAssessmentCommand,
        requested: list[SafetyDimension],
        assessment_id: uuid.UUID,
        assessment_key: str,
        lab_comparison_id: uuid.UUID | None,
        context_snapshot: dict[str, Any],
        rule_inputs: list[dict[str, Any]],
        dimensions: list[DimensionDraft],
        questions: list[QuestionDraft],
        alerts: list[TimelyAlertDraft],
        unknown_items: list[UnknownItem],
        not_checked: list[NotCheckedItem],
        envelope: OutputEnvelope,
        model_result: CaseModelResult,
        provider_status: str,
        provider_output: dict[str, Any],
        existing_key: str,
    ) -> AssessmentDetail:
        with self.session_factory() as session:
            existing = session.scalar(
                select(SafetyAssessment).where(
                    SafetyAssessment.tenant_id == scope.tenant_id,
                    SafetyAssessment.study_id == command.study_id,
                    SafetyAssessment.site_id == command.site_id,
                    SafetyAssessment.assessment_key == existing_key,
                )
            )
            if existing is not None:
                detail = self.detail(scope, existing.id)
                return AssessmentDetail(
                    assessment=detail.assessment,
                    dimensions=detail.dimensions,
                    cra_reviews=detail.cra_reviews,
                    medical_responses=detail.medical_responses,
                    issue_link=detail.issue_link,
                    replayed=True,
                )
            session.rollback()
            with session.begin():
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=command.study_id,
                    site_id=command.site_id,
                    command_name="safety.assessment.create",
                    idempotency_key=command.idempotency_key,
                    command={
                        **command.model_dump(mode="json"),
                        "assessment_key": assessment_key,
                    },
                )
                if replayed:
                    assert record.response_resource_id is not None
                    return self.detail(scope, record.response_resource_id)
                assessment = SafetyAssessment(
                    id=assessment_id,
                    tenant_id=scope.tenant_id,
                    study_id=command.study_id,
                    site_id=command.site_id,
                    subject_id=command.subject_id,
                    lab_comparison_id=lab_comparison_id,
                    assessment_key=assessment_key,
                    event_type=command.event_type,
                    event_date=command.event_date,
                    requested_dimensions=list(requested),
                    context_snapshot=context_snapshot,
                    rule_inputs=rule_inputs,
                    deterministic_summary={
                        "dimensions": [
                            {
                                "dimension": item.dimension,
                                "status": item.status,
                                "candidate_values": list(item.candidate_values),
                                "uncertainties": list(item.uncertainties),
                            }
                            for item in dimensions
                        ],
                        "questions": [
                            {
                                "question_key": item.question_key,
                                "dimension": item.dimension,
                                "question": item.question,
                                "reason": item.reason,
                                "priority": item.priority,
                                "evidence_ids": list(item.evidence_ids),
                            }
                            for item in questions
                        ],
                    },
                    provider_name=model_result.provider_name,
                    provider_version=model_result.provider_version,
                    model_version=model_result.model_version,
                    provider_status=provider_status,
                    provider_output=provider_output,
                    questions=[
                        {
                            "question_key": item.question_key,
                            "dimension": item.dimension,
                            "question": item.question,
                            "reason": item.reason,
                            "priority": item.priority,
                            "evidence_ids": list(item.evidence_ids),
                        }
                        for item in questions
                    ],
                    timely_alerts=[
                        {
                            "alert_key": item.alert_key,
                            "title": item.title,
                            "detail": item.detail,
                            "dimensions": list(item.dimensions),
                            "evidence_ids": list(item.evidence_ids),
                            "event_date": command.event_date.isoformat(),
                            "awareness_date": (
                                item.awareness_date.isoformat()
                                if item.awareness_date
                                else None
                            ),
                            "entry_date": (
                                item.entry_date.isoformat()
                                if item.entry_date
                                else None
                            ),
                            "reported_date": (
                                item.reported_date.isoformat()
                                if item.reported_date
                                else None
                            ),
                            "deadline_status": item.deadline_status,
                            "not_a_final_reportability_decision": True,
                        }
                        for item in alerts
                    ],
                    unknowns=[item.model_dump(mode="json") for item in unknown_items],
                    evidence_refs=[
                        item.model_dump(mode="json")
                        for item in envelope.evidence_refs
                    ],
                    output_envelope=envelope.model_dump(mode="json"),
                    status=envelope.status,
                    revision=1,
                    created_by=scope.actor_id,
                )
                session.add(assessment)
                session.flush()
                for item in dimensions:
                    session.add(
                        SafetyDimensionResult(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=command.study_id,
                            site_id=command.site_id,
                            assessment_id=assessment.id,
                            dimension=item.dimension,
                            status=item.status,
                            label=item.label,
                            candidate_values=list(item.candidate_values),
                            rationale=item.rationale,
                            uncertainties=list(item.uncertainties),
                            rule_version_ids=list(item.rule_version_ids),
                            evidence_ids=list(item.evidence_ids),
                            source_refs=list(item.source_refs),
                        )
                    )
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=command.study_id,
                        site_id=command.site_id,
                        actor_id=scope.actor_id,
                        action="safety.assessment.create",
                        resource_type="safety_assessment",
                        resource_id=assessment.id,
                        revision_before=None,
                        revision_after=1,
                        before_state=None,
                        after_state={
                            "event_type": command.event_type,
                            "event_date": command.event_date.isoformat(),
                            "status": assessment.status,
                            "provider_status": provider_status,
                            "dimensions": [
                                item.dimension for item in dimensions
                            ],
                        },
                        command_name="safety.assessment.create",
                        correlation_id=record.id,
                    )
                )
                self._complete(record, assessment.id, 1)
        return self.detail(scope, assessment_id)

    def record_cra_review(
        self,
        scope: ScopeContext,
        assessment_id: uuid.UUID,
        command: CraSafetyReviewCommand,
    ) -> AssessmentDetail:
        assessment = self._load_assessment(scope, assessment_id)
        self._authorize_write(scope, assessment.study_id, assessment.site_id)
        outside = sorted(
            set(command.dimensions) - set(assessment.requested_dimensions)
        )
        if outside:
            raise SafetyValidationError(
                "CRA review dimensions are outside this assessment: "
                + ", ".join(outside)
            )
        request_digest = _digest(
            {
                "assessment_id": str(assessment.id),
                "command": command.model_dump(mode="json"),
            }
        )
        with self.session_factory() as session:
            record, replayed = self._reserve(
                session,
                scope=scope,
                study_id=assessment.study_id,
                site_id=assessment.site_id,
                command_name="safety.assessment.cra_review",
                idempotency_key=command.idempotency_key,
                command={
                    "assessment_id": str(assessment_id),
                    "command": command.model_dump(mode="json"),
                    "digest": request_digest,
                },
            )
            if replayed:
                session.commit()
                return self.detail(scope, assessment_id)
            session.rollback()
        check_decision_id = None
        if command.decision == "not_checked_by_user":
            unknown_keys = [
                item["code"]
                for item in assessment.unknowns
                if any(
                    dimension in str(item.get("affected_scope", ""))
                    or dimension in str(item.get("reason", ""))
                    for dimension in command.dimensions
                )
            ]
            missing_keys = unknown_keys or [
                f"user_skipped:{dimension}" for dimension in command.dimensions
            ]
            decision = self.subjects.decide_not_checked(
                scope,
                assessment.subject_id,
                CheckDecisionCommand(
                    idempotency_key=command.idempotency_key,
                    category="safety",
                    check_type=f"safety_assessment:{assessment.id}",
                    reason="declined_missing_data",
                    scope_start=assessment.event_date,
                    scope_end=assessment.event_date,
                    missing_keys=missing_keys,
                    affected_paths=list(command.dimensions),
                    can_continue=[
                        item
                        for item in DIMENSIONS
                        if item not in command.dimensions
                    ],
                    rule_version_id=None,
                ),
            )
            check_decision_id = decision.id
        with self.session_factory() as session:
            with session.begin():
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=assessment.study_id,
                    site_id=assessment.site_id,
                    command_name="safety.assessment.cra_review",
                    idempotency_key=command.idempotency_key,
                    command={
                        "assessment_id": str(assessment_id),
                        "command": command.model_dump(mode="json"),
                        "digest": request_digest,
                    },
                )
                if replayed:
                    return self.detail(scope, assessment_id)
                review = SafetyCraReview(
                    id=uuid.uuid4(),
                    tenant_id=assessment.tenant_id,
                    study_id=assessment.study_id,
                    site_id=assessment.site_id,
                    assessment_id=assessment.id,
                    decision=command.decision,
                    dimensions=list(command.dimensions),
                    note=command.note,
                    check_decision_id=check_decision_id,
                    actor_id=scope.actor_id,
                )
                session.add(review)
                session.flush()
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=assessment.tenant_id,
                        study_id=assessment.study_id,
                        site_id=assessment.site_id,
                        actor_id=scope.actor_id,
                        action=f"safety.assessment.{command.decision}",
                        resource_type="safety_assessment",
                        resource_id=assessment.id,
                        revision_before=None,
                        revision_after=assessment.revision,
                        before_state=None,
                        after_state={
                            "review_id": str(review.id),
                            "dimensions": list(command.dimensions),
                            "check_decision_id": (
                                str(check_decision_id)
                                if check_decision_id
                                else None
                            ),
                        },
                        command_name="safety.assessment.cra_review",
                        correlation_id=record.id,
                    )
                )
                self._complete(record, review.id, assessment.revision)
        return self.detail(scope, assessment_id)

    def record_medical_response(
        self,
        scope: ScopeContext,
        assessment_id: uuid.UUID,
        command: MedicalSafetyResponseCommand,
    ) -> AssessmentDetail:
        assessment = self._load_assessment(scope, assessment_id)
        self._authorize_write(scope, assessment.study_id, assessment.site_id)
        outside = sorted(
            set(command.dimension_responses)
            - set(assessment.requested_dimensions)
        )
        if outside:
            raise SafetyValidationError(
                "medical response dimensions are outside this assessment: "
                + ", ".join(outside)
            )
        with self.session_factory() as session:
            with session.begin():
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=assessment.study_id,
                    site_id=assessment.site_id,
                    command_name="safety.assessment.medical_response",
                    idempotency_key=command.idempotency_key,
                    command={
                        "assessment_id": str(assessment_id),
                        "command": command.model_dump(mode="json"),
                    },
                )
                if replayed:
                    return self.detail(scope, assessment_id)
                response = MedicalSafetyResponse(
                    id=uuid.uuid4(),
                    tenant_id=assessment.tenant_id,
                    study_id=assessment.study_id,
                    site_id=assessment.site_id,
                    assessment_id=assessment.id,
                    respondent_role=command.respondent_role,
                    respondent_name=command.respondent_name,
                    response_text=command.response_text,
                    dimension_responses=dict(command.dimension_responses),
                    source_note=command.source_note,
                    actor_id=scope.actor_id,
                )
                session.add(response)
                session.flush()
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=assessment.tenant_id,
                        study_id=assessment.study_id,
                        site_id=assessment.site_id,
                        actor_id=scope.actor_id,
                        action="safety.assessment.medical_response",
                        resource_type="safety_assessment",
                        resource_id=assessment.id,
                        revision_before=None,
                        revision_after=assessment.revision,
                        before_state=None,
                        after_state={
                            "response_id": str(response.id),
                            "respondent_role": command.respondent_role,
                            "dimension_responses": command.dimension_responses,
                        },
                        command_name="safety.assessment.medical_response",
                        correlation_id=record.id,
                    )
                )
                self._complete(record, response.id, assessment.revision)
        return self.detail(scope, assessment_id)

    def link_issue(
        self,
        scope: ScopeContext,
        assessment_id: uuid.UUID,
        command: LinkSafetyIssuesCommand,
    ) -> IssueDetail:
        detail = self.detail(scope, assessment_id)
        assessment = detail.assessment
        self._authorize_write(scope, assessment.study_id, assessment.site_id)
        if detail.issue_link is not None:
            existing = self.issues.issue_detail(scope, detail.issue_link.issue_id)
            return existing
        selected = [
            item for item in detail.dimensions if item.dimension in command.dimensions
        ]
        if len(selected) != len(command.dimensions):
            raise SafetyValidationError(
                "one or more selected safety dimensions are outside this assessment"
            )
        source_refs = [
            ref
            for item in selected
            for ref in item.source_refs
        ]
        evidence = [
            {
                "dimension": item.dimension,
                "status": item.status,
                "candidate_values": item.candidate_values,
                "uncertainties": item.uncertainties,
                "evidence_ids": item.evidence_ids,
            }
            for item in selected
        ]
        issue = self.issues.create_issue(
            scope,
            assessment.study_id,
            CreateIssueCommand(
                idempotency_key=(
                    f"safety-assessment-issue:{assessment.id}:"
                    f"{command.idempotency_key}"
                ),
                site_id=assessment.site_id,
                subject_id=assessment.subject_id,
                issue_number=None,
                original_finding=(
                    f"CRA安全分析候选：{assessment.event_type}，事件日期"
                    f" {assessment.event_date.isoformat()}。"
                    + "；".join(
                        f"{DIMENSION_LABELS[item.dimension]}={item.status}"
                        for item in selected
                    )
                ),
                location="safety assessment",
                recommendation=(
                    command.requirement
                    or "请核实具体安全事实、适用依据和研究者/医学判断；"
                    "系统候选不构成最终医学结论。"
                ),
                recommendation_sources=[{"kind": "safety_assessment", "items": evidence}],
                source_kind="other",
                source_refs=[
                    {
                        "source_type": "safety_assessment",
                        "source_id": str(assessment.id),
                        "locator": item.dimension,
                        "status": item.status,
                    }
                    for item in selected
                ],
                actions=[
                    ActionCreate(
                        kind=command.action_kind,
                        requirement=(
                            "请核实具体事件及来源，记录研究者或医学答复；"
                            "完成状态由用户实际操作确认。"
                        ),
                        deadline_source_refs=[],
                    )
                ],
            ),
        )
        with self.session_factory() as session:
            with session.begin():
                current_link = session.scalar(
                    select(SafetyIssueLink).where(
                        SafetyIssueLink.assessment_id == assessment.id
                    )
                )
                if current_link is not None:
                    return self.issues.issue_detail(
                        scope, current_link.issue_id
                    )
                link = SafetyIssueLink(
                    id=uuid.uuid4(),
                    tenant_id=assessment.tenant_id,
                    study_id=assessment.study_id,
                    site_id=assessment.site_id,
                    assessment_id=assessment.id,
                    issue_id=issue.issue.id,
                    dimensions=list(command.dimensions),
                    created_by=scope.actor_id,
                )
                session.add(link)
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=assessment.tenant_id,
                        study_id=assessment.study_id,
                        site_id=assessment.site_id,
                        actor_id=scope.actor_id,
                        action="safety.assessment.issue_link",
                        resource_type="safety_assessment",
                        resource_id=assessment.id,
                        revision_before=None,
                        revision_after=assessment.revision,
                        before_state=None,
                        after_state={
                            "issue_id": str(issue.issue.id),
                            "dimensions": list(command.dimensions),
                            "action_kind": command.action_kind,
                        },
                        command_name="safety.assessment.issue_link",
                        correlation_id=issue.issue.id,
                    )
                )
        return issue
