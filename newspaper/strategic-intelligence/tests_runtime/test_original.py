"""W24 owned-byte acquisition, locator structure and rights-use tests."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from intelligence.archive import Archive, ArchiveError, Conflict, PermissionDenied
from intelligence.contracts import (DataPeriod, MaterialUse, ObjectKind,
                                    PermissionState, Precision, Representation,
                                    RightsBasis, RightsGrant, Scope, ScopeMode,
                                    TimePoint, UseContext, UsePermission,
                                    ValidityMode, VersionSubmission)
from intelligence.discovery import (CandidateHint, EventClusterController, EventClusterer,
                                    LineageRole)
from intelligence.editorial import (ArticleType, DecisionStage, EditorialController,
                                    PublicationBasis, S8PrerequisitePackage,
                                    TopicDecision,
                                    TopicDecisionCode, ValueBasis)
from intelligence.original import (AcquisitionMethod, AcquisitionPurpose,
                                   AcquisitionRequest, AcquisitionScope, IntakeGapCode,
                                   IntakeStatus, OriginalMaterialController,
                                   OriginalMaterialError, RetentionMode, SourceFormat,
                                   StructureNodeKind, StructureStatus)
from intelligence.sources import (PermissionStateW20, SourceAdapter,
                                  SourceAdapterController, SourceDescriptor, SourceType)

BASE = datetime(2026, 10, 31, 0, 0, tzinfo=timezone.utc)
SPEC = "a" * 64
TITLE = "Owned W24 source document"
URL = "https://example.invalid/owned-w24"
HTML = b"""<!doctype html><html><head><title>Owned W24 source document</title></head>
<body><article><h1>Owned heading</h1>
<p>Owned body paragraph with no third-party reporting.</p>
<table><caption>Owned table</caption><tr><th>Measure</th><th>Value</th></tr>
<tr><td>Owned metric</td><td>42 tonnes</td></tr></table>
<figure><img src="https://example.invalid/owned-figure.png" alt="Owned figure">
<figcaption>Owned figure caption</figcaption></figure>
</article></body></html>"""
TEXT = b"Owned first paragraph.\n\nOwned second paragraph with 17 units."


class OriginalMaterialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Archive(Path(self.temp.name) / "archive")
        self.addCleanup(self.archive.close)
        self.journal_rights = self.rights(
            "RIGHTS-W24-JOURNAL",
            allowed={MaterialUse.INDEX, MaterialUse.STORE_BODY})
        self.controller = OriginalMaterialController(
            self.archive, self.journal_rights)
        self.editorial = EditorialController(self.archive, self.journal_rights)
        self.question = self.archive.append(VersionSubmission(
            object_id="QUESTION-W24", version_id="QUESTION-W24-v001",
            kind=ObjectKind.QUESTION_VERSION, title="Owned W24 question",
            spec_sha256=SPEC, created_at=BASE, rights=self.journal_rights,
            representation=Representation.FULL_BODY),
            b"Owned synthetic question version")
        self.index = self.candidate_index()
        SourceAdapterController(self.archive, self.journal_rights).append_index(
            self.index)
        candidate = self.index.candidates[0]
        hint = CandidateHint(
            candidate_index_id=self.index.index_id,
            candidate_id=candidate.candidate_id, event_key="EVENT-W24",
            lineage_role=LineageRole.ORIGINAL,
            lineage_root_ids=("ORIGIN-W24",),
            note="Owned W24 event fixture")
        self.discovery = EventClusterer().build(
            (self.index,), (hint,), proposal_id="DISCOVERY-W24",
            spec_sha256=SPEC, created_at=BASE + timedelta(seconds=1))
        EventClusterController(
            self.archive, self.journal_rights).append_proposal(self.discovery)
        cluster = self.discovery.clusters[0]
        self.decision = TopicDecision(
            decision_id="DECISION-W24-S7", topic_id="TOPIC-W24",
            theme_id="THEME-W24", edition_id="EDITION-W42",
            spec_sha256=SPEC,
            discovery_proposal_id=self.discovery.proposal_id,
            question_version_id="QUESTION-W24-v001",
            candidate_index_ids=(self.index.index_id,),
            candidate_ids=(candidate.candidate_id,),
            cluster_ids=(cluster.cluster_id,), stage=DecisionStage.S7,
            publication_basis=PublicationBasis.CURRENT_WEEK,
            article_type=ArticleType.DEEP_THEME,
            value_bases=(ValueBasis.RESEARCH_VALUE,),
            decision=TopicDecisionCode.WATCH,
            reasons=("Owned source acquisition is required",),
            next_action="Acquire and structure the exact source version",
            research_investment_note="Owned synthetic fixture only",
            created_at=BASE + timedelta(seconds=2))
        self.editorial.append_decision(self.decision)
        self.acquired_at = BASE + timedelta(minutes=1)

    def rights(self, rights_id, *, allowed, pointer=False, translate=True):
        if translate and not pointer:
            allowed = set(allowed) | {MaterialUse.TRANSLATE}
        permissions = tuple(UsePermission(
            use=use, state=PermissionState.ALLOWED,
            validity=ValidityMode.OPEN_ENDED,
            territories=Scope(mode=ScopeMode.ANY),
            providers=Scope(mode=ScopeMode.ANY),
            content_scope=Scope(mode=ScopeMode.ANY))
            for use in allowed if use is not MaterialUse.INDEX)
        return RightsGrant(
            rights_id=rights_id,
            basis=RightsBasis.POINTER_ONLY if pointer else RightsBasis.LICENSE,
            allowed_uses=frozenset({MaterialUse.INDEX} if pointer else allowed),
            evidence="Owned synthetic acquisition grant",
            checked_by="test fixture", checked_at=BASE,
            work_title=TITLE, source_locator=URL,
            terms_url="https://example.invalid/owned-terms",
            terms_version="fixture-v1", grantor="Owned fixture author",
            permissions=permissions)

    def candidate_index(self):
        source = SourceDescriptor(
            source_id="SRC-W24-CANDIDATE",
            name="Owned W24 candidate source",
            source_url="https://example.invalid/candidates",
            source_type=SourceType.JSON_API, language="en", region="NZ",
            sector="fixture", ownership="Owned fixture owner",
            permission_state=PermissionStateW20.CLEARED,
            permission_evidence="Owned synthetic candidate")
        raw = json.dumps({"items": [{
            "id": "w24-one", "title": "Owned W24 event",
            "url": URL, "summary": "Owned candidate clue",
            "published_at": "2026-10-30T10:00:00Z"}]}).encode()
        return SourceAdapter().parse(
            source, raw, acquired_at=BASE, content_type="application/json",
            spec_sha256=SPEC)

    def request(self, raw, *, expected_format, rights=None,
                scope=AcquisitionScope.FULL_DOCUMENT,
                partial_locator=None, media_type="text/html",
                acquired_at=None, request_id="REQUEST-W24",
                purpose=AcquisitionPurpose.S8_PREREQUISITE,
                topic_decision_id=None, source_id="SRC-W24-ORIGINAL"):
        acquired_at = acquired_at or self.acquired_at
        return AcquisitionRequest(
            request_id=request_id, spec_sha256=SPEC, topic_id="TOPIC-W24",
            topic_decision_id=topic_decision_id or self.decision.decision_id,
            purpose=purpose, source_id=source_id, title=TITLE, original_url=URL,
            creator="Owned fixture author", institution="Owned fixture",
            language="en", version_label="fixture-v1",
            media_type=media_type, expected_format=expected_format,
            expected_sha256=hashlib.sha256(raw).hexdigest(),
            method=AcquisitionMethod.PROVIDED_BYTES,
            acquired_at=acquired_at, scope=scope,
            partial_locator=partial_locator,
            published_at=TimePoint(
                precision=Precision.DATE, value="2026-10-30"),
            data_period=DataPeriod(
                start=datetime(2026, 9, 1, tzinfo=timezone.utc),
                end_exclusive=datetime(2026, 10, 1, tzinfo=timezone.utc),
                source_timezone="UTC", provenance="Owned fixture period"),
            rights=rights or self.rights(
                "RIGHTS-W24-SOURCE",
                allowed={MaterialUse.INDEX, MaterialUse.STORE_BODY,
                         MaterialUse.MODEL_PROCESS,
                         MaterialUse.PRIVATE_DELIVERY}),
            use_context=UseContext(
                at=acquired_at, provider="owned-local-parser",
                territory="NZ", content=("owned-full-fixture",)),
            created_at=acquired_at)

    def intake_for(self, stored):
        return self.controller.load_intake_version(
            stored.submission.version_id)

    def ingest(self, raw, **request_changes):
        stored = self.controller.ingest(self.request(raw, **request_changes), raw)
        return stored, self.controller.load_intake_version(
            stored.submission.version_id)

    def use_context(self):
        return UseContext(
            at=self.acquired_at + timedelta(minutes=1),
            provider="owned-local-parser", territory="NZ",
            content=("owned-full-fixture",))

    def test_html_retains_exact_bytes_and_locator_only_structure(self):
        stored, intake = self.ingest(HTML, expected_format=SourceFormat.HTML)
        self.assertEqual(stored.submission.kind, ObjectKind.SOURCE_INTAKE)
        self.assertEqual(intake.status, IntakeStatus.PARTIAL)
        self.assertEqual(intake.retention, RetentionMode.RETAINED)
        self.assertEqual(intake.creator, "Owned fixture author")
        self.assertEqual(intake.institution, "Owned fixture")
        self.assertEqual(intake.language, "en")
        self.assertEqual(intake.version_label, "fixture-v1")
        self.assertEqual(intake.published_at.value, "2026-10-30")
        self.assertIsNotNone(intake.data_period)
        self.assertEqual(intake.source_version_id,
                         self.archive.latest(
                             self.controller._object(
                                 "SOURCE-MATERIAL-OBJECT-", "SRC-W24-ORIGINAL")
                         ).submission.version_id)
        source = self.archive.get(intake.source_version_id)
        self.assertEqual(source.submission.representation, Representation.FULL_BODY)
        rights = self.controller.load_rights(intake.rights_record_version_id)
        structure = self.controller.load_structure(intake.structure_version_id)
        self.assertEqual(rights.retention, RetentionMode.RETAINED)
        self.assertEqual(structure.status, StructureStatus.PARTIAL)
        self.assertIn(StructureNodeKind.TABLE,
                      {node.kind for node in structure.nodes})
        self.assertIn(IntakeGapCode.TABLE_REQUIRES_VISUAL_CHECK,
                      {gap.code for gap in structure.gaps})
        self.assertEqual(structure.figure_count, 1)
        self.assertIn(IntakeGapCode.FIGURE_REQUIRES_VISUAL_CHECK,
                      {gap.code for gap in structure.gaps})
        self.assertNotIn("Owned body paragraph", structure.model_dump_json())
        material = self.controller.read_source(
            intake.intake_id, MaterialUse.MODEL_PROCESS, self.use_context())
        self.assertEqual(material.body, HTML)
        table = next(node for node in structure.nodes
                     if node.kind is StructureNodeKind.TABLE)
        node_read = self.controller.read_node(
            intake.intake_id, table.node_id, MaterialUse.MODEL_PROCESS,
            self.use_context())
        self.assertIn("42 tonnes", node_read.text)
        self.assertTrue(node_read.original_visual_check_required)
        self.assertFalse(intake.facts_verified)
        self.assertFalse(intake.claims_supported)

    def test_text_structure_roundtrips_exact_node_reads(self):
        _, intake = self.ingest(
            TEXT, expected_format=SourceFormat.TEXT, media_type="text/plain")
        self.assertEqual(intake.status, IntakeStatus.RECORDED)
        structure = self.controller.load_structure(intake.structure_version_id)
        self.assertEqual(structure.status, StructureStatus.EXTRACTED)
        self.assertEqual(len(structure.nodes), 2)
        read = self.controller.read_node(
            intake.intake_id, structure.nodes[1].node_id,
            MaterialUse.MODEL_PROCESS, self.use_context())
        self.assertEqual(read.text, "Owned second paragraph with 17 units.")
        self.assertEqual(read.content_verification, "NOT_PERFORMED")

    def test_pointer_only_source_has_no_retained_body(self):
        pointer = self.rights(
            "RIGHTS-W24-POINTER", allowed=set(), pointer=True)
        _, intake = self.ingest(
            TEXT, expected_format=SourceFormat.TEXT, media_type="text/plain",
            rights=pointer)
        self.assertEqual(intake.status, IntakeStatus.PARTIAL)
        self.assertEqual(intake.retention, RetentionMode.POINTER_ONLY)
        source = self.archive.get(intake.source_version_id)
        self.assertEqual(source.submission.representation,
                         Representation.POINTER_ONLY)
        self.assertIn(IntakeGapCode.POINTER_ONLY,
                      {gap.code for gap in intake.gaps})
        structure = self.controller.load_structure(intake.structure_version_id)
        self.assertEqual(structure.status, StructureStatus.UNSUPPORTED)
        self.assertEqual(structure.nodes, ())
        self.assertIn(IntakeGapCode.PROCESSING_NOT_AUTHORIZED,
                      {gap.code for gap in structure.gaps})
        self.assertNotIn("Owned second paragraph", structure.model_dump_json())
        with self.assertRaises(ArchiveError):
            self.controller.read_source(
                intake.intake_id, MaterialUse.MODEL_PROCESS, self.use_context())

    def test_storage_without_processing_rights_does_not_run_parser(self):
        rights = self.rights(
            "RIGHTS-W24-STORE-ONLY",
            allowed={MaterialUse.INDEX, MaterialUse.STORE_BODY,
                     MaterialUse.PRIVATE_DELIVERY},
            translate=False)
        _, intake = self.ingest(
            HTML, expected_format=SourceFormat.HTML, rights=rights)
        self.assertEqual(intake.retention, RetentionMode.RETAINED)
        structure = self.controller.load_structure(intake.structure_version_id)
        self.assertEqual(structure.status, StructureStatus.UNSUPPORTED)
        self.assertEqual(structure.nodes, ())
        self.assertIn(IntakeGapCode.PROCESSING_NOT_AUTHORIZED,
                      {gap.code for gap in structure.gaps})
        with self.assertRaises(PermissionDenied):
            self.controller.read_source(
                intake.intake_id, MaterialUse.MODEL_PROCESS,
                self.use_context())

    def test_translation_use_is_checked_on_exact_source(self):
        rights = self.rights(
            "RIGHTS-W24-NO-TRANSLATE",
            allowed={MaterialUse.INDEX, MaterialUse.STORE_BODY,
                     MaterialUse.MODEL_PROCESS},
            translate=False)
        _, intake = self.ingest(
            TEXT, expected_format=SourceFormat.TEXT, media_type="text/plain",
            rights=rights)
        self.controller.check_source_use(
            intake.intake_id, MaterialUse.MODEL_PROCESS, self.use_context())
        with self.assertRaises(PermissionDenied):
            self.controller.check_source_use(
                intake.intake_id, MaterialUse.TRANSLATE, self.use_context())

    def test_wrong_hash_or_declared_format_never_creates_source_version(self):
        wrong = self.request(
            TEXT, expected_format=SourceFormat.TEXT, media_type="text/plain"
        ).model_copy(update={"expected_sha256": "f" * 64})
        with self.assertRaisesRegex(OriginalMaterialError, "requested version"):
            self.controller.ingest(wrong, TEXT)
        self.assertIsNone(self.archive.latest(self.controller._object(
            "SOURCE-MATERIAL-OBJECT-", "SRC-W24-ORIGINAL")))
        mismatch = self.request(
            TEXT, expected_format=SourceFormat.HTML, media_type="text/plain")
        with self.assertRaisesRegex(OriginalMaterialError, "format"):
            self.controller.ingest(mismatch, TEXT)
        self.assertIsNone(self.archive.latest(self.controller._object(
            "SOURCE-MATERIAL-OBJECT-", "SRC-W24-ORIGINAL")))

    def test_empty_source_records_failure_without_substitutes(self):
        stored, intake = self.ingest(
            b"", expected_format=SourceFormat.TEXT, media_type="text/plain")
        self.assertEqual(stored.submission.kind, ObjectKind.SOURCE_INTAKE)
        self.assertEqual(intake.status, IntakeStatus.FAILED)
        self.assertEqual(intake.retention, RetentionMode.NOT_CREATED)
        self.assertIsNone(intake.source_version_id)
        self.assertIsNone(intake.rights_record_version_id)
        self.assertIsNone(intake.structure_version_id)
        self.assertIn(IntakeGapCode.EMPTY_SOURCE,
                      {gap.code for gap in intake.gaps})

    def test_declared_partial_acquisition_remains_partial(self):
        _, intake = self.ingest(
            TEXT, expected_format=SourceFormat.TEXT, media_type="text/plain",
            scope=AcquisitionScope.DECLARED_PARTIAL,
            partial_locator="text:paragraph:1")
        self.assertEqual(intake.status, IntakeStatus.PARTIAL)
        self.assertIn(IntakeGapCode.DECLARED_PARTIAL,
                      {gap.code for gap in intake.gaps})
        structure = self.controller.load_structure(intake.structure_version_id)
        self.assertEqual(structure.status, StructureStatus.PARTIAL)
        self.assertFalse(structure.content_verification != "NOT_PERFORMED")

    def test_pdf_bytes_are_retained_but_not_fake_parsed(self):
        pdf = b"%PDF-1.4\n% Owned synthetic PDF fixture\n"
        _, intake = self.ingest(
            pdf, expected_format=SourceFormat.PDF,
            media_type="application/pdf")
        self.assertEqual(intake.retention, RetentionMode.RETAINED)
        self.assertEqual(intake.status, IntakeStatus.PARTIAL)
        structure = self.controller.load_structure(intake.structure_version_id)
        self.assertEqual(structure.status, StructureStatus.UNSUPPORTED)
        self.assertEqual(structure.nodes, ())
        codes = {gap.code for gap in structure.gaps}
        self.assertIn(IntakeGapCode.UNSUPPORTED_FORMAT, codes)
        self.assertIn(IntakeGapCode.OCR_REQUIRED, codes)

    def test_stale_editorial_decision_cannot_authorize_acquisition(self):
        later = TopicDecision(
            decision_id="DECISION-W24-S7-LATER", topic_id="TOPIC-W24",
            theme_id="THEME-W24", edition_id="EDITION-W42",
            spec_sha256=SPEC,
            discovery_proposal_id=self.discovery.proposal_id,
            question_version_id="QUESTION-W24-v001",
            candidate_index_ids=(self.index.index_id,),
            candidate_ids=(self.index.candidates[0].candidate_id,),
            cluster_ids=(self.discovery.clusters[0].cluster_id,),
            stage=DecisionStage.S7,
            publication_basis=PublicationBasis.CURRENT_WEEK,
            article_type=ArticleType.DEEP_THEME,
            value_bases=(ValueBasis.RESEARCH_VALUE,),
            decision=TopicDecisionCode.WATCH,
            reasons=("Owned later decision",),
            next_action="Start a different acquisition",
            previous_decision_id=self.decision.decision_id,
            created_at=BASE + timedelta(seconds=3))
        self.editorial.append_decision(later)
        request = self.request(
            TEXT, expected_format=SourceFormat.TEXT, media_type="text/plain")
        with self.assertRaisesRegex(OriginalMaterialError, "stale"):
            self.controller.ingest(request, TEXT)

    def test_dropped_s7_topic_cannot_authorize_acquisition(self):
        dropped = TopicDecision(
            decision_id="DECISION-W24-S7-DROP", topic_id="TOPIC-W24",
            theme_id="THEME-W24", edition_id="EDITION-W42",
            spec_sha256=SPEC,
            discovery_proposal_id=self.discovery.proposal_id,
            question_version_id="QUESTION-W24-v001",
            candidate_index_ids=(self.index.index_id,),
            candidate_ids=(self.index.candidates[0].candidate_id,),
            cluster_ids=(self.discovery.clusters[0].cluster_id,),
            stage=DecisionStage.S7,
            publication_basis=PublicationBasis.CURRENT_WEEK,
            article_type=ArticleType.DEEP_THEME,
            value_bases=(ValueBasis.RESEARCH_VALUE,),
            decision=TopicDecisionCode.DROP,
            reasons=("Owned topic drop",),
            previous_decision_id=self.decision.decision_id,
            created_at=BASE + timedelta(seconds=3))
        self.editorial.append_decision(dropped)
        request = self.request(
            TEXT, expected_format=SourceFormat.TEXT,
            media_type="text/plain").model_copy(
                update={"topic_decision_id": dropped.decision_id})
        with self.assertRaisesRegex(OriginalMaterialError, "dropped"):
            self.controller.ingest(request, TEXT)

    def test_decision_change_during_intake_is_an_atomic_conflict(self):
        request = self.request(
            TEXT, expected_format=SourceFormat.TEXT, media_type="text/plain")
        original = self.controller._extract_structure

        def change_decision_after_structure(*args, **kwargs):
            structure = original(*args, **kwargs)
            later = TopicDecision(
                decision_id="DECISION-W24-S7-RACE", topic_id="TOPIC-W24",
                theme_id="THEME-W24", edition_id="EDITION-W42",
                spec_sha256=SPEC,
                discovery_proposal_id=self.discovery.proposal_id,
                question_version_id="QUESTION-W24-v001",
                candidate_index_ids=(self.index.index_id,),
                candidate_ids=(self.index.candidates[0].candidate_id,),
                cluster_ids=(self.discovery.clusters[0].cluster_id,),
                stage=DecisionStage.S7,
                publication_basis=PublicationBasis.CURRENT_WEEK,
                article_type=ArticleType.DEEP_THEME,
                value_bases=(ValueBasis.RESEARCH_VALUE,),
                decision=TopicDecisionCode.WATCH,
                reasons=("Concurrent owned decision",),
                next_action="Recheck the acquisition plan",
                previous_decision_id=self.decision.decision_id,
                created_at=BASE + timedelta(seconds=4))
            self.editorial.append_decision(later)
            return structure

        with patch.object(self.controller, "_extract_structure",
                          side_effect=change_decision_after_structure):
            with self.assertRaises(Conflict):
                self.controller.ingest(request, TEXT)
        self.assertEqual(
            self.editorial.current_decision("TOPIC-W24").decision_id,
            "DECISION-W24-S7-RACE")

    def test_reingest_is_idempotent_and_reuses_exact_records(self):
        request = self.request(TEXT, expected_format=SourceFormat.TEXT,
                               media_type="text/plain")
        first = self.controller.ingest(request, TEXT)
        second = self.controller.ingest(request, TEXT)
        self.assertEqual(first.submission.version_id, second.submission.version_id)
        intake = self.controller.load_intake_version(
            first.submission.version_id)
        self.assertEqual(first.submission.version_id,
                         self.controller._version("SOURCE-INTAKE-", intake.intake_id))
        self.assertEqual(
            len(self.archive.history(first.submission.object_id)), 1)
        later = self.request(
            TEXT, expected_format=SourceFormat.TEXT, media_type="text/plain",
            acquired_at=self.acquired_at + timedelta(minutes=2),
            request_id="REQUEST-W24-LATER")
        third = self.controller.ingest(later, TEXT)
        later_intake = self.controller.load_intake_version(
            third.submission.version_id)
        self.assertEqual(later_intake.source_version_id,
                         intake.source_version_id)
        self.assertEqual(later_intake.structure_version_id,
                         intake.structure_version_id)
        self.assertNotEqual(later_intake.intake_id, intake.intake_id)

    def test_post_s8_cover_can_add_a_distinct_exact_source(self):
        _, prerequisite = self.ingest(
            TEXT, expected_format=SourceFormat.TEXT, media_type="text/plain")
        evidence_at = self.acquired_at + timedelta(minutes=1, seconds=10)
        reading_at = self.acquired_at + timedelta(minutes=1, seconds=20)
        evidence = self.archive.append(VersionSubmission(
            object_id="EVIDENCE-W24", version_id="EVIDENCE-W24-v001",
            kind=ObjectKind.EVIDENCE, title="Owned W24 evidence",
            spec_sha256=SPEC, created_at=evidence_at,
            rights=self.journal_rights,
            representation=Representation.FULL_BODY),
            b"Owned synthetic W24 evidence")
        reading = self.archive.append(VersionSubmission(
            object_id="READING-W24", version_id="READING-W24-v001",
            kind=ObjectKind.READING_SCOPE_PLAN,
            title="Owned W24 reading plan", spec_sha256=SPEC,
            created_at=reading_at, rights=self.journal_rights,
            representation=Representation.FULL_BODY),
            b"Owned synthetic W24 reading plan")
        package_at = self.acquired_at + timedelta(minutes=2)
        package = S8PrerequisitePackage(
            package_id="PACKAGE-W24", topic_id="TOPIC-W24",
            edition_id="EDITION-W42", spec_sha256=SPEC,
            discovery_proposal_id=self.discovery.proposal_id,
            question_version_id="QUESTION-W24-v001",
            source_material_version_ids=(prerequisite.source_version_id,),
            evidence_version_ids=(evidence.submission.version_id,),
            rights_record_version_ids=(prerequisite.rights_record_version_id,),
            reading_plan_version_id=reading.submission.version_id,
            limitations=("Owned synthetic S8 package",),
            candidate_index_ids=(self.index.index_id,),
            created_at=package_at)
        self.editorial.append_package(package)
        cover = TopicDecision(
            decision_id="DECISION-W24-S8-COVER", topic_id="TOPIC-W24",
            theme_id="THEME-W24", edition_id="EDITION-W42",
            spec_sha256=SPEC,
            discovery_proposal_id=self.discovery.proposal_id,
            question_version_id="QUESTION-W24-v001",
            candidate_index_ids=(self.index.index_id,),
            candidate_ids=(self.index.candidates[0].candidate_id,),
            cluster_ids=(self.discovery.clusters[0].cluster_id,),
            stage=DecisionStage.S8, publication_basis=PublicationBasis.CURRENT_WEEK,
            article_type=ArticleType.DEEP_THEME,
            value_bases=(ValueBasis.RESEARCH_VALUE,),
            decision=TopicDecisionCode.COVER,
            reasons=("Owned S8 cover",), previous_decision_id=self.decision.decision_id,
            s8_package_id=package.package_id,
            created_at=self.acquired_at + timedelta(minutes=3))
        self.editorial.append_decision(cover)
        protected_change = self.request(
            b"Owned changed bytes for a protected S8-package source",
            expected_format=SourceFormat.TEXT, media_type="text/plain",
            acquired_at=self.acquired_at + timedelta(minutes=4),
            request_id="REQUEST-W24-PROTECTED-CHANGE",
            purpose=AcquisitionPurpose.POST_S8_EVIDENCE,
            topic_decision_id=cover.decision_id,
            source_id="SRC-W24-ORIGINAL")
        with self.assertRaisesRegex(OriginalMaterialError, "re-review"):
            self.controller.ingest(
                protected_change,
                b"Owned changed bytes for a protected S8-package source")
        post_raw = b"Owned post-S8 supplemental source with 23 units."
        request = self.request(
            post_raw, expected_format=SourceFormat.TEXT, media_type="text/plain",
            acquired_at=self.acquired_at + timedelta(minutes=4),
            request_id="REQUEST-W24-POST-S8",
            purpose=AcquisitionPurpose.POST_S8_EVIDENCE,
            topic_decision_id=cover.decision_id,
            source_id="SRC-W24-POST")
        stored = self.controller.ingest(request, post_raw)
        intake = self.controller.load_intake_version(
            stored.submission.version_id)
        self.assertEqual(intake.purpose, AcquisitionPurpose.POST_S8_EVIDENCE)
        self.assertEqual(intake.status, IntakeStatus.RECORDED)
        self.assertNotEqual(intake.source_version_id,
                            prerequisite.source_version_id)

    def test_request_cannot_mismatch_rights_or_acquisition_time(self):
        base = self.request(TEXT, expected_format=SourceFormat.TEXT,
                            media_type="text/plain")
        wrong_rights = self.rights(
            "RIGHTS-W24-WRONG-IDENTITY",
            allowed={MaterialUse.INDEX, MaterialUse.STORE_BODY})
        wrong_rights = wrong_rights.model_copy(update={"work_title": "Different work"})
        with self.assertRaises(ValidationError):
            AcquisitionRequest.model_validate_json(json.dumps({
                **json.loads(base.model_dump_json()),
                "rights": json.loads(wrong_rights.model_dump_json()),
            }))
        with self.assertRaises(ValidationError):
            AcquisitionRequest.model_validate_json(json.dumps({
                **json.loads(base.model_dump_json()),
                "use_context": {
                    **json.loads(base.use_context.model_dump_json()),
                    "at": (self.acquired_at + timedelta(minutes=3)).isoformat(),
                },
            }))


if __name__ == "__main__":
    unittest.main()
