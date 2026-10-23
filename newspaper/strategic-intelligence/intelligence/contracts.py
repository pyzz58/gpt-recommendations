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


class Precision(str, Enum):
    UNKNOWN = "UNKNOWN"
    DATE = "DATE"
    INSTANT = "INSTANT"


class TimePoint(Contract):
    precision: Precision = Precision.UNKNOWN
    value: NonBlank | None = None
    reason: NonBlank | None = None

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.precision is Precision.UNKNOWN:
            if self.value is not None or not self.reason:
                raise ValueError("Unknown time needs a reason and cannot have a value")
        elif self.value is None:
            raise ValueError("Known time needs a value")
        elif self.precision is Precision.DATE:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", self.value):
                raise ValueError("DATE precision requires YYYY-MM-DD, not an invented midnight")
            date.fromisoformat(self.value)
        else:
            parsed = datetime.fromisoformat(self.value.replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise ValueError("INSTANT requires an explicit UTC offset")
        return self


def unknown_time() -> TimePoint:
    return TimePoint(reason="Not established")


class DataPeriod(Contract):
    start: AwareDatetime
    end_exclusive: AwareDatetime

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


class RightsGrant(Contract):
    rights_id: Identifier
    basis: RightsBasis
    allowed_uses: frozenset[MaterialUse]
    evidence: NonBlank
    checked_by: NonBlank
    checked_at: AwareDatetime

    @field_serializer("allowed_uses")
    def sorted_uses(self, value: frozenset[MaterialUse]) -> list[str]:
        return sorted(item.value for item in value)

    @model_validator(mode="after")
    def pointer_scope(self) -> Self:
        if MaterialUse.INDEX not in self.allowed_uses:
            raise ValueError("This archive requires explicit permission to retain the minimal index")
        if self.basis is RightsBasis.POINTER_ONLY and self.allowed_uses != frozenset({MaterialUse.INDEX}):
            raise ValueError("Pointer-only permission cannot authorize body storage or processing")
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


class Representation(str, Enum):
    FULL_BODY = "FULL_BODY"
    POINTER_ONLY = "POINTER_ONLY"


class VersionSubmission(Contract):
    schema_version: int = Field(default=1, ge=1, le=1)
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

    schema_version: int = Field(default=1, ge=1, le=1)
    request_id: Identifier
    spec_sha256: Digest
    created_at: AwareDatetime
    consumer: Literal["T01", "T04", "T05", "T09", "T10"]
    owner_version_id: Identifier
    reference: VersionReference
    expected_kind: ObjectKind
    intended_use: MaterialUse
    expected_body_sha256: Digest | None = None


class ReferencedMaterial(Contract):
    """A retrieval receipt, not proof of reading, truth or content approval.

    INDEX returns metadata only. Binary originals roundtrip without assuming
    UTF-8; command-line receipts omit body bytes entirely.
    """

    model_config = ConfigDict(ser_json_bytes="base64", val_json_bytes="base64")

    request: ReferenceReadRequest
    owner: StoredVersion
    version: StoredVersion
    recorded_at: AwareDatetime
    body: bytes | None


class RevocationResult(Contract):
    rights_id: Identifier
    affected_versions: tuple[Identifier, ...]
    purged_versions: tuple[Identifier, ...]
    failed_versions: tuple[Identifier, ...]
    recorded_at: AwareDatetime
