"""W31 independent reader-draft review and author-response closure.

The reviewer first fixes a real ARTICLE body and records independent inquiries.
Only then may a declared author respond with an exact revised version. Finally,
the reviewer resolves every inquiry and creates a version-bound Review and W15
adoption decision. This module does not authenticate people, establish general
reviewer capability or authorize publication.
"""
from __future__ import annotations

from enum import Enum
import hashlib
import json
from typing import Literal, Self

from pydantic import AwareDatetime, model_validator

from .adoption import (AdoptionController, CheckerRole, DecisionRequest,
                       StepState, StepSubmission)
from .archive import Archive, ArchiveError, Conflict, MissingVersion, canonical
from .article_route import ArticleRouteController, ArticleRouteError
from .contracts import (Contract, Digest, Identifier, MaterialUse, NonBlank,
                        ObjectKind, ReferenceUse, Representation, ReviewCoverage,
                        RightsGrant, SourceTimes, StoredVersion,
                        VersionReference, VersionSubmission)
from .model_admission import ModelAdmissionController, ModelDuty
from .operations import (OperationJournal, OperationKind, OperationRequest,
                         OperationStatus)
from .prospective import (ProspectiveController, ProspectiveMode,
                          ProspectiveOutput)
from .research import ResearchRevisionController
from .workflow import (ExecutionMethod, ResearchStep,
                       ResearchWorkflowController, StepDisposition,
                       WorkflowError)


class ReviewCaseState(str, Enum):
    OPEN = "OPEN"
    RESPONDED = "RESPONDED"


class InquiryType(str, Enum):
    FACT_SUPPORT = "FACT_SUPPORT"
    CALCULATION = "CALCULATION"
    TRANSLATION = "TRANSLATION"
    METHOD_OR_PROFESSIONAL = "METHOD_OR_PROFESSIONAL"
    INTERPRETATION = "INTERPRETATION"
    TEACHING = "TEACHING"
    CONDITION = "CONDITION"
    SCOPE = "SCOPE"
    ARTICLE_INTEGRITY = "ARTICLE_INTEGRITY"


class IssueSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"


class ClosureOutcome(str, Enum):
    RESOLVED = "RESOLVED"
    REVIEWER_WITHDRAWN = "REVIEWER_WITHDRAWN"
    ACCEPTED_DISPUTE = "ACCEPTED_DISPUTE"
    OPEN = "OPEN"
    UNVERIFIED = "UNVERIFIED"


class ReviewDisposition(str, Enum):
    PASS = "PASS"
    REVISE = "REVISE"
    BLOCK = "BLOCK"


class ReviewExposure(Contract):
    started_from_draft: bool
    author_self_assessment_seen: bool
    prior_review_seen: bool
    answer_key_seen: Literal[False] = False
    limitations: tuple[NonBlank, ...] = ()

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if len(self.limitations) != len(set(self.limitations)):
            raise ValueError("Duplicate review exposure limitation")
        if (self.started_from_draft
                and (self.author_self_assessment_seen
                     or self.prior_review_seen)):
            raise ValueError(
                "A draft-first review cannot also claim unseen author/review conclusions")
        if (not self.started_from_draft and not self.limitations):
            raise ValueError(
                "Non-draft-first review must record its exposure limitation")
        return self


class ReviewerInquiry(Contract):
    inquiry_id: Identifier
    inquiry_type: InquiryType
    severity: IssueSeverity
    article_locator: NonBlank
    quoted_text: NonBlank
    concern: NonBlank
    required_check: NonBlank
    claim_version_ids: tuple[Identifier, ...] = ()
    evidence_version_ids: tuple[Identifier, ...] = ()
    method_use_version_ids: tuple[Identifier, ...] = ()
    formed_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("claim", self.claim_version_ids),
                ("evidence", self.evidence_version_ids),
                ("method", self.method_use_version_ids)):
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate inquiry {name}")
        if (self.inquiry_type is not InquiryType.ARTICLE_INTEGRITY
                and not (self.claim_version_ids
                         or self.evidence_version_ids
                         or self.method_use_version_ids)):
            raise ValueError(
                "Substantive inquiry needs an exact Claim, Evidence or MethodUse")
        if (self.inquiry_type in {
                InquiryType.FACT_SUPPORT,
                InquiryType.CALCULATION,
                InquiryType.TRANSLATION,
        } and not self.evidence_version_ids):
            raise ValueError(
                "Fact/calculation/translation inquiry needs exact Evidence")
        if (self.inquiry_type is InquiryType.METHOD_OR_PROFESSIONAL
                and not (self.method_use_version_ids
                         or self.evidence_version_ids)):
            raise ValueError(
                "Method/professional inquiry needs MethodUse or Evidence")
        return self


class AuthorResponseItem(Contract):
    inquiry_id: Identifier
    responder_id: NonBlank
    response: NonBlank
    evidence_version_ids: tuple[Identifier, ...] = ()
    proposed_resolution: NonBlank
    responded_at: AwareDatetime

    @model_validator(mode="after")
    def unique_evidence(self) -> Self:
        if len(self.evidence_version_ids) != len(
                set(self.evidence_version_ids)):
            raise ValueError("Duplicate author-response Evidence")
        return self


class ReviewCaseRecord(Contract):
    schema_version: Literal[1] = 1
    review_case_id: Identifier
    review_case_version_id: Identifier
    previous_version_id: Identifier | None
    state: ReviewCaseState
    dossier_id: Identifier
    previous_snapshot_version_id: Identifier
    revision_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    task_version_id: Identifier
    initial_article_version_id: Identifier
    current_article_version_id: Identifier
    source_m10_record_version_id: Identifier
    source_m11_record_version_id: Identifier
    source_m12_record_version_id: Identifier
    source_advisor_output_version_id: Identifier
    source_teacher_output_version_id: Identifier
    source_prospective_output_version_id: Identifier
    reviewer_id: NonBlank
    author_ids: tuple[NonBlank, ...]
    producer_id: NonBlank
    reviewed_scope: tuple[NonBlank, ...]
    exposure: ReviewExposure
    inquiries: tuple[ReviewerInquiry, ...]
    responses: tuple[AuthorResponseItem, ...]
    claim_version_ids: tuple[Identifier, ...]
    evidence_version_ids: tuple[Identifier, ...]
    claim_evidence_assessment_version_ids: tuple[Identifier, ...]
    method_use_version_ids: tuple[Identifier, ...]
    execution_method: ExecutionMethod
    model_admission_id: Identifier | None
    model_configuration_id: Identifier | None
    operation_request_version_id: Identifier | None
    model_domains: tuple[NonBlank, ...]
    content_review_required: Literal[True] = True
    publication_authorized: Literal[False] = False
    created_at: AwareDatetime
    updated_at: AwareDatetime


class OpenReviewRequest(Contract):
    schema_version: Literal[1] = 1
    review_case_id: Identifier
    dossier_id: Identifier
    expected_snapshot_version_id: Identifier
    revision_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    task_version_id: Identifier
    article_version_id: Identifier
    source_m10_record_version_id: Identifier
    source_m11_record_version_id: Identifier
    source_m12_record_version_id: Identifier
    source_advisor_output_version_id: Identifier
    source_teacher_output_version_id: Identifier
    source_prospective_output_version_id: Identifier
    reviewer_id: NonBlank
    author_ids: tuple[NonBlank, ...]
    producer_id: NonBlank
    reviewed_scope: tuple[NonBlank, ...]
    exposure: ReviewExposure
    inquiries: tuple[ReviewerInquiry, ...] = ()
    claim_version_ids: tuple[Identifier, ...]
    evidence_version_ids: tuple[Identifier, ...]
    claim_evidence_assessment_version_ids: tuple[Identifier, ...]
    method_use_version_ids: tuple[Identifier, ...]
    execution_method: ExecutionMethod = ExecutionMethod.MANUAL
    model_admission_id: Identifier | None = None
    model_configuration_id: Identifier | None = None
    operation_request_version_id: Identifier | None = None
    model_domains: tuple[NonBlank, ...] = ()
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("author", self.author_ids),
                ("reviewed scope", self.reviewed_scope),
                ("inquiry", [item.inquiry_id for item in self.inquiries]),
                ("claim", self.claim_version_ids),
                ("evidence", self.evidence_version_ids),
                ("assessment", self.claim_evidence_assessment_version_ids),
                ("method", self.method_use_version_ids),
                ("model domain", self.model_domains)):
            if not values and name in (
                    "author", "reviewed scope", "claim",
                    "evidence", "assessment"):
                raise ValueError(f"Open review needs {name}")
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate review {name}")
        normalized_authors = {item.casefold() for item in self.author_ids}
        if self.reviewer_id.casefold() in normalized_authors:
            raise ValueError("Reviewer cannot be an author")
        if self.producer_id.casefold() in {
                self.reviewer_id.casefold()}:
            raise ValueError("Reviewer cannot be the producer/checker signer")
        if self.producer_id.casefold() not in normalized_authors:
            raise ValueError("Producer must be one of the declared authors")
        if any(item.formed_at > self.created_at for item in self.inquiries):
            raise ValueError("Reviewer inquiry cannot postdate the fixed review case")
        if self.execution_method is ExecutionMethod.ADMITTED_MODEL:
            if not all((self.model_admission_id, self.model_configuration_id,
                        self.operation_request_version_id, self.model_domains)):
                raise ValueError(
                    "Admitted reviewer needs admission, config and actual operation")
        elif any((self.model_admission_id, self.model_configuration_id,
                  self.operation_request_version_id)) or self.model_domains:
            raise ValueError(
                "Manual reviewer cannot carry model execution identity")
        return self


