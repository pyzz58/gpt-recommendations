"""W13 / C02 contracts: T01.L01, T04.L01, T11.L01; spec §§6,16,22.4.

These validate structure and recorded permission scope, not factual truth or
whether a human permission assessment was correct. Unknown times stay unknown.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
import re
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, field_serializer, model_validator

Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")]
Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
NonBlank = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class ObjectKind(str, Enum):
    TASK = "Task"
    SOURCE = "Source"
    DOCUMENT = "Document"
    EVIDENCE = "Evidence"
    CLAIM = "Claim"
    DOSSIER = "ResearchDossier"
    ARTICLE = "Article"
    REVIEW = "Review"
    THESIS = "Thesis"
    EDITION = "Edition"
    CONCEPT = "Concept"
    METHOD_USE = "MethodUse"
    BACKGROUND = "Background"
    STEP_SUBMISSION = "StepSubmission"
    ADOPTION_DECISION = "AdoptionDecision"
    RESEARCH_REVISION = "ResearchRevision"
    ARTIFACT_LINK = "ResearchArtifactLink"
    ARTIFACT_COMPATIBILITY = "ResearchArtifactCompatibility"
    RESEARCH_COMMIT = "ResearchCommit"
    OPERATION_REQUEST = "OperationRequest"
    OPERATION_RECEIPT = "OperationReceipt"
    PROVIDER_REQUEST_MAPPING = "ProviderRequestMapping"
    CAPABILITY_ADMISSION = "CapabilityAdmission"
    BUDGET_ENVELOPE = "BudgetEnvelope"
    BUDGET_EVENT = "BudgetEvent"
    MODEL_TASK_CONFIGURATION = "ModelTaskConfiguration"
    MODEL_VALIDATION = "ModelValidation"
    MODEL_USE_ADMISSION = "ModelUseAdmission"
    CANDIDATE_INDEX = "CandidateIndex"
    EVENT_CLUSTER_PROPOSAL = "EventClusterProposal"
    COVERAGE_REFERENCE_PLAN = "CoverageReferencePlan"
    COVERAGE_AUDIT = "CoverageAudit"
    QUESTION_VERSION = "QuestionVersion"
    SOURCE_MATERIAL = "SourceMaterial"
    SOURCE_STRUCTURE = "SourceStructure"
    SOURCE_INTAKE = "SourceIntake"
    RIGHTS_RECORD = "RightsRecord"
    READING_SCOPE_PLAN = "ReadingScopePlan"
    S8_PREREQUISITE_PACKAGE = "S8PrerequisitePackage"
    TOPIC_DECISION = "TopicDecision"
    RESEARCH_ADMISSION = "ResearchAdmission"
    EDITION_PLACEMENT_PROPOSAL = "EditionPlacementProposal"
    MATERIAL_SELECTION = "MaterialSelection"


class Precision(str, Enum):
    UNKNOWN = "UNKNOWN"
    DATE = "DATE"
    INSTANT = "INSTANT"
    DATE_RANGE = "DATE_RANGE"
    INSTANT_RANGE = "INSTANT_RANGE"
    PARTIAL_RANGE = "PARTIAL_RANGE"


class TimePoint(Contract):
    precision: Precision = Precision.UNKNOWN
    value: NonBlank | None = None
    start_value: NonBlank | None = None
    end_value: NonBlank | None = None
    endpoint_precision: Precision | None = None
    start_inclusive: bool = True
    end_inclusive: bool = True
    source_timezone: NonBlank | None = None
    provenance: NonBlank | None = None
    uncertainty: NonBlank | None = None
    reason: NonBlank | None = None

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.precision is Precision.UNKNOWN:
            if any(x is not None for x in (self.value, self.start_value, self.end_value)) or not self.reason:
                raise ValueError("Unknown time needs a reason and cannot have a value")
        elif self.precision in (Precision.DATE, Precision.INSTANT):
            if (self.value is None or self.start_value is not None or self.end_value is not None
                    or self.endpoint_precision is not None):
                raise ValueError("A point time needs exactly one value")
            if self.precision is Precision.DATE:
                self._validate_date(self.value)
            else:
                self._validate_instant(self.value)
        else:
            if self.value is not None:
                raise ValueError("A range cannot contain a point value")
            if self.start_value is None and self.end_value is None:
                raise ValueError("A range needs at least one endpoint")
            if self.precision is Precision.PARTIAL_RANGE:
                if not self.reason:
                    raise ValueError("A partial range needs an unknown-endpoint reason")
                if self.endpoint_precision not in (Precision.DATE, Precision.INSTANT):
                    raise ValueError("A partial range needs DATE or INSTANT endpoint precision")
            elif self.start_value is None or self.end_value is None:
                raise ValueError("A complete range needs both endpoints")
            elif self.endpoint_precision is not None:
                raise ValueError("Complete range precision is defined by its range type")
            if self.precision is Precision.DATE_RANGE:
                if self.start_value is not None:
                    self._validate_date(self.start_value)
                if self.end_value is not None:
                    self._validate_date(self.end_value)
                if (self.start_value is not None and self.end_value is not None
                        and self.end_value < self.start_value):
                    raise ValueError("Date range endpoints are inverted")
            elif self.precision is Precision.INSTANT_RANGE:
                start = self._validate_instant(self.start_value) if self.start_value is not None else None
                end = self._validate_instant(self.end_value) if self.end_value is not None else None
                if start is not None and end is not None and end < start:
                    raise ValueError("Instant range endpoints are inverted")
            elif self.precision is Precision.PARTIAL_RANGE:
                if self.endpoint_precision is Precision.DATE:
                    for endpoint in (self.start_value, self.end_value):
                        if endpoint is not None:
                            self._validate_date(endpoint)
                    if (self.start_value is not None and self.end_value is not None
                            and self.end_value < self.start_value):
                        raise ValueError("Date range endpoints are inverted")
                else:
                    start = self._validate_instant(self.start_value) if self.start_value else None
                    end = self._validate_instant(self.end_value) if self.end_value else None
                    if start is not None and end is not None and end < start:
                        raise ValueError("Instant range endpoints are inverted")
        return self

    @staticmethod
    def _validate_date(value: str) -> None:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("DATE precision requires YYYY-MM-DD, not an invented midnight")
        date.fromisoformat(value)

    @staticmethod
    def _validate_instant(value: str) -> datetime:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("INSTANT requires an explicit UTC offset")
        return parsed


def unknown_time() -> TimePoint:
    return TimePoint(reason="Not established")


class DataPeriod(Contract):
    start: AwareDatetime
    end_exclusive: AwareDatetime
    source_timezone: NonBlank | None = None
    provenance: NonBlank | None = None
    uncertainty: NonBlank | None = None

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end_exclusive <= self.start:
            raise ValueError("Data period must have positive duration")
        return self


class SourceTimes(Contract):
    event: TimePoint = Field(default_factory=unknown_time)
    published: TimePoint = Field(default_factory=unknown_time)
    data_period: DataPeriod | None = None


class MaterialUse(str, Enum):
    INDEX = "INDEX"
    STORE_BODY = "STORE_BODY"
    MODEL_PROCESS = "MODEL_PROCESS"
    TRANSLATE = "TRANSLATE"
    PRIVATE_DELIVERY = "PRIVATE_DELIVERY"


class RightsBasis(str, Enum):
    OWN_WORK = "OWN_WORK"
    LICENSE = "LICENSE"
    EXPLICIT_PERMISSION = "EXPLICIT_PERMISSION"
    PUBLIC_DOMAIN = "PUBLIC_DOMAIN"
    POINTER_ONLY = "POINTER_ONLY"


class ScopeMode(str, Enum):
    ANY = "ANY"
    LIST = "LIST"
    UNKNOWN = "UNKNOWN"


class Scope(Contract):
    """An explicit scope; omitted values never mean unrestricted access."""

    mode: ScopeMode = ScopeMode.UNKNOWN
    values: tuple[NonBlank, ...] = ()
    reason: NonBlank | None = None

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if len(self.values) != len({value.casefold() for value in self.values}):
            raise ValueError("Duplicate scope value")
        if self.mode is ScopeMode.LIST:
            if not self.values:
                raise ValueError("LIST scope needs at least one value")
        elif self.values:
            raise ValueError("Only LIST scope may contain values")
        if self.mode is ScopeMode.UNKNOWN and not self.reason:
            raise ValueError("UNKNOWN scope needs a reason")
        return self


class PermissionState(str, Enum):
    ALLOWED = "ALLOWED"
    DENIED = "DENIED"
    UNKNOWN = "UNKNOWN"


class ValidityMode(str, Enum):
    OPEN_ENDED = "OPEN_ENDED"
    BOUNDED = "BOUNDED"
    UNKNOWN = "UNKNOWN"


class UsePermission(Contract):
    use: MaterialUse
    state: PermissionState = PermissionState.UNKNOWN
    validity: ValidityMode = ValidityMode.UNKNOWN
    effective_from: AwareDatetime | None = None
    effective_until: AwareDatetime | None = None
    territories: Scope = Field(default_factory=lambda: Scope(reason="Territory not reviewed"))
    providers: Scope = Field(default_factory=lambda: Scope(reason="Provider not reviewed"))
    content_scope: Scope = Field(default_factory=lambda: Scope(reason="Covered content not reviewed"))
    excluded_content: tuple[NonBlank, ...] = ()
    conditions: tuple[NonBlank, ...] = ()
    conditions_satisfied: bool | None = None
    attribution_requirements: tuple[NonBlank, ...] = ()

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.validity is ValidityMode.UNKNOWN:
            if self.effective_from is not None or self.effective_until is not None:
                raise ValueError("Unknown validity cannot carry effective dates")
        elif self.validity is ValidityMode.OPEN_ENDED:
            if self.effective_from is not None or self.effective_until is not None:
                raise ValueError("Open-ended validity has no term dates")
        elif self.effective_from is None and self.effective_until is None:
            raise ValueError("Bounded validity needs an effective boundary")
        if self.effective_from is not None and self.effective_until is not None:
            if self.effective_until <= self.effective_from:
                raise ValueError("Permission validity is inverted")
        if self.conditions and self.conditions_satisfied is None:
            # This is allowed for recording an unresolved condition; evaluation denies it.
            pass
        if len(self.excluded_content) != len(set(self.excluded_content)):
            raise ValueError("Duplicate excluded content")
        if len(self.attribution_requirements) != len(set(self.attribution_requirements)):
            raise ValueError("Duplicate attribution requirement")
        return self


class RightsGrant(Contract):
    rights_id: Identifier
    basis: RightsBasis
    allowed_uses: frozenset[MaterialUse]
    evidence: NonBlank
    checked_by: NonBlank
    checked_at: AwareDatetime
    work_title: NonBlank | None = None
    source_locator: NonBlank | None = None
    terms_url: NonBlank | None = None
    terms_version: NonBlank | None = None
    grantor: NonBlank | None = None
    permissions: tuple[UsePermission, ...] = ()

    @field_serializer("allowed_uses")
    def sorted_uses(self, value: frozenset[MaterialUse]) -> list[str]:
        return sorted(item.value for item in value)

    @model_validator(mode="after")
    def pointer_scope(self) -> Self:
        if MaterialUse.INDEX not in self.allowed_uses:
            raise ValueError("This archive requires explicit permission to retain the minimal index")
        if self.basis is RightsBasis.POINTER_ONLY and self.allowed_uses != frozenset({MaterialUse.INDEX}):
            raise ValueError("Pointer-only permission cannot authorize body storage or processing")
        uses = [item.use for item in self.permissions]
        if len(uses) != len(set(uses)):
            raise ValueError("Duplicate structured permission for one use")
        if any(item.state is PermissionState.ALLOWED and item.use not in self.allowed_uses
               for item in self.permissions):
            raise ValueError("A structured ALLOWED use must also be in allowed_uses")
        return self


class ReferenceUse(str, Enum):
    SOURCE = "SOURCE"
    SUPPORT = "SUPPORT"
    METHOD = "METHOD"
    BASIS = "BASIS"
    REVIEW_OF = "REVIEW_OF"
    ASSEMBLY = "ASSEMBLY"
    LINEAGE = "LINEAGE"
    BACKGROUND = "BACKGROUND"


class VersionReference(Contract):
    target_version_id: Identifier
    use: ReferenceUse
    locator: NonBlank


class ReviewCoverage(Contract):
    """One exact task/subject/use range actually covered by a Review."""

    task_version_id: Identifier
    subject_version_id: Identifier
    reviewed_scope: tuple[NonBlank, ...]


class Representation(str, Enum):
    FULL_BODY = "FULL_BODY"
    POINTER_ONLY = "POINTER_ONLY"


class VersionSubmission(Contract):
    schema_version: int = Field(default=2, ge=1, le=2)
    object_id: Identifier
    kind: ObjectKind
    version_id: Identifier
    parent_version_id: Identifier | None = None
    title: NonBlank
    spec_sha256: Digest
    created_at: AwareDatetime
    as_of: TimePoint = Field(default_factory=unknown_time)
    source_times: SourceTimes = Field(default_factory=SourceTimes)
    rights: RightsGrant
    representation: Representation
    source_locator: NonBlank | None = None
    media_type: NonBlank = "text/markdown; charset=utf-8"
    references: tuple[VersionReference, ...] = ()
    review_coverage: tuple[ReviewCoverage, ...] = ()

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.version_id == self.parent_version_id:
            raise ValueError("A version cannot be its own parent")
        if self.representation is Representation.POINTER_ONLY and not self.source_locator:
            raise ValueError("Pointer-only records need an original source locator")
        if self.representation is Representation.FULL_BODY and MaterialUse.STORE_BODY not in self.rights.allowed_uses:
            raise ValueError("Full body requires a recorded STORE_BODY grant")
        keys = [(r.target_version_id, r.use, r.locator) for r in self.references]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate version reference")
        if any(r.target_version_id == self.version_id for r in self.references):
            raise ValueError("A version cannot reference itself")
        if self.review_coverage and self.kind is not ObjectKind.REVIEW:
            raise ValueError("Only a Review can declare review coverage")
        coverage_keys = [(item.task_version_id, item.subject_version_id)
                         for item in self.review_coverage]
        if len(coverage_keys) != len(set(coverage_keys)):
            raise ValueError("Duplicate Review coverage for one task/subject pair")
        for item in self.review_coverage:
            if item.task_version_id == item.subject_version_id:
                raise ValueError("A Review task cannot also be its reviewed subject")
            normalized = [value.casefold() for value in item.reviewed_scope]
            if len(normalized) != len(set(normalized)):
                raise ValueError("Duplicate reviewed scope")
        return self


class StoredVersion(Contract):
    submission: VersionSubmission
    ordinal: int = Field(ge=1)
    recorded_at: AwareDatetime
    body_sha256: Digest | None
    body_bytes: int | None = Field(ge=0)
    body_retention_revoked: bool


class ReferenceReadRequest(Contract):
    """A caller-declared use of an already committed, exact version reference.

    consumer is a routing label, not an authenticated role. spec_sha256 records
    the caller's declared basis; checking the current spec belongs to W14.
    """

    schema_version: int = Field(default=2, ge=1, le=2)
    request_id: Identifier
    spec_sha256: Digest
    created_at: AwareDatetime
    consumer: Literal["T01", "T04", "T05", "T09", "T10"]
    owner_version_id: Identifier
    reference: VersionReference
    expected_kind: ObjectKind
    intended_use: MaterialUse
    expected_body_sha256: Digest | None = None
    expected_selected_body_sha256: Digest | None = None
    use_context: UseContext | None = None


class UseContext(Contract):
    """Facts available at a specific downstream-use check.

    Provider and territory values are caller-declared execution context. W13
    checks them against recorded terms; it does not authenticate the caller.
    """

    at: AwareDatetime
    provider: NonBlank | None = None
    territory: NonBlank | None = None
    content: tuple[NonBlank, ...] = ()
    selected_version_id: Identifier | None = None


class ReferencedMaterial(Contract):
    """A retrieval receipt, not proof of reading, truth or content approval.

    INDEX returns metadata only. Binary originals roundtrip without assuming
    UTF-8; command-line receipts omit body bytes entirely.
    """

    model_config = ConfigDict(ser_json_bytes="base64", val_json_bytes="base64")

    request: ReferenceReadRequest
    owner: StoredVersion
    version: StoredVersion
    selected_version: StoredVersion | None = None
    recorded_at: AwareDatetime
    body: bytes | None
    required_attribution: tuple[NonBlank, ...] = ()


class RevocationResult(Contract):
    rights_id: Identifier
    revoked_uses: tuple[MaterialUse, ...] = ()
    affected_versions: tuple[Identifier, ...]
    purged_versions: tuple[Identifier, ...]
    failed_versions: tuple[Identifier, ...]
    recorded_at: AwareDatetime
