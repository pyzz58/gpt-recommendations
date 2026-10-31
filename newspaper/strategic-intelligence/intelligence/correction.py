"""W34 correction impact, shared use restrictions and bounded recovery."""
from __future__ import annotations

from enum import Enum
import hashlib
from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from .adoption import AdoptionDecision, StepState
from .archive import Archive, ArchiveError, Conflict, MissingVersion, canonical
from .contracts import (Contract, Digest, Identifier, NonBlank, ObjectKind,
                        ReferenceUse, Representation, ReviewCoverage,
                        RightsGrant, SourceTimes, StoredVersion,
                        VersionReference, VersionSubmission)


class CorrectionKind(str, Enum):
    SOURCE_CORRECTION = "SOURCE_CORRECTION"
    SOURCE_WITHDRAWAL = "SOURCE_WITHDRAWAL"
    METHOD_OR_ARGUMENT_ERROR = "METHOD_OR_ARGUMENT_ERROR"
    CONDITION_CHANGE = "CONDITION_CHANGE"
    LICENSE_CHANGE = "LICENSE_CHANGE"


class CorrectionPhase(str, Enum):
    RESTRICTED = "RESTRICTED"
    ASSESSED = "ASSESSED"
    RECOVERED = "RECOVERED"


class ImpactOutcome(str, Enum):
    MAINTAINED = "MAINTAINED"
    NARROWED = "NARROWED"
    RETRACTED = "RETRACTED"
    UNRESOLVED = "UNRESOLVED"
    NOT_AFFECTED = "NOT_AFFECTED"


class CorrectionChange(Contract):
    previous_version_id: Identifier
    corrected_version_id: Identifier | None
    kind: CorrectionKind
    reason: NonBlank
    changed_at: AwareDatetime


class DependencyEdge(Contract):
    dependent_version_id: Identifier
    dependency_version_id: Identifier
    reference_use: ReferenceUse
    locator: NonBlank
    depth: int = Field(ge=1)


class CorrectionBeginRequest(Contract):
    schema_version: Literal[1] = 1
    correction_id: Identifier
    previous_version_id: Identifier
    corrected_version_id: Identifier | None = None
    kind: CorrectionKind
    reason: NonBlank
    changed_at: AwareDatetime
    affected_scopes: tuple[NonBlank, ...]
    adoption_decision_ids: tuple[Identifier, ...] = ()
    max_depth: int = Field(default=12, ge=1, le=32)
    scope_limitation: NonBlank
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if not self.affected_scopes or len(self.affected_scopes) != len(
                set(self.affected_scopes)):
            raise ValueError(
                "Correction needs unique affected use scopes")
        if len(self.adoption_decision_ids) != len(
                set(self.adoption_decision_ids)):
            raise ValueError("Duplicate affected adoption decision")
        if self.changed_at > self.created_at:
            raise ValueError("Correction cannot be registered before it was observed")
        if (self.kind is CorrectionKind.SOURCE_CORRECTION
                and self.corrected_version_id is None):
            raise ValueError("Source correction needs the corrected version")
        if (self.kind is CorrectionKind.SOURCE_WITHDRAWAL
                and self.corrected_version_id is not None):
            raise ValueError("Withdrawal cannot carry a replacement version")
        return self


class VersionImpactDecision(Contract):
    target_version_id: Identifier
    outcome: ImpactOutcome
    retained_scope: tuple[NonBlank, ...] = ()
    remaining_support_version_ids: tuple[Identifier, ...] = ()
    reason: NonBlank
    next_owner: Literal["T04", "T05", "T07", "T09", "W40"]

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if len(self.retained_scope) != len(set(self.retained_scope)):
            raise ValueError("Duplicate retained impact scope")
        if len(self.remaining_support_version_ids) != len(
                set(self.remaining_support_version_ids)):
            raise ValueError("Duplicate remaining support")
        if self.outcome is ImpactOutcome.MAINTAINED and not (
                self.remaining_support_version_ids):
            raise ValueError(
                "Maintained impact needs remaining exact support")
        if self.outcome is ImpactOutcome.NARROWED and (
                not self.retained_scope
                or not self.remaining_support_version_ids):
            raise ValueError(
                "Narrowed impact needs retained scope and remaining support")
        if self.outcome in (
                ImpactOutcome.RETRACTED,
                ImpactOutcome.UNRESOLVED) and self.retained_scope:
            raise ValueError(
                "Retracted/unresolved impact cannot retain an approved scope")
        return self