class AuthorResponseRequest(Contract):
    schema_version: Literal[1] = 1
    review_case_version_id: Identifier
    expected_current_case_version_id: Identifier
    responder_id: NonBlank
    article_version_id: Identifier
    responses: tuple[AuthorResponseItem, ...]
    note: NonBlank
    responded_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.review_case_version_id != self.expected_current_case_version_id:
            raise ValueError(
                "Author response must be prepared from its exact expected case")
        if len({item.inquiry_id for item in self.responses}) != len(
                self.responses):
            raise ValueError("Only one response per reviewer inquiry")
        if any(item.responder_id != self.responder_id for item in self.responses):
            raise ValueError("Author response must come from one declared responder")
        return self


class IssueClosure(Contract):
    inquiry_id: Identifier
    outcome: ClosureOutcome
    basis_version_ids: tuple[Identifier, ...] = ()
    rationale: NonBlank
    checked_at: AwareDatetime


class FinalReviewRequest(Contract):
    schema_version: Literal[1] = 1
    review_case_version_id: Identifier
    expected_current_case_version_id: Identifier
    review_id: Identifier
    article_version_id: Identifier
    reviewer_id: NonBlank
    decision: ReviewDisposition
    reviewed_scope: tuple[NonBlank, ...]
    closures: tuple[IssueClosure, ...]
    decision_reason: NonBlank
    remaining_limitations: tuple[NonBlank, ...] = ()
    expires_at: AwareDatetime | None = None
    decided_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.review_case_version_id != self.expected_current_case_version_id:
            raise ValueError(
                "Final review must bind its exact expected current case")
        if len({item.inquiry_id for item in self.closures}) != len(
                self.closures):
            raise ValueError("Only one closure per reviewer inquiry")
        if not self.reviewed_scope or len(self.reviewed_scope) != len(
                set(self.reviewed_scope)):
            raise ValueError("Final review needs a unique exact scope")
        if len(self.remaining_limitations) != len(
                set(self.remaining_limitations)):
            raise ValueError("Duplicate remaining review limitation")
        if self.expires_at is not None and self.expires_at <= self.decided_at:
            raise ValueError("PASS expiry must follow the decision")
        unresolved = {
            item.inquiry_id for item in self.closures
            if item.outcome in (ClosureOutcome.OPEN, ClosureOutcome.UNVERIFIED)}
        if self.decision is ReviewDisposition.PASS and unresolved:
            raise ValueError("PASS cannot leave open or unverified inquiries")
        if self.decision is ReviewDisposition.REVISE and not unresolved:
            raise ValueError("REVISE needs at least one open or unverified inquiry")
        return self


class EditorialReviewDecision(Contract):
    schema_version: Literal[1] = 1
    review_id: Identifier
    review_case_id: Identifier
    review_case_version_id: Identifier
    task_version_id: Identifier
    article_version_id: Identifier
    article_body_sha256: Digest
    spec_sha256: Digest
    reviewer_id: NonBlank
    author_ids: tuple[NonBlank, ...]
    producer_id: NonBlank
    exposure: ReviewExposure
    inquiries: tuple[ReviewerInquiry, ...]
    responses: tuple[AuthorResponseItem, ...]
    closures: tuple[IssueClosure, ...]
    decision: ReviewDisposition
    reviewed_scope: tuple[NonBlank, ...]
    decision_reason: NonBlank
    remaining_limitations: tuple[NonBlank, ...]
    source_advisor_output_version_id: Identifier
    source_teacher_output_version_id: Identifier
    source_prospective_output_version_id: Identifier
    execution_method: ExecutionMethod
    model_admission_id: Identifier | None
    model_configuration_id: Identifier | None
    operation_request_version_id: Identifier | None
    model_domains: tuple[NonBlank, ...]
    review_performed: Literal[True] = True
    author_self_approved: Literal[False] = False
    model_self_passed: Literal[False] = False
    publication_authorized: Literal[False] = False
    review_capability_certified: Literal[False] = False
    created_at: AwareDatetime


class ShortFormReviewCaseRecord(Contract):
    schema_version: Literal[2] = 2
    review_case_id: Identifier
    review_case_version_id: Identifier
    previous_version_id: Identifier | None
    state: ReviewCaseState
    article_route_version_id: Identifier
    task_version_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    initial_article_version_id: Identifier
    current_article_version_id: Identifier
    evidence_version_ids: tuple[Identifier, ...]
    reviewer_id: NonBlank
    author_ids: tuple[NonBlank, ...]
    producer_id: NonBlank
    reviewed_scope: tuple[NonBlank, ...]
    exposure: ReviewExposure
    inquiries: tuple[ReviewerInquiry, ...]
    responses: tuple[AuthorResponseItem, ...]
    content_review_required: Literal[True] = True
    publication_authorized: Literal[False] = False
    created_at: AwareDatetime
    updated_at: AwareDatetime


class ShortFormOpenReviewRequest(Contract):
    schema_version: Literal[2] = 2
    review_case_id: Identifier
    article_route_version_id: Identifier
    task_version_id: Identifier
    article_version_id: Identifier
    spec_sha256: Digest
    reviewer_id: NonBlank
    author_ids: tuple[NonBlank, ...]
    producer_id: NonBlank
    reviewed_scope: tuple[NonBlank, ...]
    exposure: ReviewExposure
    inquiries: tuple[ReviewerInquiry, ...] = ()
    evidence_version_ids: tuple[Identifier, ...]
    execution_method: Literal[ExecutionMethod.MANUAL] = ExecutionMethod.MANUAL
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("author", self.author_ids),
                ("reviewed scope", self.reviewed_scope),
                ("inquiry", [item.inquiry_id for item in self.inquiries]),
                ("evidence", self.evidence_version_ids)):
            if not values and name != "inquiry":
                raise ValueError(f"Short-form review needs {name}")
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate short-form review {name}")
        normalized_authors = {item.casefold() for item in self.author_ids}
        if self.reviewer_id.casefold() in normalized_authors:
            raise ValueError("Reviewer cannot be an author")
        if self.producer_id.casefold() == self.reviewer_id.casefold():
            raise ValueError("Reviewer cannot be the producer/checker signer")
        if self.producer_id.casefold() not in normalized_authors:
            raise ValueError("Producer must be one of the declared authors")
        if any(item.formed_at > self.created_at for item in self.inquiries):
            raise ValueError(
                "Reviewer inquiry cannot postdate the fixed review case")
        return self


class ShortFormReviewDecision(Contract):
    schema_version: Literal[2] = 2
    review_id: Identifier
    review_case_id: Identifier
    review_case_version_id: Identifier
    article_route_version_id: Identifier
    task_version_id: Identifier
    article_version_id: Identifier
    article_body_sha256: Digest
    spec_sha256: Digest
    reviewer_id: NonBlank
    author_ids: tuple[NonBlank, ...]
    producer_id: NonBlank
    exposure: ReviewExposure
    inquiries: tuple[ReviewerInquiry, ...]
    responses: tuple[AuthorResponseItem, ...]
    closures: tuple[IssueClosure, ...]
    decision: ReviewDisposition
    reviewed_scope: tuple[NonBlank, ...]
    decision_reason: NonBlank
    remaining_limitations: tuple[NonBlank, ...]
    evidence_version_ids: tuple[Identifier, ...]
    review_performed: Literal[True] = True
    author_self_approved: Literal[False] = False
    model_self_passed: Literal[False] = False
    publication_authorized: Literal[False] = False
    review_capability_certified: Literal[False] = False
    created_at: AwareDatetime


