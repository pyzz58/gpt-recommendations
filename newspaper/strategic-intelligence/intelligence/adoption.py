"""W15 minimal authoritative adoption journal.

Producers submit version-bound results and proposed states. Reviews declare their
exact task/subject/use coverage. A separate checker request records a decision
only after exact task, subject, dependency, evidence and Review checks; decision
chains are isolated by stable Task object and current authorization recursively
checks required dependencies. This interface does not authenticate checker
identity, judge content truth or authorize publication; W17 and W31 retain those
duties.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import hashlib
from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from .archive import Archive, ArchiveError, MissingVersion, canonical
from .contracts import (Contract, Digest, Identifier, NonBlank, ObjectKind, ReferenceUse,
                        Representation, ReviewCoverage, RightsGrant, SourceTimes,
                        StoredVersion, VersionReference, VersionSubmission)


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
    schema_version: Literal[1, 2] = 2
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
    task_object_id: Identifier | None = None

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
    schema_version: Literal[1, 2] = 2
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
    task_object_id: Identifier | None = None


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
    def _legacy_object_id(prefix: str, work_id: str, step_id: str) -> str:
        return f"{prefix}-{work_id}-{step_id}"

    @staticmethod
    def _scoped_object_id(prefix: str, task_object_id: str, work_id: str, step_id: str) -> str:
        identity = canonical([task_object_id, work_id, step_id]).encode()
        return f"{prefix}-{hashlib.sha256(identity).hexdigest()[:32]}"

    @staticmethod
    def _scope_values(values: tuple[str, ...]) -> set[str]:
        return {value.strip().casefold() for value in values}

    @classmethod
    def _scope_is_covered(cls, required: tuple[str, ...], covered: tuple[str, ...]) -> bool:
        return cls._scope_values(required) <= cls._scope_values(covered)

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
        if (record.task_object_id is not None
                and record.task_object_id != task.submission.object_id):
            raise AdoptionError("Submission task object identity does not match the exact Task version")
        record = StepSubmission.model_validate_json(record.model_copy(update={
            "schema_version": 2,
            "task_object_id": task.submission.object_id,
        }).model_dump_json())
        subject = self.archive.get(record.subject_version_id)
        if subject.submission.spec_sha256 != record.spec_sha256:
            raise AdoptionError("Subject uses a different specification")
        for version_id in (*record.input_version_ids, *record.evidence_version_ids):
            self.archive.get(version_id)
        self._validate_dependencies(record, record.created_at)
        object_id = self._scoped_object_id(
            "STEP", record.task_object_id, record.work_id, record.step_id)
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
        task = self.archive.get(submission.task_version_id)
        if task.submission.kind is not ObjectKind.TASK:
            raise AdoptionError("Submission owner is not a Task")
        self._require_available(task, "Task")
        self._require_latest(task, "Task")
        if (submission.task_object_id is not None
                and submission.task_object_id != task.submission.object_id):
            raise AdoptionError("Submission task object identity does not match the exact Task version")
        submission = StepSubmission.model_validate_json(submission.model_copy(update={
            "schema_version": 2,
            "task_object_id": task.submission.object_id,
        }).model_dump_json())
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
        if task.submission.spec_sha256 != submission.spec_sha256:
            raise AdoptionError("Task specification changed")
        subject = self.archive.get(submission.subject_version_id)
        if subject.submission.spec_sha256 != submission.spec_sha256:
            raise AdoptionError("Subject specification changed")
        self._require_available(subject, "Subject")
        self._require_latest(subject, "Subject")
        if request.state is StepState.READY and not self._scope_is_covered(
                request.allowed_scope, submission.claimed_scope):
            raise AdoptionError("Decision scope exceeds the submitted scope")
        self._require_review_coverage(
            review, submission, request.allowed_scope)
        for version_id in (*submission.input_version_ids, *submission.evidence_version_ids):
            stored = self.archive.get(version_id)
            if stored.body_retention_revoked:
                raise AdoptionError(f"Required input or evidence was withdrawn: {version_id}")
        self._validate_dependencies(submission, request.decided_at)
        object_id = self._scoped_object_id(
            "DEC", submission.task_object_id, submission.work_id, submission.step_id)
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
            decided_at=request.decided_at, expires_at=request.expires_at,
            task_object_id=submission.task_object_id)
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

    @staticmethod
    def _review_covers(
            review: StoredVersion, task_version_id: str, subject_version_id: str,
            required_scope: tuple[str, ...]) -> bool:
        entries = [
            item for item in review.submission.review_coverage
            if item.task_version_id == task_version_id
            and item.subject_version_id == subject_version_id
        ]
        if not entries:
            return False
        covered = tuple(value for item in entries for value in item.reviewed_scope)
        return AdoptionController._scope_is_covered(required_scope, covered)

    def _require_review_coverage(
            self, review: StoredVersion, submission: StepSubmission,
            allowed_scope: tuple[str, ...] = ()) -> None:
        required_scope = (*submission.claimed_scope, *allowed_scope)
        if not self._review_covers(
                review, submission.task_version_id, submission.subject_version_id,
                required_scope):
            raise AdoptionError(
                "Review does not structurally cover this exact task, subject and use scope")

    def _decision_task_object_id(self, decision: AdoptionDecision) -> str:
        if decision.task_object_id is not None:
            return decision.task_object_id
        task = self.archive.get(decision.task_version_id)
        if task.submission.kind is not ObjectKind.TASK:
            raise AdoptionError("Decision task version is not a Task")
        return task.submission.object_id

    @staticmethod
    def _decision_matches_submission(
            decision: AdoptionDecision, submission: StepSubmission) -> bool:
        return (
            decision.submission_version_id == submission.submission_id
            and decision.work_id == submission.work_id
            and decision.step_id == submission.step_id
            and decision.spec_sha256 == submission.spec_sha256
            and decision.task_version_id == submission.task_version_id
            and decision.subject_version_id == submission.subject_version_id
            and decision.input_version_ids == submission.input_version_ids
            and decision.evidence_version_ids == submission.evidence_version_ids
            and decision.dependency_decisions == submission.dependency_decisions
            and decision.task_object_id == submission.task_object_id
        )

    @staticmethod
    def _require_available(stored: StoredVersion, label: str) -> None:
        if stored.body_retention_revoked:
            raise AdoptionError(f"{label} was withdrawn for current use")

    def _require_latest(self, stored: StoredVersion, label: str) -> None:
        latest = self.archive.latest(stored.submission.object_id)
        if latest is None or latest.submission.version_id != stored.submission.version_id:
            raise AdoptionError(f"{label} version was superseded")

    def _validate_dependencies(
            self, submission: StepSubmission, at: datetime,
            trail: frozenset[str] = frozenset()) -> None:
        for dependency in submission.dependency_decisions:
            decision = self.load(dependency.decision_id)
            if decision.spec_sha256 != submission.spec_sha256:
                raise AdoptionError("Dependency decision uses a different specification")
            if decision.subject_version_id != dependency.expected_subject_version_id:
                raise AdoptionError("Dependency decision binds a different subject version")
            self._require_effective_decision(
                decision, at, allow_not_applicable=True, trail=trail)

    def _require_effective_decision(
            self, decision: AdoptionDecision, at: datetime, *,
            allow_not_applicable: bool, trail: frozenset[str]) -> None:
        if decision.decision_id in trail:
            raise AdoptionError("Adoption dependency cycle detected")
        task_object_id = self._decision_task_object_id(decision)
        if decision.task_object_id is None:
            decision = AdoptionDecision.model_validate_json(decision.model_copy(update={
                "schema_version": 2,
                "task_object_id": task_object_id,
            }).model_dump_json())
        current = self.current(
            decision.work_id, decision.step_id, task_object_id)
        if current is None or current.decision_id != decision.decision_id:
            raise AdoptionError("Dependency decision was superseded")
        allowed_states = (
            (StepState.READY, StepState.NOT_APPLICABLE)
            if allow_not_applicable else (StepState.READY,)
        )
        if decision.state not in allowed_states:
            raise AdoptionError("Dependency has not been adopted")
        if decision.expires_at is not None and at >= decision.expires_at:
            raise AdoptionError("Dependency adoption has expired")
        stored_submission, raw = self._load_body(
            decision.submission_version_id, ObjectKind.STEP_SUBMISSION)
        submission = StepSubmission.model_validate_json(raw)
        if stored_submission.submission.version_id != submission.submission_id:
            raise AdoptionError("Step submission identity mismatch")
        if submission.task_object_id is None:
            task = self.archive.get(submission.task_version_id)
            if task.submission.kind is not ObjectKind.TASK:
                raise AdoptionError("Submission owner is not a Task")
            submission = StepSubmission.model_validate_json(submission.model_copy(update={
                "schema_version": 2,
                "task_object_id": task.submission.object_id,
            }).model_dump_json())
        if not self._decision_matches_submission(decision, submission):
            raise AdoptionError("Adoption decision no longer matches its submitted records")
        if decision.review_version_id not in submission.evidence_version_ids:
            raise AdoptionError("Decision Review is not declared submission evidence")
        if decision.state is StepState.READY and not self._scope_is_covered(
                decision.allowed_scope, submission.claimed_scope):
            raise AdoptionError("Decision scope exceeds the submitted scope")
        task = self.archive.get(submission.task_version_id)
        subject = self.archive.get(submission.subject_version_id)
        review = self.archive.get(decision.review_version_id)
        if task.submission.kind is not ObjectKind.TASK:
            raise AdoptionError("Submission owner is not a Task")
        if task.submission.object_id != submission.task_object_id:
            raise AdoptionError("Task object identity changed")
        if review.submission.kind is not ObjectKind.REVIEW:
            raise AdoptionError("Decision basis is not an archived Review")
        if (task.submission.spec_sha256 != submission.spec_sha256
                or subject.submission.spec_sha256 != submission.spec_sha256
                or review.submission.spec_sha256 != submission.spec_sha256):
            raise AdoptionError("Decision inputs use a different specification")
        for stored, label in (
                (task, "Task"), (subject, "Subject"), (review, "Review")):
            self._require_available(stored, label)
        self._require_latest(task, "Task")
        self._require_latest(subject, "Subject")
        self._require_review_coverage(review, submission, decision.allowed_scope)
        for version_id in (*submission.input_version_ids, *submission.evidence_version_ids):
            self._require_available(
                self.archive.get(version_id), f"Required input or evidence {version_id}")
        self._validate_dependencies(
            submission, at, trail | frozenset({decision.decision_id}))

    def load(self, decision_id: str) -> AdoptionDecision:
        stored, raw = self._load_body(decision_id, ObjectKind.ADOPTION_DECISION)
        decision = AdoptionDecision.model_validate_json(raw)
        self._parse_id(stored, decision.decision_id)
        return decision

    def current(
            self, work_id: str, step_id: str,
            task_object_id: str) -> AdoptionDecision | None:
        """Return one exact Task object's current decision record."""
        stored = self.archive.latest(
            self._scoped_object_id("DEC", task_object_id, work_id, step_id))
        if stored is not None:
            decision = self.load(stored.submission.version_id)
            return (decision if self._decision_task_object_id(decision) == task_object_id
                    else None)
        # Schema-1 records lived in one shared slot. Read their history without
        # ever borrowing the latest decision from a different Task.
        legacy = self.archive.history(
            self._legacy_object_id("DEC", work_id, step_id))
        for stored in reversed(legacy):
            decision = self.load(stored.submission.version_id)
            if self._decision_task_object_id(decision) == task_object_id:
                return decision
        return None

    def current_state(
            self, work_id: str, step_id: str, task_object_id: str) -> StepState:
        decision = self.current(work_id, step_id, task_object_id)
        return decision.state if decision is not None else StepState.PENDING

    def is_current(self, decision_id: str, at: AwareDatetime | None = None) -> bool:
        try:
            decision = self.load(decision_id)
            # W34 correction limits are shared with all downstream uses. Check
            # them before the normal W15 dependency/version walk.
            from .correction import is_version_restricted
            if is_version_restricted(
                    self.archive, decision.subject_version_id,
                    decision.allowed_scope, decision.decision_id):
                return False
            self._require_effective_decision(
                decision, at or datetime.now(timezone.utc),
                allow_not_applicable=False, trail=frozenset())
            return True
        except (ArchiveError, AdoptionError, ValueError):
            return False

    def authorizes(self, decision_id: str, required_scope: tuple[str, ...],
                   at: AwareDatetime | None = None) -> bool:
        """Check a current READY decision for the exact downstream scope."""
        if not required_scope or not self.is_current(decision_id, at):
            return False
        decision = self.load(decision_id)
        allowed = {value.casefold() for value in decision.allowed_scope}
        return all(value.casefold() in allowed for value in required_scope)
