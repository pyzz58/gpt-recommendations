"""W26 owned-fixture tests for Chinese material scope and update isolation."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from pydantic import ValidationError

from intelligence.archive import Archive, ArchiveError, PermissionDenied
from intelligence.contracts import (DataPeriod, MaterialUse, ObjectKind,
                                    PermissionState, Precision, Representation,
                                    RightsBasis, RightsGrant, Scope, ScopeMode,
                                    TimePoint, UseContext, UsePermission,
                                    ValidityMode, VersionSubmission)
from intelligence.discovery import (CandidateHint, EventClusterController, EventClusterer,
                                    LineageRole)
from intelligence.editorial import (ArticleType, DecisionStage, EditorialController,
                                    PublicationBasis, S8PrerequisitePackage,
                                    TopicDecision, TopicDecisionCode, ValueBasis)
from intelligence.evidence import EvidenceController, EvidenceNature, EvidenceRequest
from intelligence.materials import (ChineseMaterialController, ChineseMaterialError,
                                    ChineseMaterialMethod, ChineseMaterialMode,
                                    ChineseMaterialRequest, ChineseSegment,
                                    CriticalElementCheck, CriticalElementKind,
                                    FullSourceAttestation,
                                    ImportantUpdateRequest, MaterialUpdateError,
                                    OmissionRecord, UpdateAction)
from intelligence.original import (AcquisitionMethod, AcquisitionPurpose,
                                   AcquisitionRequest, AcquisitionScope,
                                   OriginalMaterialController, SourceFormat)
from intelligence.sources import (PermissionStateW20, SourceAdapter,
                                  SourceAdapterController, SourceDescriptor, SourceType)

BASE = datetime(2026, 10, 31, 0, 0, tzinfo=timezone.utc)
SPEC = "a" * 64
TITLE_A = "Owned source A"
URL_A = "https://example.invalid/w26-a"
RAW_A = (
    b"Owned first paragraph says the trial was not approved.\n\n"
    b"Owned second paragraph records 42 tonnes in September 2026.")
TITLE_B = "Owned source B"
URL_B = "https://example.invalid/w26-b"
RAW_B = b"Owned guide source records a separate non-translated observation."
PERIOD = DataPeriod(
    start=datetime(2026, 9, 1, tzinfo=timezone.utc),
    end_exclusive=datetime(2026, 10, 1, tzinfo=timezone.utc),
    source_timezone="UTC", provenance="Owned W26 period")


class ChineseMaterialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Archive(Path(self.temp.name) / "archive")
        self.addCleanup(self.archive.close)
        self.journal_rights = self.rights(
            "RIGHTS-W26-JOURNAL", "Owned W26 journal",
            "https://example.invalid/w26-journal",
            allowed={MaterialUse.INDEX, MaterialUse.STORE_BODY})
        self.original = OriginalMaterialController(
            self.archive, self.journal_rights)
        self.evidence = EvidenceController(
            self.archive, self.journal_rights, self.original)
        self.materials = ChineseMaterialController(
            self.archive, self.journal_rights, self.original, self.evidence)
        self.question = self.archive.append(VersionSubmission(
            object_id="QUESTION-W26", version_id="QUESTION-W26-v001",
            kind=ObjectKind.QUESTION_VERSION, title="Owned W26 question",
            spec_sha256=SPEC, created_at=BASE,
            rights=self.journal_rights,
            representation=Representation.FULL_BODY),
            b"Owned W26 question fixture")
        self.index_a = self.candidate_index("SRC-W26-A", TITLE_A, URL_A)
        self.index_b = self.candidate_index("SRC-W26-B", TITLE_B, URL_B)
        source_controller = SourceAdapterController(
            self.archive, self.journal_rights)
        source_controller.append_index(self.index_a)
        source_controller.append_index(self.index_b)
        self.proposal = self.discovery_review()
        EventClusterController(
            self.archive, self.journal_rights).append_proposal(self.proposal)
        self.cluster = self.proposal.clusters[0]
        self.s7 = TopicDecision(
            decision_id="DECISION-W26-S7", topic_id="TOPIC-W26",
            theme_id="THEME-W26", edition_id="EDITION-W42",
            spec_sha256=SPEC,
            discovery_proposal_id=self.proposal.proposal_id,
            question_version_id="QUESTION-W26-v001",
            candidate_index_ids=(self.index_a.index_id, self.index_b.index_id),
            candidate_ids=tuple(
                index.candidates[0].candidate_id
                for index in (self.index_a, self.index_b)),
            cluster_ids=(self.cluster.cluster_id,),
            stage=DecisionStage.S7,
            publication_basis=PublicationBasis.CURRENT_WEEK,
            article_type=ArticleType.SOURCE_SELECTION,
            value_bases=(ValueBasis.RESEARCH_VALUE,),
            decision=TopicDecisionCode.WATCH,
            reasons=("Owned Chinese material preparation requires S8",),
            next_action="Acquire exact sources and return to S8",
            created_at=BASE + timedelta(seconds=2))
        self.editorial = EditorialController(
            self.archive, self.journal_rights)
        self.editorial.append_decision(self.s7)
        self.acquired_a = BASE + timedelta(seconds=30)
        self.acquired_b = BASE + timedelta(seconds=40)
        self.intake_a = self.acquire(
            "SRC-W26-A", TITLE_A, URL_A, RAW_A, self.acquired_a,
            purpose=AcquisitionPurpose.S8_PREREQUISITE,
            decision_id=self.s7.decision_id,
            translate=True)
        self.intake_b = self.acquire(
            "SRC-W26-B", TITLE_B, URL_B, RAW_B, self.acquired_b,
            purpose=AcquisitionPurpose.S8_PREREQUISITE,
            decision_id=self.s7.decision_id,
            translate=False)
        self.use_context = UseContext(
            at=BASE + timedelta(minutes=5), provider="owned-w26",
            territory="NZ", content=("owned-w26",))
        self.evidence_a = self.evidence.append_evidence(EvidenceRequest(
            evidence_id="EVIDENCE-W26-A", theme_id="THEME-W26",
            spec_sha256=SPEC,
            intake_version_id=self.intake_a_version,
            structure_version_id=self.intake_a.structure_version_id,
            lineage_proposal_id=self.proposal.proposal_id,
            cluster_id=self.cluster.cluster_id,
            node_ids=(self.structure_a.nodes[0].node_id,),
            nature=EvidenceNature.DOCUMENTED_FACT,
            use_context=UseContext(
                at=BASE + timedelta(minutes=1), provider="owned-w26",
                territory="NZ", content=("owned-w26",)),
            created_at=BASE + timedelta(minutes=2)))
        self.evidence_b = self.evidence.append_evidence(EvidenceRequest(
            evidence_id="EVIDENCE-W26-B", theme_id="THEME-W26",
            spec_sha256=SPEC,
            intake_version_id=self.intake_b_version,
            structure_version_id=self.intake_b.structure_version_id,
            lineage_proposal_id=self.proposal.proposal_id,
            cluster_id=self.cluster.cluster_id,
            node_ids=(self.structure_b.nodes[0].node_id,),
            nature=EvidenceNature.DOCUMENTED_FACT,
            use_context=UseContext(
                at=BASE + timedelta(minutes=1), provider="owned-w26",
                territory="NZ", content=("owned-w26",)),
            created_at=BASE + timedelta(minutes=2, seconds=10)))
        reading = self.archive.append(VersionSubmission(
            object_id="READING-W26", version_id="READING-W26-v001",
            kind=ObjectKind.READING_SCOPE_PLAN,
            title="Owned W26 reading plan", spec_sha256=SPEC,
            created_at=BASE + timedelta(minutes=2, seconds=20),
            rights=self.journal_rights,
            representation=Representation.FULL_BODY),
            b"Owned W26 reading plan")
        package = S8PrerequisitePackage(
            package_id="PACKAGE-W26", topic_id="TOPIC-W26",
            edition_id="EDITION-W42", spec_sha256=SPEC,
            discovery_proposal_id=self.proposal.proposal_id,
            question_version_id="QUESTION-W26-v001",
            source_material_version_ids=(
                self.intake_a.source_version_id,
                self.intake_b.source_version_id),
            evidence_version_ids=(
                self.evidence_a.submission.version_id,
                self.evidence_b.submission.version_id),
            rights_record_version_ids=(
                self.intake_a.rights_record_version_id,
                self.intake_b.rights_record_version_id),
            reading_plan_version_id=reading.submission.version_id,
            limitations=("Owned synthetic S8 package",),
            candidate_index_ids=(self.index_a.index_id, self.index_b.index_id),
            created_at=BASE + timedelta(minutes=3))
        self.editorial.append_package(package)
        self.cover = TopicDecision(
            decision_id="DECISION-W26-S8-COVER", topic_id="TOPIC-W26",
            theme_id="THEME-W26", edition_id="EDITION-W42",
            spec_sha256=SPEC,
            discovery_proposal_id=self.proposal.proposal_id,
            question_version_id="QUESTION-W26-v001",
            candidate_index_ids=(self.index_a.index_id, self.index_b.index_id),
            candidate_ids=tuple(
                index.candidates[0].candidate_id
                for index in (self.index_a, self.index_b)),
            cluster_ids=(self.cluster.cluster_id,),
            stage=DecisionStage.S8,
            publication_basis=PublicationBasis.CURRENT_WEEK,
            article_type=ArticleType.SOURCE_SELECTION,
            value_bases=(ValueBasis.RESEARCH_VALUE,),
            decision=TopicDecisionCode.COVER,
            reasons=("Owned S8 source selection cover",),
            previous_decision_id=self.s7.decision_id,
            s8_package_id=package.package_id,
            created_at=BASE + timedelta(minutes=4))
        self.editorial.append_decision(self.cover)
        self.intake_a_version = self.original._version(
            "SOURCE-INTAKE-", self.intake_a.intake_id)
        self.intake_b_version = self.original._version(
            "SOURCE-INTAKE-", self.intake_b.intake_id)

    def rights(self, rights_id, title, url, *, allowed):
        permissions = tuple(UsePermission(
            use=use, state=PermissionState.ALLOWED,
            validity=ValidityMode.OPEN_ENDED,
            territories=Scope(mode=ScopeMode.ANY),
            providers=Scope(mode=ScopeMode.ANY),
            content_scope=Scope(mode=ScopeMode.ANY))
            for use in allowed if use is not MaterialUse.INDEX)
        return RightsGrant(
            rights_id=rights_id, basis=RightsBasis.LICENSE,
            allowed_uses=frozenset(allowed),
            evidence="Owned synthetic W26 rights", checked_by="test fixture",
            checked_at=BASE, work_title=title, source_locator=url,
            terms_url="https://example.invalid/w26-terms",
            terms_version="fixture-v1", grantor="Owned source author",
            permissions=permissions)

    def candidate_index(self, source_id, title, url):
        source = SourceDescriptor(
            source_id=source_id, name=title, source_url=url,
            source_type=SourceType.JSON_API, language="en", region="NZ",
            sector="fixture", ownership="Owned source owner",
            permission_state=PermissionStateW20.CLEARED,
            permission_evidence="Owned synthetic W26 source")
        raw = json.dumps({"items": [{
            "id": source_id, "title": title, "url": url,
            "summary": "Owned W26 clue", "published_at": "2026-10-30"}]}).encode()
        return SourceAdapter().parse(
            source, raw, acquired_at=BASE, content_type="application/json",
            spec_sha256=SPEC)

    def discovery_review(self):
        return EventClusterer().build(
            (self.index_a, self.index_b),
            (
                CandidateHint(
                    candidate_index_id=self.index_a.index_id,
                    candidate_id=self.index_a.candidates[0].candidate_id,
                    event_key="EVENT-W26", lineage_role=LineageRole.ORIGINAL,
                    lineage_root_ids=("ROOT-W26-A",), note="Owned root A"),
                CandidateHint(
                    candidate_index_id=self.index_b.index_id,
                    candidate_id=self.index_b.candidates[0].candidate_id,
                    event_key="EVENT-W26", lineage_role=LineageRole.ORIGINAL,
                    lineage_root_ids=("ROOT-W26-B",), note="Owned root B"),
            ),
            proposal_id="DISCOVERY-W26", spec_sha256=SPEC,
            created_at=BASE + timedelta(seconds=1))

    def acquire(self, source_id, title, url, raw, acquired_at, *, purpose,
                decision_id, translate):
        allowed = {MaterialUse.INDEX, MaterialUse.STORE_BODY,
                   MaterialUse.MODEL_PROCESS}
        if translate:
            allowed.add(MaterialUse.TRANSLATE)
        rights = self.rights(
            "RIGHTS-" + source_id, title, url, allowed=allowed)
        request = AcquisitionRequest(
            request_id="REQUEST-" + source_id, spec_sha256=SPEC,
            topic_id="TOPIC-W26", topic_decision_id=decision_id,
            purpose=purpose, source_id=source_id, title=title,
            original_url=url, creator="Owned source author",
            institution="Owned source institution", language="en",
            version_label="fixture-v1", media_type="text/plain",
            expected_format=SourceFormat.TEXT,
            expected_sha256=hashlib.sha256(raw).hexdigest(),
            method=AcquisitionMethod.PROVIDED_BYTES,
            acquired_at=acquired_at, scope=AcquisitionScope.FULL_DOCUMENT,
            published_at=TimePoint(
                precision=Precision.DATE, value="2026-10-30"),
            data_period=PERIOD, rights=rights,
            use_context=UseContext(
                at=acquired_at, provider="owned-w26", territory="NZ",
                content=("owned-w26",)),
            created_at=acquired_at)
        stored = self.original.ingest(request, raw)
        intake = self.original.load_intake_version(stored.submission.version_id)
        if source_id == "SRC-W26-A":
            self.intake_a_version = stored.submission.version_id
            self.structure_a = self.original.load_structure(
                intake.structure_version_id)
        elif source_id == "SRC-W26-B":
            self.intake_b_version = stored.submission.version_id
            self.structure_b = self.original.load_structure(
                intake.structure_version_id)
        return intake

    @staticmethod
    def segment(segment_id, node_ids, text):
        return ChineseSegment(
            segment_id=segment_id, source_node_ids=tuple(node_ids),
            chinese_text=text,
            chinese_text_sha256=hashlib.sha256(
                text.encode("utf-8")).hexdigest())

    def base_request(self, material_id="MATERIAL-W26-A", *, intake,
                     structure, evidence_id, mode, selected, segments,
                     omissions=(), critical=(), title="自有材料中文版",
                     use_context=None, full_attestation=None):
        return ChineseMaterialRequest(
            material_id=material_id, theme_id="THEME-W26",
            spec_sha256=SPEC, topic_id="TOPIC-W26",
            topic_decision_id=self.cover.decision_id,
            evidence_version_ids=(evidence_id,),
            source_intake_version_id=(
                self.intake_a_version if intake.source_id == "SRC-W26-A"
                else self.intake_b_version),
            source_structure_version_id=structure.structure_id if False else
                intake.structure_version_id,
            mode=mode, selected_node_ids=tuple(selected), title_zh=title,
            segments=tuple(segments), omissions=tuple(omissions),
            critical_element_checks=tuple(critical),
            full_source_attestation=full_attestation,
            knowledge_cutoff=intake.acquired_at,
            method=ChineseMaterialMethod.SUPPLIED_CHINESE,
            translated_or_written_by="owned synthetic fixture author",
            use_context=use_context or self.use_context,
            created_at=BASE + timedelta(minutes=5))

    def test_excerpt_translation_and_source_map_are_exact(self):
        node = self.structure_a.nodes[0]
        request = self.base_request(
            intake=self.intake_a, structure=self.structure_a,
            evidence_id=self.evidence_a.submission.version_id,
            mode=ChineseMaterialMode.EXCERPT_TRANSLATION,
            selected=(node.node_id,),
            segments=(self.segment(
                "SEG-W26-EXCERPT", (node.node_id,),
                "自有译文：试验未获批准。"),),
            critical=(CriticalElementCheck(
                element_id="ELEMENT-W26-NEGATION",
                kind=CriticalElementKind.NEGATION,
                source_node_id=node.node_id,
                source_locator=node.locator,
                chinese_segment_id="SEG-W26-EXCERPT",
                chinese_locator="译文：未获批准",
                checked_by="owned test translator",
                checked_at=BASE + timedelta(minutes=4, seconds=50),
                note="Owned negation preserved"),),
            omissions=(OmissionRecord(
                locator=self.structure_a.nodes[1].locator,
                reason="只摘与本题限制有关的否定句"),))
        stored = self.materials.append_material(request)
        material = self.materials.load_material(stored.submission.version_id)
        source_map = self.materials.load_source_map(stored.submission.version_id)
        self.assertEqual(material.scope_label, "EXCERPT_TRANSLATION")
        self.assertFalse(material.complete_source_selected)
        self.assertTrue(material.accuracy_review_required)
        self.assertFalse(material.translation_accuracy_verified)
        self.assertFalse(material.facts_verified)
        self.assertEqual(material.segments[0].chinese_text,
                         "自有译文：试验未获批准。")
        self.assertEqual(material.critical_element_checks[0].kind,
                         CriticalElementKind.NEGATION)
        self.assertEqual(source_map.source_intake_version_id,
                         self.intake_a_version)
        self.assertEqual(source_map.segments[0].source_bindings[0],
                         (node.node_id, node.locator, node.text_sha256))
        self.assertEqual(self.materials.append_material(request).submission.version_id,
                         stored.submission.version_id)

    def test_full_translation_requires_all_nodes_and_complete_source(self):
        segments = tuple(
            self.segment(f"SEG-W26-FULL-{index}", (node.node_id,), text)
            for index, (node, text) in enumerate(zip(
                self.structure_a.nodes,
                ("自有译文第一段。", "自有译文第二段记录42吨。")), start=1))
        attestation = FullSourceAttestation(
            source_sha256=self.intake_a.source_sha256,
            structure_id=self.structure_a.structure_id,
            attested_by="owned test source checker",
            attested_at=BASE + timedelta(minutes=4, seconds=40),
            note="Owned plain-text source is fully represented")
        request = self.base_request(
            material_id="MATERIAL-W26-FULL", intake=self.intake_a,
            structure=self.structure_a,
            evidence_id=self.evidence_a.submission.version_id,
            mode=ChineseMaterialMode.FULL_TRANSLATION,
            selected=tuple(node.node_id for node in self.structure_a.nodes),
            segments=segments,
            critical=(
                CriticalElementCheck(
                    element_id="ELEMENT-W26-FULL-NUMBER",
                    kind=CriticalElementKind.NUMBER,
                    source_node_id=self.structure_a.nodes[1].node_id,
                    source_locator=self.structure_a.nodes[1].locator,
                    chinese_segment_id="SEG-W26-FULL-2",
                    chinese_locator="42吨", checked_by="owned test translator",
                    checked_at=BASE + timedelta(minutes=4, seconds=50),
                    note="Owned number preserved"),
                CriticalElementCheck(
                    element_id="ELEMENT-W26-FULL-UNIT",
                    kind=CriticalElementKind.UNIT_OR_DENOMINATOR,
                    source_node_id=self.structure_a.nodes[1].node_id,
                    source_locator=self.structure_a.nodes[1].locator,
                    chinese_segment_id="SEG-W26-FULL-2",
                    chinese_locator="42吨", checked_by="owned test translator",
                    checked_at=BASE + timedelta(minutes=4, seconds=50),
                    note="Owned unit preserved"),
            ),
            full_attestation=attestation,
            title="自有全文中文版")
        stored = self.materials.append_material(request)
        material = self.materials.load_material(stored.submission.version_id)
        self.assertEqual(material.scope_label, "FULL_TRANSLATION")
        self.assertTrue(material.complete_source_selected)
        incomplete = self.base_request(
            material_id="MATERIAL-W26-FULL-BAD", intake=self.intake_a,
            structure=self.structure_a,
            evidence_id=self.evidence_a.submission.version_id,
            mode=ChineseMaterialMode.FULL_TRANSLATION,
            selected=(self.structure_a.nodes[0].node_id,),
            segments=(self.segment(
                "SEG-W26-FULL-BAD", (self.structure_a.nodes[0].node_id,),
                "不完整全文。"),),
            full_attestation=attestation)
        with self.assertRaises(ChineseMaterialError):
            self.materials.append_material(incomplete)

    def test_independent_guide_does_not_require_translation_right(self):
        node = self.structure_b.nodes[0]
        request = self.base_request(
            material_id="MATERIAL-W26-GUIDE", intake=self.intake_b,
            structure=self.structure_b,
            evidence_id=self.evidence_b.submission.version_id,
            mode=ChineseMaterialMode.INDEPENDENT_GUIDE,
            selected=(node.node_id,),
            segments=(self.segment(
                "SEG-W26-GUIDE", (node.node_id,),
                "本刊独立导读，不是原文直译。"),),
            title="自有独立导读")
        stored = self.materials.append_material(request)
        material = self.materials.load_material(stored.submission.version_id)
        self.assertEqual(material.scope_label, "INDEPENDENT_GUIDE")
        translation_attempt = self.base_request(
            material_id="MATERIAL-W26-NO-TRANSLATE",
            intake=self.intake_b, structure=self.structure_b,
            evidence_id=self.evidence_b.submission.version_id,
            mode=ChineseMaterialMode.EXCERPT_TRANSLATION,
            selected=(node.node_id,),
            segments=(self.segment(
                "SEG-W26-NO-TRANSLATE", (node.node_id,),
                "无权制作的中文译文。"),),
            omissions=(OmissionRecord(
                locator="其余原文", reason="未提供"),))
        with self.assertRaises(ArchiveError):
            self.materials.append_material(translation_attempt)

    def test_excerpt_without_omissions_and_foreign_evidence_are_rejected(self):
        node = self.structure_a.nodes[0]
        with self.assertRaises(ValidationError):
            ChineseMaterialRequest(
                material_id="MATERIAL-W26-BAD-EXCERPT",
                theme_id="THEME-W26", spec_sha256=SPEC,
                topic_id="TOPIC-W26",
                topic_decision_id=self.cover.decision_id,
                evidence_version_ids=(self.evidence_a.submission.version_id,),
                source_intake_version_id=self.intake_a_version,
                source_structure_version_id=self.intake_a.structure_version_id,
                mode=ChineseMaterialMode.EXCERPT_TRANSLATION,
                selected_node_ids=(node.node_id,), title_zh="错误节选",
                segments=(self.segment(
                    "SEG-W26-BAD-EXCERPT", (node.node_id,), "错误节选译文。"),),
                knowledge_cutoff=self.acquired_a,
                method=ChineseMaterialMethod.SUPPLIED_CHINESE,
                translated_or_written_by="owned test author",
                use_context=self.use_context,
                created_at=BASE + timedelta(minutes=5))
        wrong_evidence = self.base_request(
            material_id="MATERIAL-W26-FOREIGN-EVIDENCE",
            intake=self.intake_a, structure=self.structure_a,
            evidence_id=self.evidence_b.submission.version_id,
            mode=ChineseMaterialMode.EXCERPT_TRANSLATION,
            selected=(node.node_id,),
            segments=(self.segment(
                "SEG-W26-FOREIGN", (node.node_id,), "错误来源证据。"),),
            omissions=(OmissionRecord(
                locator=self.structure_a.nodes[1].locator, reason="节选"),))
        with self.assertRaises(ChineseMaterialError):
            self.materials.append_material(wrong_evidence)

    def test_pre_s8_material_and_object_change_routing_are_blocked(self):
        node = self.structure_a.nodes[0]
        request = self.base_request(
            material_id="MATERIAL-W26-PRE-S8", intake=self.intake_a,
            structure=self.structure_a,
            evidence_id=self.evidence_a.submission.version_id,
            mode=ChineseMaterialMode.EXCERPT_TRANSLATION,
            selected=(node.node_id,),
            segments=(self.segment(
                "SEG-W26-PRE-S8", (node.node_id,), "S8前不得制作。"),),
            omissions=(OmissionRecord(locator="其余", reason="节选"),)).model_copy(
                update={"topic_decision_id": self.s7.decision_id})
        request = ChineseMaterialRequest.model_validate_json(
            request.model_dump_json())
        with self.assertRaises(ChineseMaterialError):
            self.materials.append_material(request)
        with self.assertRaises(ValidationError):
            ImportantUpdateRequest(
                update_check_id="UPDATE-W26-WRONG-ROUTE",
                material_version_id="MATERIAL-W26-PRE-S8",
                theme_id="THEME-W26", spec_sha256=SPEC,
                affects_core_judgment=True,
                changes_object_scope_or_type=True,
                action=UpdateAction.RETURN_TO_W25,
                reason="Object changed", next_action="Wrong route",
                checked_by="owned test checker",
                checked_at=BASE + timedelta(minutes=7))

    def test_material_revision_preserves_previous_version(self):
        node = self.structure_a.nodes[0]
        first_request = self.base_request(
            intake=self.intake_a, structure=self.structure_a,
            evidence_id=self.evidence_a.submission.version_id,
            mode=ChineseMaterialMode.EXCERPT_TRANSLATION,
            selected=(node.node_id,),
            segments=(self.segment("SEG-W26-REV-1", (node.node_id,), "第一版译文。"),),
            omissions=(OmissionRecord(locator="其余", reason="节选"),))
        first = self.materials.append_material(first_request)
        revision_request = first_request.model_copy(update={
            "previous_version_id": first.submission.version_id,
            "segments": (self.segment(
                "SEG-W26-REV-2", (node.node_id,), "第二版校正译文。"),),
            "created_at": BASE + timedelta(minutes=6),
        })
        revision_request = ChineseMaterialRequest.model_validate_json(
            revision_request.model_dump_json())
        second = self.materials.append_material(revision_request)
        self.assertNotEqual(first.submission.version_id,
                            second.submission.version_id)
        first_body = self.materials.load_material(first.submission.version_id)
        second_body = self.materials.load_material(second.submission.version_id)
        self.assertEqual(second_body.previous_version_id,
                         first.submission.version_id)
        self.assertEqual(first_body.segments[0].chinese_text, "第一版译文。")
        self.assertEqual(second_body.segments[0].chinese_text, "第二版校正译文。")

    def test_post_cutoff_core_update_cannot_be_ignored(self):
        node = self.structure_a.nodes[0]
        material_request = self.base_request(
            material_id="MATERIAL-W26-CUTOFF", intake=self.intake_a,
            structure=self.structure_a,
            evidence_id=self.evidence_a.submission.version_id,
            mode=ChineseMaterialMode.EXCERPT_TRANSLATION,
            selected=(node.node_id,),
            segments=(self.segment(
                "SEG-W26-CUTOFF", (node.node_id,), "截点内材料。"),),
            omissions=(OmissionRecord(locator="其余", reason="节选"),))
        material_stored = self.materials.append_material(material_request)
        later_at = BASE + timedelta(minutes=6)
        new_intake = self.acquire(
            "SRC-W26-C", "Owned source C",
            "https://example.invalid/w26-c",
            b"Owned later source C changes the core owner conclusion.",
            later_at, purpose=AcquisitionPurpose.POST_S8_EVIDENCE,
            decision_id=self.cover.decision_id, translate=False)
        new_intake_version = self.original._version(
            "SOURCE-INTAKE-", new_intake.intake_id)
        bad_request = ImportantUpdateRequest(
            update_check_id="UPDATE-W26-BAD",
            material_version_id=material_stored.submission.version_id,
            theme_id="THEME-W26", spec_sha256=SPEC,
            observed_source_intake_version_ids=(new_intake_version,),
            affects_core_judgment=True, changes_object_scope_or_type=False,
            action=UpdateAction.NO_IMPORTANT_UPDATE,
            reason="Owned post-cutoff material", next_action="Continue old cutoff",
            checked_by="owned test checker",
            checked_at=BASE + timedelta(minutes=7))
        with self.assertRaises(MaterialUpdateError):
            self.materials.append_update_check(bad_request)
        good_request = bad_request.model_copy(update={
            "update_check_id": "UPDATE-W26-GOOD",
            "action": UpdateAction.UPDATE_CUTOFF_AND_REOPEN,
            "new_knowledge_cutoff": BASE + timedelta(minutes=6, seconds=30),
            "reason": "Core update discovered after the original cutoff",
            "next_action": "Reopen research at the new cutoff",
        })
        good_request = ImportantUpdateRequest.model_validate_json(
            good_request.model_dump_json())
        stored = self.materials.append_update_check(good_request)
        check = self.materials.load_update_check(stored.submission.version_id)
        self.assertTrue(check.observed_after_cutoff)
        self.assertTrue(check.affects_core_judgment)
        self.assertEqual(check.action, UpdateAction.UPDATE_CUTOFF_AND_REOPEN)
        old_material = self.materials.load_material(
            material_stored.submission.version_id)
        self.assertEqual(old_material.knowledge_cutoff, self.acquired_a)


if __name__ == "__main__":
    unittest.main()
