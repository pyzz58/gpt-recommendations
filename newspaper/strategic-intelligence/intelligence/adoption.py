"""W15 minimal authoritative adoption journal.

Producers submit version-bound results and proposed states. A separate checker
request records a decision only after exact task, subject, dependency, evidence
and review-version checks. This interface does not authenticate checker identity,
judge content truth or authorize publication; W17 and W31 retain those duties.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from .archive import Archive, ArchiveError, MissingVersion, canonical
from .contracts import (Contract, Digest, Identifier, NonBlank, ObjectKind, ReferenceUse,
                        Representation, RightsGrant, SourceTimes, StoredVersion,
                        VersionReference, VersionSubmission)


class StepState(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    RETURN = "RETURN"
    BLOCKED = "BLOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class CheckerRole(str, Enum):
    EXECUTOR = "EXECUTOR"
    L5 = "L5"
    L6 = "L6"


class DependencyDecision(Contract):
    decision_id: Identifier
    expected_subject_version_id: Identifier


class StepSubmission(Contract):
    schema_version: Literal[1] = 1
    submission_id: Identifier
    work_id: Identifier
    step_id: Identifier
    spec_sha256: Digest
    task_version_id: Identifier
    subject_version_id: Identifier
    producer_id: NonBlank
    proposed_state: StepState
    claimed_scope: tuple[NonBlank, ...] = ()
    input_version_ids: tuple[Identifier, ...] = ()
    evidence_version_ids: tuple[Identifier, ...] = ()
    dependency_decisions: tuple[DependencyDecision, ...] = ()
    gaps: tuple[NonBlank, ...] = ()
    created_at: AwareDatetime

    @model_validator(mode="after")
    def unique_bindings(self) -> Self:
        for name, values in (("input", self.input_version_ids),
                             ("evidence", self.evidence_version_ids)):
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate {name} version")
        keys = [(item.decision_id, item.expected_subject_version_id)
                for item in self.dependency_decisions]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate dependency decision")
        return self


class DecisionRequest(Contract):
    schema_version: Literal[1] = 1
    decision_id: Identifier
    submission_version_id: Identifier
    state: StepState
    checker_id: NonBlank
    checker_role: CheckerRole
    review_version_id: Identifier
    allowed_scope: tuple[NonBlank, ...] = ()
    reason: NonBlank
    decided_at: AwareDatetime
    expires_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.state is StepState.PENDING:
            raise ValueError("PENDING has no authoritative decision record")
        if self.expires_at is not None and self.expires_at <= self.decided_at:
            raise ValueError("Adoption approval must expire after its decision time")
        if self.state is StepState.READY and not self.allowed_scope:
            raise ValueError("READY needs an explicit allowed scope")
        if self.state is not StepState.READY and self.allowed_scope:
            raise ValueError("Only READY may carry an adoptable scope")
        return self


class AdoptionDecision(Contract):
    schema_version: Literal[1] = 1
    decision_id: Identifier
    submission_version_id: Identifier
    work_id: Identifier
    step_id: Identifier
    spec_sha256: Digest
    task_version_id: Identifier
    subject_version_id: Identifier
    state: StepState
    checker_id: NonBlank
    checker_role: CheckerRole
    review_version_id: Identifier
    allowed_scope: tuple[NonBlank, ...]
    reason: NonBlank
    input_version_ids: tuple[Identifier, ...]
    evidence_version_ids: tuple[Identifier, ...]
    dependency_decisions: tuple[DependencyDecision, ...]
    decided_at: AwareDatetime
    expires_at: AwareDatetime | None = None


class AdoptionError(ArchiveError):
    """A record/transition failure, never a content PASS or publication grant."""


class AdoptionController:
    def __init__(self, archive: Archive, rights: RightsGrant):
        if not isinstance(archive, Archive):
            raise TypeError("AdoptionController requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError("AdoptionController requires an immutable internal journal grant")
        self.archive = archive
        self.rights = rights

    @staticmethod
    def _object_id(prefix: str, work_id: str, step_id: str) -> str:
        return f"{prefix}-{work_id}-{step_id}"

    def _load_body(self, version_id: str, kind: ObjectKind) -> tuple[StoredVersion, bytes]:
        stored = self.archive.get(version_id)
        if stored.submission.kind is not kind:
            raise AdoptionError(f"{version_id} is not a {kind.value}")
        return stored, self.archive.read_body(version_id)

    @staticmethod
    def _parse_id(stored: StoredVersion, record_id: str) -> None:
        if stored.submission.version_id != record_id:
            raise AdoptionError("Stored journal version does not match its record ID")

    def submit(self, record: StepSubmission) -> StoredVersion:
        if not isinstance(record, StepSubmission):
            raise TypeError("submit requires a StepSubmission")
        record = StepSubmission.model_validate_json(record.model_dump_json(warnings=False))
        task = self.archive.get(record.task_version_id)
        if task.submission.kind is not ObjectKind.TASK:
            raise AdoptionError("Submission owner is not a Task")
        if task.submission.spec_sha256 != record.spec_sha256:
            raise AdoptionError("Task and submission use different specifications")
        subject = self.archive.get(record.subject_version_id)
        if subject.submission.spec_sha256 != record.spec_sha256:
            raise AdoptionError("Subject uses a different specification")
        for version_id in (*record.input_version_ids, *record.evidence_version_ids):
            self.archive.get(version_id)
        self._validate_dependencies(record, record.created_at)
        object_id = self._object_id("STEP", record.work_id, record.step_id)
        latest = self.archive.latest(object_id)
        parent = latest.submission.version_id if latest else None
        references = [
            VersionReference(target_version_id=record.task_version_id,
                             use=ReferenceUse.BASIS, locator="submitted task version"),
            VersionReference(target_version_id=record.subject_version_id,
                             use=ReferenceUse.REVIEW_OF, locator="submitted result version"),
        ]
        references.extend(VersionReference(target_version_id=value, use=ReferenceUse.SUPPORT,
                                           locator=f"input {index}")
                          for index, value in enumerate(record.input_version_ids))
        references.extend(VersionReference(target_version_id=value, use=ReferenceUse.SUPPORT,
                                           locator=f"evidence {index}")
                          for index, value in enumerate(record.evidence_version_ids))
        references.extend(VersionReference(target_version_id=item.decision_id, use=ReferenceUse.BASIS,
                                           locator=f"dependency {index}")
                          for index, item in enumerate(record.dependency_decisions))
        submission = VersionSubmission(
            schema_version=2, object_id=object_id, kind=ObjectKind.STEP_SUBMISSION,
            version_id=record.submission_id, parent_version_id=parent,
            title=f"{record.work_id}/{record.step_id} step submission",
            spec_sha256=record.spec_sha256, created_at=record.created_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY, references=tuple(references))
        return self.archive.append(submission, canonical(record.model_dump(mode="json")).encode())

    def decide(self, request: DecisionRequest) -> StoredVersion:
        if not isinstance(request, DecisionRequest):
            raise TypeError("decide requires a DecisionRequest")
        request = DecisionRequest.model_validate_json(request.model_dump_json(warnings=False))
        submission_stored, raw = self._load_body(
            request.submission_version_id, ObjectKind.STEP_SUBMISSION)
        submission = StepSubmission.model_validate_json(raw)
        if submission_stored.submission.version_id != submission.submission_id:
            raise AdoptionError("Step submission identity mismatch")
        if request.checker_id.strip().casefold() == submission.producer_id.strip().casefold():
            raise AdoptionError("The producer cannot issue the authoritative decision")
        if request.review_version_id not in submission.evidence_version_ids:
            raise AdoptionError("Decision review must be a declared submission evidence version")
        review = self.archive.get(request.review_version_id)
        if review.submission.kind is not ObjectKind.REVIEW:
            raise AdoptionError("Decision basis is not an archived Review")
        if review.submission.spec_sha256 != submission.spec_sha256:
            raise AdoptionError("Review and submission use different specifications")
        if review.body_retention_revoked:
            raise AdoptionError("Review body was withdrawn")
        task = self.archive.get(submission.task_version_id)
        if task.submission.spec_sha256 != submission.spec_sha256:
            raise AdoptionError("Task specification changed")
        self.archive.get(submission.subject_version_id)
        for version_id in (*submission.input_version_ids, *submission.evidence_version_ids):
            self.archive.get(version_id)
        self._validate_dependencies(submission, request.decided_at)
        object_id = self._object_id("DEC", submission.work_id, submission.step_id)
        latest = self.archive.latest(object_id)
        parent = latest.submission.version_id if latest else None
        decision = AdoptionDecision(
            decision_id=request.decision_id, submission_version_id=submission.submission_id,
            work_id=submission.work_id, step_id=submission.step_id,
            spec_sha256=submission.spec_sha256, task_version_id=submission.task_version_id,
            subject_version_id=submission.subject_version_id, state=request.state,
            checker_id=request.checker_id, checker_role=request.checker_role,
            review_version_id=request.review_version_id, allowed_scope=request.allowed_scope,
            reason=request.reason, input_version_ids=submission.input_version_ids,
            evidence_version_ids=submission.evidence_version_ids,
            dependency_decisions=submission.dependency_decisions,
            decided_at=request.decided_at, expires_at=request.expires_at)
        references = (
            VersionReference(target_version_id=request.submission_version_id,
                             use=ReferenceUse.REVIEW_OF, locator="submitted step result"),
            VersionReference(target_version_id=request.review_version_id,
                             use=ReferenceUse.SUPPORT, locator="independent check"),
            VersionReference(target_version_id=submission.task_version_id,
                             use=ReferenceUse.BASIS, locator="task version"),
            VersionReference(target_version_id=submission.subject_version_id,
                             use=ReferenceUse.REVIEW_OF, locator="subject result version"),
        )
        version = VersionSubmission(
            schema_version=2, object_id=object_id, kind=ObjectKind.ADOPTION_DECISION,
            version_id=request.decision_id, parent_version_id=parent,
            title=f"{submission.work_id}/{submission.step_id} adoption decision",
            spec_sha256=submission.spec_sha256, created_at=request.decided_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY, references=references)
        return self.archive.append(version, canonical(decision.model_dump(mode="json")).encode())

    def _validate_dependencies(self, submission: StepSubmission, at: datetime) -> None:
        for dependency in submission.dependency_decisions:
            decision = self.load(dependency.decision_id)
            current = self.current(decision.work_id, decision.step_id)
            if current is None or current.decision_id != decision.decision_id:
                raise AdoptionError("Dependency decision was superseded")
            if decision.spec_sha256 != submission.spec_sha256:
                raise AdoptionError("Dependency decision uses a different specification")
            if decision.subject_version_id != dependency.expected_subject_version_id:
                raise AdoptionError("Dependency decision binds a different subject version")
            if decision.state not in (StepState.READY, StepState.NOT_APPLICABLE):
                raise AdoptionError("Dependency has not been adopted")
            if decision.expires_at is not None and at >= decision.expires_at:
                raise AdoptionError("Dependency adoption has expired")

    def load(self, decision_id: str) -> AdoptionDecision:
        stored, raw = self._load_body(decision_id, ObjectKind.ADOPTION_DECISION)
        decision = AdoptionDecision.model_validate_json(raw)
        self._parse_id(stored, decision.decision_id)
        return decision

    def current(self, work_id: str, step_id: str) -> AdoptionDecision | None:
        stored = self.archive.latest(self._object_id("DEC", work_id, step_id))
        return None if stored is None else self.load(stored.submission.version_id)

    def current_state(self, work_id: str, step_id: str) -> StepState:
        decision = self.current(work_id, step_id)
        return decision.state if decision is not None else StepState.PENDING

    def is_current(self, decision_id: str, at: AwareDatetime | None = None) -> bool:
        try:
            return self._is_current(decision_id, at)
        except (ArchiveError, ValueError):
            return False

    def _is_current(self, decision_id: str, at: AwareDatetime | None = None) -> bool:
        decision = self.load(decision_id)
        current = self.current(decision.work_id, decision.step_id)
        if current is None or current.decision_id != decision_id:
            return False
        instant = at or datetime.now(timezone.utc)
        if decision.state is not StepState.READY:
            return False
        if decision.expires_at is not None and instant >= decision.expires_at:
            return False
        stored_submission, raw = self._load_body(
            decision.submission_version_id, ObjectKind.STEP_SUBMISSION)
        submission = StepSubmission.model_validate_json(raw)
        if stored_submission.submission.version_id != submission.submission_id:
            return False
        if decision.review_version_id not in submission.evidence_version_ids:
            return False
        try:
            self._validate_dependencies(submission, instant)
        except (ArchiveError, ValueError):
            return False
        task = self.archive.get(decision.task_version_id)
        subject = self.archive.get(decision.subject_version_id)
        review = self.archive.get(decision.review_version_id)
        if (task.submission.kind is not ObjectKind.TASK
                or review.submission.kind is not ObjectKind.REVIEW
                or task.submission.spec_sha256 != decision.spec_sha256
                or subject.submission.spec_sha256 != decision.spec_sha256
                or review.submission.spec_sha256 != decision.spec_sha256
                or review.body_retention_revoked):
            return False
        return True

    def authorizes(self, decision_id: str, required_scope: tuple[str, ...],
                   at: AwareDatetime | None = None) -> bool:
        """Check a current READY decision for the exact downstream scope."""
        if not required_scope or not self.is_current(decision_id, at):
            return False
        decision = self.load(decision_id)
        allowed = {value.casefold() for value in decision.allowed_scope}
        return all(value.casefold() in allowed for value in required_scope)