class ImpactAssessmentRequest(Contract):
    schema_version: Literal[1] = 1
    correction_case_version_id: Identifier
    decisions: tuple[VersionImpactDecision, ...]
    unsearched_scope: tuple[NonBlank, ...] = ()
    assessed_by: NonBlank
    assessed_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if len({item.target_version_id for item in self.decisions}) != len(
                self.decisions):
            raise ValueError("One impact decision is needed per target version")
        if len(self.unsearched_scope) != len(set(self.unsearched_scope)):
            raise ValueError("Duplicate unsearched impact scope")
        return self


class CorrectionCaseRecord(Contract):
    schema_version: Literal[1] = 1
    correction_id: Identifier
    correction_case_version_id: Identifier
    previous_version_id: Identifier | None
    phase: CorrectionPhase
    spec_sha256: Digest
    change: CorrectionChange
    affected_scopes: tuple[NonBlank, ...]
    dependency_edges: tuple[DependencyEdge, ...]
    affected_version_ids: tuple[Identifier, ...]
    affected_decision_ids: tuple[Identifier, ...]
    restriction_version_ids: tuple[Identifier, ...]
    impact_decisions: tuple[VersionImpactDecision, ...] = ()
    unsearched_scope: tuple[NonBlank, ...] = ()
    recovery_binding_ids: tuple[Identifier, ...] = ()
    recovery_restriction_version_ids: tuple[Identifier, ...] = ()
    scope_limitation: NonBlank
    assessed_by: NonBlank | None = None
    restored_by: NonBlank | None = None
    publication_authorized: Literal[False] = False
    created_at: AwareDatetime
    updated_at: AwareDatetime


class CorrectionResult(Contract):
    correction_case_version_id: Identifier
    phase: CorrectionPhase
    affected_version_ids: tuple[Identifier, ...]
    affected_decision_ids: tuple[Identifier, ...]
    restriction_version_ids: tuple[Identifier, ...]


class RestrictionItem(Contract):
    correction_id: Identifier
    scopes: tuple[NonBlank, ...]
    recovery_correction_case_version_id: Identifier | None = None
    recovery_review_version_id: Identifier | None = None
    recovered_scopes: tuple[NonBlank, ...] = ()
    allowed_decision_ids: tuple[Identifier, ...] = ()
    updated_at: AwareDatetime


class UseRestrictionRecord(Contract):
    schema_version: Literal[1] = 1
    use_restriction_id: Identifier
    use_restriction_version_id: Identifier
    target_version_id: Identifier
    items: tuple[RestrictionItem, ...]
    created_at: AwareDatetime


class RecoveryBinding(Contract):
    binding_id: Identifier
    target_version_id: Identifier
    recovery_review_version_id: Identifier
    recovered_scope: tuple[NonBlank, ...]
    allowed_decision_ids: tuple[Identifier, ...] = ()

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if not self.recovered_scope or len(self.recovered_scope) != len(
                set(self.recovered_scope)):
            raise ValueError(
                "Recovery binding needs a unique nonempty scope")
        if len(self.allowed_decision_ids) != len(
                set(self.allowed_decision_ids)):
            raise ValueError("Duplicate allowed recovery decision")
        return self


class CorrectionRecoveryRequest(Contract):
    schema_version: Literal[1] = 1
    correction_case_version_id: Identifier
    expected_current_version_id: Identifier
    bindings: tuple[RecoveryBinding, ...]
    restored_by: NonBlank
    reason: NonBlank
    restored_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.correction_case_version_id != self.expected_current_version_id:
            raise ValueError(
                "Recovery must bind the exact expected correction case")
        if (not self.bindings
                or len({item.binding_id for item in self.bindings})
                != len(self.bindings)
                or len({item.target_version_id for item in self.bindings})
                != len(self.bindings)):
            raise ValueError(
                "Recovery needs unique bindings and target versions")
        return self