class ReviewDecisionResult(Contract):
    review_case_version_id: Identifier
    review_version_id: Identifier
    adoption_submission_version_id: Identifier
    adoption_decision_version_id: Identifier


class EditorialReviewError(ArchiveError):
    """Independent review failure; never generic reviewer certification."""


def _digest(value) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _version(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([prefix, identity]).encode()).hexdigest()[:32]


def _object(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([identity]).encode()).hexdigest()[:32]


class EditorialReviewController:
    def __init__(self, archive: Archive, rights: RightsGrant,
                 workflow: ResearchWorkflowController | None = None):
        if not isinstance(archive, Archive):
            raise TypeError("EditorialReviewController requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError("EditorialReviewController requires an internal journal grant")
        self.archive = archive
        self.rights = rights
        self.workflow = workflow or ResearchWorkflowController(archive, rights)
        self.research = ResearchRevisionController(archive, rights)
        self.prospective = ProspectiveController(archive, rights, workflow)
        self.adoption = AdoptionController(archive, rights)
        self.model_admission = ModelAdmissionController(archive, rights)
        self.routes = ArticleRouteController(archive, rights)

    @staticmethod
    def _current_version(stored: StoredVersion,
                         latest: StoredVersion | None, label: str) -> None:
        if latest is None or latest.submission.version_id != stored.submission.version_id:
            raise EditorialReviewError(f"Review {label} is not current")

    def _load_article(self, article_version_id: str, request_revision_id: str,
                      task_version_id: str,
                      source_record_ids: tuple[str, str, str],
                      output_version_ids: tuple[str, str, str]) -> tuple[
                          StoredVersion, bytes, str]:
        stored = self.archive.get(article_version_id)
        if stored.submission.kind is not ObjectKind.ARTICLE:
            raise EditorialReviewError("Reviewed item is not an Article")
        if stored.submission.representation is not Representation.FULL_BODY:
            raise EditorialReviewError("Review needs the actual reader draft body")
        if stored.body_retention_revoked:
            raise EditorialReviewError("Reader draft body was withdrawn")
        self._current_version(
            stored, self.archive.latest(stored.submission.object_id),
            "Article")
        body = self.archive.read_body(article_version_id)
        if not body:
            raise EditorialReviewError("Reader draft body is empty")
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise EditorialReviewError(
                "Reader draft is not valid UTF-8 for content review") from exc
        references = {
            item.target_version_id for item in stored.submission.references}
        required = {
            request_revision_id,
            task_version_id,
            *source_record_ids,
            *output_version_ids,
        }
        if not required <= references:
            raise EditorialReviewError(
                "Reader draft does not reference the exact research revision and B1/B2/C records")
        return stored, body, text

    def _load_research(self, *, dossier_id: str, revision_id: str,
                       theme_id: str, spec_sha256: str,
                       m10_id: str, m11_id: str, m12_id: str,
                       advisor_id: str, teacher_id: str,
                       prospective_id: str) -> tuple:
        snapshot_stored, snapshot = self.workflow.current_snapshot(dossier_id)
        if (snapshot.theme_id != theme_id
                or snapshot.spec_sha256 != spec_sha256
                or snapshot.revision_id != revision_id):
            raise EditorialReviewError(
                "Review case and dossier identity differ")
        revision = self.research.load_revision(revision_id)
        current = self.research.current_revision(theme_id)
        if current is None or current.revision_id != revision.revision_id:
            raise EditorialReviewError("Review research revision is stale")
        active = {item.step: item for item in snapshot.active_steps}
        expected = {
            ResearchStep.M10: (m10_id, StepDisposition.READY_FOR_NEXT,
                               StepDisposition.CANDIDATE,
                               StepDisposition.LIMITED),
            ResearchStep.M11: (m11_id, StepDisposition.READY_FOR_NEXT,
                               StepDisposition.LIMITED),
            ResearchStep.M12: (m12_id, StepDisposition.READY_FOR_NEXT,
                               StepDisposition.LIMITED),
        }
        records = {}
        for step, (record_id, *allowed) in expected.items():
            binding = active.get(step)
            if binding is None or binding.record_version_id != record_id:
                raise EditorialReviewError(
                    f"Review needs the current active {step.value}")
            record = self.workflow.load_step_record(record_id)
            if (record.dossier_id != dossier_id
                    or record.revision_id != revision_id
                    or record.spec_sha256 != spec_sha256
                    or record.disposition not in allowed):
                raise EditorialReviewError(
                    f"Review {step.value} record is not usable")
            records[step] = record
        advisor = self.prospective.advisors.load_advisor(advisor_id)
        teacher = self.prospective.teachers.load_teacher(teacher_id)
        prospective = self.prospective.load(prospective_id)
        if (advisor.dossier_id != dossier_id
                or teacher.dossier_id != dossier_id
                or prospective.dossier_id != dossier_id
                or advisor.revision_id != revision_id
                or teacher.revision_id != revision_id
                or prospective.revision_id != revision_id
                or advisor.spec_sha256 != spec_sha256
                or teacher.spec_sha256 != spec_sha256
                or prospective.spec_sha256 != spec_sha256):
            raise EditorialReviewError(
                "B1/B2/C outputs cross the review research basis")
        latest_outputs = (
            (_object("ADVISOR-OBJECT-", advisor.advisory_id),
             advisor_id, "B1"),
            (_object("TEACHER-OBJECT-", teacher.teaching_id),
             teacher_id, "B2"),
            (_object("CONDITIONAL-OBJECT-", prospective.prospective_id),
             prospective_id, "C"),
        )
        for object_id, expected_id, label in latest_outputs:
            latest = self.archive.latest(object_id)
            if (latest is None
                    or latest.submission.version_id != expected_id):
                raise EditorialReviewError(
                    f"Review uses a superseded {label} output")
        if records[ResearchStep.M10].artifact_version_ids != (advisor_id,):
            raise EditorialReviewError("M10 does not bind the selected B1 output")
        if records[ResearchStep.M11].artifact_version_ids != (teacher_id,):
            raise EditorialReviewError("M11 does not bind the selected B2 output")
        if records[ResearchStep.M12].artifact_version_ids != (prospective_id,):
            raise EditorialReviewError("M12 does not bind the selected C output")
        expected_claims = set(prospective.claim_version_ids)
        expected_evidence = set(prospective.evidence_version_ids)
        expected_assessments = set(
            prospective.claim_evidence_assessment_version_ids)
        expected_methods = set(prospective.method_use_version_ids)
        if not set(advisor.claim_version_ids) <= expected_claims:
            raise EditorialReviewError(
                "C output does not include the B1 Claim basis")
        if not set(teacher.claim_version_ids) <= expected_claims:
            raise EditorialReviewError(
                "C output does not include the B2 Claim basis")
        return (snapshot_stored, snapshot, revision, records, advisor, teacher,
                prospective, expected_claims, expected_evidence,
                expected_assessments, expected_methods)

    def _validate_claim_basis(self, *, request, revision) -> None:
        revision_inputs = set(revision.input_version_ids)
        for claim_id in request.claim_version_ids:
            stored = self.archive.get(claim_id)
            claim = self.prospective.evidence.load_claim(claim_id)
            if (stored.body_retention_revoked
                    or claim.theme_id != request.theme_id
                    or claim.spec_sha256 != request.spec_sha256
                    or claim_id not in revision_inputs):
                raise EditorialReviewError(
                    "Review Claim is unavailable or outside the exact revision")
            self._current_version(
                stored, self.archive.latest(stored.submission.object_id),
                "Claim")
        revision_evidence = set(revision.evidence_version_ids)
        for evidence_id in request.evidence_version_ids:
            stored = self.archive.get(evidence_id)
            evidence = self.prospective.evidence.load_evidence(evidence_id)
            if (stored.body_retention_revoked
                    or evidence.theme_id != request.theme_id
                    or evidence.spec_sha256 != request.spec_sha256
                    or evidence_id not in revision_inputs
                    or evidence_id not in revision_evidence):
                raise EditorialReviewError(
                    "Review Evidence is unavailable or outside the exact revision")
            self._current_version(
                stored, self.archive.latest(stored.submission.object_id),
                "Evidence")
        for assessment_id in request.claim_evidence_assessment_version_ids:
            stored = self.archive.get(assessment_id)
            assessment = self.prospective.evidence.load_assessment(
                assessment_id)
            if (stored.body_retention_revoked
                    or assessment.theme_id != request.theme_id
                    or assessment.spec_sha256 != request.spec_sha256
                    or assessment_id not in revision_inputs):
                raise EditorialReviewError(
                    "Review assessment is unavailable or outside the exact revision")
            self._current_version(
                stored, self.archive.latest(stored.submission.object_id),
                "W25 assessment")
        for method_id in request.method_use_version_ids:
            method = self.workflow.load_method(method_id)
            if (method.theme_id != request.theme_id
                    or method.spec_sha256 != request.spec_sha256):
                raise EditorialReviewError(
                    "Review MethodUse crosses theme or specification")

    def _ensure_case_research_current(self, case: ReviewCaseRecord) -> None:
        loaded = self._load_research(
            dossier_id=case.dossier_id,
            revision_id=case.revision_id,
            theme_id=case.theme_id,
            spec_sha256=case.spec_sha256,
            m10_id=case.source_m10_record_version_id,
            m11_id=case.source_m11_record_version_id,
            m12_id=case.source_m12_record_version_id,
            advisor_id=case.source_advisor_output_version_id,
            teacher_id=case.source_teacher_output_version_id,
            prospective_id=case.source_prospective_output_version_id)
        snapshot_stored = loaded[0]
        if (snapshot_stored.submission.version_id
                != case.previous_snapshot_version_id):
            raise EditorialReviewError(
                "Review case research snapshot changed after case opening")
        if (set(loaded[7]) != set(case.claim_version_ids)
                or set(loaded[8]) != set(case.evidence_version_ids)
                or set(loaded[9])
                != set(case.claim_evidence_assessment_version_ids)
                or set(loaded[10]) != set(case.method_use_version_ids)):
            raise EditorialReviewError(
                "Review case source basis changed after case opening")

    def _validate_reviewer_execution(self, request, advisor, teacher,
                                     prospective) -> None:
        if request.execution_method is ExecutionMethod.MANUAL:
            return
        if not self.model_admission.authorizes(
                request.model_admission_id,
                configuration_id=request.model_configuration_id,
                duty=ModelDuty.REVIEW, domains=request.model_domains,
                require_given_material=True, at=request.created_at):
            raise EditorialReviewError(
                "Review execution is outside a current admitted review scope")
        writer_configs = {
            item for item in (
                advisor.model_configuration_id,
                teacher.model_configuration_id,
                prospective.model_configuration_id) if item is not None}
        if request.model_configuration_id in writer_configs:
            raise EditorialReviewError(
                "Reviewer configuration must be separate from the writer configuration")
        operation = self.archive.get(request.operation_request_version_id)
        if operation.submission.kind is not ObjectKind.OPERATION_REQUEST:
            raise EditorialReviewError(
                "Review execution has no actual OperationRequest")
        operation_body = OperationRequest.model_validate_json(
            self.archive.read_body(request.operation_request_version_id))
        if (operation_body.kind is not OperationKind.MODEL
                or operation_body.step_id != "W31"
                or operation_body.material_use is not MaterialUse.MODEL_PROCESS):
            raise EditorialReviewError(
                "Review execution is not the authorized W31 model task")
        configuration = self.model_admission.load_configuration(
            request.model_configuration_id)
        if (operation_body.spec_sha256 != request.spec_sha256
                or operation_body.configuration_sha256
                != configuration.configuration_sha256):
            raise EditorialReviewError(
                "Review operation and configuration differ")
        required_inputs = {
            request.expected_snapshot_version_id,
            request.revision_id,
            request.task_version_id,
            request.article_version_id,
            request.source_m10_record_version_id,
            request.source_m11_record_version_id,
            request.source_m12_record_version_id,
            request.source_advisor_output_version_id,
            request.source_teacher_output_version_id,
            request.source_prospective_output_version_id,
            *request.claim_version_ids,
            *request.evidence_version_ids,
            *request.claim_evidence_assessment_version_ids,
            *request.method_use_version_ids,
        }
        if not required_inputs <= set(operation_body.input_version_ids):
            raise EditorialReviewError(
                "Review operation does not bind every reviewed input")
        receipt = OperationJournal(self.archive, self.rights).receipt(
            request.operation_request_version_id)
        if receipt is None or receipt.status is not OperationStatus.SUCCEEDED:
            raise EditorialReviewError(
                "Review execution has no successful operation receipt")
        if (request.created_at < receipt.ended_at
                or request.created_at < receipt.recorded_at
                or operation_body.created_at > receipt.started_at):
            raise EditorialReviewError(
                "Review case predates its actual model operation")

    def open_case(self, request: OpenReviewRequest) -> ReviewCaseRecord:
        if not isinstance(request, OpenReviewRequest):
            raise TypeError("open_case requires OpenReviewRequest")
        request = OpenReviewRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        source_records = (
            request.source_m10_record_version_id,
            request.source_m11_record_version_id,
            request.source_m12_record_version_id)
        article, article_body, article_text = self._load_article(
            request.article_version_id, request.revision_id,
            request.task_version_id, source_records,
            (request.source_advisor_output_version_id,
             request.source_teacher_output_version_id,
             request.source_prospective_output_version_id))
        if article.submission.spec_sha256 != request.spec_sha256:
            raise EditorialReviewError(
                "Reader draft uses another specification")
        snapshot_stored, snapshot, revision, records, advisor, teacher, prospective, claims, evidence, assessments, methods = self._load_research(
            dossier_id=request.dossier_id,
            revision_id=request.revision_id,
            theme_id=request.theme_id,
            spec_sha256=request.spec_sha256,
            m10_id=request.source_m10_record_version_id,
            m11_id=request.source_m11_record_version_id,
            m12_id=request.source_m12_record_version_id,
            advisor_id=request.source_advisor_output_version_id,
            teacher_id=request.source_teacher_output_version_id,
            prospective_id=request.source_prospective_output_version_id)
        if snapshot_stored.submission.version_id != request.expected_snapshot_version_id:
            raise WorkflowError("Review case uses a stale dossier snapshot")
        self._validate_claim_basis(
            request=request, revision=revision)
        if (set(request.claim_version_ids) != claims
                or set(request.evidence_version_ids) != evidence
                or set(request.claim_evidence_assessment_version_ids)
                != assessments
                or set(request.method_use_version_ids) != methods):
            raise EditorialReviewError(
                "Review basis must match the exact C/B1/B2 research basis")
        for inquiry in request.inquiries:
            if inquiry.quoted_text not in article_text:
                raise EditorialReviewError(
                    "Reviewer quotation does not occur in the actual reader draft")
            if not set(inquiry.claim_version_ids) <= claims:
                raise EditorialReviewError(
                    "Reviewer inquiry cites an undeclared Claim")
            if not set(inquiry.evidence_version_ids) <= evidence:
                raise EditorialReviewError(
                    "Reviewer inquiry cites undeclared Evidence")
            if not set(inquiry.method_use_version_ids) <= methods:
                raise EditorialReviewError(
                    "Reviewer inquiry cites an undeclared MethodUse")
        task = self.archive.get(request.task_version_id)
        if task.submission.kind is not ObjectKind.TASK:
            raise EditorialReviewError("Review task is not a Task version")
        if task.submission.spec_sha256 != request.spec_sha256:
            raise EditorialReviewError(
                "Review Task uses another specification")
        self._current_version(
            task, self.archive.latest(task.submission.object_id), "Task")
        self._validate_reviewer_execution(
            request, advisor, teacher, prospective)
        case_object = _object("REVIEW-CASE-OBJECT-", request.review_case_id)
        latest = self.archive.latest(case_object)
        if latest is not None:
            raise EditorialReviewError("Review case ID already exists")
        content = canonical(request.model_dump(mode="json")).encode()
        case_version = _version("REVIEW-CASE-", canonical([
            request.review_case_id, None, _digest(content)]))
        record = ReviewCaseRecord(
            review_case_id=request.review_case_id,
            review_case_version_id=case_version,
            previous_version_id=None, state=ReviewCaseState.OPEN,
            dossier_id=request.dossier_id,
            previous_snapshot_version_id=(
                request.expected_snapshot_version_id),
            revision_id=request.revision_id,
            theme_id=request.theme_id, spec_sha256=request.spec_sha256,
            task_version_id=request.task_version_id,
            initial_article_version_id=request.article_version_id,
            current_article_version_id=request.article_version_id,
            source_m10_record_version_id=(
                request.source_m10_record_version_id),
            source_m11_record_version_id=(
                request.source_m11_record_version_id),
            source_m12_record_version_id=(
                request.source_m12_record_version_id),
            source_advisor_output_version_id=(
                request.source_advisor_output_version_id),
            source_teacher_output_version_id=(
                request.source_teacher_output_version_id),
            source_prospective_output_version_id=(
                request.source_prospective_output_version_id),
            reviewer_id=request.reviewer_id,
            author_ids=request.author_ids,
            producer_id=request.producer_id,
            reviewed_scope=request.reviewed_scope,
            exposure=request.exposure, inquiries=request.inquiries,
            responses=(), claim_version_ids=request.claim_version_ids,
            evidence_version_ids=request.evidence_version_ids,
            claim_evidence_assessment_version_ids=(
                request.claim_evidence_assessment_version_ids),
            method_use_version_ids=request.method_use_version_ids,
            execution_method=request.execution_method,
            model_admission_id=request.model_admission_id,
            model_configuration_id=request.model_configuration_id,
            operation_request_version_id=(
                request.operation_request_version_id),
            model_domains=request.model_domains,
            created_at=request.created_at, updated_at=request.created_at)
        refs = [
            VersionReference(
                target_version_id=request.expected_snapshot_version_id,
                use=ReferenceUse.BASIS, locator="fixed dossier snapshot"),
            VersionReference(
                target_version_id=request.revision_id,
                use=ReferenceUse.BASIS, locator="exact research revision"),
            VersionReference(
                target_version_id=request.task_version_id,
                use=ReferenceUse.BASIS, locator="review task"),
            VersionReference(
                target_version_id=request.article_version_id,
                use=ReferenceUse.REVIEW_OF, locator="actual reader draft"),
            VersionReference(
                target_version_id=request.source_m10_record_version_id,
                use=ReferenceUse.BASIS, locator="B1 M10"),
            VersionReference(
                target_version_id=request.source_m11_record_version_id,
                use=ReferenceUse.BASIS, locator="B2 M11"),
            VersionReference(
                target_version_id=request.source_m12_record_version_id,
                use=ReferenceUse.BASIS, locator="C M12"),
            VersionReference(
                target_version_id=request.source_advisor_output_version_id,
                use=ReferenceUse.REVIEW_OF, locator="B1 review input"),
            VersionReference(
                target_version_id=request.source_teacher_output_version_id,
                use=ReferenceUse.REVIEW_OF, locator="B2 review input"),
            VersionReference(
                target_version_id=request.source_prospective_output_version_id,
                use=ReferenceUse.REVIEW_OF, locator="C review input"),
        ]
        submission = VersionSubmission(
            schema_version=2, object_id=case_object,
            version_id=case_version, parent_version_id=None,
            kind=ObjectKind.REVIEW_CASE,
            title=f"independent review case {request.review_case_id}",
            spec_sha256=request.spec_sha256,
            created_at=request.created_at, source_times=SourceTimes(),
            rights=self.rights, representation=Representation.FULL_BODY,
            references=tuple(refs))
        expected = {
            case_object: None,
            snapshot_stored.submission.object_id:
                snapshot_stored.submission.version_id,
            self.research._revision_object(request.theme_id):
                request.revision_id,
            article.submission.object_id: article.submission.version_id,
            task.submission.object_id: task.submission.version_id,
        }
        self.archive.append(
            submission, canonical(record.model_dump(mode="json")).encode(),
            expected_current=expected)
        return record

    def respond(self, request: AuthorResponseRequest) -> ReviewCaseRecord:
        if not isinstance(request, AuthorResponseRequest):
            raise TypeError("respond requires AuthorResponseRequest")
        request = AuthorResponseRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        latest, current = self.current_case(
            request.expected_current_case_version_id)
        if latest.submission.version_id != request.expected_current_case_version_id:
            raise Conflict("Review case changed before author response")
        if current.state is not ReviewCaseState.OPEN:
            raise Conflict("Author response is only valid for an open review case")
        self._ensure_case_research_current(current)
        if request.responder_id not in current.author_ids:
            raise EditorialReviewError(
                "Author response came from an undeclared author")
        if request.responder_id == current.reviewer_id:
            raise EditorialReviewError("Reviewer cannot author the response")
        if set(item.inquiry_id for item in request.responses) != {
                item.inquiry_id for item in current.inquiries}:
            raise EditorialReviewError(
                "Author response must address every reviewer inquiry exactly once")
        inquiry_times = {
            item.inquiry_id: item.formed_at for item in current.inquiries}
        if any(item.responded_at < inquiry_times[item.inquiry_id]
               for item in request.responses):
            raise EditorialReviewError(
                "Author response cannot predate the corresponding inquiry")
        if request.responded_at < current.created_at:
            raise EditorialReviewError(
                "Author response cannot predate the fixed review case")
        article, body, _ = self._load_article(
            request.article_version_id, current.revision_id,
            current.task_version_id,
            (current.source_m10_record_version_id,
             current.source_m11_record_version_id,
             current.source_m12_record_version_id),
            (current.source_advisor_output_version_id,
             current.source_teacher_output_version_id,
             current.source_prospective_output_version_id))
        if article.submission.spec_sha256 != current.spec_sha256:
            raise EditorialReviewError(
                "Revised reader draft uses another specification")
        history = self.archive.history(article.submission.object_id)
        if current.initial_article_version_id not in {
                item.submission.version_id for item in history}:
            raise EditorialReviewError(
                "Revised draft is unrelated to the fixed initial Article")
        for response in request.responses:
            for evidence_id in response.evidence_version_ids:
                self.archive.get(evidence_id)
        updated = current.model_copy(update={
            "review_case_version_id": _version("REVIEW-CASE-", canonical([
                current.review_case_id, current.review_case_version_id,
                _digest(request.model_dump(mode="json"))])),
            "previous_version_id": current.review_case_version_id,
            "state": ReviewCaseState.RESPONDED,
            "current_article_version_id": request.article_version_id,
            "responses": request.responses,
            "updated_at": request.responded_at,
        })
        refs = (
            VersionReference(
                target_version_id=current.review_case_version_id,
                use=ReferenceUse.BASIS, locator="open review case"),
            VersionReference(
                target_version_id=request.article_version_id,
                use=ReferenceUse.REVIEW_OF, locator="revised reader draft"),
            VersionReference(
                target_version_id=current.initial_article_version_id,
                use=ReferenceUse.REVIEW_OF, locator="initial reader draft"),
            *(
                VersionReference(
                    target_version_id=version_id,
                    use=ReferenceUse.SUPPORT,
                    locator=f"author response evidence {index}")
                for index, version_id in enumerate(sorted({
                    item for response in request.responses
                    for item in response.evidence_version_ids}))
            ),
        )
        submission = VersionSubmission(
            schema_version=2, object_id=latest.submission.object_id,
            version_id=updated.review_case_version_id,
            parent_version_id=current.review_case_version_id,
            kind=ObjectKind.REVIEW_CASE,
            title=f"independent review case {current.review_case_id}",
            spec_sha256=current.spec_sha256,
            created_at=request.responded_at, source_times=SourceTimes(),
            rights=self.rights, representation=Representation.FULL_BODY,
            references=refs)
        expected = {
            latest.submission.object_id: latest.submission.version_id,
            self.research._revision_object(current.theme_id):
                current.revision_id,
            article.submission.object_id: article.submission.version_id,
        }
        self.archive.append(
            submission, canonical(updated.model_dump(mode="json")).encode(),
            expected_current=expected)
        return updated

    def decide(self, request: FinalReviewRequest) -> ReviewDecisionResult:
        if not isinstance(request, FinalReviewRequest):
            raise TypeError("decide requires FinalReviewRequest")
        request = FinalReviewRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        case_stored, case = self.current_case(
            request.expected_current_case_version_id)
        if case_stored.submission.version_id != request.review_case_version_id:
            raise Conflict("Final review prepared from a stale case version")
        if case.state is not ReviewCaseState.RESPONDED:
            raise Conflict("Final review needs a recorded author response")
        self._ensure_case_research_current(case)
        if request.reviewer_id != case.reviewer_id:
            raise EditorialReviewError(
                "Only the fixed reviewer can issue this decision")
        if request.article_version_id != case.current_article_version_id:
            raise EditorialReviewError(
                "Final review does not bind the responded Article version")
        if not set(request.reviewed_scope) <= set(case.reviewed_scope):
            raise EditorialReviewError(
                "Final decision scope exceeds the fixed review scope")
        if {item.inquiry_id for item in request.closures} != {
                item.inquiry_id for item in case.inquiries}:
            raise EditorialReviewError(
                "Every reviewer inquiry needs exactly one final closure")
        inquiry_by_id = {
            item.inquiry_id: item for item in case.inquiries}
        closure_by_id = {
            item.inquiry_id: item for item in request.closures}
        if any(item.checked_at < case.updated_at
               for item in request.closures):
            raise EditorialReviewError(
                "Inquiry closure cannot predate the author response")
        if request.decided_at < max(
                [case.updated_at]
                + [item.checked_at for item in request.closures]):
            raise EditorialReviewError(
                "Final decision cannot predate its response or closure checks")
        if request.decision is ReviewDisposition.BLOCK:
            if not any(
                    inquiry_by_id[item.inquiry_id].severity
                    is IssueSeverity.CRITICAL
                    and item.outcome in (
                        ClosureOutcome.OPEN, ClosureOutcome.UNVERIFIED)
                    for item in request.closures):
                raise EditorialReviewError(
                    "BLOCK needs at least one unresolved critical inquiry")
        for closure in request.closures:
            for version_id in closure.basis_version_ids:
                self.archive.get(version_id)
        article, body, _ = self._load_article(
            request.article_version_id, case.revision_id,
            case.task_version_id,
            (case.source_m10_record_version_id,
             case.source_m11_record_version_id,
             case.source_m12_record_version_id),
            (case.source_advisor_output_version_id,
             case.source_teacher_output_version_id,
             case.source_prospective_output_version_id))
        decision = EditorialReviewDecision(
            review_id=request.review_id, review_case_id=case.review_case_id,
            review_case_version_id=case.review_case_version_id,
            task_version_id=case.task_version_id,
            article_version_id=request.article_version_id,
            article_body_sha256=article.body_sha256,
            spec_sha256=case.spec_sha256,
            reviewer_id=case.reviewer_id, author_ids=case.author_ids,
            producer_id=case.producer_id, exposure=case.exposure,
            inquiries=case.inquiries, responses=case.responses,
            closures=request.closures, decision=request.decision,
            reviewed_scope=request.reviewed_scope,
            decision_reason=request.decision_reason,
            remaining_limitations=request.remaining_limitations,
            source_advisor_output_version_id=(
                case.source_advisor_output_version_id),
            source_teacher_output_version_id=(
                case.source_teacher_output_version_id),
            source_prospective_output_version_id=(
                case.source_prospective_output_version_id),
            execution_method=case.execution_method,
            model_admission_id=case.model_admission_id,
            model_configuration_id=case.model_configuration_id,
            operation_request_version_id=case.operation_request_version_id,
            model_domains=case.model_domains,
            created_at=request.decided_at)
        review_object = _object("EDITORIAL-REVIEW-", request.review_id)
        review_refs = (
            VersionReference(
                target_version_id=case.task_version_id,
                use=ReferenceUse.BASIS, locator="review task"),
            VersionReference(
                target_version_id=request.article_version_id,
                use=ReferenceUse.REVIEW_OF, locator="final reader draft"),
            VersionReference(
                target_version_id=case.review_case_version_id,
                use=ReferenceUse.BASIS, locator="responded review case"),
            VersionReference(
                target_version_id=case.source_m10_record_version_id,
                use=ReferenceUse.BASIS, locator="B1 M10"),
            VersionReference(
                target_version_id=case.source_m11_record_version_id,
                use=ReferenceUse.BASIS, locator="B2 M11"),
            VersionReference(
                target_version_id=case.source_m12_record_version_id,
                use=ReferenceUse.BASIS, locator="C M12"),
            VersionReference(
                target_version_id=case.source_advisor_output_version_id,
                use=ReferenceUse.REVIEW_OF, locator="B1 content"),
            VersionReference(
                target_version_id=case.source_teacher_output_version_id,
                use=ReferenceUse.REVIEW_OF, locator="B2 content"),
            VersionReference(
                target_version_id=case.source_prospective_output_version_id,
                use=ReferenceUse.REVIEW_OF, locator="C content"),
            *(
                VersionReference(
                    target_version_id=version_id,
                    use=ReferenceUse.SUPPORT,
                    locator=f"issue closure evidence {index}")
                for index, version_id in enumerate(sorted({
                    item for closure in request.closures
                    for item in closure.basis_version_ids}))
            ),
        )
        review_submission = VersionSubmission(
            schema_version=2, object_id=review_object,
            version_id=request.review_id, parent_version_id=None,
            kind=ObjectKind.REVIEW,
            title=f"independent content review {request.review_id}",
            spec_sha256=case.spec_sha256,
            created_at=request.decided_at, source_times=SourceTimes(),
            rights=self.rights, representation=Representation.FULL_BODY,
            references=review_refs,
            review_coverage=(ReviewCoverage(
                task_version_id=case.task_version_id,
                subject_version_id=request.article_version_id,
                reviewed_scope=request.reviewed_scope),))
        expected_review = {
            review_object: None,
            case_stored.submission.object_id: case.review_case_version_id,
            article.submission.object_id: article.submission.version_id,
            self.research._revision_object(case.theme_id): case.revision_id,
        }
        try:
            self.archive.append(
                review_submission,
                canonical(decision.model_dump(mode="json")).encode(),
                expected_current=expected_review)
            review_stored = self.archive.get(request.review_id)
        except Conflict:
            review_stored = self.archive.get(request.review_id)
            expected_hash = hashlib.sha256(
                canonical(decision.model_dump(mode="json")).encode()).hexdigest()
            if (review_stored.submission.kind is not ObjectKind.REVIEW
                    or review_stored.body_sha256 != expected_hash):
                raise
        state = {
            ReviewDisposition.PASS: StepState.READY,
            ReviewDisposition.REVISE: StepState.RETURN,
            ReviewDisposition.BLOCK: StepState.BLOCKED,
        }[request.decision]
        claimed_scope = (
            request.reviewed_scope
            if request.decision is ReviewDisposition.PASS else ())
        submission_id = _version("W31-REVIEW-SUBMISSION-", canonical([
            request.review_id, request.article_version_id]))
        submission_record = StepSubmission(
            schema_version=2, submission_id=submission_id,
            work_id="W31",
            step_id="CONTENT_REVIEW_" + case.review_case_id,
            spec_sha256=case.spec_sha256,
            task_version_id=case.task_version_id,
            subject_version_id=request.article_version_id,
            producer_id=case.producer_id, proposed_state=state,
            claimed_scope=claimed_scope,
            input_version_ids=(
                request.article_version_id,
                case.source_m10_record_version_id,
                case.source_m11_record_version_id,
                case.source_m12_record_version_id,
            ),
            evidence_version_ids=(request.review_id,),
            gaps=tuple(request.remaining_limitations),
            created_at=request.decided_at)
        try:
            self.archive.get(submission_id)
        except MissingVersion:
            try:
                self.adoption.submit(submission_record)
            except (Conflict, ValueError):
                self.archive.get(submission_id)
        decision_id = _version("W31-REVIEW-DECISION-", canonical([
            request.review_id, request.article_version_id]))
        try:
            self.adoption.load(decision_id)
        except MissingVersion:
            try:
                self.adoption.decide(DecisionRequest(
                    decision_id=decision_id,
                    submission_version_id=submission_id,
                    state=state,
                    checker_id=case.reviewer_id, checker_role=CheckerRole.L5,
                    review_version_id=request.review_id,
                    allowed_scope=claimed_scope,
                    reason=request.decision_reason,
                    decided_at=request.decided_at,
                    expires_at=(
                        request.expires_at
                        if request.decision is ReviewDisposition.PASS else None)))
            except (Conflict, ValueError):
                self.adoption.load(decision_id)
        return ReviewDecisionResult(
            review_case_version_id=case.review_case_version_id,
            review_version_id=request.review_id,
            adoption_submission_version_id=submission_id,
            adoption_decision_version_id=decision_id)

    def current_case(
            self, version_id: str
    ) -> tuple[StoredVersion, ReviewCaseRecord | ShortFormReviewCaseRecord]:
        stored = self.archive.get(version_id)
        if stored.submission.kind is not ObjectKind.REVIEW_CASE:
            raise EditorialReviewError("Requested version is not a ReviewCase")
        raw = self.archive.read_body(version_id)
        payload = json.loads(raw)
        if payload.get("article_route_version_id") is not None:
            record = ShortFormReviewCaseRecord.model_validate_json(raw)
        else:
            record = ReviewCaseRecord.model_validate_json(raw)
        latest = self.archive.latest(stored.submission.object_id)
        if (latest is None or latest.submission.version_id
                != stored.submission.version_id
                or record.review_case_version_id
                != stored.submission.version_id
                or stored.submission.spec_sha256 != record.spec_sha256
                or stored.submission.created_at != record.updated_at):
            raise EditorialReviewError("Review case identity/version mismatch")
        return stored, record

    def load_review(
            self, review_version_id: str
    ) -> EditorialReviewDecision | ShortFormReviewDecision:
        stored = self.archive.get(review_version_id)
        if stored.submission.kind is not ObjectKind.REVIEW:
            raise EditorialReviewError("Requested version is not a Review")
        raw = self.archive.read_body(review_version_id)
        payload = json.loads(raw)
        if payload.get("article_route_version_id") is not None:
            review = ShortFormReviewDecision.model_validate_json(raw)
        else:
            review = EditorialReviewDecision.model_validate_json(raw)
        if (review.review_id != review_version_id
                or stored.submission.spec_sha256 != review.spec_sha256
                or stored.submission.created_at != review.created_at):
            raise EditorialReviewError("Review identity mismatch")
        return review


class ShortFormReviewController:
    """Independent review for routed source-selection and update/correction."""

    def __init__(self, archive: Archive, rights: RightsGrant,
                 routes: ArticleRouteController | None = None,
                 adoption: AdoptionController | None = None):
        if not isinstance(archive, Archive):
            raise TypeError(
                "ShortFormReviewController requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError(
                "ShortFormReviewController requires an internal journal grant")
        self.archive = archive
        self.rights = rights
        self.routes = routes or ArticleRouteController(archive, rights)
        self.adoption = adoption or AdoptionController(archive, rights)

    def open_case(
            self, request: ShortFormOpenReviewRequest
    ) -> ShortFormReviewCaseRecord:
        if not isinstance(request, ShortFormOpenReviewRequest):
            raise TypeError("open_case requires ShortFormOpenReviewRequest")
        request = ShortFormOpenReviewRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        route = self.routes.require_current(
            request.article_route_version_id,
            request.article_version_id)
        if route.article_version_id != request.article_version_id:
            raise EditorialReviewError(
                "Short-form review must open on the routed initial Article")
        if (route.task_version_id != request.task_version_id
                or route.spec_sha256 != request.spec_sha256
                or set(route.evidence_version_ids)
                != set(request.evidence_version_ids)):
            raise EditorialReviewError(
                "Short-form review crosses its Article route")
        task = self.archive.get(request.task_version_id)
        if (task.submission.kind is not ObjectKind.TASK
                or task.submission.spec_sha256 != request.spec_sha256):
            raise EditorialReviewError(
                "Short-form review task is invalid")
        latest = self.archive.latest(task.submission.object_id)
        if latest is None or latest.submission.version_id != (
                task.submission.version_id):
            raise EditorialReviewError(
                "Short-form review task is stale")
        article = self.archive.get(request.article_version_id)
        body = self.archive.read_body(request.article_version_id)
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise EditorialReviewError(
                "Short-form reader draft is not UTF-8") from exc
        for inquiry in request.inquiries:
            if inquiry.quoted_text not in text:
                raise EditorialReviewError(
                    "Reviewer quotation does not occur in the routed Article")
            if not set(inquiry.evidence_version_ids) <= set(
                    route.evidence_version_ids):
                raise EditorialReviewError(
                    "Reviewer inquiry cites undeclared route Evidence")
            if inquiry.claim_version_ids or inquiry.method_use_version_ids:
                raise EditorialReviewError(
                    "Short-form inquiry cannot pretend to use deep Claim/MethodUse IDs")
        case_object = _object(
            "REVIEW-CASE-OBJECT-", request.review_case_id)
        if self.archive.latest(case_object) is not None:
            raise EditorialReviewError("Review case ID already exists")
        content = canonical(request.model_dump(mode="json")).encode()
        case_version = _version("REVIEW-CASE-", canonical([
            request.review_case_id, None, _digest(content)]))
        record = ShortFormReviewCaseRecord(
            review_case_id=request.review_case_id,
            review_case_version_id=case_version,
            previous_version_id=None, state=ReviewCaseState.OPEN,
            article_route_version_id=request.article_route_version_id,
            task_version_id=request.task_version_id,
            theme_id=route.theme_id, spec_sha256=request.spec_sha256,
            initial_article_version_id=request.article_version_id,
            current_article_version_id=request.article_version_id,
            evidence_version_ids=request.evidence_version_ids,
            reviewer_id=request.reviewer_id,
            author_ids=request.author_ids,
            producer_id=request.producer_id,
            reviewed_scope=request.reviewed_scope,
            exposure=request.exposure,
            inquiries=request.inquiries, responses=(),
            created_at=request.created_at, updated_at=request.created_at)
        refs = (
            VersionReference(
                target_version_id=request.article_route_version_id,
                use=ReferenceUse.BASIS, locator="exact short-form route"),
            VersionReference(
                target_version_id=request.task_version_id,
                use=ReferenceUse.BASIS, locator="review task"),
            VersionReference(
                target_version_id=request.article_version_id,
                use=ReferenceUse.REVIEW_OF, locator="actual routed draft"),
            *(
                VersionReference(
                    target_version_id=evidence_id,
                    use=ReferenceUse.SUPPORT,
                    locator=f"short-form review Evidence {index}")
                for index, evidence_id in enumerate(
                    request.evidence_version_ids)
            ),
        )
        submission = VersionSubmission(
            schema_version=2, object_id=case_object,
            version_id=case_version, parent_version_id=None,
            kind=ObjectKind.REVIEW_CASE,
            title=f"short-form review case {request.review_case_id}",
            spec_sha256=request.spec_sha256,
            created_at=request.created_at, source_times=SourceTimes(),
            rights=self.rights, representation=Representation.FULL_BODY,
            references=refs)
        expected = {
            case_object: None,
            article.submission.object_id: article.submission.version_id,
            task.submission.object_id: task.submission.version_id,
            self.archive.get(
                request.article_route_version_id
            ).submission.object_id: request.article_route_version_id,
        }
        self.archive.append(
            submission, canonical(record.model_dump(mode="json")).encode(),
            expected_current=expected)
        return record

    def respond(
            self, request: AuthorResponseRequest) -> ShortFormReviewCaseRecord:
        if not isinstance(request, AuthorResponseRequest):
            raise TypeError("respond requires AuthorResponseRequest")
        request = AuthorResponseRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        latest, current = EditorialReviewController(
            self.archive, self.rights).current_case(
                request.expected_current_case_version_id)
        if not isinstance(current, ShortFormReviewCaseRecord):
            raise EditorialReviewError(
                "Short-form response target is not a routed review case")
        if latest.submission.version_id != (
                request.expected_current_case_version_id):
            raise Conflict("Review case changed before author response")
        if current.state is not ReviewCaseState.OPEN:
            raise Conflict(
                "Author response is only valid for an open routed case")
        self.routes.require_current(
            current.article_route_version_id, request.article_version_id)
        if request.responder_id not in current.author_ids:
            raise EditorialReviewError(
                "Author response came from an undeclared author")
        if request.responder_id == current.reviewer_id:
            raise EditorialReviewError(
                "Reviewer cannot author the response")
        if {item.inquiry_id for item in request.responses} != {
                item.inquiry_id for item in current.inquiries}:
            raise EditorialReviewError(
                "Author response must address every routed inquiry exactly once")
        inquiry_times = {
            item.inquiry_id: item.formed_at for item in current.inquiries}
        if any(item.responded_at < inquiry_times[item.inquiry_id]
               for item in request.responses):
            raise EditorialReviewError(
                "Author response cannot predate the corresponding inquiry")
        if request.responded_at < current.created_at:
            raise EditorialReviewError(
                "Author response cannot predate the fixed routed case")
        article = self.archive.get(request.article_version_id)
        history = self.archive.history(article.submission.object_id)
        if current.initial_article_version_id not in {
                item.submission.version_id for item in history}:
            raise EditorialReviewError(
                "Revised draft is unrelated to the routed initial Article")
        updated = current.model_copy(update={
            "review_case_version_id": _version("REVIEW-CASE-", canonical([
                current.review_case_id, current.review_case_version_id,
                _digest(request.model_dump(mode="json"))])),
            "previous_version_id": current.review_case_version_id,
            "state": ReviewCaseState.RESPONDED,
            "current_article_version_id": request.article_version_id,
            "responses": request.responses,
            "updated_at": request.responded_at,
        })
        refs = (
            VersionReference(
                target_version_id=current.review_case_version_id,
                use=ReferenceUse.BASIS, locator="open routed review case"),
            VersionReference(
                target_version_id=request.article_version_id,
                use=ReferenceUse.REVIEW_OF, locator="revised routed draft"),
            VersionReference(
                target_version_id=current.initial_article_version_id,
                use=ReferenceUse.REVIEW_OF, locator="initial routed draft"),
        )
        submission = VersionSubmission(
            schema_version=2, object_id=latest.submission.object_id,
            version_id=updated.review_case_version_id,
            parent_version_id=current.review_case_version_id,
            kind=ObjectKind.REVIEW_CASE,
            title=f"short-form review case {current.review_case_id}",
            spec_sha256=current.spec_sha256,
            created_at=request.responded_at, source_times=SourceTimes(),
            rights=self.rights, representation=Representation.FULL_BODY,
            references=refs)
        self.archive.append(
            submission,
            canonical(updated.model_dump(mode="json")).encode(),
            expected_current={
                latest.submission.object_id:
                    latest.submission.version_id,
                article.submission.object_id:
                    article.submission.version_id,
            })
        return updated

    def decide(
            self, request: FinalReviewRequest) -> ReviewDecisionResult:
        if not isinstance(request, FinalReviewRequest):
            raise TypeError("decide requires FinalReviewRequest")
        request = FinalReviewRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        reviewer = EditorialReviewController(self.archive, self.rights)
        case_stored, case = reviewer.current_case(
            request.expected_current_case_version_id)
        if not isinstance(case, ShortFormReviewCaseRecord):
            raise EditorialReviewError(
                "Short-form decision target is not a routed case")
        if case_stored.submission.version_id != (
                request.review_case_version_id):
            raise Conflict("Final review prepared from a stale routed case")
        if case.state is not ReviewCaseState.RESPONDED:
            raise Conflict("Final review needs a recorded author response")
        self.routes.require_current(
            case.article_route_version_id, request.article_version_id)
        if request.reviewer_id != case.reviewer_id:
            raise EditorialReviewError(
                "Only the fixed reviewer can issue this routed decision")
        if request.article_version_id != case.current_article_version_id:
            raise EditorialReviewError(
                "Final review does not bind the responded routed Article")
        if not set(request.reviewed_scope) <= set(case.reviewed_scope):
            raise EditorialReviewError(
                "Final decision scope exceeds the fixed routed scope")
        if {item.inquiry_id for item in request.closures} != {
                item.inquiry_id for item in case.inquiries}:
            raise EditorialReviewError(
                "Every routed inquiry needs exactly one final closure")
        inquiry_by_id = {
            item.inquiry_id: item for item in case.inquiries}
        if any(item.checked_at < case.updated_at
               for item in request.closures):
            raise EditorialReviewError(
                "Routed closure cannot predate the author response")
        if request.decided_at < max(
                [case.updated_at]
                + [item.checked_at for item in request.closures]):
            raise EditorialReviewError(
                "Routed decision cannot predate its response or closures")
        if request.decision is ReviewDisposition.BLOCK and not any(
                inquiry_by_id[item.inquiry_id].severity
                is IssueSeverity.CRITICAL
                and item.outcome in (
                    ClosureOutcome.OPEN, ClosureOutcome.UNVERIFIED)
                for item in request.closures):
            raise EditorialReviewError(
                "BLOCK needs an unresolved critical routed inquiry")
        for closure in request.closures:
            for version_id in closure.basis_version_ids:
                self.archive.get(version_id)
        article = self.archive.get(request.article_version_id)
        decision = ShortFormReviewDecision(
            review_id=request.review_id,
            review_case_id=case.review_case_id,
            review_case_version_id=case.review_case_version_id,
            article_route_version_id=case.article_route_version_id,
            task_version_id=case.task_version_id,
            article_version_id=request.article_version_id,
            article_body_sha256=article.body_sha256,
            spec_sha256=case.spec_sha256,
            reviewer_id=case.reviewer_id,
            author_ids=case.author_ids,
            producer_id=case.producer_id,
            exposure=case.exposure,
            inquiries=case.inquiries, responses=case.responses,
            closures=request.closures, decision=request.decision,
            reviewed_scope=request.reviewed_scope,
            decision_reason=request.decision_reason,
            remaining_limitations=request.remaining_limitations,
            evidence_version_ids=case.evidence_version_ids,
            created_at=request.decided_at)
        review_object = _object(
            "EDITORIAL-REVIEW-", request.review_id)
        refs = (
            VersionReference(
                target_version_id=case.article_route_version_id,
                use=ReferenceUse.BASIS, locator="routed review basis"),
            VersionReference(
                target_version_id=case.task_version_id,
                use=ReferenceUse.BASIS, locator="review task"),
            VersionReference(
                target_version_id=request.article_version_id,
                use=ReferenceUse.REVIEW_OF, locator="final routed draft"),
            VersionReference(
                target_version_id=case.review_case_version_id,
                use=ReferenceUse.BASIS, locator="responded routed case"),
            *(
                VersionReference(
                    target_version_id=evidence_id,
                    use=ReferenceUse.SUPPORT,
                    locator=f"routed review Evidence {index}")
                for index, evidence_id in enumerate(
                    case.evidence_version_ids)
            ),
            *(
                VersionReference(
                    target_version_id=version_id,
                    use=ReferenceUse.SUPPORT,
                    locator=f"routed issue closure {index}")
                for index, version_id in enumerate(sorted({
                    item for closure in request.closures
                    for item in closure.basis_version_ids}))
            ),
        )
        submission = VersionSubmission(
            schema_version=2, object_id=review_object,
            version_id=request.review_id, parent_version_id=None,
            kind=ObjectKind.REVIEW,
            title=f"independent routed content review {request.review_id}",
            spec_sha256=case.spec_sha256,
            created_at=request.decided_at, source_times=SourceTimes(),
            rights=self.rights, representation=Representation.FULL_BODY,
            references=refs,
            review_coverage=(ReviewCoverage(
                task_version_id=case.task_version_id,
                subject_version_id=request.article_version_id,
                reviewed_scope=request.reviewed_scope),))
        self.archive.append(
            submission,
            canonical(decision.model_dump(mode="json")).encode(),
            expected_current={
                review_object: None,
                case_stored.submission.object_id:
                    case.review_case_version_id,
                article.submission.object_id:
                    article.submission.version_id,
            })
        state = {
            ReviewDisposition.PASS: StepState.READY,
            ReviewDisposition.REVISE: StepState.RETURN,
            ReviewDisposition.BLOCK: StepState.BLOCKED,
        }[request.decision]
        claimed_scope = (
            request.reviewed_scope
            if request.decision is ReviewDisposition.PASS else ())
        submission_id = _version(
            "W37-REVIEW-SUBMISSION-", canonical([
                request.review_id, request.article_version_id]))
        self.adoption.submit(StepSubmission(
            schema_version=2, submission_id=submission_id,
            work_id="W37",
            step_id="CONTENT_REVIEW_" + case.review_case_id,
            spec_sha256=case.spec_sha256,
            task_version_id=case.task_version_id,
            subject_version_id=request.article_version_id,
            producer_id=case.producer_id, proposed_state=state,
            claimed_scope=claimed_scope,
            input_version_ids=(
                request.article_version_id,
                case.article_route_version_id,
                *case.evidence_version_ids,
            ),
            evidence_version_ids=(request.review_id,),
            gaps=tuple(request.remaining_limitations),
            created_at=request.decided_at))
        decision_id = _version(
            "W37-REVIEW-DECISION-", canonical([
                request.review_id, request.article_version_id]))
        self.adoption.decide(DecisionRequest(
            decision_id=decision_id,
            submission_version_id=submission_id,
            state=state,
            checker_id=case.reviewer_id, checker_role=CheckerRole.L5,
            review_version_id=request.review_id,
            allowed_scope=claimed_scope,
            reason=request.decision_reason,
            decided_at=request.decided_at,
            expires_at=(
                request.expires_at
                if request.decision is ReviewDisposition.PASS else None)))
        return ReviewDecisionResult(
            review_case_version_id=case.review_case_version_id,
            review_version_id=request.review_id,
            adoption_submission_version_id=submission_id,
            adoption_decision_version_id=decision_id)
