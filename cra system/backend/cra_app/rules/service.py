"""Authorized rule extraction, confirmation and applicability services."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, exists, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, sessionmaker

from cra_app.documents.models import (
    DocumentVersion,
    SourceAnchor,
    SourceDocument,
)
from cra_app.governance.models import AuditEvent, IdempotencyRecord
from cra_app.governance.service import (
    AuthorizationDenied,
    GovernanceService,
    IdempotencyConflict,
    RevisionConflict,
    ScopeContext,
)
from cra_app.platform.jobs import digest_payload
from cra_app.providers.ports import ParsedAnchor
from cra_app.providers.rule_extraction import (
    AnchoredRuleExtractor,
    NUMBER,
    compare_rule_semantics,
    node_digest,
    validate_candidate_semantics,
)
from cra_app.rules.common_policy import CommonPolicySet
from cra_app.rules.contracts import (
    BranchEvaluation,
    ConfirmRuleCommand,
    ConfirmationOperation,
    EvaluationResult,
    FactValue,
    NodeEvaluation,
    RuleBranch,
    RuleCondition,
    RuleException,
    RuleExtractionResult,
    RuleNode,
    RuleSourceRef,
)
from cra_app.rules.evaluator import evaluate_node
from cra_app.rules.models import (
    Rule,
    RuleExtractionCoverage,
    RuleRelation,
    RuleSnapshot,
    RuleSourceRef as RuleSourceRefRow,
    RuleVersion,
    VersionActivation,
)
from cra_app.rules.version_activation import ActivationInterval
from cra_app.shared.output_contract import (
    Claim,
    ConflictItem,
    InputRevision,
    OutputCapability,
    OutputEnvelope,
    OutputScope,
    PolicyVersion,
    SourceRef,
    UnknownItem,
)


class RuleServiceError(Exception):
    pass


class RuleNotFound(RuleServiceError):
    pass


class RuleValidationError(RuleServiceError):
    pass


class RuleStateConflict(RuleServiceError):
    pass


class ExtractRuleCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    expected_revision: int = Field(default=0, ge=0)
    idempotency_key: str = Field(min_length=1, max_length=128)


class CreateActivationCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    expected_revision: int = Field(default=0, ge=0)
    idempotency_key: str = Field(min_length=1, max_length=128)
    document_version_id: uuid.UUID
    site_id: uuid.UUID | None = None
    starts_on: date
    ends_before: date | None = None
    supersedes_activation_id: uuid.UUID | None = None
    reason: str = Field(min_length=1, max_length=500)


class PreviewActivationChangeCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    starts_on: date
    ends_before: date | None = None
    reason: str = Field(min_length=1, max_length=500)


class ApplicableRuleQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    study_id: uuid.UUID
    site_id: uuid.UUID
    event_date: date
    jurisdiction: str = Field(default="synthetic", min_length=1, max_length=64)
    facts: dict[str, FactValue] = Field(default_factory=dict)


@dataclass(frozen=True)
class ExtractionOutcome:
    snapshot_id: uuid.UUID
    document_version_id: uuid.UUID
    status: str
    rule_version_ids: tuple[uuid.UUID, ...]
    replayed: bool
    duplicate_source: bool
    candidate_count: int
    confirmed_count: int


@dataclass(frozen=True)
class ConfirmationOutcome:
    rule_id: uuid.UUID
    rule_version_id: uuid.UUID
    revision: int
    replayed: bool


@dataclass(frozen=True)
class ActivationOutcome:
    activation_id: uuid.UUID
    revision: int
    conflicts: tuple[str, ...]
    replayed: bool


@dataclass(frozen=True)
class RuleListItem:
    rule: Rule
    current_version: RuleVersion | None
    candidate_versions: tuple[RuleVersion, ...]


@dataclass(frozen=True)
class RuleVersionItem:
    rule: Rule
    version: RuleVersion
    tree: RuleNode
    source_refs: tuple[RuleSourceRefRow, ...]
    relations: tuple[RuleRelation, ...]


@dataclass(frozen=True)
class ApplicabilityItem:
    rule: Rule
    version: RuleVersion
    tree: RuleNode
    evaluation: NodeEvaluation
    activation_id: uuid.UUID


@dataclass(frozen=True)
class ApplicabilityOutcome:
    envelope: OutputEnvelope
    rules: tuple[ApplicabilityItem, ...]


def _json_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _normal_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _source_ref_dict(ref: RuleSourceRef) -> dict[str, Any]:
    return ref.model_dump(mode="json")


def _walk_nodes(node: RuleNode) -> Iterable[RuleNode]:
    yield node
    for child in node.children:
        yield from _walk_nodes(child)


def _walk_source_refs(node: RuleNode) -> Iterable[RuleSourceRef]:
    for current in _walk_nodes(node):
        yield from current.source_refs
        for branch in current.branches:
            yield from branch.source_refs
        for exception in current.exceptions:
            yield from exception.source_refs


def _condition_operands(condition: RuleCondition | None) -> Iterable[Any]:
    if condition is None:
        return
    yield from (condition.left, condition.right, *condition.values)
    if condition.child:
        yield from _condition_operands(condition.child)
    for child in condition.children:
        yield from _condition_operands(child)


def _validator_numbers(node: RuleNode) -> set[str]:
    values: set[str] = set()
    for value in (
        node.summary,
        node.follow_up or "",
        node.completion or "",
        node.node_key,
    ):
        values.update(NUMBER.findall(value))
    for condition in (
        *node.preconditions,
        node.trigger,
        *[branch.condition for branch in node.branches],
        *[
            exception.condition
            for exception in node.exceptions
            if exception.condition is not None
        ],
    ):
        if condition is None:
            continue
        for operand in _condition_operands(condition):
            if operand is not None and operand.value is not None:
                values.update(NUMBER.findall(str(operand.value)))
    return values


class RuleService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        governance: GovernanceService | None = None,
        provider: Any | None = None,
        common_policy_set: CommonPolicySet | None = None,
    ):
        self.session_factory = session_factory
        self.governance = governance or GovernanceService(session_factory)
        self.provider = provider or AnchoredRuleExtractor()
        self.common_policy_set = common_policy_set

    def _authorize_write(
        self, scope: ScopeContext, study_id: uuid.UUID, site_id: uuid.UUID | None
    ) -> None:
        if site_id is None:
            self.governance.authorize(scope, "manage_study", study_id)
        else:
            self.governance.authorize(scope, "write_site", study_id, site_id)

    def _authorize_read(
        self, scope: ScopeContext, study_id: uuid.UUID, site_id: uuid.UUID | None
    ) -> None:
        if site_id is None:
            self.governance.authorize(scope, "read_study", study_id)
        else:
            self.governance.authorize(scope, "read_site", study_id, site_id)

    def _scope_fingerprint(
        self, scope: ScopeContext, study_id: uuid.UUID, site_id: uuid.UUID | None
    ) -> str:
        return digest_payload(
            {
                "tenant_id": scope.tenant_id,
                "study_id": str(study_id),
                "site_id": str(site_id) if site_id else None,
            }
        )

    def _reserve_idempotency(
        self,
        session: Session,
        *,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID | None,
        command_name: str,
        command: BaseModel,
        request_payload: dict[str, Any],
    ) -> tuple[IdempotencyRecord, bool]:
        scope_fingerprint = self._scope_fingerprint(scope, study_id, site_id)
        request_digest = digest_payload(
            {
                "command_name": command_name,
                "scope_fingerprint": scope_fingerprint,
                "command": command.model_dump(mode="json"),
                "request": request_payload,
            }
        )
        record_id = uuid.uuid4()
        session.execute(
            pg_insert(IdempotencyRecord)
            .values(
                id=record_id,
                actor_id=scope.actor_id,
                tenant_id=scope.tenant_id,
                study_id=study_id,
                site_id=site_id,
                scope_fingerprint=scope_fingerprint,
                command_name=command_name,
                idempotency_key=command.idempotency_key,
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
                IdempotencyRecord.scope_fingerprint == scope_fingerprint,
                IdempotencyRecord.command_name == command_name,
                IdempotencyRecord.idempotency_key == command.idempotency_key,
            )
            .with_for_update()
        )
        if record is None:
            raise RuntimeError("failed to reserve idempotency key")
        if record.request_digest != request_digest:
            raise IdempotencyConflict(
                "idempotency key was already used with different input"
            )
        replayed = record.response_resource_id is not None
        return record, replayed

    @staticmethod
    def _complete_idempotency(
        record: IdempotencyRecord, resource_id: uuid.UUID, revision: int
    ) -> None:
        record.response_resource_id = resource_id
        record.response_revision = revision
        record.completed_at = datetime.now(UTC)

    @staticmethod
    def _anchor_from_model(anchor: SourceAnchor) -> ParsedAnchor:
        return ParsedAnchor(
            anchor_type=anchor.anchor_type,
            logical_node_id=anchor.logical_node_id,
            text=anchor.text,
            ordinal=anchor.ordinal,
            section_path=list(anchor.section_path),
            style=dict(anchor.style),
            page_number=anchor.page_number,
            bbox=list(anchor.bbox) if anchor.bbox else None,
            table_index=anchor.table_index,
            row_index=anchor.row_index,
            column_index=anchor.column_index,
            footnote_id=anchor.footnote_id,
            metadata={**dict(anchor.style)},
        )

    def _load_document_version(
        self, scope: ScopeContext, document_version_id: uuid.UUID
    ) -> tuple[DocumentVersion, SourceDocument]:
        with self.session_factory() as session:
            version = session.scalar(
                select(DocumentVersion).where(
                    DocumentVersion.id == document_version_id,
                    DocumentVersion.tenant_id == scope.tenant_id,
                )
            )
            if version is None:
                raise RuleNotFound("document version was not found")
            document = session.scalar(
                select(SourceDocument).where(
                    SourceDocument.id == version.document_id,
                    SourceDocument.tenant_id == scope.tenant_id,
                )
            )
            if document is None:
                raise RuleNotFound("source document was not found")
            return version, document

    def _load_anchors(
        self, scope: ScopeContext, document_version_id: uuid.UUID
    ) -> list[SourceAnchor]:
        with self.session_factory() as session:
            return list(
                session.scalars(
                    select(SourceAnchor)
                    .where(
                        SourceAnchor.document_version_id == document_version_id,
                        SourceAnchor.tenant_id == scope.tenant_id,
                    )
                    .order_by(SourceAnchor.ordinal)
                )
            )

    def _validate_provider_result(
        self,
        result: RuleExtractionResult,
        anchors: list[SourceAnchor],
    ) -> tuple[dict[str, RuleNode], dict[str, SourceAnchor]]:
        if not isinstance(result, RuleExtractionResult):
            raise RuleValidationError("rule provider returned an invalid result")
        anchor_index = {anchor.logical_node_id: anchor for anchor in anchors}
        validated: dict[str, RuleNode] = {}
        for node in result.rules:
            if node.node_key in validated:
                raise RuleValidationError(
                    f"duplicate rule candidate {node.node_key}"
                )
            refs = list(_walk_source_refs(node))
            if not refs:
                raise RuleValidationError(
                    f"rule {node.node_key} has no source evidence"
                )
            quote_numbers: set[str] = set()
            for ref in refs:
                anchor = anchor_index.get(ref.anchor_key)
                if anchor is None:
                    raise RuleValidationError(
                        f"rule {node.node_key} references unknown anchor "
                        f"{ref.anchor_key}"
                    )
                if _normal_text(ref.quote) not in _normal_text(anchor.text):
                    raise RuleValidationError(
                        f"quote does not belong to anchor {ref.anchor_key}"
                    )
                quote_numbers.update(NUMBER.findall(anchor.text))
            missing_numbers = _validator_numbers(node) - quote_numbers
            if missing_numbers:
                raise RuleValidationError(
                    f"rule {node.node_key} contains numbers absent from source: "
                    + ", ".join(sorted(missing_numbers))
                )
            quoted = "\n".join(ref.quote for ref in refs)
            errors = validate_candidate_semantics(node, quoted)
            if errors and node.semantic_status != "analysis_required":
                raise RuleValidationError(
                    f"rule {node.node_key} lost source semantics: "
                    + "; ".join(errors)
                )
            validated[node.node_key] = self._attach_current_anchors(
                node,
                anchor_index,
                document_version_id=anchors[0].document_version_id if anchors else None,
            )
        return validated, anchor_index

    @staticmethod
    def _attach_current_anchors(
        node: RuleNode,
        anchor_index: dict[str, SourceAnchor],
        *,
        document_version_id: uuid.UUID | None,
    ) -> RuleNode:
        def attach(ref: RuleSourceRef) -> RuleSourceRef:
            anchor = anchor_index[ref.anchor_key]
            return ref.model_copy(
                update={
                    "anchor_id": anchor.id,
                    "document_version_id": document_version_id,
                }
            )

        updated = node.model_copy(deep=True)
        updated.source_refs = [attach(ref) for ref in updated.source_refs]
        for branch in updated.branches:
            branch.source_refs = [attach(ref) for ref in branch.source_refs]
        for exception in updated.exceptions:
            exception.source_refs = [attach(ref) for ref in exception.source_refs]
        updated.children = [
            RuleService._attach_current_anchors(
                child,
                anchor_index,
                document_version_id=document_version_id,
            )
            for child in updated.children
        ]
        return updated

    @staticmethod
    def _persist_source_refs(
        session: Session,
        *,
        version: RuleVersion,
        node: RuleNode,
    ) -> None:
        seen: set[tuple[uuid.UUID, str]] = set()
        ordinal = 0
        for ref in _walk_source_refs(node):
            if ref.anchor_id is None:
                raise RuleValidationError("source reference has no anchor id")
            quote = ref.quote.strip()
            digest = hashlib.sha256(quote.encode("utf-8")).hexdigest()
            key = (ref.anchor_id, digest)
            if key in seen:
                continue
            seen.add(key)
            session.add(
                RuleSourceRefRow(
                    id=uuid.uuid4(),
                    tenant_id=version.tenant_id,
                    study_id=version.study_id,
                    rule_version_id=version.id,
                    anchor_id=ref.anchor_id,
                    quote=quote,
                    quote_digest=digest,
                    locator=ref.locator,
                    ordinal=ordinal,
                )
            )
            ordinal += 1

    def _prior_snapshot(
        self, session: Session, document_id: uuid.UUID, current_snapshot_id: uuid.UUID
    ) -> RuleSnapshot | None:
        return session.scalar(
            select(RuleSnapshot)
            .join(
                DocumentVersion,
                and_(
                    DocumentVersion.tenant_id
                    == RuleSnapshot.tenant_id,
                    DocumentVersion.study_id == RuleSnapshot.study_id,
                    DocumentVersion.id
                    == RuleSnapshot.source_document_version_id,
                ),
            )
            .where(
                DocumentVersion.document_id == document_id,
                RuleSnapshot.id != current_snapshot_id,
            )
            .order_by(RuleSnapshot.created_at.desc())
            .limit(1)
        )

    @staticmethod
    def _latest_versions(
        session: Session, snapshot_id: uuid.UUID
    ) -> dict[uuid.UUID, RuleVersion]:
        versions = list(
            session.scalars(
                select(RuleVersion)
                .where(
                    RuleVersion.snapshot_id == snapshot_id,
                    RuleVersion.state.in_(("candidate", "confirmed", "withdrawn")),
                )
                .order_by(RuleVersion.rule_id, RuleVersion.version_no)
            )
        )
        latest: dict[uuid.UUID, RuleVersion] = {}
        for version in versions:
            latest[version.rule_id] = version
        return latest

    def _replay_extraction_snapshot(
        self,
        scope: ScopeContext,
        version: DocumentVersion,
        command: ExtractRuleCommand,
        snapshot: RuleSnapshot,
        *,
        duplicate_source: bool = False,
    ) -> ExtractionOutcome:
        with self.session_factory() as session:
            with session.begin():
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=version.study_id,
                    site_id=version.site_id,
                    command_name="rules.extract",
                    command=command,
                    request_payload={
                        "document_version_id": str(version.id),
                        "provider": snapshot.provider_name,
                        "provider_version": snapshot.provider_version,
                    },
                )
                if not replayed:
                    self._complete_idempotency(record, snapshot.id, 1)
                return self._outcome_for_snapshot(
                    session,
                    snapshot,
                    replayed=True,
                    duplicate_source=duplicate_source,
                )

    @staticmethod
    def _explicit_relation(
        result: RuleExtractionResult, rule_key: str, target_key: str
    ) -> str | None:
        for relation in result.relations:
            if (
                relation.rule_key == rule_key
                and (
                    relation.target_rule_key == target_key
                    or relation.target_rule_key is None
                )
            ):
                return relation.relation_type
        return None

    def extract_candidates(
        self,
        scope: ScopeContext,
        document_version_id: uuid.UUID,
        command: ExtractRuleCommand,
    ) -> ExtractionOutcome:
        if command.expected_revision != 0:
            raise RuleValidationError("extraction requires expected_revision=0")
        version, document = self._load_document_version(scope, document_version_id)
        self._authorize_write(scope, version.study_id, version.site_id)
        if version.parse_status not in {"completed", "partial"}:
            raise RuleValidationError(
                "source document must finish parsing before rule extraction"
            )
        duplicate_source = False
        if version.duplicate_of_version_id is not None:
            duplicate_source = True
            canonical = self._load_document_version(
                scope, version.duplicate_of_version_id
            )[0]
            with self.session_factory() as session:
                existing_snapshot = session.scalar(
                    select(RuleSnapshot).where(
                        RuleSnapshot.source_document_version_id == canonical.id,
                        RuleSnapshot.tenant_id == scope.tenant_id,
                    )
                )
                if existing_snapshot is not None:
                    return self._replay_extraction_snapshot(
                        scope,
                        version,
                        command,
                        existing_snapshot,
                        duplicate_source=True,
                    )
            raise RuleValidationError(
                "duplicate source has no canonical extraction yet; extract the "
                "canonical document version first"
            )

        with self.session_factory() as session:
            existing_snapshot = session.scalar(
                select(RuleSnapshot).where(
                    RuleSnapshot.source_document_version_id == version.id,
                    RuleSnapshot.tenant_id == scope.tenant_id,
                )
            )
            if existing_snapshot is not None:
                return self._replay_extraction_snapshot(
                    scope,
                    version,
                    command,
                    existing_snapshot,
                )

        anchors = self._load_anchors(scope, version.id)
        if not anchors:
            raise RuleValidationError("parsed source contains no anchors")
        provider_result = self.provider.extract_rules(
            anchors=[self._anchor_from_model(anchor) for anchor in anchors]
        )
        validated, anchor_index = self._validate_provider_result(
            provider_result, anchors
        )
        if not validated:
            raise RuleValidationError("provider produced no supported rule candidates")

        snapshot_id = uuid.uuid4()
        try:
            with self.session_factory() as session:
                with session.begin():
                    record, replayed = self._reserve_idempotency(
                        session,
                        scope=scope,
                        study_id=version.study_id,
                        site_id=version.site_id,
                        command_name="rules.extract",
                        command=command,
                        request_payload={
                            "document_version_id": str(version.id),
                            "provider": provider_result.provider_name,
                            "provider_version": provider_result.provider_version,
                        },
                    )
                    if replayed:
                        assert record.response_resource_id is not None
                        existing_snapshot = session.get(
                            RuleSnapshot, record.response_resource_id
                        )
                        if existing_snapshot is None:
                            raise RuleValidationError(
                                "idempotent extraction snapshot is unavailable"
                            )
                        return self._outcome_for_snapshot(
                            session, existing_snapshot, replayed=True
                        )
                    snapshot = RuleSnapshot(
                        id=snapshot_id,
                        tenant_id=scope.tenant_id,
                        study_id=version.study_id,
                        site_id=version.site_id,
                        source_document_version_id=version.id,
                        provider_name=provider_result.provider_name,
                        provider_version=provider_result.provider_version,
                        status="needs_review",
                        validation_summary={
                            "warnings": provider_result.warnings,
                            "semantic_analysis_required": sum(
                                node.semantic_status == "analysis_required"
                                for node in validated.values()
                            ),
                        },
                        revision=1,
                        created_by=scope.actor_id,
                    )
                    session.add(snapshot)
                    prior = self._prior_snapshot(session, version.document_id, snapshot_id)
                    snapshot.prior_snapshot_id = prior.id if prior else None
                    previous_versions = (
                        self._latest_versions(session, prior.id) if prior else {}
                    )
                    created_versions: list[RuleVersion] = []
                    relation_counts: Counter[str] = Counter()

                    all_keys = set(validated) | {
                        version_item.tree.get("node_key")
                        for version_item in previous_versions.values()
                    }
                    for rule_key in sorted(key for key in all_keys if key):
                        prior_version = next(
                            (
                                item
                                for item in previous_versions.values()
                                if item.tree.get("node_key") == rule_key
                            ),
                            None,
                        )
                        current_tree = validated.get(rule_key)
                        if prior_version is not None and current_tree is None:
                            inherited = RuleNode.model_validate(prior_version.tree)
                            relation_type = "unchanged"
                            reason = (
                                "rule is not mentioned in the new source; it remains "
                                "in force and is not treated as withdrawn"
                            )
                            state = (
                                "confirmed"
                                if prior_version.state == "confirmed"
                                else "candidate"
                            )
                            basis = (
                                "unchanged_inheritance"
                                if state == "confirmed"
                                else "candidate"
                            )
                            new_tree = inherited
                            from_version = prior_version
                            inherited_from = prior_version.id
                        elif current_tree is not None:
                            inherited_from = None
                            from_version = prior_version
                            if prior_version is None:
                                relation_type = "new"
                                reason = "rule key did not exist in the prior snapshot"
                                state = (
                                    "confirmed"
                                    if provider_result.direct_accept
                                    else "candidate"
                                )
                                basis = (
                                    "direct_rule_text"
                                    if provider_result.direct_accept
                                    else "candidate"
                                )
                            else:
                                previous_tree = RuleNode.model_validate(
                                    prior_version.tree
                                )
                                explicit = self._explicit_relation(
                                    provider_result,
                                    rule_key,
                                    previous_tree.node_key,
                                )
                                relation_type, reason = compare_rule_semantics(
                                    previous_tree,
                                    current_tree,
                                    explicit_relation=explicit,
                                )
                                if relation_type == "unchanged":
                                    state = (
                                        "confirmed"
                                        if prior_version.state == "confirmed"
                                        else "candidate"
                                    )
                                    basis = (
                                        "unchanged_inheritance"
                                        if state == "confirmed"
                                        else "candidate"
                                    )
                                    inherited_from = prior_version.id
                                else:
                                    state = (
                                        "confirmed"
                                        if provider_result.direct_accept
                                        else "candidate"
                                    )
                                    basis = (
                                        "direct_rule_text"
                                        if provider_result.direct_accept
                                        else "candidate"
                                    )
                            new_tree = current_tree
                        else:
                            continue

                        rule = session.scalar(
                            select(Rule).where(
                                Rule.tenant_id == scope.tenant_id,
                                Rule.study_id == version.study_id,
                                Rule.site_id.is_not_distinct_from(version.site_id),
                                Rule.rule_key == rule_key,
                            )
                        )
                        if rule is None:
                            rule = Rule(
                                id=uuid.uuid4(),
                                tenant_id=scope.tenant_id,
                                study_id=version.study_id,
                                site_id=version.site_id,
                                policy_layer=(
                                    "site" if version.site_id is not None else "study"
                                ),
                                rule_key=rule_key,
                                title=new_tree.summary[:255],
                                status=(
                                    "active" if state == "confirmed" else "candidate"
                                ),
                                revision=1,
                                created_by=scope.actor_id,
                                updated_by=scope.actor_id,
                            )
                            session.add(rule)
                            session.flush()
                        max_version = session.scalar(
                            select(RuleVersion.version_no)
                            .where(RuleVersion.rule_id == rule.id)
                            .order_by(RuleVersion.version_no.desc())
                            .limit(1)
                        )
                        version_no = int(max_version or 0) + 1
                        confirmed = state == "confirmed"
                        rule_version = RuleVersion(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=version.study_id,
                            site_id=version.site_id,
                            rule_id=rule.id,
                            snapshot_id=snapshot_id,
                            source_document_version_id=version.id,
                            inherited_from_version_id=inherited_from,
                            version_no=version_no,
                            state=state,
                            confirmation_basis=basis,
                            semantic_status=new_tree.semantic_status,
                            tree=new_tree.model_dump(mode="json"),
                            unknowns=new_tree.unknowns,
                            content_hash=node_digest(new_tree),
                            created_by=(
                                scope.actor_id
                                if not confirmed
                                or basis == "user_confirmation"
                                else f"system:{provider_result.provider_name}"
                            ),
                            confirmed_by=(
                                scope.actor_id
                                if confirmed
                                else None
                            ),
                            confirmed_at=datetime.now(UTC) if confirmed else None,
                        )
                        session.add(rule_version)
                        session.flush()
                        self._persist_source_refs(
                            session, version=rule_version, node=new_tree
                        )
                        rule.current_version_id = rule_version.id
                        rule.revision += 1
                        rule.updated_by = scope.actor_id
                        rule.status = "active" if confirmed else "candidate"
                        session.add(
                            RuleRelation(
                                id=uuid.uuid4(),
                                tenant_id=scope.tenant_id,
                                study_id=version.study_id,
                                from_version_id=(
                                    from_version.id if from_version is not None else None
                                ),
                                to_version_id=rule_version.id,
                                rule_key=rule_key,
                                relation_type=relation_type,
                                reason=reason[:500],
                                evidence=[
                                    _source_ref_dict(ref)
                                    for ref in new_tree.source_refs
                                ],
                            )
                        )
                        relation_counts[relation_type] += 1
                        created_versions.append(rule_version)

                    coverage_rows = []
                    for coverage in provider_result.coverage:
                        anchor = anchor_index.get(coverage.anchor_key or "")
                        coverage_rows.append(
                            RuleExtractionCoverage(
                                id=uuid.uuid4(),
                                tenant_id=scope.tenant_id,
                                study_id=version.study_id,
                                snapshot_id=snapshot_id,
                                unit_key=coverage.unit_key,
                                status=coverage.status,
                                reason=coverage.reason,
                                anchor_id=anchor.id if anchor else None,
                            )
                        )
                    session.add_all(coverage_rows)
                    candidate_count = sum(
                        item.state == "candidate" for item in created_versions
                    )
                    snapshot.status = (
                        "needs_review" if candidate_count else "ready"
                    )
                    snapshot.validation_summary = {
                        **snapshot.validation_summary,
                        "relation_counts": dict(relation_counts),
                        "candidate_count": candidate_count,
                        "confirmed_count": len(created_versions) - candidate_count,
                    }
                    if not created_versions:
                        raise RuleValidationError(
                            "extraction did not materialize any rule versions"
                        )
                    self._complete_idempotency(record, snapshot_id, 1)
                    session.add(
                        AuditEvent(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=version.study_id,
                            site_id=version.site_id,
                            actor_id=scope.actor_id,
                            action="rules.extract",
                            resource_type="rule_snapshot",
                            resource_id=snapshot_id,
                            revision_before=None,
                            revision_after=1,
                            before_state=None,
                            after_state={
                                "source_document_version_id": str(version.id),
                                "rule_version_ids": [
                                    str(item.id) for item in created_versions
                                ],
                                "relation_counts": dict(relation_counts),
                            },
                            command_name="rules.extract",
                            correlation_id=record.id,
                        )
                    )
                    snapshot.revision = 1
            with self.session_factory() as session:
                created_snapshot = session.get(RuleSnapshot, snapshot_id)
                assert created_snapshot is not None
                return self._outcome_for_snapshot(
                    session,
                    created_snapshot,
                    replayed=False,
                    duplicate_source=duplicate_source,
                )
        except Exception:
            raise

    @staticmethod
    def _outcome_for_snapshot(
        session: Session,
        snapshot: RuleSnapshot,
        *,
        replayed: bool,
        duplicate_source: bool = False,
    ) -> ExtractionOutcome:
        versions = list(
            session.scalars(
                select(RuleVersion)
                .where(RuleVersion.snapshot_id == snapshot.id)
                .order_by(RuleVersion.rule_id, RuleVersion.version_no)
            )
        )
        latest_by_rule: dict[uuid.UUID, RuleVersion] = {}
        for version in versions:
            latest_by_rule[version.rule_id] = version
        current = tuple(latest_by_rule.values())
        return ExtractionOutcome(
            snapshot_id=snapshot.id,
            document_version_id=snapshot.source_document_version_id,
            status=snapshot.status,
            rule_version_ids=tuple(item.id for item in current),
            replayed=replayed,
            duplicate_source=duplicate_source,
            candidate_count=sum(item.state == "candidate" for item in current),
            confirmed_count=sum(item.state == "confirmed" for item in current),
        )

    @staticmethod
    def _apply_operations(
        rule_key: str,
        tree: RuleNode,
        operations: list[ConfirmationOperation],
    ) -> RuleNode:
        updated = tree.model_copy(deep=True)
        for operation in operations:
            if operation.op == "edit_fields":
                if operation.summary is not None:
                    updated.summary = operation.summary
                if operation.preconditions is not None:
                    updated.preconditions = operation.preconditions
                if operation.has_trigger is False:
                    updated.trigger = None
                elif operation.trigger is not None:
                    updated.trigger = operation.trigger
                if operation.follow_up is not None:
                    updated.follow_up = operation.follow_up
                if operation.completion is not None:
                    updated.completion = operation.completion
                if operation.required_facts is not None:
                    updated.required_facts = operation.required_facts
            elif operation.op == "add_child":
                assert operation.child is not None
                if any(
                    child.node_key == operation.child.node_key
                    for child in updated.children
                ):
                    raise RuleStateConflict(
                        f"child {operation.child.node_key} already exists"
                    )
                updated.children.append(operation.child)
            elif operation.op == "remove_child":
                assert operation.child_key is not None
                before = len(updated.children)
                updated.children = [
                    child
                    for child in updated.children
                    if child.node_key != operation.child_key
                ]
                if len(updated.children) == before:
                    raise RuleNotFound(
                        f"child {operation.child_key} was not found"
                    )
            elif operation.op == "add_exception":
                assert operation.exception is not None
                if any(
                    item.exception_key == operation.exception.exception_key
                    for item in updated.exceptions
                ):
                    raise RuleStateConflict(
                        f"exception {operation.exception.exception_key} already exists"
                    )
                updated.exceptions.append(operation.exception)
        updated.node_key = rule_key
        return RuleNode.model_validate(updated.model_dump(mode="json"))

    @staticmethod
    def _resolve_confirmation_refs(
        tree: RuleNode,
        anchors: dict[str, SourceAnchor],
    ) -> RuleNode:
        def resolve(ref: RuleSourceRef) -> RuleSourceRef:
            if ref.anchor_id is not None:
                return ref
            anchor = anchors.get(ref.anchor_key)
            if anchor is None:
                raise RuleValidationError(
                    f"confirmation references unknown anchor {ref.anchor_key}"
                )
            if _normal_text(ref.quote) not in _normal_text(anchor.text):
                raise RuleValidationError(
                    f"confirmation quote does not belong to {ref.anchor_key}"
                )
            return ref.model_copy(
                update={
                    "anchor_id": anchor.id,
                    "document_version_id": anchor.document_version_id,
                }
            )

        updated = tree.model_copy(deep=True)
        updated.source_refs = [resolve(ref) for ref in updated.source_refs]
        for branch in updated.branches:
            branch.source_refs = [resolve(ref) for ref in branch.source_refs]
        for exception in updated.exceptions:
            exception.source_refs = [
                resolve(ref) for ref in exception.source_refs
            ]
        updated.children = [
            RuleService._resolve_confirmation_refs(child, anchors)
            for child in updated.children
        ]
        return updated

    def confirm_rule(
        self,
        scope: ScopeContext,
        rule_id: uuid.UUID,
        command: ConfirmRuleCommand,
    ) -> ConfirmationOutcome:
        with self.session_factory() as session:
            with session.begin():
                rule = session.scalar(
                    select(Rule)
                    .where(
                        Rule.id == rule_id,
                        Rule.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if rule is None:
                    raise RuleNotFound("rule was not found")
                self._authorize_write(scope, rule.study_id, rule.site_id)
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=rule.study_id,
                    site_id=rule.site_id,
                    command_name="rules.confirm",
                    command=command,
                    request_payload={"rule_id": str(rule_id)},
                )
                if replayed:
                    assert record.response_resource_id is not None
                    return ConfirmationOutcome(
                        rule_id=rule_id,
                        rule_version_id=record.response_resource_id,
                        revision=int(record.response_revision or rule.revision),
                        replayed=True,
                    )
                if rule.revision != command.expected_revision:
                    raise RevisionConflict(rule.revision)
                base = session.scalar(
                    select(RuleVersion).where(
                        RuleVersion.id == command.base_version_id,
                        RuleVersion.rule_id == rule.id,
                        RuleVersion.tenant_id == scope.tenant_id,
                    )
                )
                if base is None:
                    raise RuleNotFound("base rule version was not found")
                base_tree = RuleNode.model_validate(base.tree)
                updated_tree = self._apply_operations(
                    rule.rule_key, base_tree, command.operations
                )
                anchors = {
                    item.logical_node_id: item
                    for item in session.scalars(
                        select(SourceAnchor).where(
                            SourceAnchor.tenant_id == scope.tenant_id,
                            SourceAnchor.study_id == rule.study_id,
                            SourceAnchor.document_version_id
                            == base.source_document_version_id,
                        )
                    )
                }
                updated_tree = self._resolve_confirmation_refs(
                    updated_tree, anchors
                )
                source_text = "\n".join(
                    ref.quote for ref in _walk_source_refs(updated_tree)
                )
                semantic_errors = validate_candidate_semantics(
                    updated_tree, source_text
                )
                if (
                    semantic_errors
                    and updated_tree.semantic_status == "complete"
                ):
                    raise RuleValidationError(
                        "confirmed rule loses source semantics: "
                        + "; ".join(semantic_errors)
                    )
                max_version = session.scalar(
                    select(RuleVersion.version_no)
                    .where(RuleVersion.rule_id == rule.id)
                    .order_by(RuleVersion.version_no.desc())
                    .limit(1)
                )
                new_version = RuleVersion(
                    id=uuid.uuid4(),
                    tenant_id=rule.tenant_id,
                    study_id=rule.study_id,
                    site_id=rule.site_id,
                    rule_id=rule.id,
                    snapshot_id=base.snapshot_id,
                    source_document_version_id=base.source_document_version_id,
                    inherited_from_version_id=base.id,
                    version_no=int(max_version or 0) + 1,
                    state="confirmed",
                    confirmation_basis="user_confirmation",
                    semantic_status=updated_tree.semantic_status,
                    tree=updated_tree.model_dump(mode="json"),
                    unknowns=updated_tree.unknowns,
                    content_hash=node_digest(updated_tree),
                    created_by=scope.actor_id,
                    confirmed_by=scope.actor_id,
                    confirmed_at=datetime.now(UTC),
                )
                session.add(new_version)
                session.flush()
                self._persist_source_refs(
                    session, version=new_version, node=updated_tree
                )
                rule.current_version_id = new_version.id
                rule.revision += 1
                rule.updated_by = scope.actor_id
                rule.status = "active"
                relation_type = (
                    "exception"
                    if any(op.op == "add_exception" for op in command.operations)
                    else "supplement"
                )
                session.add(
                    RuleRelation(
                        id=uuid.uuid4(),
                        tenant_id=rule.tenant_id,
                        study_id=rule.study_id,
                        from_version_id=base.id,
                        to_version_id=new_version.id,
                        rule_key=rule.rule_key,
                        relation_type=relation_type,
                        reason=command.reason,
                        evidence=[
                            _source_ref_dict(ref)
                            for ref in updated_tree.source_refs
                        ],
                    )
                )
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=rule.tenant_id,
                        study_id=rule.study_id,
                        site_id=rule.site_id,
                        actor_id=scope.actor_id,
                        action="rules.confirm",
                        resource_type="rule",
                        resource_id=rule.id,
                        revision_before=command.expected_revision,
                        revision_after=rule.revision,
                        before_state={"rule_version_id": str(base.id)},
                        after_state={
                            "rule_version_id": str(new_version.id),
                            "reason": command.reason,
                        },
                        command_name="rules.confirm",
                        correlation_id=record.id,
                    )
                )
                self._complete_idempotency(record, new_version.id, rule.revision)
                return ConfirmationOutcome(
                    rule_id=rule.id,
                    rule_version_id=new_version.id,
                    revision=rule.revision,
                    replayed=False,
                )

    def list_rules(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID | None,
    ) -> list[RuleListItem]:
        self._authorize_read(scope, study_id, site_id)
        with self.session_factory() as session:
            site_condition = (
                Rule.site_id.is_(None)
                if site_id is None
                else or_(Rule.site_id.is_(None), Rule.site_id == site_id)
            )
            rules = list(
                session.scalars(
                    select(Rule)
                    .where(
                        Rule.tenant_id == scope.tenant_id,
                        Rule.study_id == study_id,
                        site_condition,
                    )
                    .order_by(Rule.rule_key)
                )
            )
            result = []
            for rule in rules:
                versions = list(
                    session.scalars(
                        select(RuleVersion)
                        .where(RuleVersion.rule_id == rule.id)
                        .order_by(RuleVersion.version_no.desc())
                    )
                )
                current = next(
                    (
                        item
                        for item in versions
                        if item.id == rule.current_version_id
                    ),
                    versions[0] if versions else None,
                )
                candidates = tuple(
                    item for item in versions if item.state == "candidate"
                )
                result.append(
                    RuleListItem(
                        rule=rule,
                        current_version=current,
                        candidate_versions=candidates,
                    )
                )
            return result

    def get_rule_version(
        self, scope: ScopeContext, rule_version_id: uuid.UUID
    ) -> RuleVersionItem:
        with self.session_factory() as session:
            version = session.scalar(
                select(RuleVersion).where(
                    RuleVersion.id == rule_version_id,
                    RuleVersion.tenant_id == scope.tenant_id,
                )
            )
            if version is None:
                raise RuleNotFound("rule version was not found")
            rule = session.scalar(
                select(Rule).where(
                    Rule.id == version.rule_id,
                    Rule.tenant_id == scope.tenant_id,
                )
            )
            if rule is None:
                raise RuleNotFound("rule was not found")
            self._authorize_read(scope, rule.study_id, rule.site_id)
            refs = tuple(
                session.scalars(
                    select(RuleSourceRefRow)
                    .where(RuleSourceRefRow.rule_version_id == version.id)
                    .order_by(RuleSourceRefRow.ordinal)
                )
            )
            relations = tuple(
                session.scalars(
                    select(RuleRelation)
                    .where(RuleRelation.to_version_id == version.id)
                    .order_by(RuleRelation.created_at)
                )
            )
            return RuleVersionItem(
                rule=rule,
                version=version,
                tree=RuleNode.model_validate(version.tree),
                source_refs=refs,
                relations=relations,
            )

    def list_rule_versions(
        self, scope: ScopeContext, rule_id: uuid.UUID
    ) -> list[RuleVersion]:
        with self.session_factory() as session:
            rule = session.scalar(
                select(Rule).where(
                    Rule.id == rule_id,
                    Rule.tenant_id == scope.tenant_id,
                )
            )
            if rule is None:
                raise RuleNotFound("rule was not found")
            self._authorize_read(scope, rule.study_id, rule.site_id)
            return list(
                session.scalars(
                    select(RuleVersion)
                    .where(
                        RuleVersion.rule_id == rule_id,
                        RuleVersion.tenant_id == scope.tenant_id,
                    )
                    .order_by(RuleVersion.version_no.desc())
                )
            )

    def list_extraction_coverage(
        self, scope: ScopeContext, snapshot_id: uuid.UUID
    ) -> list[RuleExtractionCoverage]:
        with self.session_factory() as session:
            snapshot = session.scalar(
                select(RuleSnapshot).where(
                    RuleSnapshot.id == snapshot_id,
                    RuleSnapshot.tenant_id == scope.tenant_id,
                )
            )
            if snapshot is None:
                raise RuleNotFound("rule snapshot was not found")
            self._authorize_read(scope, snapshot.study_id, snapshot.site_id)
            return list(
                session.scalars(
                    select(RuleExtractionCoverage)
                    .where(RuleExtractionCoverage.snapshot_id == snapshot_id)
                    .order_by(RuleExtractionCoverage.unit_key)
                )
            )

    def _activation_conflicts(
        self,
        session: Session,
        *,
        snapshot: RuleSnapshot,
        site_id: uuid.UUID | None,
        interval: ActivationInterval,
        exclude_id: uuid.UUID | None = None,
    ) -> list[VersionActivation]:
        statement = (
            select(VersionActivation)
            .join(
                RuleSnapshot,
                and_(
                    RuleSnapshot.tenant_id == VersionActivation.tenant_id,
                    RuleSnapshot.study_id == VersionActivation.study_id,
                    RuleSnapshot.id == VersionActivation.snapshot_id,
                ),
            )
            .join(
                DocumentVersion,
                and_(
                    DocumentVersion.tenant_id == RuleSnapshot.tenant_id,
                    DocumentVersion.study_id == RuleSnapshot.study_id,
                    DocumentVersion.id
                    == RuleSnapshot.source_document_version_id,
                ),
            )
            .where(
                VersionActivation.tenant_id == snapshot.tenant_id,
                VersionActivation.study_id == snapshot.study_id,
                VersionActivation.site_id.is_not_distinct_from(site_id),
                VersionActivation.status == "active",
                DocumentVersion.document_id
                == session.scalar(
                    select(DocumentVersion.document_id).where(
                        DocumentVersion.id == snapshot.source_document_version_id
                    )
                ),
            )
        )
        if exclude_id is not None:
            statement = statement.where(VersionActivation.id != exclude_id)
        return [
            item
            for item in session.scalars(statement)
            if interval.overlaps(
                ActivationInterval(item.starts_on, item.ends_before)
            )
        ]

    def create_activation(
        self,
        scope: ScopeContext,
        command: CreateActivationCommand,
    ) -> ActivationOutcome:
        if command.expected_revision != 0:
            raise RuleValidationError("activation create requires expected_revision=0")
        if (
            command.ends_before is not None
            and command.ends_before <= command.starts_on
        ):
            raise RuleValidationError("ends_before must be after starts_on")
        version, document = self._load_document_version(
            scope, command.document_version_id
        )
        effective_site_id = (
            command.site_id if command.site_id is not None else version.site_id
        )
        self._authorize_write(scope, version.study_id, effective_site_id)
        if document.site_id is None and command.site_id is not None:
            raise RuleValidationError(
                "a study-wide document cannot be activated for one site"
            )
        if document.site_id is not None and command.site_id not in {
            None,
            document.site_id,
        }:
            raise RuleValidationError(
                "activation site does not match the source document"
            )
        with self.session_factory() as session:
            with session.begin():
                snapshot = session.scalar(
                    select(RuleSnapshot).where(
                        RuleSnapshot.source_document_version_id == version.id,
                        RuleSnapshot.tenant_id == scope.tenant_id,
                    )
                )
                if snapshot is None:
                    raise RuleValidationError(
                        "rule extraction must finish before activation"
                    )
                if not session.scalar(
                    select(
                        exists().where(
                            RuleVersion.snapshot_id == snapshot.id,
                            RuleVersion.state == "confirmed",
                        )
                    )
                ):
                    raise RuleValidationError(
                        "at least one rule must be confirmed before activation"
                    )
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=version.study_id,
                    site_id=effective_site_id,
                    command_name="version_activations.create",
                    command=command,
                    request_payload={"snapshot_id": str(snapshot.id)},
                )
                if replayed:
                    assert record.response_resource_id is not None
                    activation = session.get(
                        VersionActivation, record.response_resource_id
                    )
                    if activation is None:
                        raise RuleValidationError(
                            "idempotent activation is unavailable"
                        )
                    return ActivationOutcome(
                        activation_id=activation.id,
                        revision=activation.revision,
                        conflicts=(),
                        replayed=True,
                    )
                supersedes = None
                revision = 1
                if command.supersedes_activation_id is not None:
                    supersedes = session.scalar(
                        select(VersionActivation)
                        .where(
                            VersionActivation.id
                            == command.supersedes_activation_id,
                            VersionActivation.snapshot_id == snapshot.id,
                            VersionActivation.tenant_id == scope.tenant_id,
                        )
                        .with_for_update()
                    )
                    if supersedes is None:
                        raise RuleNotFound("activation to correct was not found")
                    supersedes.status = "superseded"
                    revision = supersedes.revision + 1
                interval = ActivationInterval(
                    command.starts_on, command.ends_before
                )
                conflicts = self._activation_conflicts(
                    session,
                    snapshot=snapshot,
                    site_id=effective_site_id,
                    interval=interval,
                    exclude_id=(
                        supersedes.id if supersedes is not None else None
                    ),
                )
                activation = VersionActivation(
                    id=uuid.uuid4(),
                    tenant_id=scope.tenant_id,
                    study_id=version.study_id,
                    site_id=effective_site_id,
                    snapshot_id=snapshot.id,
                    document_version_id=version.id,
                    starts_on=command.starts_on,
                    ends_before=command.ends_before,
                    status="active",
                    revision=revision,
                    supersedes_activation_id=(
                        supersedes.id if supersedes is not None else None
                    ),
                    reason=command.reason,
                    actor_id=scope.actor_id,
                )
                session.add(activation)
                session.flush()
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=version.study_id,
                        site_id=effective_site_id,
                        actor_id=scope.actor_id,
                        action="version_activation.create",
                        resource_type="version_activation",
                        resource_id=activation.id,
                        revision_before=(
                            supersedes.revision if supersedes else None
                        ),
                        revision_after=activation.revision,
                        before_state=(
                            {
                                "starts_on": supersedes.starts_on.isoformat(),
                                "ends_before": (
                                    supersedes.ends_before.isoformat()
                                    if supersedes.ends_before
                                    else None
                                ),
                            }
                            if supersedes
                            else None
                        ),
                        after_state={
                            "starts_on": activation.starts_on.isoformat(),
                            "ends_before": (
                                activation.ends_before.isoformat()
                                if activation.ends_before
                                else None
                            ),
                            "conflict_ids": [str(item.id) for item in conflicts],
                            "reason": activation.reason,
                        },
                        command_name="version_activation.create",
                        correlation_id=record.id,
                    )
                )
                self._complete_idempotency(
                    record, activation.id, activation.revision
                )
                return ActivationOutcome(
                    activation_id=activation.id,
                    revision=activation.revision,
                    conflicts=tuple(str(item.id) for item in conflicts),
                    replayed=False,
                )

    def preview_activation_change(
        self,
        scope: ScopeContext,
        activation_id: uuid.UUID,
        command: PreviewActivationChangeCommand,
    ) -> dict[str, Any]:
        if (
            command.ends_before is not None
            and command.ends_before <= command.starts_on
        ):
            raise RuleValidationError("ends_before must be after starts_on")
        with self.session_factory() as session:
            activation = session.scalar(
                select(VersionActivation).where(
                    VersionActivation.id == activation_id,
                    VersionActivation.tenant_id == scope.tenant_id,
                )
            )
            if activation is None:
                raise RuleNotFound("version activation was not found")
            self._authorize_write(
                scope, activation.study_id, activation.site_id
            )
            snapshot = session.get(RuleSnapshot, activation.snapshot_id)
            assert snapshot is not None
            interval = ActivationInterval(
                command.starts_on, command.ends_before
            )
            conflicts = self._activation_conflicts(
                session,
                snapshot=snapshot,
                site_id=activation.site_id,
                interval=interval,
                exclude_id=activation.id,
            )
            versions = list(
                session.execute(
                    select(RuleVersion.rule_id, RuleVersion.id)
                    .where(RuleVersion.snapshot_id == snapshot.id)
                    .order_by(RuleVersion.rule_id, RuleVersion.version_no.desc())
                )
            )
            latest_rule_versions: dict[uuid.UUID, uuid.UUID] = {}
            for rule_id, version_id in versions:
                latest_rule_versions.setdefault(rule_id, version_id)
            return {
                "activation_id": str(activation.id),
                "current": {
                    "starts_on": activation.starts_on.isoformat(),
                    "ends_before": (
                        activation.ends_before.isoformat()
                        if activation.ends_before
                        else None
                    ),
                },
                "proposed": {
                    "starts_on": command.starts_on.isoformat(),
                    "ends_before": (
                        command.ends_before.isoformat()
                        if command.ends_before
                        else None
                    ),
                    "reason": command.reason,
                },
                "contains_start": interval.contains(command.starts_on),
                "conflicting_activation_ids": [
                    str(item.id) for item in conflicts
                ],
                "affected_rule_ids": [
                    str(item) for item in sorted(latest_rule_versions)
                ],
                "affected_rule_version_ids": [
                    str(item) for item in latest_rule_versions.values()
                ],
                "retroactive_reassessment": False,
            }

    def _active_activations(
        self,
        session: Session,
        *,
        tenant_id: str,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
        event_date: date,
    ) -> list[VersionActivation]:
        return list(
            session.scalars(
                select(VersionActivation)
                .where(
                    VersionActivation.tenant_id == tenant_id,
                    VersionActivation.study_id == study_id,
                    or_(
                        VersionActivation.site_id.is_(None),
                        VersionActivation.site_id == site_id,
                    ),
                    VersionActivation.status == "active",
                    VersionActivation.starts_on <= event_date,
                    or_(
                        VersionActivation.ends_before.is_(None),
                        VersionActivation.ends_before > event_date,
                    ),
                )
                .order_by(
                    VersionActivation.site_id.nullsfirst(),
                    VersionActivation.starts_on,
                )
            )
        )

    def applicable_rules(
        self,
        scope: ScopeContext,
        query: ApplicableRuleQuery,
    ) -> ApplicabilityOutcome:
        self._authorize_read(scope, query.study_id, query.site_id)
        with self.session_factory() as session:
            activations = self._active_activations(
                session,
                tenant_id=scope.tenant_id,
                study_id=query.study_id,
                site_id=query.site_id,
                event_date=query.event_date,
            )
            selected: list[tuple[VersionActivation, Rule, RuleVersion]] = []
            conflicts: list[ConflictItem] = []
            for activation in activations:
                snapshot = session.get(RuleSnapshot, activation.snapshot_id)
                if snapshot is None:
                    continue
                versions = list(
                    session.execute(
                        select(Rule, RuleVersion)
                        .join(Rule, Rule.id == RuleVersion.rule_id)
                        .where(
                            RuleVersion.snapshot_id == snapshot.id,
                            RuleVersion.state == "confirmed",
                            Rule.tenant_id == scope.tenant_id,
                        )
                        .order_by(RuleVersion.rule_id, RuleVersion.version_no.desc())
                    )
                )
                latest_by_rule: dict[uuid.UUID, tuple[Rule, RuleVersion]] = {}
                for rule, version in versions:
                    latest_by_rule.setdefault(rule.id, (rule, version))
                selected.extend(
                    (activation, rule, version)
                    for rule, version in latest_by_rule.values()
                )

            by_rule_layer_key: dict[tuple[str, str, uuid.UUID | None], list[Any]] = {}
            for item in selected:
                _, rule, _ = item
                by_rule_layer_key.setdefault(
                    (rule.policy_layer, rule.rule_key, rule.site_id), []
                ).append(item)
            accepted: list[tuple[VersionActivation, Rule, RuleVersion]] = []
            for key, items in by_rule_layer_key.items():
                version_ids = {item[2].id for item in items}
                if len(version_ids) > 1:
                    conflicts.append(
                        ConflictItem(
                            conflict_id=f"rule-overlap:{key[0]}:{key[1]}",
                            description=(
                                "multiple activated confirmed versions overlap "
                                "for the same rule scope"
                            ),
                            source_refs=[
                                SourceRef(
                                    source_type="record",
                                    source_id=str(item[2].id),
                                    version=str(item[2].version_no),
                                    locator="rule_version",
                                )
                                for item in items
                            ],
                        )
                    )
                    continue
                accepted.append(items[0])

            evaluations: list[ApplicabilityItem] = []
            unknown_items: list[UnknownItem] = []
            evidence_refs: list[SourceRef] = []
            claims: list[Claim] = []
            for activation, rule, version in accepted:
                tree = RuleNode.model_validate(version.tree)
                evaluation = evaluate_node(tree, query.facts)
                evaluations.append(
                    ApplicabilityItem(
                        rule=rule,
                        version=version,
                        tree=tree,
                        evaluation=evaluation,
                        activation_id=activation.id,
                    )
                )
                for message in evaluation.unknowns:
                    unknown_items.append(
                        UnknownItem(
                            code="condition_unknown",
                            reason=message,
                            affected_scope=f"{rule.rule_key}@{query.event_date.isoformat()}",
                        )
                    )
                for ref in _walk_source_refs(tree):
                    evidence_refs.append(
                        SourceRef(
                            source_type="document_anchor",
                            source_id=str(ref.anchor_id or ref.anchor_key),
                            version=(
                                str(ref.document_version_id)
                                if ref.document_version_id
                                else None
                            ),
                            locator=ref.locator,
                            quote=ref.quote,
                        )
                    )
                claims.append(
                    Claim(
                        claim_id=f"rule:{rule.id}",
                        kind="user_confirmation",
                        label=tree.summary,
                        value={
                            "rule_id": str(rule.id),
                            "rule_version_id": str(version.id),
                            "conditions": [
                                item.model_dump(mode="json")
                                for item in tree.preconditions
                            ],
                            "trigger": (
                                tree.trigger.model_dump(mode="json")
                                if tree.trigger
                                else None
                            ),
                            "exceptions": [
                                item.model_dump(mode="json")
                                for item in tree.exceptions
                            ],
                            "evaluation": evaluation.model_dump(mode="json"),
                        },
                        verification_status="cra_confirmed",
                        source_refs=[
                            SourceRef(
                                source_type="document_anchor",
                                source_id=str(ref.anchor_id or ref.anchor_key),
                                version=(
                                    str(ref.document_version_id)
                                    if ref.document_version_id
                                    else None
                                ),
                                locator=ref.locator,
                                quote=ref.quote,
                            )
                            for ref in tree.source_refs
                        ],
                    )
                )

            common_entries, common_unknowns = (
                self.common_policy_set.applicable(
                    query.event_date, query.jurisdiction
                )
                if self.common_policy_set
                else ([], ["common policy package is not configured"])
            )
            unknown_items.extend(
                UnknownItem(
                    code="common_policy_unknown",
                    reason=reason,
                    affected_scope="common-policy",
                )
                for reason in common_unknowns
            )
            if not activations:
                unknown_items.append(
                    UnknownItem(
                        code="activation_missing",
                        reason=(
                            "no active rule document version covers the clinical "
                            "event date"
                        ),
                        affected_scope=query.event_date.isoformat(),
                    )
                )
            envelope_conflicts = conflicts
            for item in evaluations:
                if item.tree.semantic_status == "analysis_required":
                    envelope_conflicts.append(
                        ConflictItem(
                            conflict_id=f"analysis-required:{item.version.id}",
                            description=(
                                "rule contains a clause that cannot be evaluated "
                                "by the finite condition AST"
                            ),
                            source_refs=[
                                SourceRef(
                                    source_type="record",
                                    source_id=str(item.version.id),
                                    locator="rule_version",
                                )
                            ],
                        )
                    )
            status = (
                "needs_clarification"
                if envelope_conflicts
                else "limited"
                if unknown_items
                else "ready_to_review"
            )
            policy_versions = [
                PolicyVersion(
                    layer="common",
                    policy_id=entry.policy_id,
                    version=entry.version,
                    activation_date=entry.official_effective_on.isoformat(),
                )
                for entry in common_entries
            ]
            policy_versions.extend(
                PolicyVersion(
                    layer=(
                        "site" if activation.site_id is not None else "study"
                    ),
                    policy_id=str(activation.snapshot_id),
                    version=activation.revision.__str__(),
                    activation_date=activation.starts_on.isoformat(),
                )
                for activation in activations
            )
            envelope = OutputEnvelope(
                output_id=uuid.uuid4(),
                purpose="rule_candidate",
                scope=OutputScope(
                    tenant_id=scope.tenant_id,
                    study_id=query.study_id,
                    site_id=query.site_id,
                ),
                input_revisions=[
                    InputRevision(
                        resource_type="version_activation",
                        resource_id=str(item.id),
                        revision=item.revision,
                        digest=_json_digest(
                            {
                                "starts_on": item.starts_on.isoformat(),
                                "ends_before": (
                                    item.ends_before.isoformat()
                                    if item.ends_before
                                    else None
                                ),
                                "snapshot_id": str(item.snapshot_id),
                            }
                        ),
                    )
                    for item in activations
                ],
                policy_versions=policy_versions,
                claims=claims,
                evidence_refs=evidence_refs,
                unknowns=unknown_items,
                conflicts=envelope_conflicts,
                capabilities=[
                    OutputCapability(
                        capability_id="anchored-rule-subset",
                        level="limited",
                        validated=True,
                        limitations=[
                            "supports the documented W04 statement subset only",
                            "not validated on real clinical protocols",
                        ],
                    )
                ],
                status=status,
                generated_at=datetime.now(UTC),
                actor_id=scope.actor_id,
            )
            return ApplicabilityOutcome(
                envelope=envelope,
                rules=tuple(evaluations),
            )