class CorrectionError(ArchiveError):
    """Correction/dependency failure, never automatic truth or recovery."""


def _digest(value) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _version(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([prefix, identity]).encode()).hexdigest()[:32]


def _object(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([identity]).encode()).hexdigest()[:32]


def _scope_overlap(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    left_set = {item.casefold() for item in left}
    right_set = {item.casefold() for item in right}
    return not left_set or not right_set or bool(left_set & right_set)


def is_version_restricted(archive: Archive, version_id: str,
                          required_scope: tuple[str, ...] = (),
                          decision_id: str | None = None) -> bool:
    """Check active correction limits without treating them as content judgment."""
    object_id = _object("USE-RESTRICTION-OBJECT-", version_id)
    stored = archive.latest(object_id)
    if stored is None:
        return False
    if stored.submission.kind is not ObjectKind.USE_RESTRICTION:
        raise CorrectionError("Correction restriction object has wrong kind")
    record = UseRestrictionRecord.model_validate_json(
        archive.read_body(stored.submission.version_id))
    if (record.target_version_id != version_id
            or record.use_restriction_version_id
            != stored.submission.version_id):
        raise CorrectionError("Use restriction identity mismatch")
    for item in record.items:
        if item.scopes and required_scope and not _scope_overlap(
                item.scopes, required_scope):
            continue
        if (decision_id is not None
                and decision_id in item.allowed_decision_ids):
            continue
        if item.recovery_review_version_id is not None and decision_id is None:
            if set(required_scope) <= set(item.recovered_scopes):
                review = archive.get(item.recovery_review_version_id)
                reviewed = {
                    reference.target_version_id
                    for reference in review.submission.references}
                if (review.submission.kind is ObjectKind.REVIEW
                        and not review.body_retention_revoked
                        and version_id in reviewed
                        and item.recovery_correction_case_version_id
                        in reviewed):
                    continue
        return True
    return False


class CorrectionController:
    def __init__(self, archive: Archive, rights: RightsGrant):
        if not isinstance(archive, Archive):
            raise TypeError("CorrectionController requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError("CorrectionController requires an internal journal grant")
        self.archive = archive
        self.rights = rights

    def _dependency_closure(self, source_version_id: str, max_depth: int):
        edges = []
        affected = {source_version_id}
        frontier = [(source_version_id, 0)]
        visited = {source_version_id}
        while frontier:
            target, depth = frontier.pop(0)
            if depth >= max_depth:
                continue
            for reference in self.archive.referrers(target):
                dependent = reference["version_id"]
                edge = DependencyEdge(
                    dependent_version_id=dependent,
                    dependency_version_id=target,
                    reference_use=ReferenceUse(reference["use"]),
                    locator=reference["locator"],
                    depth=depth + 1)
                edges.append(edge)
                affected.add(dependent)
                if dependent not in visited:
                    visited.add(dependent)
                    frontier.append((dependent, depth + 1))
        unique = {}
        for edge in edges:
            unique[(edge.dependent_version_id,
                    edge.dependency_version_id,
                    edge.reference_use,
                    edge.locator)] = edge
        return tuple(unique.values()), tuple(sorted(affected))

    def _append_restrictions(self, correction_id: str,
                             targets: tuple[str, ...], scopes: tuple[str, ...],
                             at) -> tuple[str, ...]:
        written = []
        for target in targets:
            object_id = _object("USE-RESTRICTION-OBJECT-", target)
            latest = self.archive.latest(object_id)
            items = ()
            if latest is not None:
                if latest.submission.kind is not ObjectKind.USE_RESTRICTION:
                    raise CorrectionError("Restriction object kind mismatch")
                items = UseRestrictionRecord.model_validate_json(
                    self.archive.read_body(latest.submission.version_id)).items
            items = tuple(
                item for item in items
                if item.correction_id != correction_id)
            item = RestrictionItem(
                correction_id=correction_id,
                scopes=scopes, updated_at=at)
            items = (*items, item)
            record_id = "USE-RESTRICTION-" + _digest([target, correction_id])[:32]
            version_id = _version("USE-RESTRICTION-", [
                target, correction_id, record_id])
            record = UseRestrictionRecord(
                use_restriction_id=record_id,
                use_restriction_version_id=version_id,
                target_version_id=target, items=items, created_at=at)
            target_stored = self.archive.get(target)
            submission = VersionSubmission(
                schema_version=2, object_id=object_id,
                version_id=version_id,
                parent_version_id=(
                    latest.submission.version_id if latest else None),
                kind=ObjectKind.USE_RESTRICTION,
                title=f"use restriction {target}",
                spec_sha256=target_stored.submission.spec_sha256,
                created_at=at, source_times=SourceTimes(), rights=self.rights,
                representation=Representation.FULL_BODY,
                references=(VersionReference(
                    target_version_id=target, use=ReferenceUse.REVIEW_OF,
                    locator="restricted exact version"),))
            self.archive.append(
                submission, canonical(record.model_dump(mode="json")).encode(),
                expected_current={
                    object_id: latest.submission.version_id if latest else None,
                })
            written.append(version_id)
        return tuple(written)

    def begin(self, request: CorrectionBeginRequest) -> CorrectionResult:
        if not isinstance(request, CorrectionBeginRequest):
            raise TypeError("begin requires CorrectionBeginRequest")
        request = CorrectionBeginRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        previous = self.archive.get(request.previous_version_id)
        if previous.body_retention_revoked and request.kind not in (
                CorrectionKind.SOURCE_WITHDRAWAL,
                CorrectionKind.LICENSE_CHANGE):
            raise CorrectionError(
                "Correction old source is unavailable for this change kind")
        if request.corrected_version_id is not None:
            corrected = self.archive.get(request.corrected_version_id)
            corrected_latest = self.archive.latest(
                corrected.submission.object_id)
            if (corrected.submission.object_id
                    != previous.submission.object_id
                    or corrected.ordinal <= previous.ordinal
                    or corrected_latest is None
                    or corrected_latest.submission.version_id
                    != request.corrected_version_id):
                raise CorrectionError(
                    "Corrected version does not follow and currently represent the changed object")
        edges, affected = self._dependency_closure(
            request.previous_version_id, request.max_depth)
        decision_records = []
        for decision_id in request.adoption_decision_ids:
            stored = self.archive.get(decision_id)
            if stored.submission.kind is not ObjectKind.ADOPTION_DECISION:
                raise CorrectionError(
                    "Affected adoption ID is not an AdoptionDecision")
            decision = AdoptionDecision.model_validate_json(
                self.archive.read_body(decision_id))
            if decision.subject_version_id not in affected:
                raise CorrectionError(
                    "Affected adoption subject is outside the explicit dependency graph")
            decision_records.append(decision)
        object_id = _object("CORRECTION-OBJECT-", request.correction_id)
        latest = self.archive.latest(object_id)
        content = canonical(request.model_dump(mode="json")).encode()
        case_version_id = _version("CORRECTION-CASE-", canonical([
            request.correction_id, None, _digest(content), affected]))
        try:
            existing = self.archive.get(case_version_id)
            case = CorrectionCaseRecord.model_validate_json(
                self.archive.read_body(case_version_id))
            if existing.submission.kind is not ObjectKind.CORRECTION_CASE:
                raise CorrectionError("Correction case version kind mismatch")
            return CorrectionResult(
                correction_case_version_id=case_version_id,
                phase=case.phase,
                affected_version_ids=case.affected_version_ids,
                affected_decision_ids=case.affected_decision_ids,
                restriction_version_ids=case.restriction_version_ids)
        except MissingVersion:
            pass
        if latest is not None:
            raise Conflict(
                "Correction ID already has a different current case history")
        restriction_ids = self._append_restrictions(
            request.correction_id, affected, request.affected_scopes,
            request.created_at)
        change = CorrectionChange(
            previous_version_id=request.previous_version_id,
            corrected_version_id=request.corrected_version_id,
            kind=request.kind, reason=request.reason,
            changed_at=request.changed_at)
        case = CorrectionCaseRecord(
            correction_id=request.correction_id,
            correction_case_version_id=case_version_id,
            previous_version_id=None, phase=CorrectionPhase.RESTRICTED,
            spec_sha256=previous.submission.spec_sha256,
            change=change, affected_scopes=request.affected_scopes,
            dependency_edges=edges, affected_version_ids=affected,
            affected_decision_ids=request.adoption_decision_ids,
            restriction_version_ids=restriction_ids,
            scope_limitation=request.scope_limitation,
            created_at=request.created_at, updated_at=request.created_at)
        references = [
            VersionReference(
                target_version_id=request.previous_version_id,
                use=ReferenceUse.REVIEW_OF, locator="changed old version"),
            *(
                VersionReference(
                    target_version_id=version_id,
                    use=ReferenceUse.SUPPORT,
                    locator="dependency or restriction")
                for version_id in affected
            ),
            *(
                VersionReference(
                    target_version_id=version_id,
                    use=ReferenceUse.SUPPORT,
                    locator="active use restriction")
                for version_id in restriction_ids
            ),
        ]
        if request.corrected_version_id is not None:
            references.append(VersionReference(
                target_version_id=request.corrected_version_id,
                use=ReferenceUse.BASIS, locator="corrected source version"))
        submission = VersionSubmission(
            schema_version=2, object_id=object_id,
            version_id=case_version_id, parent_version_id=None,
            kind=ObjectKind.CORRECTION_CASE,
            title=f"correction case {request.correction_id}",
            spec_sha256=case.spec_sha256,
            created_at=request.created_at, source_times=SourceTimes(),
            rights=self.rights, representation=Representation.FULL_BODY,
            references=tuple(references))
        expected = {
            object_id: None,
        }
        if request.corrected_version_id is not None:
            corrected_stored = self.archive.get(request.corrected_version_id)
            expected[corrected_stored.submission.object_id] = (
                corrected_stored.submission.version_id)
        self.archive.append(
            submission, canonical(case.model_dump(mode="json")).encode(),
            expected_current=expected)
        return CorrectionResult(
            correction_case_version_id=case_version_id,
            phase=case.phase, affected_version_ids=affected,
            affected_decision_ids=request.adoption_decision_ids,
            restriction_version_ids=restriction_ids)

    def assess(self, request: ImpactAssessmentRequest) -> CorrectionCaseRecord:
        stored = self.archive.get(request.correction_case_version_id)
        if stored.submission.kind is not ObjectKind.CORRECTION_CASE:
            raise CorrectionError("Impact assessment target is not a correction case")
        current = CorrectionCaseRecord.model_validate_json(
            self.archive.read_body(stored.submission.version_id))
        if current.phase is not CorrectionPhase.RESTRICTED:
            raise CorrectionError("Only a restricted case can be assessed")
        if {item.target_version_id for item in request.decisions} != set(
                current.affected_version_ids):
            raise CorrectionError(
                "Impact assessment must classify every explicit dependent")
        for decision in request.decisions:
            for support_id in decision.remaining_support_version_ids:
                self.archive.get(support_id)
        object_id = stored.submission.object_id
        updated = current.model_copy(update={
            "correction_case_version_id": _version(
                "CORRECTION-CASE-", canonical([
                    current.correction_id, current.correction_case_version_id,
                    _digest(request.model_dump(mode="json"))])),
            "previous_version_id": current.correction_case_version_id,
            "phase": CorrectionPhase.ASSESSED,
            "impact_decisions": request.decisions,
            "unsearched_scope": request.unsearched_scope,
            "assessed_by": request.assessed_by,
            "updated_at": request.assessed_at,
        })
        submission = VersionSubmission(
            schema_version=2, object_id=object_id,
            version_id=updated.correction_case_version_id,
            parent_version_id=current.correction_case_version_id,
            kind=ObjectKind.CORRECTION_CASE,
            title=f"correction case {current.correction_id}",
            spec_sha256=current.spec_sha256,
            created_at=request.assessed_at, source_times=SourceTimes(),
            rights=self.rights, representation=Representation.FULL_BODY,
            references=(VersionReference(
                target_version_id=current.correction_case_version_id,
                use=ReferenceUse.BASIS, locator="restricted correction case"),))
        self.archive.append(
            submission, canonical(updated.model_dump(mode="json")).encode(),
            expected_current={
                object_id: current.correction_case_version_id,
            })
        return updated

    def recover(self, request: CorrectionRecoveryRequest) -> CorrectionCaseRecord:
        stored = self.archive.get(request.expected_current_version_id)
        if stored.submission.kind is not ObjectKind.CORRECTION_CASE:
            raise CorrectionError("Recovery target is not a correction case")
        current = CorrectionCaseRecord.model_validate_json(
            self.archive.read_body(stored.submission.version_id))
        if current.phase is not CorrectionPhase.ASSESSED:
            raise CorrectionError("Recovery needs an assessed correction case")
        outcome = {
            item.target_version_id: item.outcome
            for item in current.impact_decisions}
        for binding in request.bindings:
            if binding.target_version_id not in current.affected_version_ids:
                raise CorrectionError("Recovery target is outside this correction")
            if outcome[binding.target_version_id] is ImpactOutcome.RETRACTED:
                raise CorrectionError(
                    "Retracted content cannot be restored without a new version")
            if not set(binding.recovered_scope) <= set(current.affected_scopes):
                raise CorrectionError(
                    "Recovery scope exceeds the corrections' restricted scope")
            review = self.archive.get(binding.recovery_review_version_id)
            if (review.submission.kind is not ObjectKind.REVIEW
                    or review.submission.spec_sha256 != current.spec_sha256
                    or review.body_retention_revoked):
                raise CorrectionError("Recovery needs an available exact Review")
            reviewed = {
                item.target_version_id for item in review.submission.references
                if item.use is ReferenceUse.REVIEW_OF}
            all_review_refs = {
                item.target_version_id
                for item in review.submission.references}
            if (binding.target_version_id not in reviewed
                    or current.correction_case_version_id
                    not in all_review_refs):
                raise CorrectionError(
                    "Recovery Review does not cover the target and correction case")
            for decision_id in binding.allowed_decision_ids:
                decision_stored = self.archive.get(decision_id)
                if decision_stored.submission.kind is not ObjectKind.ADOPTION_DECISION:
                    raise CorrectionError(
                        "Allowed recovery decision is not a W15 decision")
                decision = AdoptionDecision.model_validate_json(
                    self.archive.read_body(decision_id))
                if (decision.state is not StepState.READY
                        or decision.subject_version_id
                        != binding.target_version_id
                        or decision.review_version_id
                        != binding.recovery_review_version_id
                        or not set(decision.allowed_scope)
                        <= set(binding.recovered_scope)
                        or decision_id in current.affected_decision_ids):
                    raise CorrectionError(
                        "Allowed recovery decision does not bind the new Review/scope")
        updated_items = {}
        for binding in request.bindings:
            object_id = _object(
                "USE-RESTRICTION-OBJECT-", binding.target_version_id)
            latest = self.archive.latest(object_id)
            if latest is None:
                raise CorrectionError("Recovery target has no restriction record")
            record = UseRestrictionRecord.model_validate_json(
                self.archive.read_body(latest.submission.version_id))
            items = []
            matched = False
            for item in record.items:
                if item.correction_id != current.correction_id:
                    items.append(item)
                    continue
                matched = True
                items.append(item.model_copy(update={
                    "recovery_correction_case_version_id":
                        current.correction_case_version_id,
                    "recovery_review_version_id":
                        binding.recovery_review_version_id,
                    "recovered_scopes": binding.recovered_scope,
                    "allowed_decision_ids": binding.allowed_decision_ids,
                    "updated_at": request.restored_at,
                }))
            if not matched:
                raise CorrectionError(
                    "Recovery target restriction belongs to another case")
            updated_record = record.model_copy(update={
                "use_restriction_version_id": _version(
                    "USE-RESTRICTION-", canonical([
                        binding.target_version_id,
                        current.correction_case_version_id,
                        _digest(binding.model_dump(mode="json"))])),
                "items": tuple(items), "created_at": request.restored_at,
            })
            self.archive.get(binding.target_version_id)
            submission = VersionSubmission(
                schema_version=2, object_id=object_id,
                version_id=updated_record.use_restriction_version_id,
                parent_version_id=latest.submission.version_id,
                kind=ObjectKind.USE_RESTRICTION,
                title=f"use restriction {binding.target_version_id}",
                spec_sha256=current.spec_sha256,
                created_at=request.restored_at, source_times=SourceTimes(),
                rights=self.rights, representation=Representation.FULL_BODY,
                references=(VersionReference(
                    target_version_id=binding.target_version_id,
                    use=ReferenceUse.REVIEW_OF,
                    locator="restored exact version"),))
            self.archive.append(
                submission,
                canonical(updated_record.model_dump(mode="json")).encode(),
                expected_current={
                    object_id: latest.submission.version_id,
                })
            updated_items[binding.binding_id] = (
                updated_record.use_restriction_version_id)
        case_version_id = _version("CORRECTION-CASE-", canonical([
            current.correction_id, current.correction_case_version_id,
            _digest(request.model_dump(mode="json"))]))
        updated = current.model_copy(update={
            "correction_case_version_id": case_version_id,
            "previous_version_id": current.correction_case_version_id,
            "phase": CorrectionPhase.RECOVERED,
            "recovery_binding_ids": tuple(
                binding.binding_id for binding in request.bindings),
            "recovery_restriction_version_ids": tuple(
                updated_items.values()),
            "restored_by": request.restored_by,
            "updated_at": request.restored_at,
        })
        case_submission = VersionSubmission(
            schema_version=2, object_id=stored.submission.object_id,
            version_id=case_version_id,
            parent_version_id=current.correction_case_version_id,
            kind=ObjectKind.CORRECTION_CASE,
            title=f"correction case {current.correction_id}",
            spec_sha256=current.spec_sha256,
            created_at=request.restored_at, source_times=SourceTimes(),
            rights=self.rights, representation=Representation.FULL_BODY,
            references=(
                VersionReference(
                    target_version_id=current.correction_case_version_id,
                    use=ReferenceUse.BASIS,
                    locator="assessed correction case"),
                *(
                    VersionReference(
                        target_version_id=binding.recovery_review_version_id,
                        use=ReferenceUse.REVIEW_OF,
                        locator=f"recovery review {index}")
                    for index, binding in enumerate(request.bindings)
                ),
            ))
        expected = {stored.submission.object_id:
                    current.correction_case_version_id}
        for version_id in updated_items.values():
            restriction = self.archive.get(version_id)
            expected[restriction.submission.object_id] = version_id
        self.archive.append(
            case_submission,
            canonical(updated.model_dump(mode="json")).encode(),
            expected_current=expected)
        return updated

    def load(self, correction_case_version_id: str) -> CorrectionCaseRecord:
        stored = self.archive.get(correction_case_version_id)
        if stored.submission.kind is not ObjectKind.CORRECTION_CASE:
            raise CorrectionError("Requested version is not a correction case")
        case = CorrectionCaseRecord.model_validate_json(
            self.archive.read_body(correction_case_version_id))
        if (case.correction_case_version_id != correction_case_version_id
                or stored.submission.spec_sha256 != case.spec_sha256
                or stored.submission.created_at != case.updated_at):
            raise CorrectionError("Correction case identity mismatch")
        return case
