"""W26 versioned selected Chinese material, source maps and update checks."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
import hashlib
from typing import Literal, Self

from pydantic import AwareDatetime, model_validator

from .archive import Archive, ArchiveError, MissingVersion, canonical
from .contracts import (Contract, Digest, Identifier, MaterialUse, NonBlank, ObjectKind,
                        ReferenceUse, Representation, RightsGrant, SourceTimes,
                        StoredVersion, UseContext, VersionReference, VersionSubmission)
from .editorial import DecisionStage, EditorialController, TopicDecisionCode
from .evidence import EvidenceController
from .original import (AcquisitionScope, OriginalMaterialController, SourceFormat,
                       StructureStatus)


class ChineseMaterialMode(str, Enum):
    EXCERPT_TRANSLATION = "EXCERPT_TRANSLATION"
    FULL_TRANSLATION = "FULL_TRANSLATION"
    INDEPENDENT_GUIDE = "INDEPENDENT_GUIDE"


class ChineseMaterialMethod(str, Enum):
    SUPPLIED_CHINESE = "SUPPLIED_CHINESE"
    AUTHORIZED_HUMAN_TRANSLATION = "AUTHORIZED_HUMAN_TRANSLATION"


class CriticalElementKind(str, Enum):
    NEGATION = "NEGATION"
    NUMBER = "NUMBER"
    UNIT_OR_DENOMINATOR = "UNIT_OR_DENOMINATOR"
    CONDITION = "CONDITION"
    TABLE_OR_FOOTNOTE = "TABLE_OR_FOOTNOTE"
    ATTRIBUTION = "ATTRIBUTION"


class UpdateAction(str, Enum):
    NO_IMPORTANT_UPDATE = "NO_IMPORTANT_UPDATE"
    UPDATE_CUTOFF_AND_REOPEN = "UPDATE_CUTOFF_AND_REOPEN"
    RETAIN_OLD_CUTOFF_AND_RESCHEDULE = "RETAIN_OLD_CUTOFF_AND_RESCHEDULE"
    RETURN_TO_W23 = "RETURN_TO_W23"
    RETURN_TO_W25 = "RETURN_TO_W25"
    CORRECTION_W34 = "CORRECTION_W34"


class OmissionRecord(Contract):
    locator: NonBlank
    reason: NonBlank


class VisualCheck(Contract):
    node_id: Identifier
    checked_by: NonBlank
    checked_at: AwareDatetime
    note: NonBlank


class CriticalElementCheck(Contract):
    element_id: Identifier
    kind: CriticalElementKind
    source_node_id: Identifier
    source_locator: NonBlank
    chinese_segment_id: Identifier
    chinese_locator: NonBlank
    checked_by: NonBlank
    checked_at: AwareDatetime
    note: NonBlank


class FullSourceAttestation(Contract):
    source_sha256: Digest
    structure_id: Identifier
    attested_by: NonBlank
    attested_at: AwareDatetime
    note: NonBlank


class ChineseSegment(Contract):
    segment_id: Identifier
    source_node_ids: tuple[Identifier, ...]
    chinese_text: NonBlank
    chinese_text_sha256: Digest

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if (not self.source_node_ids
                or len(self.source_node_ids) != len(set(self.source_node_ids))):
            raise ValueError("A Chinese segment needs unique exact source nodes")
        actual = hashlib.sha256(self.chinese_text.encode("utf-8")).hexdigest()
        if actual != self.chinese_text_sha256:
            raise ValueError("Chinese segment text does not match its declared hash")
        return self


class ChineseMaterialRequest(Contract):
    schema_version: Literal[1] = 1
    material_id: Identifier
    previous_version_id: Identifier | None = None
    theme_id: Identifier
    spec_sha256: Digest
    topic_id: Identifier
    topic_decision_id: Identifier
    evidence_version_ids: tuple[Identifier, ...]
    source_intake_version_id: Identifier
    source_structure_version_id: Identifier
    mode: ChineseMaterialMode
    selected_node_ids: tuple[Identifier, ...]
    title_zh: NonBlank
    segments: tuple[ChineseSegment, ...]
    omissions: tuple[OmissionRecord, ...] = ()
    visual_checks: tuple[VisualCheck, ...] = ()
    critical_element_checks: tuple[CriticalElementCheck, ...] = ()
    full_source_attestation: FullSourceAttestation | None = None
    knowledge_cutoff: AwareDatetime
    method: ChineseMaterialMethod
    translated_or_written_by: NonBlank
    use_context: UseContext
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        groups = (
            ("evidence", self.evidence_version_ids),
            ("selected node", self.selected_node_ids),
            ("segment", [item.segment_id for item in self.segments]),
            ("visual check", [item.node_id for item in self.visual_checks]),
            ("critical element", [item.element_id for item in self.critical_element_checks]),
        )
        for name, values in groups:
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate Chinese material {name}")
        if not self.evidence_version_ids or not self.selected_node_ids or not self.segments:
            raise ValueError("Chinese material needs evidence, selected nodes and segments")
        selected = set(self.selected_node_ids)
        if any(not set(segment.source_node_ids) <= selected for segment in self.segments):
            raise ValueError("A Chinese segment points outside the selected source nodes")
        used = {
            node_id for segment in self.segments for node_id in segment.source_node_ids}
        if used != selected:
            raise ValueError("Every selected source node needs an explicit Chinese segment")
        if self.mode is ChineseMaterialMode.FULL_TRANSLATION and self.omissions:
            raise ValueError("Full translation cannot declare omitted source ranges")
        if (self.mode is ChineseMaterialMode.FULL_TRANSLATION
                and self.full_source_attestation is None):
            raise ValueError("Full translation needs an exact full-source attestation")
        if (self.mode is not ChineseMaterialMode.FULL_TRANSLATION
                and self.full_source_attestation is not None):
            raise ValueError("Only full translation may claim full-source coverage")
        if self.mode is ChineseMaterialMode.EXCERPT_TRANSLATION and not self.omissions:
            raise ValueError("Translated excerpt must declare all omitted ranges")
        segments = {item.segment_id: item for item in self.segments}
        for check in self.critical_element_checks:
            segment = segments.get(check.chinese_segment_id)
            if segment is None or check.source_node_id not in segment.source_node_ids:
                raise ValueError(
                    "Critical-element check must bind its exact source and Chinese segment")
            if check.checked_at > self.created_at:
                raise ValueError("Critical-element check occurs after material creation")
        if (self.full_source_attestation is not None
                and self.full_source_attestation.attested_at > self.created_at):
            raise ValueError("Full-source attestation occurs after material creation")
        if self.knowledge_cutoff > self.created_at:
            raise ValueError("Chinese material cannot be created before its knowledge cutoff")
        return self


class ChineseMaterial(Contract):
    schema_version: Literal[1] = 1
    material_id: Identifier
    material_version_id: Identifier
    previous_version_id: Identifier | None
    theme_id: Identifier
    spec_sha256: Digest
    topic_id: Identifier
    topic_decision_id: Identifier
    evidence_version_ids: tuple[Identifier, ...]
    source_intake_version_id: Identifier
    source_structure_version_id: Identifier
    source_sha256: Digest
    mode: ChineseMaterialMode
    scope_label: Literal["FULL_TRANSLATION", "EXCERPT_TRANSLATION", "INDEPENDENT_GUIDE"]
    selected_node_ids: tuple[Identifier, ...]
    title_zh: NonBlank
    segments: tuple[ChineseSegment, ...]
    omissions: tuple[OmissionRecord, ...]
    visual_checks: tuple[VisualCheck, ...]
    critical_element_checks: tuple[CriticalElementCheck, ...]
    full_source_attestation: FullSourceAttestation | None
    knowledge_cutoff: AwareDatetime
    method: ChineseMaterialMethod
    translated_or_written_by: NonBlank
    complete_source_selected: bool
    facts_verified: Literal[False] = False
    causal_support: Literal[False] = False
    translation_accuracy_verified: Literal[False] = False
    accuracy_review_required: Literal[True] = True
    review_status: Literal["PENDING"] = "PENDING"
    publication_authorized: Literal[False] = False
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.complete_source_selected != (
                self.mode is ChineseMaterialMode.FULL_TRANSLATION):
            raise ValueError("Only full translation may claim complete source selection")
        expected_label = {
            ChineseMaterialMode.FULL_TRANSLATION: "FULL_TRANSLATION",
            ChineseMaterialMode.EXCERPT_TRANSLATION: "EXCERPT_TRANSLATION",
            ChineseMaterialMode.INDEPENDENT_GUIDE: "INDEPENDENT_GUIDE",
        }[self.mode]
        if self.scope_label != expected_label:
            raise ValueError("Chinese material scope label differs from its mode")
        return self


class SegmentSourceMap(Contract):
    segment_id: Identifier
    chinese_text_sha256: Digest
    source_bindings: tuple[tuple[Identifier, NonBlank, Digest], ...]

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if not self.source_bindings:
            raise ValueError("Segment source map needs at least one binding")
        return self


class SourceMap(Contract):
    schema_version: Literal[1] = 1
    source_map_id: Identifier
    material_version_id: Identifier
    source_intake_version_id: Identifier
    source_structure_version_id: Identifier
    source_sha256: Digest
    segments: tuple[SegmentSourceMap, ...]
    omissions: tuple[OmissionRecord, ...]
    visual_checks: tuple[VisualCheck, ...]
    critical_element_checks: tuple[CriticalElementCheck, ...]
    full_source_attestation: FullSourceAttestation | None
    content_verification: Literal["LOCATOR_MAPPING_ONLY"] = "LOCATOR_MAPPING_ONLY"
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        ids = [item.segment_id for item in self.segments]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("SourceMap segments must be nonempty and unique")
        return self


class ImportantUpdateRequest(Contract):
    schema_version: Literal[1] = 1
    update_check_id: Identifier
    material_version_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    observed_source_intake_version_ids: tuple[Identifier, ...] = ()
    affects_core_judgment: bool
    changes_object_scope_or_type: bool
    action: UpdateAction
    new_knowledge_cutoff: AwareDatetime | None = None
    reason: NonBlank
    next_action: NonBlank
    checked_by: NonBlank
    checked_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if len(self.observed_source_intake_version_ids) != len(
                set(self.observed_source_intake_version_ids)):
            raise ValueError("Duplicate observed update source")
        if self.changes_object_scope_or_type and self.action is not UpdateAction.RETURN_TO_W23:
            raise ValueError("Object/scope/type change must return to W23")
        if (self.action is UpdateAction.UPDATE_CUTOFF_AND_REOPEN
                and self.new_knowledge_cutoff is None):
            raise ValueError("Updating a cutoff needs the new explicit cutoff")
        if (self.action is not UpdateAction.UPDATE_CUTOFF_AND_REOPEN
                and self.new_knowledge_cutoff is not None):
            raise ValueError("Only cutoff update may carry a new cutoff")
        return self


class ImportantUpdateCheck(Contract):
    schema_version: Literal[1] = 1
    update_check_id: Identifier
    material_version_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    observed_source_intake_version_ids: tuple[Identifier, ...]
    observed_after_cutoff: bool
    affects_core_judgment: bool
    changes_object_scope_or_type: bool
    action: UpdateAction
    previous_knowledge_cutoff: AwareDatetime
    new_knowledge_cutoff: AwareDatetime | None
    reason: NonBlank
    next_action: NonBlank
    checked_by: NonBlank
    checked_at: AwareDatetime
    facts_verified: Literal[False] = False
    publication_authorized: Literal[False] = False

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if (self.observed_after_cutoff and self.affects_core_judgment
                and self.action is UpdateAction.NO_IMPORTANT_UPDATE):
            raise ValueError(
                "Post-cutoff material affecting the core cannot use NO_IMPORTANT_UPDATE")
        return self


class ChineseMaterialError(ArchiveError):
    """A selected-material record failure, never reader or review approval."""


class MaterialUpdateError(ArchiveError):
    """An update-check failure, never publication approval."""


def _digest(value) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _version(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([prefix, identity]).encode()).hexdigest()[:32]


def _object(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([identity]).encode()).hexdigest()[:32]


def _text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ChineseMaterialController:
    def __init__(self, archive: Archive, journal_rights: RightsGrant,
                 original: OriginalMaterialController | None = None,
                 evidence: EvidenceController | None = None):
        if not isinstance(archive, Archive):
            raise TypeError("ChineseMaterialController requires the shared Archive")
        if not isinstance(journal_rights, RightsGrant):
            raise TypeError("ChineseMaterialController requires an internal journal grant")
        self.archive = archive
        self.rights = journal_rights
        self.original = original or OriginalMaterialController(archive, journal_rights)
        self.evidence = evidence or EvidenceController(
            archive, journal_rights, self.original)
        self.editorial = EditorialController(archive, journal_rights)

    def _decision_in_history(self, current, decision_id: str) -> bool:
        seen = set()
        cursor = current
        while cursor is not None and cursor.decision_id not in seen:
            if cursor.decision_id == decision_id:
                return True
            seen.add(cursor.decision_id)
            cursor = (
                None if cursor.previous_decision_id is None
                else self.editorial.load_decision(cursor.previous_decision_id))
        return False

    def _validate_decision_and_source(self, request: ChineseMaterialRequest):
        try:
            decision, context = self.editorial._current_decision_context(
                request.topic_decision_id)
        except ArchiveError as exc:
            raise ChineseMaterialError(
                f"Chinese material editorial context is stale: {exc}") from exc
        if (decision.topic_id != request.topic_id
                or decision.theme_id != request.theme_id
                or decision.spec_sha256 != request.spec_sha256):
            raise ChineseMaterialError("Chinese material crosses decision topic/theme/spec")
        if (decision.stage is not DecisionStage.S8
                or decision.decision is not TopicDecisionCode.COVER):
            raise ChineseMaterialError("Chinese material may be produced only after S8 COVER")
        if request.created_at < decision.created_at:
            raise ChineseMaterialError("Chinese material predates its S8 decision")
        intake = self.original.load_intake_version(
            request.source_intake_version_id)
        if request.knowledge_cutoff < intake.acquired_at:
            raise ChineseMaterialError(
                "Chinese material knowledge cutoff predates its source acquisition")
        if any(check.checked_at < intake.acquired_at for check in (
                *request.visual_checks, *request.critical_element_checks)):
            raise ChineseMaterialError(
                "Chinese material checks cannot predate source acquisition")
        if (request.full_source_attestation is not None
                and request.full_source_attestation.attested_at < intake.acquired_at):
            raise ChineseMaterialError(
                "Full-source attestation cannot predate source acquisition")
        source_decision = self.editorial.load_decision(intake.topic_decision_id)
        if (intake.spec_sha256 != request.spec_sha256
                or source_decision.topic_id != request.topic_id
                or source_decision.theme_id != request.theme_id
                or not self._decision_in_history(decision, source_decision.decision_id)):
            raise ChineseMaterialError(
                "Chinese material source intake is not in this S8 decision history")
        if intake.structure_version_id != request.source_structure_version_id:
            raise ChineseMaterialError("Chinese material structure does not match its intake")
        structure = self.original.load_structure(
            request.source_structure_version_id)
        nodes = {node.node_id: node for node in structure.nodes}
        if not set(request.selected_node_ids) <= set(nodes):
            raise ChineseMaterialError("Selected Chinese nodes are outside the exact structure")
        for check in request.critical_element_checks:
            if check.source_locator != nodes[check.source_node_id].locator:
                raise ChineseMaterialError(
                    "Critical-element source locator differs from its exact structure node")
        evidence_records = []
        for evidence_version_id in request.evidence_version_ids:
            evidence = self.evidence.load_evidence(evidence_version_id)
            if (evidence.theme_id != request.theme_id
                    or evidence.spec_sha256 != request.spec_sha256
                    or evidence.intake_version_id != request.source_intake_version_id):
                raise ChineseMaterialError(
                    "Chinese material evidence does not bind this theme/source/spec")
            evidence_nodes = {node.node_id for node in evidence.nodes}
            if not evidence_nodes & set(request.selected_node_ids):
                raise ChineseMaterialError(
                    "Chinese material evidence has no selected source node in common")
            evidence_records.append(evidence)
        decision_stored = next(
            item for item in context if item.submission.kind is ObjectKind.TOPIC_DECISION)
        return decision, decision_stored, intake, structure, nodes, evidence_records

    def _check_visual_nodes(self, request: ChineseMaterialRequest, nodes) -> None:
        visual = {
            node_id for node_id in request.selected_node_ids
            if nodes[node_id].requires_original_visual_check}
        checked = {item.node_id for item in request.visual_checks}
        if visual != checked:
            raise ChineseMaterialError(
                "Every selected table/figure node needs one exact visual check")
        if any(item.checked_at > request.created_at for item in request.visual_checks):
            raise ChineseMaterialError("Visual check occurs after Chinese material creation")

    def _check_selection(self, request: ChineseMaterialRequest, intake, structure) -> None:
        all_node_ids = tuple(node.node_id for node in structure.nodes)
        if request.mode is ChineseMaterialMode.FULL_TRANSLATION:
            if intake.acquisition_scope is not AcquisitionScope.FULL_DOCUMENT:
                raise ChineseMaterialError("Full translation requires full source acquisition")
            if (structure.status is not StructureStatus.EXTRACTED or structure.gaps
                    or set(request.selected_node_ids) != set(all_node_ids)):
                raise ChineseMaterialError(
                    "Full translation requires a complete gap-free structure and all nodes")
            if (request.full_source_attestation is None
                    or request.full_source_attestation.source_sha256 != intake.source_sha256
                    or request.full_source_attestation.structure_id != structure.structure_id):
                raise ChineseMaterialError(
                    "Full translation attestation does not bind this exact source and structure")
        elif request.mode is ChineseMaterialMode.EXCERPT_TRANSLATION:
            if set(request.selected_node_ids) == set(all_node_ids) and not request.omissions:
                raise ChineseMaterialError(
                    "A translation selecting every node should be labelled full or explain why not")

    def append_material(self, request: ChineseMaterialRequest) -> StoredVersion:
        if not isinstance(request, ChineseMaterialRequest):
            raise TypeError("append_material requires ChineseMaterialRequest")
        request = ChineseMaterialRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        decision, decision_stored, intake, structure, nodes, evidence_records = (
            self._validate_decision_and_source(request))
        self._check_visual_nodes(request, nodes)
        self._check_selection(request, intake, structure)
        intended_use = (
            MaterialUse.MODEL_PROCESS
            if request.mode is ChineseMaterialMode.INDEPENDENT_GUIDE
            else MaterialUse.TRANSLATE)
        for node_id in request.selected_node_ids:
            self.original.read_node(
                intake.intake_id, node_id, intended_use, request.use_context)
        content_hash = _digest(request.model_dump(mode="json"))
        material_version_id = _version("CHINESE-MATERIAL-", canonical([
            request.material_id, request.previous_version_id, content_hash]))
        material = ChineseMaterial(
            material_id=request.material_id,
            material_version_id=material_version_id,
            previous_version_id=request.previous_version_id,
            theme_id=request.theme_id, spec_sha256=request.spec_sha256,
            topic_id=request.topic_id,
            topic_decision_id=request.topic_decision_id,
            evidence_version_ids=request.evidence_version_ids,
            source_intake_version_id=request.source_intake_version_id,
            source_structure_version_id=request.source_structure_version_id,
            source_sha256=intake.source_sha256,
            mode=request.mode,
            scope_label={
                ChineseMaterialMode.FULL_TRANSLATION: "FULL_TRANSLATION",
                ChineseMaterialMode.EXCERPT_TRANSLATION: "EXCERPT_TRANSLATION",
                ChineseMaterialMode.INDEPENDENT_GUIDE: "INDEPENDENT_GUIDE",
            }[request.mode],
            selected_node_ids=request.selected_node_ids,
            title_zh=request.title_zh, segments=request.segments,
            omissions=request.omissions, visual_checks=request.visual_checks,
            critical_element_checks=request.critical_element_checks,
            full_source_attestation=request.full_source_attestation,
            knowledge_cutoff=request.knowledge_cutoff,
            method=request.method,
            translated_or_written_by=request.translated_or_written_by,
            complete_source_selected=(
                request.mode is ChineseMaterialMode.FULL_TRANSLATION),
            created_at=request.created_at)
        object_id = _object("CHINESE-MATERIAL-OBJECT-", request.material_id)
        try:
            existing = self.archive.get(material_version_id)
            if (existing.submission.kind is ObjectKind.CHINESE_MATERIAL
                    and existing.body_sha256 == _digest(
                        canonical(material.model_dump(mode="json")).encode())):
                material_stored = existing
            else:
                raise ChineseMaterialError("Material version ID is already in use")
        except MissingVersion:
            latest = self.archive.latest(object_id)
            if request.previous_version_id is None:
                if latest is not None:
                    raise ChineseMaterialError(
                        "Existing Chinese material history requires previous_version_id")
            elif latest is None or latest.submission.version_id != request.previous_version_id:
                raise ChineseMaterialError("Chinese material previous version is not current")
            references = [
                VersionReference(
                    target_version_id=decision_stored.submission.version_id,
                    use=ReferenceUse.BASIS, locator="current S8 COVER"),
                VersionReference(
                    target_version_id=request.source_intake_version_id,
                    use=ReferenceUse.SOURCE, locator="exact selected source intake"),
                VersionReference(
                    target_version_id=request.source_structure_version_id,
                    use=ReferenceUse.SUPPORT, locator="exact source locator map"),
                *(
                    VersionReference(
                        target_version_id=evidence_id,
                        use=ReferenceUse.SUPPORT, locator=f"selected evidence {index}")
                    for index, evidence_id in enumerate(request.evidence_version_ids)
                ),
            ]
            expected = {
                decision_stored.submission.object_id:
                    decision_stored.submission.version_id,
                object_id: latest.submission.version_id if latest else None,
                _object("SOURCE-INTAKE-OBJECT-", intake.intake_id):
                    request.source_intake_version_id,
                _object("SOURCE-STRUCTURE-OBJECT-", structure.structure_id):
                    request.source_structure_version_id,
            }
            for evidence_id in request.evidence_version_ids:
                evidence_stored = self.archive.get(evidence_id)
                expected[evidence_stored.submission.object_id] = evidence_stored.submission.version_id
            submission = VersionSubmission(
                schema_version=2, object_id=object_id,
                version_id=material_version_id,
                parent_version_id=request.previous_version_id,
                kind=ObjectKind.CHINESE_MATERIAL,
                title=f"Chinese material {request.material_id}",
                spec_sha256=request.spec_sha256,
                created_at=request.created_at, source_times=SourceTimes(),
                rights=self.rights, representation=Representation.FULL_BODY,
                references=tuple(references))
            material_stored = self.archive.append(
                submission,
                canonical(material.model_dump(mode="json")).encode(),
                expected_current=expected)
        source_map_id = _version(
            "SOURCE-MAP-", material_version_id)
        source_map = SourceMap(
            source_map_id=source_map_id,
            material_version_id=material_version_id,
            source_intake_version_id=request.source_intake_version_id,
            source_structure_version_id=request.source_structure_version_id,
            source_sha256=intake.source_sha256,
            segments=tuple(
                SegmentSourceMap(
                    segment_id=segment.segment_id,
                    chinese_text_sha256=segment.chinese_text_sha256,
                    source_bindings=tuple(
                        (node_id, nodes[node_id].locator, nodes[node_id].text_sha256)
                        for node_id in segment.source_node_ids))
                for segment in request.segments),
            omissions=request.omissions,
            visual_checks=request.visual_checks,
            critical_element_checks=request.critical_element_checks,
            full_source_attestation=request.full_source_attestation,
            created_at=request.created_at)
        map_object = _object("SOURCE-MAP-OBJECT-", source_map_id)
        map_version = _version("SOURCE-MAP-", source_map_id)
        source_map_bytes = canonical(source_map.model_dump(mode="json")).encode()
        try:
            existing_map = self.archive.get(map_version)
            if (existing_map.submission.kind is not ObjectKind.SOURCE_MAP
                    or existing_map.body_sha256 != _digest(source_map_bytes)):
                raise ChineseMaterialError(
                    "SourceMap version ID is already used by different content")
        except MissingVersion:
            map_expected = {
                material_stored.submission.object_id:
                    material_stored.submission.version_id,
                map_object: None,
                _object("SOURCE-INTAKE-OBJECT-", intake.intake_id):
                    request.source_intake_version_id,
                _object("SOURCE-STRUCTURE-OBJECT-", structure.structure_id):
                    request.source_structure_version_id,
            }
            map_submission = VersionSubmission(
                schema_version=2, object_id=map_object,
                version_id=map_version, kind=ObjectKind.SOURCE_MAP,
                title=f"source map {material_version_id}",
                spec_sha256=request.spec_sha256,
                created_at=request.created_at, source_times=SourceTimes(),
                rights=self.rights, representation=Representation.FULL_BODY,
                references=(
                    VersionReference(
                        target_version_id=material_version_id,
                        use=ReferenceUse.REVIEW_OF, locator="exact Chinese material"),
                    VersionReference(
                        target_version_id=request.source_intake_version_id,
                        use=ReferenceUse.SOURCE, locator="source intake"),
                    VersionReference(
                        target_version_id=request.source_structure_version_id,
                        use=ReferenceUse.SUPPORT, locator="source structure"),
                ))
            self.archive.append(
                map_submission,
                source_map_bytes,
                expected_current=map_expected)
        return material_stored

    def load_material(self, material_version_id: str) -> ChineseMaterial:
        stored = self.archive.get(material_version_id)
        if stored.submission.kind is not ObjectKind.CHINESE_MATERIAL:
            raise ChineseMaterialError("Requested version is not ChineseMaterial")
        material = ChineseMaterial.model_validate_json(
            self.archive.read_body(material_version_id))
        if (material.material_version_id != material_version_id
                or stored.submission.spec_sha256 != material.spec_sha256
                or stored.submission.created_at != material.created_at):
            raise ChineseMaterialError("Chinese material identity mismatch")
        return material

    def load_source_map(self, material_version_id: str) -> SourceMap:
        source_map_id = _version("SOURCE-MAP-", material_version_id)
        map_version = _version("SOURCE-MAP-", source_map_id)
        stored = self.archive.get(map_version)
        if stored.submission.kind is not ObjectKind.SOURCE_MAP:
            raise ChineseMaterialError("Requested version is not a SourceMap")
        source_map = SourceMap.model_validate_json(
            self.archive.read_body(map_version))
        if (source_map.material_version_id != material_version_id
                or stored.submission.version_id != _version(
                    "SOURCE-MAP-", source_map.source_map_id)
                or stored.submission.object_id != _object(
                    "SOURCE-MAP-OBJECT-", source_map.source_map_id)
                or stored.submission.spec_sha256 != self.load_material(
                    material_version_id).spec_sha256
                or stored.submission.created_at != source_map.created_at):
            raise ChineseMaterialError("SourceMap identity mismatch")
        return source_map

    def append_update_check(
            self, request: ImportantUpdateRequest) -> StoredVersion:
        if not isinstance(request, ImportantUpdateRequest):
            raise TypeError("append_update_check requires ImportantUpdateRequest")
        request = ImportantUpdateRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        material = self.load_material(request.material_version_id)
        if (material.theme_id != request.theme_id
                or material.spec_sha256 != request.spec_sha256):
            raise MaterialUpdateError("Update check and Chinese material theme/spec differ")
        if request.checked_at < material.created_at:
            raise MaterialUpdateError("Update check predates the material")
        observed_after = False
        intake_stored = []
        for intake_id in request.observed_source_intake_version_ids:
            intake = self.original.load_intake_version(intake_id)
            if intake.spec_sha256 != request.spec_sha256:
                raise MaterialUpdateError("Observed update source uses another specification")
            if intake.acquired_at > request.checked_at:
                raise MaterialUpdateError("Update check predates an observed source acquisition")
            observed_after = observed_after or (
                intake.acquired_at > material.knowledge_cutoff)
            intake_stored.append(self.archive.get(intake_id))
        if (observed_after and request.affects_core_judgment
                and request.action is UpdateAction.NO_IMPORTANT_UPDATE):
            raise MaterialUpdateError(
                "Post-cutoff material affecting core judgment cannot be marked no update")
        if (request.action is UpdateAction.UPDATE_CUTOFF_AND_REOPEN
                and request.new_knowledge_cutoff <= material.knowledge_cutoff):
            raise MaterialUpdateError("Updated knowledge cutoff must advance")
        if (request.new_knowledge_cutoff is not None
                and request.new_knowledge_cutoff > request.checked_at):
            raise MaterialUpdateError("New knowledge cutoff cannot postdate the update check")
        check = ImportantUpdateCheck(
            update_check_id=request.update_check_id,
            material_version_id=request.material_version_id,
            theme_id=request.theme_id, spec_sha256=request.spec_sha256,
            observed_source_intake_version_ids=request.observed_source_intake_version_ids,
            observed_after_cutoff=observed_after,
            affects_core_judgment=request.affects_core_judgment,
            changes_object_scope_or_type=request.changes_object_scope_or_type,
            action=request.action,
            previous_knowledge_cutoff=material.knowledge_cutoff,
            new_knowledge_cutoff=request.new_knowledge_cutoff,
            reason=request.reason, next_action=request.next_action,
            checked_by=request.checked_by, checked_at=request.checked_at)
        version_id = _version("UPDATE-CHECK-", request.update_check_id)
        object_id = _object("UPDATE-CHECK-OBJECT-", request.update_check_id)
        references = [VersionReference(
            target_version_id=request.material_version_id,
            use=ReferenceUse.REVIEW_OF, locator="exact Chinese material"),
            *(
                VersionReference(
                    target_version_id=intake_id,
                    use=ReferenceUse.SOURCE, locator=f"observed update source {index}")
                for index, intake_id in enumerate(
                    request.observed_source_intake_version_ids)
            ),
        ]
        expected = {object_id: None}
        material_stored = self.archive.get(request.material_version_id)
        expected[material_stored.submission.object_id] = material_stored.submission.version_id
        for stored in intake_stored:
            expected[stored.submission.object_id] = stored.submission.version_id
        submission = VersionSubmission(
            schema_version=2, object_id=object_id, version_id=version_id,
            kind=ObjectKind.IMPORTANT_UPDATE_CHECK,
            title=f"important update check {request.update_check_id}",
            spec_sha256=request.spec_sha256, created_at=request.checked_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY,
            references=tuple(references))
        return self.archive.append(
            submission, canonical(check.model_dump(mode="json")).encode(),
            expected_current=expected)

    def load_update_check(self, update_check_version_id: str) -> ImportantUpdateCheck:
        stored = self.archive.get(update_check_version_id)
        if stored.submission.kind is not ObjectKind.IMPORTANT_UPDATE_CHECK:
            raise MaterialUpdateError("Requested version is not an ImportantUpdateCheck")
        check = ImportantUpdateCheck.model_validate_json(
            self.archive.read_body(update_check_version_id))
        if (stored.submission.version_id != _version(
                "UPDATE-CHECK-", check.update_check_id)
                or stored.submission.object_id != _object(
                    "UPDATE-CHECK-OBJECT-", check.update_check_id)
                or stored.submission.spec_sha256 != check.spec_sha256
                or stored.submission.created_at != check.checked_at):
            raise MaterialUpdateError("Update check identity mismatch")
        return check
