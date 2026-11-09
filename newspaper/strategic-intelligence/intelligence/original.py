"""W24 original acquisition, structure mapping and purpose-aware source use."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
import hashlib
import re
from typing import Literal, Self

from lxml import etree, html as lxml_html
from pydantic import AwareDatetime, Field, model_validator
import trafilatura

from .archive import Archive, ArchiveError, BodyUnavailable, MissingVersion, PermissionDenied, canonical
from .contracts import (Contract, DataPeriod, Digest, Identifier, MaterialUse, NonBlank,
                        ObjectKind, ReferenceReadRequest, ReferenceUse, ReferencedMaterial,
                        Representation, RightsGrant, SourceTimes, StoredVersion, TimePoint,
                        UseContext, VersionReference, VersionSubmission)
from .editorial import DecisionStage, EditorialController, TopicDecisionCode


class AcquisitionPurpose(str, Enum):
    S8_PREREQUISITE = "S8_PREREQUISITE"
    POST_S8_EVIDENCE = "POST_S8_EVIDENCE"
    REVIEW_RECHECK = "REVIEW_RECHECK"


class AcquisitionMethod(str, Enum):
    PROVIDED_BYTES = "PROVIDED_BYTES"
    MANUAL_DOWNLOAD = "MANUAL_DOWNLOAD"


class AcquisitionScope(str, Enum):
    FULL_DOCUMENT = "FULL_DOCUMENT"
    DECLARED_PARTIAL = "DECLARED_PARTIAL"


class SourceFormat(str, Enum):
    HTML = "HTML"
    TEXT = "TEXT"
    PDF = "PDF"
    OTHER = "OTHER"


class IntakeStatus(str, Enum):
    RECORDED = "RECORDED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class RetentionMode(str, Enum):
    RETAINED = "RETAINED"
    POINTER_ONLY = "POINTER_ONLY"
    NOT_CREATED = "NOT_CREATED"


class StructureStatus(str, Enum):
    EXTRACTED = "EXTRACTED"
    PARTIAL = "PARTIAL"
    EMPTY = "EMPTY"
    UNSUPPORTED = "UNSUPPORTED"


class StructureNodeKind(str, Enum):
    HEADING = "HEADING"
    PARAGRAPH = "PARAGRAPH"
    LIST_ITEM = "LIST_ITEM"
    TABLE = "TABLE"


class IntakeGapCode(str, Enum):
    EMPTY_SOURCE = "EMPTY_SOURCE"
    POINTER_ONLY = "POINTER_ONLY"
    STORAGE_NOT_AUTHORIZED = "STORAGE_NOT_AUTHORIZED"
    PROCESSING_NOT_AUTHORIZED = "PROCESSING_NOT_AUTHORIZED"
    BODY_RETENTION_REVOKED = "BODY_RETENTION_REVOKED"
    DECLARED_PARTIAL = "DECLARED_PARTIAL"
    EMPTY_EXTRACTION = "EMPTY_EXTRACTION"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    OCR_REQUIRED = "OCR_REQUIRED"
    TABLE_REQUIRES_VISUAL_CHECK = "TABLE_REQUIRES_VISUAL_CHECK"
    FIGURE_REQUIRES_VISUAL_CHECK = "FIGURE_REQUIRES_VISUAL_CHECK"
    EXTRACTION_DID_NOT_COVER_FULL_RAW_TEXT = "EXTRACTION_DID_NOT_COVER_FULL_RAW_TEXT"


class IntakeGap(Contract):
    code: IntakeGapCode
    message: NonBlank
    locator: NonBlank | None = None
    required_visual_check: bool = False


class AcquisitionRequest(Contract):
    schema_version: Literal[1] = 1
    request_id: Identifier
    spec_sha256: Digest
    topic_id: Identifier
    topic_decision_id: Identifier
    purpose: AcquisitionPurpose
    source_id: Identifier
    title: NonBlank
    original_url: NonBlank
    creator: NonBlank | None = None
    institution: NonBlank | None = None
    language: NonBlank | None = None
    version_label: NonBlank | None = None
    media_type: NonBlank
    expected_format: SourceFormat
    expected_sha256: Digest
    method: AcquisitionMethod
    acquired_at: AwareDatetime
    scope: AcquisitionScope
    partial_locator: NonBlank | None = None
    published_at: TimePoint
    data_period: DataPeriod | None = None
    rights: RightsGrant
    use_context: UseContext
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.created_at > self.acquired_at:
            raise ValueError("Acquisition request cannot be created after acquisition")
        if self.rights.checked_at > self.acquired_at:
            raise ValueError("Rights were checked after the claimed acquisition")
        if self.rights.work_title != self.title:
            raise ValueError("Rights record must identify this exact work title")
        if self.rights.source_locator != self.original_url:
            raise ValueError("Rights record must identify this exact source locator")
        if self.use_context.at != self.acquired_at:
            raise ValueError("Acquisition use context must be evaluated at acquisition time")
        if self.scope is AcquisitionScope.DECLARED_PARTIAL and not self.partial_locator:
            raise ValueError("Declared partial acquisition needs the actual acquired locator")
        if self.scope is AcquisitionScope.FULL_DOCUMENT and self.partial_locator is not None:
            raise ValueError("Full acquisition cannot carry a partial locator")
        return self


class StructureNode(Contract):
    node_id: Identifier
    ordinal: int = Field(ge=1)
    kind: StructureNodeKind
    locator: NonBlank
    text_sha256: Digest
    char_start: int = Field(ge=0)
    char_end: int = Field(gt=0)
    requires_original_visual_check: bool = False

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.char_end <= self.char_start:
            raise ValueError("Structure node character range is empty or inverted")
        if self.kind is StructureNodeKind.TABLE and not self.requires_original_visual_check:
            raise ValueError("A table structure must require original visual verification")
        return self


class SourceStructure(Contract):
    schema_version: Literal[1] = 1
    structure_id: Identifier
    source_version_id: Identifier
    source_sha256: Digest
    source_format: SourceFormat
    extractor: NonBlank
    extractor_version: NonBlank
    acquisition_scope: AcquisitionScope
    partial_locator: NonBlank | None = None
    status: StructureStatus
    nodes: tuple[StructureNode, ...]
    table_count: int = Field(ge=0)
    figure_count: int = Field(ge=0)
    text_character_count: int = Field(ge=0)
    gaps: tuple[IntakeGap, ...]
    content_verification: Literal["NOT_PERFORMED"] = "NOT_PERFORMED"
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("node", [item.node_id for item in self.nodes]),
                ("ordinal", [item.ordinal for item in self.nodes]),
                ("locator", [item.locator for item in self.nodes])):
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate structure {name}")
        if [item.ordinal for item in self.nodes] != list(
                range(1, len(self.nodes) + 1)):
            raise ValueError("Structure node ordinals must be continuous")
        if self.status in (StructureStatus.EXTRACTED, StructureStatus.PARTIAL):
            if not self.nodes:
                raise ValueError("A parsed structure must contain locatable nodes")
        elif self.nodes:
            raise ValueError("Empty/unsupported structure cannot claim parsed nodes")
        if self.table_count != sum(
                node.kind is StructureNodeKind.TABLE for node in self.nodes):
            raise ValueError("Table count does not match table nodes")
        if self.content_verification != "NOT_PERFORMED":
            raise ValueError("Structure extraction cannot assert content verification")
        if self.status is StructureStatus.EXTRACTED and any(
                gap.code in {
                    IntakeGapCode.DECLARED_PARTIAL,
                    IntakeGapCode.EMPTY_EXTRACTION,
                    IntakeGapCode.UNSUPPORTED_FORMAT,
                    IntakeGapCode.OCR_REQUIRED,
                    IntakeGapCode.EXTRACTION_DID_NOT_COVER_FULL_RAW_TEXT,
                } for gap in self.gaps):
            raise ValueError("Extracted structure contains a blocking extraction gap")
        if self.acquisition_scope is AcquisitionScope.DECLARED_PARTIAL:
            if not self.partial_locator or not any(
                    gap.code is IntakeGapCode.DECLARED_PARTIAL for gap in self.gaps):
                raise ValueError("Declared partial structure needs its locator and gap")
        elif self.partial_locator is not None:
            raise ValueError("Full structure cannot carry a partial locator")
        return self


class RightsRecord(Contract):
    schema_version: Literal[1] = 1
    rights_record_id: Identifier
    source_version_id: Identifier
    source_id: Identifier
    source_sha256: Digest
    title: NonBlank
    original_url: NonBlank
    retention: RetentionMode
    rights: RightsGrant
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.retention is RetentionMode.NOT_CREATED:
            raise ValueError("A retained RightsRecord must have a created source version")
        if self.rights.work_title != self.title:
            raise ValueError("RightsRecord title differs from its grant")
        if self.rights.source_locator != self.original_url:
            raise ValueError("RightsRecord locator differs from its grant")
        if self.rights.checked_at > self.created_at:
            raise ValueError("RightsRecord cannot predate its rights check")
        return self


class SourceIntake(Contract):
    schema_version: Literal[1] = 1
    intake_id: Identifier
    request_id: Identifier
    request_sha256: Digest
    spec_sha256: Digest
    topic_id: Identifier
    topic_decision_id: Identifier
    question_version_id: Identifier
    purpose: AcquisitionPurpose
    source_id: Identifier
    title: NonBlank
    original_url: NonBlank
    creator: NonBlank | None = None
    institution: NonBlank | None = None
    language: NonBlank | None = None
    version_label: NonBlank | None = None
    published_at: TimePoint
    data_period: DataPeriod | None = None
    source_sha256: Digest
    expected_sha256: Digest
    byte_count: int = Field(ge=0)
    media_type: NonBlank
    source_format: SourceFormat
    method: AcquisitionMethod
    acquisition_scope: AcquisitionScope
    partial_locator: NonBlank | None = None
    status: IntakeStatus
    source_version_id: Identifier | None = None
    rights_record_version_id: Identifier | None = None
    structure_version_id: Identifier | None = None
    rights_id: Identifier
    retention: RetentionMode
    gaps: tuple[IntakeGap, ...]
    facts_verified: Literal[False] = False
    claims_supported: Literal[False] = False
    content_review_required: Literal[True] = True
    review_status: Literal["PENDING"] = "PENDING"
    acquired_at: AwareDatetime
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.source_sha256 != self.expected_sha256:
            raise ValueError("Intake hash differs from the requested exact version")
        if self.byte_count == 0:
            if not any(gap.code is IntakeGapCode.EMPTY_SOURCE for gap in self.gaps):
                raise ValueError("Empty acquisition needs an explicit empty-source gap")
        if self.status is IntakeStatus.FAILED:
            if any((self.source_version_id, self.rights_record_version_id,
                    self.structure_version_id)):
                raise ValueError("Failed intake cannot point to derived source records")
            if self.retention is not RetentionMode.NOT_CREATED or not self.gaps:
                raise ValueError("Failed intake needs NOT_CREATED retention and gaps")
        else:
            if not all((self.source_version_id, self.rights_record_version_id,
                        self.structure_version_id)):
                raise ValueError("Recorded/partial intake needs source, rights and structure")
            if self.retention is RetentionMode.NOT_CREATED:
                raise ValueError("Recorded/partial intake needs a created source version")
        if self.status is IntakeStatus.RECORDED:
            if self.retention is not RetentionMode.RETAINED or self.gaps:
                raise ValueError("Recorded intake requires retained source and no intake gaps")
        if self.status is IntakeStatus.PARTIAL and not self.gaps:
            raise ValueError("Partial intake must state its gaps")
        if self.acquisition_scope is AcquisitionScope.DECLARED_PARTIAL:
            if not self.partial_locator or not any(
                    gap.code is IntakeGapCode.DECLARED_PARTIAL for gap in self.gaps):
                raise ValueError("Partial intake needs its locator and declared gap")
        elif self.partial_locator is not None:
            raise ValueError("Full intake cannot carry a partial locator")
        return self


class SourceNodeRead(Contract):
    intake_version_id: Identifier
    source_version_id: Identifier
    structure_id: Identifier
    node: StructureNode
    text: NonBlank
    content_verification: Literal["NOT_PERFORMED"] = "NOT_PERFORMED"
    original_visual_check_required: bool = False


class OriginalMaterialError(ArchiveError):
    """A source intake/use failure, never a factual support decision."""


def _digest_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _infer_format(media_type: str, raw: bytes) -> SourceFormat:
    lowered = media_type.casefold()
    head = raw[:512].lstrip().lower()
    if "pdf" in lowered or head.startswith(b"%pdf-"):
        return SourceFormat.PDF
    if "html" in lowered or head.startswith((b"<!doctype html", b"<html", b"<article")):
        return SourceFormat.HTML
    if lowered.startswith("text/") or "json" in lowered or "xml" in lowered:
        return SourceFormat.TEXT
    return SourceFormat.OTHER


def _node_id(ordinal: int, kind: StructureNodeKind, locator: str, digest: str) -> str:
    value = canonical([ordinal, kind.value, locator, digest])
    return "NODE-" + hashlib.sha256(value.encode()).hexdigest()[:32]


def _html_nodes(raw: bytes) -> tuple[tuple[StructureNode, ...], int, int]:
    parser = lxml_html.HTMLParser(recover=True, no_network=True)
    root = lxml_html.fromstring(raw, parser=parser)
    containers = root.xpath("//article")
    if not containers:
        containers = root.xpath("//main")
    if not containers:
        containers = root.xpath("//body")
    container = containers[0] if containers else root
    tag_map = {
        "h1": StructureNodeKind.HEADING,
        "h2": StructureNodeKind.HEADING,
        "h3": StructureNodeKind.HEADING,
        "h4": StructureNodeKind.HEADING,
        "p": StructureNodeKind.PARAGRAPH,
        "li": StructureNodeKind.LIST_ITEM,
        "table": StructureNodeKind.TABLE,
    }
    nodes = []
    cursor = 0
    for element in container.iter():
        if not isinstance(element.tag, str):
            continue
        kind = tag_map.get(element.tag.casefold())
        if kind is None:
            continue
        if kind is not StructureNodeKind.TABLE and element.xpath("ancestor::table"):
            continue
        text = _normalize_text(" ".join(element.itertext()))
        if not text:
            continue
        locator = element.getroottree().getpath(element)
        if not locator:
            continue
        start = cursor
        end = start + len(text)
        cursor = end + 2
        digest = _digest_text(text)
        nodes.append(StructureNode(
            node_id=_node_id(len(nodes) + 1, kind, locator, digest),
            ordinal=len(nodes) + 1, kind=kind, locator=locator,
            text_sha256=digest, char_start=start, char_end=end,
            requires_original_visual_check=(kind is StructureNodeKind.TABLE)))
    figure_count = (
        len(container.xpath(".//figure"))
        + len(container.xpath(
            ".//img[not(ancestor::figure)] | .//svg[not(ancestor::figure)]")))
    return tuple(nodes), cursor, figure_count


def _text_blocks(raw: bytes) -> list[str]:
    text = raw.decode("utf-8")
    return [
        normalized for block in re.split(r"\n\s*\n|\n(?=\s*\S)", text)
        if (normalized := _normalize_text(block))
    ]


def _text_nodes(raw: bytes) -> tuple[tuple[StructureNode, ...], int]:
    text = raw.decode("utf-8")
    nodes = []
    cursor = 0
    for normalized in _text_blocks(raw):
        locator = f"text:chars:{len(nodes) + 1}"
        digest = _digest_text(normalized)
        start = cursor
        end = start + len(normalized)
        cursor = end + 2
        nodes.append(StructureNode(
            node_id=_node_id(len(nodes) + 1, StructureNodeKind.PARAGRAPH,
                             locator, digest),
            ordinal=len(nodes) + 1, kind=StructureNodeKind.PARAGRAPH,
            locator=locator, text_sha256=digest,
            char_start=start, char_end=end))
    return tuple(nodes), len(text)


class OriginalMaterialController:
    def __init__(self, archive: Archive, journal_rights: RightsGrant):
        if not isinstance(archive, Archive):
            raise TypeError("OriginalMaterialController requires the shared Archive")
        if not isinstance(journal_rights, RightsGrant):
            raise TypeError("OriginalMaterialController requires an internal journal grant")
        self.archive = archive
        self.journal_rights = journal_rights
        self.editorial = EditorialController(archive, journal_rights)

    @staticmethod
    def _version(prefix: str, identity: str) -> str:
        return prefix + hashlib.sha256(
            canonical([prefix, identity]).encode()).hexdigest()[:32]

    @staticmethod
    def _object(prefix: str, identity: str) -> str:
        return prefix + hashlib.sha256(
            canonical([identity]).encode()).hexdigest()[:32]

    @staticmethod
    def _request_digest(request: AcquisitionRequest) -> str:
        return hashlib.sha256(
            canonical(request.model_dump(mode="json")).encode()).hexdigest()

    def _decision(self, request: AcquisitionRequest):
        try:
            decision, context = self.editorial._current_decision_context(
                request.topic_decision_id)
        except ArchiveError as exc:
            raise OriginalMaterialError(
                f"Acquisition authorization failed: {exc}") from exc
        if decision.topic_id != request.topic_id:
            raise OriginalMaterialError("Acquisition request names a different topic")
        if decision.spec_sha256 != request.spec_sha256:
            raise OriginalMaterialError("Topic decision and acquisition specifications differ")
        if request.created_at < decision.created_at:
            raise OriginalMaterialError("Acquisition request predates its editorial decision")
        if request.purpose is AcquisitionPurpose.S8_PREREQUISITE:
            if decision.stage is not DecisionStage.S7:
                raise OriginalMaterialError(
                    "S8-prerequisite acquisition needs a current S7 decision")
            if decision.decision not in (
                    TopicDecisionCode.REVISE, TopicDecisionCode.WATCH):
                raise OriginalMaterialError(
                    "A dropped S7 topic cannot authorize original acquisition")
        elif (decision.stage is not DecisionStage.S8
              or decision.decision is not TopicDecisionCode.COVER):
            raise OriginalMaterialError(
                "Post-S8 acquisition needs a current S8 COVER decision")
        if (request.purpose is not AcquisitionPurpose.S8_PREREQUISITE
                and decision.s8_package_id):
            package = self.editorial.load_package(decision.s8_package_id)
            protected_objects = {
                self.archive.get(version_id).submission.object_id
                for version_id in package.source_material_version_ids}
            candidate_object = self._object(
                "SOURCE-MATERIAL-OBJECT-", request.source_id)
            if candidate_object in protected_objects:
                raise OriginalMaterialError(
                    "A post-S8 source change to an S8-package source requires editorial re-review")
        stored = next(
            item for item in context if item.submission.kind is ObjectKind.TOPIC_DECISION)
        return decision, stored

    def _extract_structure(self, request: AcquisitionRequest, raw: bytes,
                           source_version_id: str,
                           source_format: SourceFormat,
                           processing_allowed: bool) -> SourceStructure:
        extractor_version = (
            f"trafilatura {trafilatura.__version__}; "
            f"lxml {'.'.join(str(value) for value in etree.LXML_VERSION)}")
        structure_id = "STRUCTURE-" + hashlib.sha256(canonical([
            source_version_id, source_format.value, extractor_version,
            request.scope.value, request.partial_locator,
            processing_allowed]).encode()).hexdigest()[:32]
        structure_version_id = self._version(
            "SOURCE-STRUCTURE-", structure_id)
        try:
            existing = self.archive.get(structure_version_id)
            if existing.submission.kind is ObjectKind.SOURCE_STRUCTURE:
                structure = SourceStructure.model_validate_json(
                    self.archive.read_body(structure_version_id))
                if (structure.source_version_id == source_version_id
                        and structure.source_sha256 == request.expected_sha256
                        and processing_allowed):
                    return structure
        except MissingVersion:
            pass
        gaps = []
        nodes = ()
        char_count = 0
        figure_count = 0
        if request.scope is AcquisitionScope.DECLARED_PARTIAL:
            gaps.append(IntakeGap(
                code=IntakeGapCode.DECLARED_PARTIAL,
                message="Only the declared source range was supplied; do not infer the rest",
                locator=request.partial_locator))
        if not processing_allowed:
            nodes = ()
            char_count = 0
            format_name = source_format.value
            gaps.append(IntakeGap(
                code=IntakeGapCode.PROCESSING_NOT_AUTHORIZED,
                message="The recorded rights do not authorize machine structure extraction"))
        elif source_format is SourceFormat.HTML:
            try:
                nodes, char_count, figure_count = _html_nodes(raw)
                extracted = trafilatura.extract(
                    raw, output_format="txt", include_comments=False,
                    include_tables=True, favor_precision=True)
                if not extracted or not extracted.strip():
                    gaps.append(IntakeGap(
                        code=IntakeGapCode.EMPTY_EXTRACTION,
                        message="Trafilatura found no usable main text in the supplied bytes"))
                elif not nodes:
                    gaps.append(IntakeGap(
                        code=IntakeGapCode.EXTRACTION_DID_NOT_COVER_FULL_RAW_TEXT,
                        message="Trafilatura returned text but no locatable structure nodes"))
            except Exception as exc:
                nodes = ()
                char_count = 0
                figure_count = 0
                gaps.append(IntakeGap(
                    code=IntakeGapCode.EMPTY_EXTRACTION,
                    message=f"HTML structure extraction failed: {exc}"))
            format_name = "HTML"
        elif source_format is SourceFormat.TEXT:
            try:
                nodes, char_count = _text_nodes(raw)
            except UnicodeDecodeError:
                gaps.append(IntakeGap(
                    code=IntakeGapCode.UNSUPPORTED_FORMAT,
                    message="Declared text source is not valid UTF-8"))
            format_name = "TEXT"
        elif source_format is SourceFormat.PDF:
            format_name = "PDF"
            gaps.append(IntakeGap(
                code=IntakeGapCode.UNSUPPORTED_FORMAT,
                message="PDF parsing is not installed; retain the exact original and use an authorized layout parser"))
            gaps.append(IntakeGap(
                code=IntakeGapCode.OCR_REQUIRED,
                message="PDF text, tables and scans were not read; use the original page before claim support",
                required_visual_check=True))
        else:
            format_name = "OTHER"
            gaps.append(IntakeGap(
                code=IntakeGapCode.UNSUPPORTED_FORMAT,
                message="No structure adapter exists for this media type"))
        for node in nodes:
            if node.kind is StructureNodeKind.TABLE:
                gaps.append(IntakeGap(
                    code=IntakeGapCode.TABLE_REQUIRES_VISUAL_CHECK,
                    message="Return to the original table before using values, units or notes",
                    locator=node.locator, required_visual_check=True))
        if figure_count:
            gaps.append(IntakeGap(
                code=IntakeGapCode.FIGURE_REQUIRES_VISUAL_CHECK,
                message="Return to the original figures/images before interpreting their content",
                required_visual_check=True))
        if not processing_allowed:
            status = StructureStatus.UNSUPPORTED
        elif source_format in (SourceFormat.HTML, SourceFormat.TEXT) and not nodes:
            status = StructureStatus.EMPTY
        elif source_format in (SourceFormat.PDF, SourceFormat.OTHER):
            status = StructureStatus.UNSUPPORTED
        elif gaps:
            status = StructureStatus.PARTIAL
        else:
            status = StructureStatus.EXTRACTED
        if not gaps and nodes and request.scope is AcquisitionScope.FULL_DOCUMENT:
            status = StructureStatus.EXTRACTED
        return SourceStructure(
            structure_id=structure_id,
            source_version_id=source_version_id,
            source_sha256=request.expected_sha256,
            source_format=source_format,
            extractor=f"{format_name} locator extractor",
            extractor_version=extractor_version,
            acquisition_scope=request.scope,
            partial_locator=request.partial_locator,
            status=status, nodes=nodes, table_count=sum(
                node.kind is StructureNodeKind.TABLE for node in nodes),
            figure_count=figure_count,
            text_character_count=char_count, gaps=tuple(gaps),
            created_at=request.acquired_at)

    def _source_version_id(self, request: AcquisitionRequest,
                           representation: Representation) -> str:
        rights_digest = hashlib.sha256(
            canonical(request.rights.model_dump(mode="json")).encode()).hexdigest()
        return self._version("SOURCE-MATERIAL-", canonical([
            request.spec_sha256, request.source_id, request.expected_sha256,
            request.media_type,
            representation.value, rights_digest]))

    def _store_source(self, request: AcquisitionRequest, raw: bytes,
                      decision_stored: StoredVersion) -> tuple[StoredVersion, bool,
                                                               list[IntakeGap]]:
        object_id = self._object("SOURCE-MATERIAL-OBJECT-", request.source_id)
        latest = self.archive.latest(object_id)
        gaps = []
        representations = []
        if MaterialUse.STORE_BODY in request.rights.allowed_uses:
            representations.append(Representation.FULL_BODY)
        representations.append(Representation.POINTER_ONLY)
        for representation in representations:
            version_id = self._source_version_id(request, representation)
            try:
                existing = self.archive.get(version_id)
                if existing.submission.kind is not ObjectKind.SOURCE_MATERIAL:
                    raise OriginalMaterialError("Source version ID belongs to another kind")
                if (existing.submission.spec_sha256 != request.spec_sha256
                        or existing.submission.title != request.title
                        or existing.submission.media_type != request.media_type
                        or existing.submission.source_locator != request.original_url
                        or existing.submission.rights != request.rights
                        or existing.submission.representation is not representation
                        or (representation is Representation.FULL_BODY
                            and existing.body_sha256 != request.expected_sha256)):
                    raise OriginalMaterialError(
                        "Existing source version identity differs from this acquisition")
                retained = (
                    representation is Representation.FULL_BODY
                    and not existing.body_retention_revoked)
                if representation is Representation.FULL_BODY and not retained:
                    gaps.append(IntakeGap(
                        code=IntakeGapCode.BODY_RETENTION_REVOKED,
                        message="The exact source body was retained but its storage grant was withdrawn"))
                    latest = self.archive.latest(object_id)
                    continue
                return existing, retained, gaps
            except MissingVersion:
                pass
            expected = {decision_stored.submission.object_id:
                        decision_stored.submission.version_id,
                        object_id: latest.submission.version_id if latest else None}
            submission = VersionSubmission(
                schema_version=2, object_id=object_id,
                version_id=version_id,
                parent_version_id=latest.submission.version_id if latest else None,
                kind=ObjectKind.SOURCE_MATERIAL,
                title=request.title, spec_sha256=request.spec_sha256,
                created_at=request.acquired_at,
                source_times=SourceTimes(
                    published=request.published_at,
                    data_period=request.data_period),
                rights=request.rights,
                representation=representation,
                source_locator=request.original_url,
                media_type=request.media_type)
            try:
                if representation is Representation.FULL_BODY:
                    stored = self.archive.append(
                        submission, raw, storage_context=request.use_context,
                        expected_current=expected)
                    return stored, True, gaps
                gaps.append(IntakeGap(
                    code=IntakeGapCode.POINTER_ONLY,
                    message="Exact bytes were inspected but not retained; only this pointer/hash remains"))
                stored = self.archive.append(
                    submission, expected_current=expected)
                return stored, False, gaps
            except PermissionDenied:
                if representation is Representation.POINTER_ONLY:
                    raise
                gaps.append(IntakeGap(
                    code=IntakeGapCode.STORAGE_NOT_AUTHORIZED,
                    message="The recorded grant does not authorize retaining this full source body"))
        raise OriginalMaterialError("No legal source representation could be recorded")

    def _append_derived(self, *, kind: ObjectKind, object_identity: str,
                        version_identity: str, title: str, created_at: datetime,
                        spec_sha256: str, body: Contract,
                        reference: VersionReference,
                        decision_stored: StoredVersion,
                        basis_records: tuple[StoredVersion, ...]) -> StoredVersion:
        kind_prefix = kind.name.replace("_", "-")
        object_id = self._object(kind_prefix + "-OBJECT-", object_identity)
        version_id = self._version(kind_prefix + "-", version_identity)
        body_bytes = canonical(body.model_dump(mode="json")).encode()
        try:
            existing = self.archive.get(version_id)
            if (existing.submission.kind is kind
                    and existing.body_sha256 == _digest_bytes(body_bytes)):
                return existing
            raise OriginalMaterialError("Derived record ID is already used by different content")
        except MissingVersion:
            pass
        latest = self.archive.latest(object_id)
        submission = VersionSubmission(
            schema_version=2, object_id=object_id, version_id=version_id,
            parent_version_id=latest.submission.version_id if latest else None,
            kind=kind, title=title, spec_sha256=spec_sha256,
            created_at=created_at, source_times=SourceTimes(),
            rights=self.journal_rights, representation=Representation.FULL_BODY,
            references=(reference,))
        expected = {
            decision_stored.submission.object_id:
                decision_stored.submission.version_id,
            object_id: latest.submission.version_id if latest else None,
        }
        for record in basis_records:
            expected[record.submission.object_id] = record.submission.version_id
        return self.archive.append(
            submission, body_bytes,
            expected_current=expected)

    def _store_structure(self, structure: SourceStructure,
                         decision_stored: StoredVersion,
                         spec_sha256: str) -> StoredVersion:
        source_version = self.archive.get(structure.source_version_id)
        return self._append_derived(
            kind=ObjectKind.SOURCE_STRUCTURE,
            object_identity=structure.structure_id,
            version_identity=structure.structure_id,
            title=f"source structure {structure.structure_id}",
            created_at=structure.created_at, spec_sha256=spec_sha256,
            body=structure,
            reference=VersionReference(
                target_version_id=source_version.submission.version_id,
                use=ReferenceUse.SOURCE, locator="exact acquired source version"),
            decision_stored=decision_stored,
            basis_records=(source_version,))

    def _store_rights(self, rights_record: RightsRecord,
                      decision_stored: StoredVersion,
                      spec_sha256: str) -> StoredVersion:
        source_version = self.archive.get(rights_record.source_version_id)
        return self._append_derived(
            kind=ObjectKind.RIGHTS_RECORD,
            object_identity=rights_record.rights_record_id,
            version_identity=rights_record.rights_record_id,
            title=f"rights record {rights_record.rights_record_id}",
            created_at=rights_record.created_at, spec_sha256=spec_sha256,
            body=rights_record,
            reference=VersionReference(
                target_version_id=rights_record.source_version_id,
                use=ReferenceUse.BASIS, locator="source rights subject"),
            decision_stored=decision_stored,
            basis_records=(source_version,))

    def _store_intake(self, intake: SourceIntake, decision_stored: StoredVersion,
                      references: tuple[VersionReference, ...],
                      basis_records: tuple[StoredVersion, ...]) -> StoredVersion:
        object_id = self._object("SOURCE-INTAKE-OBJECT-", intake.intake_id)
        version_id = self._version("SOURCE-INTAKE-", intake.intake_id)
        body_bytes = canonical(intake.model_dump(mode="json")).encode()
        try:
            existing = self.archive.get(version_id)
            if (existing.submission.kind is ObjectKind.SOURCE_INTAKE
                    and existing.body_sha256 == _digest_bytes(body_bytes)):
                return existing
            raise OriginalMaterialError("Source intake ID is already used by different content")
        except MissingVersion:
            pass
        latest = self.archive.latest(object_id)
        submission = VersionSubmission(
            schema_version=2, object_id=object_id, version_id=version_id,
            parent_version_id=latest.submission.version_id if latest else None,
            kind=ObjectKind.SOURCE_INTAKE,
            title=f"source intake {intake.source_id}",
            spec_sha256=intake.spec_sha256, created_at=intake.created_at,
            source_times=SourceTimes(),
            rights=self.journal_rights, representation=Representation.FULL_BODY,
            references=references)
        expected = {
            decision_stored.submission.object_id:
                decision_stored.submission.version_id,
            object_id: latest.submission.version_id if latest else None,
        }
        for record in basis_records:
            expected[record.submission.object_id] = record.submission.version_id
        return self.archive.append(
            submission, body_bytes,
            expected_current=expected)

    def _failed_intake(self, request: AcquisitionRequest, raw: bytes,
                       decision, decision_stored: StoredVersion,
                       source_format: SourceFormat) -> StoredVersion:
        request_sha = self._request_digest(request)
        intake_id = "INTAKE-" + hashlib.sha256(canonical([
            request.request_id, request_sha, "failed"]).encode()).hexdigest()[:32]
        intake = SourceIntake(
            intake_id=intake_id, request_id=request.request_id,
            request_sha256=request_sha, spec_sha256=request.spec_sha256,
            topic_id=request.topic_id,
            topic_decision_id=request.topic_decision_id,
            question_version_id=decision.question_version_id,
            purpose=request.purpose, source_id=request.source_id,
            title=request.title, original_url=request.original_url,
            creator=request.creator, institution=request.institution,
            language=request.language, version_label=request.version_label,
            published_at=request.published_at, data_period=request.data_period,
            source_sha256=_digest_bytes(raw), expected_sha256=request.expected_sha256,
            byte_count=len(raw), media_type=request.media_type,
            source_format=source_format, method=request.method,
            acquisition_scope=request.scope,
            partial_locator=request.partial_locator,
            status=IntakeStatus.FAILED,
            rights_id=request.rights.rights_id,
            retention=RetentionMode.NOT_CREATED,
            gaps=(IntakeGap(
                code=IntakeGapCode.EMPTY_SOURCE,
                message="No source bytes were returned; the index cannot substitute for the original"),),
            acquired_at=request.acquired_at, created_at=request.acquired_at)
        decision_version = self._version(
            "TOPIC-DECISION-", request.topic_decision_id)
        return self._store_intake(
            intake, decision_stored,
            (VersionReference(
                target_version_id=decision_version,
                use=ReferenceUse.BASIS,
                locator="source acquisition request basis"),),
            (decision_stored,))

    def ingest(self, request: AcquisitionRequest, raw: bytes) -> StoredVersion:
        if not isinstance(request, AcquisitionRequest):
            raise TypeError("ingest requires AcquisitionRequest")
        request = AcquisitionRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        if type(raw) is not bytes:
            raise TypeError("Original acquisition requires exact provided bytes")
        decision, decision_stored = self._decision(request)
        actual_sha = _digest_bytes(raw)
        if actual_sha != request.expected_sha256:
            raise OriginalMaterialError(
                f"Acquired source hash differs from the requested version: {actual_sha}")
        source_format = _infer_format(request.media_type, raw)
        if source_format is not request.expected_format:
            raise OriginalMaterialError(
                f"Acquired source format is {source_format.value}, not {request.expected_format.value}")
        if not raw:
            return self._failed_intake(
                request, raw, decision, decision_stored, source_format)
        source_stored, retained, intake_gaps = self._store_source(
            request, raw, decision_stored)
        try:
            self.archive.check_version_use(
                source_stored.submission.version_id,
                MaterialUse.MODEL_PROCESS, request.use_context)
            processing_allowed = True
        except PermissionDenied:
            processing_allowed = False
        structure = self._extract_structure(
            request, raw, source_stored.submission.version_id, source_format,
            processing_allowed)
        structure_stored = self._store_structure(
            structure, decision_stored, request.spec_sha256)
        rights_record = RightsRecord(
            rights_record_id="RIGHTS-RECORD-" + hashlib.sha256(canonical([
                source_stored.submission.version_id,
                request.rights.rights_id]).encode()).hexdigest()[:32],
            source_version_id=source_stored.submission.version_id,
            source_id=request.source_id,
            source_sha256=request.expected_sha256,
            title=request.title, original_url=request.original_url,
            retention=(RetentionMode.RETAINED if retained
                       else RetentionMode.POINTER_ONLY),
            rights=request.rights,
            created_at=source_stored.submission.created_at)
        rights_stored = self._store_rights(
            rights_record, decision_stored, request.spec_sha256)
        gaps = list(intake_gaps)
        gaps.extend(structure.gaps)
        if not retained and not any(
                gap.code is IntakeGapCode.POINTER_ONLY for gap in gaps):
            gaps.append(IntakeGap(
                code=IntakeGapCode.POINTER_ONLY,
                message="Exact source bytes were not retained"))
        status = (
            IntakeStatus.RECORDED
            if retained and not gaps and structure.status is StructureStatus.EXTRACTED
            else IntakeStatus.PARTIAL)
        request_sha = self._request_digest(request)
        intake_id = "INTAKE-" + hashlib.sha256(canonical([
            request.request_id, request_sha,
            source_stored.submission.version_id]).encode()).hexdigest()[:32]
        intake = SourceIntake(
            intake_id=intake_id, request_id=request.request_id,
            request_sha256=request_sha, spec_sha256=request.spec_sha256,
            topic_id=request.topic_id,
            topic_decision_id=request.topic_decision_id,
            question_version_id=decision.question_version_id,
            purpose=request.purpose, source_id=request.source_id,
            title=request.title, original_url=request.original_url,
            creator=request.creator, institution=request.institution,
            language=request.language, version_label=request.version_label,
            published_at=request.published_at, data_period=request.data_period,
            source_sha256=request.expected_sha256,
            expected_sha256=request.expected_sha256, byte_count=len(raw),
            media_type=request.media_type, source_format=source_format,
            method=request.method, acquisition_scope=request.scope,
            partial_locator=request.partial_locator, status=status,
            source_version_id=source_stored.submission.version_id,
            rights_record_version_id=rights_stored.submission.version_id,
            structure_version_id=structure_stored.submission.version_id,
            rights_id=request.rights.rights_id,
            retention=(RetentionMode.RETAINED if retained
                       else RetentionMode.POINTER_ONLY),
            gaps=tuple(gaps), acquired_at=request.acquired_at,
            created_at=request.acquired_at)
        decision_version = self._version(
            "TOPIC-DECISION-", request.topic_decision_id)
        return self._store_intake(
            intake, decision_stored,
            (VersionReference(
                target_version_id=decision_version,
                use=ReferenceUse.BASIS, locator="source acquisition request basis"),
            VersionReference(
                target_version_id=source_stored.submission.version_id,
                use=ReferenceUse.SOURCE, locator="exact acquired source version"),
            VersionReference(
                target_version_id=rights_stored.submission.version_id,
                use=ReferenceUse.BASIS, locator="source rights record"),
            VersionReference(
                target_version_id=structure_stored.submission.version_id,
                use=ReferenceUse.BASIS, locator="locator-only source structure"),
            ),
            (decision_stored, source_stored, rights_stored, structure_stored))

    def load_intake_version(self, intake_version_id: str) -> SourceIntake:
        stored = self.archive.get(intake_version_id)
        if stored.submission.kind is not ObjectKind.SOURCE_INTAKE:
            raise OriginalMaterialError("Requested version is not a SourceIntake")
        intake = SourceIntake.model_validate_json(
            self.archive.read_body(intake_version_id))
        if (stored.submission.version_id != self._version(
                "SOURCE-INTAKE-", intake.intake_id)
                or stored.submission.object_id != self._object(
                    "SOURCE-INTAKE-OBJECT-", intake.intake_id)
                or intake.spec_sha256 != stored.submission.spec_sha256
                or intake.created_at != stored.submission.created_at):
            raise OriginalMaterialError("Source intake identity mismatch")
        return intake

    def load_intake(self, intake_id: str) -> SourceIntake:
        return self.load_intake_version(
            self._version("SOURCE-INTAKE-", intake_id))

    def load_structure(self, structure_version_id: str) -> SourceStructure:
        stored = self.archive.get(structure_version_id)
        if stored.submission.kind is not ObjectKind.SOURCE_STRUCTURE:
            raise OriginalMaterialError("Requested version is not a SourceStructure")
        structure = SourceStructure.model_validate_json(
            self.archive.read_body(structure_version_id))
        if (stored.submission.version_id != self._version(
                "SOURCE-STRUCTURE-", structure.structure_id)
                or stored.submission.object_id != self._object(
                    "SOURCE-STRUCTURE-OBJECT-", structure.structure_id)
                or stored.submission.created_at != structure.created_at):
            raise OriginalMaterialError("Source structure identity mismatch")
        return structure

    def load_rights(self, rights_record_version_id: str) -> RightsRecord:
        stored = self.archive.get(rights_record_version_id)
        if stored.submission.kind is not ObjectKind.RIGHTS_RECORD:
            raise OriginalMaterialError("Requested version is not a RightsRecord")
        record = RightsRecord.model_validate_json(
            self.archive.read_body(rights_record_version_id))
        if stored.submission.version_id != self._version(
                "RIGHTS-RECORD-", record.rights_record_id):
            raise OriginalMaterialError("RightsRecord identity mismatch")
        if (stored.submission.object_id != self._object(
                "RIGHTS-RECORD-OBJECT-", record.rights_record_id)
                or stored.submission.created_at != record.created_at):
            raise OriginalMaterialError("RightsRecord time identity mismatch")
        return record

    def check_source_use(self, intake_id: str, intended_use: MaterialUse,
                         context: UseContext) -> tuple[str, ...]:
        intake = self.load_intake(intake_id)
        if intake.source_version_id is None:
            raise OriginalMaterialError("Failed intake has no source version")
        if intended_use is not MaterialUse.INDEX and intake.retention is not RetentionMode.RETAINED:
            raise BodyUnavailable("Source bytes were not retained under the recorded rights")
        return self.archive.check_version_use(
            intake.source_version_id, intended_use, context)

    def read_source(self, intake_id: str, intended_use: MaterialUse,
                    context: UseContext) -> ReferencedMaterial:
        intake = self.load_intake(intake_id)
        if intake.source_version_id is None:
            raise OriginalMaterialError("Failed intake has no source version")
        intake_version_id = self._version("SOURCE-INTAKE-", intake_id)
        request = ReferenceReadRequest(
            request_id="READ-" + hashlib.sha256(canonical([
                intake_id, intended_use.value, context.at.isoformat()]).encode()).hexdigest()[:32],
            spec_sha256=intake.spec_sha256, created_at=context.at,
            consumer="T04", owner_version_id=intake_version_id,
            reference=VersionReference(
                target_version_id=intake.source_version_id,
                use=ReferenceUse.SOURCE, locator="exact acquired source version"),
            expected_kind=ObjectKind.SOURCE_MATERIAL,
            intended_use=intended_use,
            expected_body_sha256=intake.source_sha256,
            use_context=context)
        material = self.archive.read_reference(request)
        if material.version.submission.version_id != intake.source_version_id:
            raise OriginalMaterialError("Reference read returned a different source version")
        return material

    @staticmethod
    def _ephemeral_nodes(raw: bytes, source_format: SourceFormat) -> tuple[StructureNode, ...]:
        if source_format is SourceFormat.HTML:
            return _html_nodes(raw)[0]
        if source_format is SourceFormat.TEXT:
            return _text_nodes(raw)[0]
        raise OriginalMaterialError("This source format has no locatable text adapter")

    def read_node(self, intake_id: str, node_id: str, intended_use: MaterialUse,
                  context: UseContext) -> SourceNodeRead:
        if intended_use is MaterialUse.INDEX:
            raise OriginalMaterialError("Reading a structure node requires a body-use permission")
        intake = self.load_intake(intake_id)
        if intake.structure_version_id is None:
            raise OriginalMaterialError("Intake has no source structure")
        material = self.read_source(intake_id, intended_use, context)
        if material.body is None:
            raise BodyUnavailable("Structure-node reads require retained source bytes")
        structure = self.load_structure(intake.structure_version_id)
        nodes = self._ephemeral_nodes(material.body, intake.source_format)
        actual = next((node for node in nodes if node.node_id == node_id), None)
        expected = next(
            (node for node in structure.nodes if node.node_id == node_id), None)
        if actual is None or expected is None or actual != expected:
            raise OriginalMaterialError("Source node locator/hash no longer matches its structure")
        if intake.source_format is SourceFormat.HTML:
            parser = lxml_html.HTMLParser(recover=True, no_network=True)
            root = lxml_html.fromstring(material.body, parser=parser)
            selected = root.xpath(actual.locator)
            if not selected:
                raise OriginalMaterialError("Source node locator no longer resolves")
            text = _normalize_text(" ".join(selected[0].itertext()))
        else:
            blocks = _text_blocks(material.body)
            if actual.ordinal > len(blocks):
                raise OriginalMaterialError("Source text node is no longer present")
            text = blocks[actual.ordinal - 1]
        if _digest_text(text) != actual.text_sha256:
            raise OriginalMaterialError("Source node text hash differs from its structure")
        return SourceNodeRead(
            intake_version_id=self._version("SOURCE-INTAKE-", intake_id),
            source_version_id=intake.source_version_id,
            structure_id=structure.structure_id, node=actual, text=text,
            original_visual_check_required=actual.requires_original_visual_check)
