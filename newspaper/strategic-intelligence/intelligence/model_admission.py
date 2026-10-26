"""W19 model/task configuration identity and limited-use admission records.

This module validates archived evidence and scope. It does not call a model,
judge semantic quality, authenticate a vendor, or grant publication/delivery
permission.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib
from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from .archive import Archive, ArchiveError, canonical
from .contracts import (Contract, Digest, Identifier, NonBlank, ObjectKind, ReferenceUse,
                        Representation, RightsGrant, SourceTimes, StoredVersion,
                        VersionReference, VersionSubmission)
from .operations import OperationJournal, OperationRequest, OperationStatus


class ModelDuty(str, Enum):
    FACT_EXTRACTION = "FACT_EXTRACTION"
    EXPLANATION = "EXPLANATION"
    ADVISER = "ADVISER"
    TEACHER = "TEACHER"
    REVIEW = "REVIEW"
    EDIT = "EDIT"


class ValidationKind(str, Enum):
    GIVEN_MATERIAL = "GIVEN_MATERIAL"
    REAL_RETRIEVAL = "REAL_RETRIEVAL"
    CONSTRAINT_GAIN = "CONSTRAINT_GAIN"


class ValidationOutcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


class AdmissionStatus(str, Enum):
    APPROVED = "APPROVED"
    CONTROLLED_TRIAL = "CONTROLLED_TRIAL"
    LIMITED = "LIMITED"


class ToolConfiguration(Contract):
    tool_id: Identifier
    tool_version: NonBlank
    settings_sha256: Digest


class ModelTaskConfiguration(Contract):
    schema_version: Literal[1] = 1
    configuration_id: Identifier
    provider_id: NonBlank
    model_id: NonBlank
    model_version: NonBlank | None = None
    spec_sha256: Digest
    task_instruction_sha256: Digest
    prompt_sha256: Digest
    context_policy_sha256: Digest
    generation_settings_sha256: Digest
    method_version: NonBlank
    tools: tuple[ToolConfiguration, ...] = ()
    duties: tuple[ModelDuty, ...]
    domains: tuple[NonBlank, ...]
    material_forms: tuple[NonBlank, ...]
    unknown_fields: tuple[NonBlank, ...] = ()
    configuration_sha256: Digest | None = None
    created_at: AwareDatetime

    @staticmethod
    def _fingerprint_payload(values: dict) -> bytes:
        payload = dict(values)
        payload.pop("configuration_sha256", None)
        return canonical(payload).encode()

    @model_validator(mode="after")
    def coherent(self) -> Self:
        groups = (
            ("duty", self.duties),
            ("domain", self.domains),
            ("material form", self.material_forms),
        )
        for name, values in groups:
            if not values or len(values) != len(set(values)):
                raise ValueError(f"Model configuration {name} list must be nonempty and unique")
        if len(self.unknown_fields) != len(set(self.unknown_fields)):
            raise ValueError("Duplicate unknown model configuration field")
        tool_keys = [
            (item.tool_id, item.tool_version, item.settings_sha256)
            for item in self.tools
        ]
        if len(tool_keys) != len(set(tool_keys)):
            raise ValueError("Duplicate model tool configuration")
        if self.model_version is None and "model_version" not in self.unknown_fields:
            raise ValueError("Unknown model version must be recorded explicitly")
        expected = hashlib.sha256(self._fingerprint_payload(
            self.model_dump(mode="json"))).hexdigest()
        if self.configuration_sha256 is not None and self.configuration_sha256 != expected:
            raise ValueError("Model configuration fingerprint mismatch")
        return self

    def fingerprint(self) -> str:
        return hashlib.sha256(self._fingerprint_payload(
            self.model_dump(mode="json"))).hexdigest()


class ValidationAttempt(Contract):
    attempt_id: Identifier
    artifact_version_id: Identifier
    outcome: ValidationOutcome
    human_help_version_ids: tuple[Identifier, ...] = ()
    limitations: tuple[NonBlank, ...] = ()

    @model_validator(mode="after")
    def unique_refs(self) -> Self:
        if len(self.human_help_version_ids) != len(set(self.human_help_version_ids)):
            raise ValueError("Duplicate human-help version")
        return self


class ModelValidation(Contract):
    schema_version: Literal[1] = 1
    validation_id: Identifier
    configuration_id: Identifier
    spec_sha256: Digest
    kind: ValidationKind
    duty: ModelDuty
    domains: tuple[NonBlank, ...]
    case_version_ids: tuple[Identifier, ...] = ()
    baseline_artifact_version_id: Identifier | None = None
    constrained_artifact_version_id: Identifier | None = None
    operation_receipt_ids: tuple[Identifier, ...] = ()
    review_version_id: Identifier
    primary_outcome: ValidationOutcome
    attempts: tuple[ValidationAttempt, ...]
    unverified_scope: tuple[NonBlank, ...] = ()
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("domain", self.domains),
                ("case", self.case_version_ids),
                ("operation receipt", self.operation_receipt_ids),
                ("attempt", [item.attempt_id for item in self.attempts])):
            if (not values and name not in ("case", "operation receipt")) or (
                    len(values) != len(set(values))):
                raise ValueError(f"Invalid model validation {name} list")
        if self.kind is ValidationKind.GIVEN_MATERIAL and not self.case_version_ids:
            raise ValueError("Given-material validation needs fixed case versions")
        if self.kind is ValidationKind.REAL_RETRIEVAL and not self.operation_receipt_ids:
            raise ValueError("Real-retrieval validation needs operation receipts")
        if self.kind is ValidationKind.CONSTRAINT_GAIN:
            if (not self.baseline_artifact_version_id
                    or not self.constrained_artifact_version_id
                    or self.baseline_artifact_version_id
                    == self.constrained_artifact_version_id):
                raise ValueError("Constraint gain needs two different artifact versions")
        if self.primary_outcome is ValidationOutcome.PASS and not any(
                item.outcome is ValidationOutcome.PASS for item in self.attempts):
            raise ValueError("A passing validation needs at least one passing attempt")
        return self


class ModelUseAdmission(Contract):
    schema_version: Literal[1] = 1
    admission_id: Identifier
    configuration_id: Identifier
    spec_sha256: Digest
    duties: tuple[ModelDuty, ...]
    domains: tuple[NonBlank, ...]
    validation_ids: tuple[Identifier, ...]
    known_failure_ids: tuple[Identifier, ...] = ()
    allow_given_material: bool
    allow_real_retrieval: bool
    constraint_gain_verified: bool
    manual_review_required: bool
    restrictions: tuple[NonBlank, ...]
    review_version_id: Identifier
    status: AdmissionStatus
    valid_from: AwareDatetime
    valid_until: AwareDatetime
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.valid_until <= self.valid_from:
            raise ValueError("Model-use admission must end after it begins")
        for name, values in (
                ("duty", self.duties),
                ("domain", self.domains),
                ("validation", self.validation_ids)):
            if not values or len(values) != len(set(values)):
                raise ValueError(f"Model-use admission {name} list must be nonempty and unique")
        if len(self.known_failure_ids) != len(set(self.known_failure_ids)):
            raise ValueError("Duplicate known validation failure")
        if self.status is AdmissionStatus.CONTROLLED_TRIAL and not self.manual_review_required:
            raise ValueError("Controlled trial must require manual review")
        if (self.status in (AdmissionStatus.CONTROLLED_TRIAL, AdmissionStatus.LIMITED)
                and not self.restrictions):
            raise ValueError("Limited/controlled admission needs explicit restrictions")
        return self


class ModelAdmissionError(ArchiveError):
    """A configuration/evidence/scope failure, never a content PASS."""


@dataclass(frozen=True)
class RevalidationPlan:
    required_kinds: tuple[ValidationKind, ...]
    changed_fields: tuple[str, ...]


class ModelAdmissionController:
    def __init__(self, archive: Archive, rights: RightsGrant):
        if not isinstance(archive, Archive):
            raise TypeError("ModelAdmissionController requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError("ModelAdmissionController requires an internal journal grant")
        self.archive = archive
        self.rights = rights

    @staticmethod
    def _config_version(configuration_id: str) -> str:
        digest = hashlib.sha256(canonical(["model-config", configuration_id]).encode()).hexdigest()
        return "MODEL-CFG-" + digest[:32]

    @staticmethod
    def _validation_version(validation_id: str) -> str:
        digest = hashlib.sha256(canonical(["model-validation", validation_id]).encode()).hexdigest()
        return "MODEL-VALIDATION-" + digest[:32]

    @staticmethod
    def _admission_version(admission_id: str) -> str:
        digest = hashlib.sha256(canonical(["model-admission", admission_id]).encode()).hexdigest()
        return "MODEL-ADMISSION-" + digest[:32]

    def append_configuration(self, configuration: ModelTaskConfiguration) -> StoredVersion:
        if not isinstance(configuration, ModelTaskConfiguration):
            raise TypeError("append_configuration requires ModelTaskConfiguration")
        configuration = ModelTaskConfiguration.model_validate_json(
            configuration.model_dump_json(warnings=False))
        fingerprint = configuration.fingerprint()
        configuration = ModelTaskConfiguration.model_validate_json(
            configuration.model_copy(update={"configuration_sha256": fingerprint}).model_dump_json())
        version_id = self._config_version(configuration.configuration_id)
        submission = VersionSubmission(
            schema_version=2, object_id="CONFIG-" + _id_digest(
                configuration.configuration_id)[:32],
            kind=ObjectKind.MODEL_TASK_CONFIGURATION, version_id=version_id,
            title=f"model configuration {configuration.configuration_id}",
            spec_sha256=configuration.spec_sha256, created_at=configuration.created_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY)
        return self.archive.append(
            submission, canonical(configuration.model_dump(mode="json")).encode())

    def load_configuration(self, configuration_id: str) -> ModelTaskConfiguration:
        version_id = self._config_version(configuration_id)
        stored = self.archive.get(version_id)
        if stored.submission.kind is not ObjectKind.MODEL_TASK_CONFIGURATION:
            raise ModelAdmissionError("Requested version is not a model configuration")
        configuration = ModelTaskConfiguration.model_validate_json(
            self.archive.read_body(version_id))
        if configuration.configuration_id != configuration_id:
            raise ModelAdmissionError("Model configuration identity mismatch")
        return configuration

    def append_validation(self, validation: ModelValidation) -> StoredVersion:
        if not isinstance(validation, ModelValidation):
            raise TypeError("append_validation requires ModelValidation")
        validation = ModelValidation.model_validate_json(
            validation.model_dump_json(warnings=False))
        configuration = self.load_configuration(validation.configuration_id)
        if configuration.spec_sha256 != validation.spec_sha256:
            raise ModelAdmissionError("Validation and model configuration use different specifications")
        if validation.duty not in configuration.duties:
            raise ModelAdmissionError("Validation duty is outside the model configuration")
        if not set(validation.domains) <= set(configuration.domains):
            raise ModelAdmissionError("Validation domain is outside the model configuration")
        for version_id in validation.case_version_ids:
            self.archive.get(version_id)
        for attempt in validation.attempts:
            artifact = self.archive.get(attempt.artifact_version_id)
            if artifact.submission.spec_sha256 != validation.spec_sha256:
                raise ModelAdmissionError("Validation artifact uses a different specification")
            if not any(item.target_version_id == self._config_version(validation.configuration_id)
                       for item in artifact.submission.references):
                raise ModelAdmissionError("Validation artifact does not bind the model configuration")
            for version_id in attempt.human_help_version_ids:
                self.archive.get(version_id)
        if validation.kind is ValidationKind.CONSTRAINT_GAIN:
            for version_id in (validation.baseline_artifact_version_id,
                               validation.constrained_artifact_version_id):
                artifact = self.archive.get(version_id)
                if not any(item.target_version_id == self._config_version(
                        validation.configuration_id) for item in artifact.submission.references):
                    raise ModelAdmissionError("Constraint artifact does not bind the model configuration")
        if validation.kind is ValidationKind.REAL_RETRIEVAL:
            journal = OperationJournal(self.archive, self.rights)
            for operation_id in validation.operation_receipt_ids:
                request = self.archive.get(operation_id)
                if request.submission.kind is not ObjectKind.OPERATION_REQUEST:
                    raise ModelAdmissionError("Retrieval evidence target is not an operation")
                request_body = OperationRequest.model_validate_json(
                    self.archive.read_body(operation_id))
                if (request_body.spec_sha256 != configuration.spec_sha256
                        or request_body.configuration_sha256
                        != configuration.configuration_sha256):
                    raise ModelAdmissionError(
                        "Retrieval operation does not bind the model configuration")
                receipt = journal.receipt(operation_id)
                if receipt is None or receipt.status is not OperationStatus.SUCCEEDED:
                    raise ModelAdmissionError("Retrieval evidence has no successful operation receipt")
        review = self.archive.get(validation.review_version_id)
        if review.submission.kind is not ObjectKind.REVIEW:
            raise ModelAdmissionError("Model validation needs an archived Review")
        if review.submission.spec_sha256 != validation.spec_sha256:
            raise ModelAdmissionError("Validation Review uses a different specification")
        if review.body_retention_revoked:
            raise ModelAdmissionError("Validation Review was withdrawn")
        required_review_targets = {
            self._config_version(validation.configuration_id),
            *(item.artifact_version_id for item in validation.attempts),
        }
        if validation.baseline_artifact_version_id:
            required_review_targets.add(validation.baseline_artifact_version_id)
        if validation.constrained_artifact_version_id:
            required_review_targets.add(validation.constrained_artifact_version_id)
        required_review_targets.update(validation.operation_receipt_ids)
        reviewed = {
            item.target_version_id for item in review.submission.references
            if item.use is ReferenceUse.REVIEW_OF
        }
        if not required_review_targets <= reviewed:
            raise ModelAdmissionError("Validation Review does not cover exact configuration and attempts")
        references = (
            VersionReference(target_version_id=self._config_version(validation.configuration_id),
                use=ReferenceUse.BASIS, locator="exact model configuration"),
            VersionReference(target_version_id=validation.review_version_id,
                use=ReferenceUse.REVIEW_OF, locator="validation Review"),
        )
        submission = VersionSubmission(
            schema_version=2, object_id="VALIDATION-" + _id_digest(
                validation.validation_id)[:32],
            kind=ObjectKind.MODEL_VALIDATION,
            version_id=self._validation_version(validation.validation_id),
            title=f"model validation {validation.kind.value}",
            spec_sha256=validation.spec_sha256, created_at=validation.created_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY, references=references)
        return self.archive.append(
            submission, canonical(validation.model_dump(mode="json")).encode())

    def load_validation(self, validation_id: str) -> ModelValidation:
        version_id = self._validation_version(validation_id)
        stored = self.archive.get(version_id)
        if stored.submission.kind is not ObjectKind.MODEL_VALIDATION:
            raise ModelAdmissionError("Requested version is not a model validation")
        validation = ModelValidation.model_validate_json(self.archive.read_body(version_id))
        if validation.validation_id != validation_id:
            raise ModelAdmissionError("Model validation identity mismatch")
        return validation

    def append_admission(self, admission: ModelUseAdmission) -> StoredVersion:
        if not isinstance(admission, ModelUseAdmission):
            raise TypeError("append_admission requires ModelUseAdmission")
        admission = ModelUseAdmission.model_validate_json(
            admission.model_dump_json(warnings=False))
        configuration = self.load_configuration(admission.configuration_id)
        if configuration.spec_sha256 != admission.spec_sha256:
            raise ModelAdmissionError("Admission and model configuration use different specifications")
        if not set(admission.duties) <= set(configuration.duties):
            raise ModelAdmissionError("Admission duty is outside the model configuration")
        if not set(admission.domains) <= set(configuration.domains):
            raise ModelAdmissionError("Admission domain is outside the model configuration")
        validations = [self.load_validation(item) for item in admission.validation_ids]
        for validation in validations:
            if (validation.configuration_id != admission.configuration_id
                    or validation.duty not in admission.duties
                    or not set(admission.domains) <= set(validation.domains)):
                raise ModelAdmissionError("Admission exceeds validation configuration/duty/domain")
        for duty in admission.duties:
            if not any(
                    validation.duty is duty
                    and validation.primary_outcome is ValidationOutcome.PASS
                    for validation in validations):
                raise ModelAdmissionError(
                    f"Admission duty has no passing task-specific validation: {duty.value}")
        failed = tuple(sorted(
            validation.validation_id for validation in validations
            if validation.primary_outcome is not ValidationOutcome.PASS
            or any(item.outcome is not ValidationOutcome.PASS for item in validation.attempts)))
        if tuple(sorted(admission.known_failure_ids)) != failed:
            raise ModelAdmissionError("Admission must retain every known failed or inconclusive validation")
        if failed and not admission.manual_review_required:
            raise ModelAdmissionError("Known validation failure requires manual review")
        passing = {
            validation.kind for validation in validations
            if validation.primary_outcome is ValidationOutcome.PASS
        }
        if admission.allow_given_material and ValidationKind.GIVEN_MATERIAL not in passing:
            raise ModelAdmissionError("Given-material use needs a passing validation")
        if admission.allow_real_retrieval and ValidationKind.REAL_RETRIEVAL not in passing:
            raise ModelAdmissionError("Real retrieval needs a passing retrieval validation")
        if (admission.constraint_gain_verified
                and ValidationKind.CONSTRAINT_GAIN not in passing):
            raise ModelAdmissionError("Constraint gain needs a passing comparison validation")
        human_help = any(
            attempt.human_help_version_ids
            for validation in validations for attempt in validation.attempts)
        if human_help and not admission.manual_review_required:
            raise ModelAdmissionError("Human-assisted validation requires manual review")
        if not (admission.allow_given_material or admission.allow_real_retrieval
                or admission.constraint_gain_verified):
            raise ModelAdmissionError("Admission grants no usable scope")
        review = self.archive.get(admission.review_version_id)
        if review.submission.kind is not ObjectKind.REVIEW:
            raise ModelAdmissionError("Model-use admission needs a Review")
        if review.submission.spec_sha256 != admission.spec_sha256:
            raise ModelAdmissionError("Model-use Review uses a different specification")
        if review.body_retention_revoked:
            raise ModelAdmissionError("Model-use Review was withdrawn")
        required_reviewed = {
            self._config_version(admission.configuration_id),
            *(self._validation_version(item) for item in admission.validation_ids),
        }
        reviewed = {
            item.target_version_id for item in review.submission.references
            if item.use is ReferenceUse.REVIEW_OF
        }
        if not required_reviewed <= reviewed:
            raise ModelAdmissionError("Model-use Review does not cover exact config and validation")
        submission = VersionSubmission(
            schema_version=2, object_id="USE-ADMISSION-" + _id_digest(
                admission.admission_id)[:32],
            kind=ObjectKind.MODEL_USE_ADMISSION,
            version_id=self._admission_version(admission.admission_id),
            title=f"model use admission {admission.status.value}",
            spec_sha256=admission.spec_sha256, created_at=admission.created_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY,
            references=(
                VersionReference(target_version_id=self._config_version(
                    admission.configuration_id), use=ReferenceUse.BASIS,
                    locator="admitted model configuration"),
                VersionReference(target_version_id=admission.review_version_id,
                    use=ReferenceUse.REVIEW_OF, locator="model-use Review"),
                *(
                    VersionReference(target_version_id=self._validation_version(item),
                        use=ReferenceUse.SUPPORT, locator=f"validation {index}")
                    for index, item in enumerate(admission.validation_ids)
                ),
            ))
        return self.archive.append(
            submission, canonical(admission.model_dump(mode="json")).encode())

    def load_admission(self, admission_id: str) -> ModelUseAdmission:
        version_id = self._admission_version(admission_id)
        stored = self.archive.get(version_id)
        if stored.submission.kind is not ObjectKind.MODEL_USE_ADMISSION:
            raise ModelAdmissionError("Requested version is not a model-use admission")
        admission = ModelUseAdmission.model_validate_json(self.archive.read_body(version_id))
        if admission.admission_id != admission_id:
            raise ModelAdmissionError("Model-use admission identity mismatch")
        return admission

    def authorizes(self, admission_id: str, *, configuration_id: str,
                   duty: ModelDuty, domains: tuple[str, ...],
                   require_given_material: bool = False,
                   require_real_retrieval: bool = False,
                   require_constraint_gain: bool = False,
                   at: datetime) -> bool:
        try:
            admission = self.load_admission(admission_id)
            configuration = self.load_configuration(configuration_id)
            if (admission.configuration_id != configuration_id
                    or admission.spec_sha256 != configuration.spec_sha256):
                return False
            latest = self.archive.latest(
                "CONFIG-" + _id_digest(configuration_id)[:32])
            if latest is None or latest.submission.version_id != self._config_version(configuration_id):
                return False
            if not (admission.valid_from <= at < admission.valid_until):
                return False
            if duty not in admission.duties or not set(domains) <= set(admission.domains):
                return False
            if admission.status is not AdmissionStatus.APPROVED:
                return False
            if admission.manual_review_required:
                return False
            if require_given_material and not admission.allow_given_material:
                return False
            if require_real_retrieval and not admission.allow_real_retrieval:
                return False
            if require_constraint_gain and not admission.constraint_gain_verified:
                return False
            for validation_id in admission.validation_ids:
                validation = self.load_validation(validation_id)
                if (validation.configuration_id != configuration_id
                        or validation.primary_outcome is not ValidationOutcome.PASS):
                    return False
                validation_review = self.archive.get(validation.review_version_id)
                if (validation_review.submission.kind is not ObjectKind.REVIEW
                        or validation_review.body_retention_revoked):
                    return False
                for attempt in validation.attempts:
                    artifact = self.archive.get(attempt.artifact_version_id)
                    if artifact.body_retention_revoked:
                        return False
            review = self.archive.get(admission.review_version_id)
            return (review.submission.kind is ObjectKind.REVIEW
                    and not review.body_retention_revoked)
        except (ArchiveError, ModelAdmissionError, ValueError):
            return False

    def revalidation_requirements(
            self, old: ModelTaskConfiguration,
            new: ModelTaskConfiguration) -> RevalidationPlan:
        fields = (
            "provider_id", "model_id", "model_version", "spec_sha256",
            "task_instruction_sha256", "prompt_sha256", "context_policy_sha256",
            "generation_settings_sha256", "method_version", "tools",
            "duties", "domains", "material_forms", "unknown_fields",
        )
        changed = tuple(
            name for name in fields
            if getattr(old, name) != getattr(new, name))
        if not changed:
            return RevalidationPlan((), ())
        identity_fields = {
            "provider_id", "model_id", "model_version", "spec_sha256",
            "task_instruction_sha256", "prompt_sha256", "context_policy_sha256",
            "generation_settings_sha256", "method_version", "tools",
            "unknown_fields",
        }
        if set(changed) & identity_fields:
            required = (
                ValidationKind.GIVEN_MATERIAL,
                ValidationKind.REAL_RETRIEVAL,
                ValidationKind.CONSTRAINT_GAIN,
            )
        else:
            required = (
                ValidationKind.GIVEN_MATERIAL,
                ValidationKind.REAL_RETRIEVAL,
            )
        return RevalidationPlan(
            required_kinds=required,
            changed_fields=changed)


def _id_digest(value: str) -> str:
    return hashlib.sha256(canonical([value]).encode()).hexdigest()
