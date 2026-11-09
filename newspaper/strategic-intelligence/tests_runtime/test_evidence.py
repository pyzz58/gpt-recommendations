"""W25 owned-fixture tests for claim support, calculations and gap follow-up."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from pydantic import ValidationError

from intelligence.archive import Archive
from intelligence.contracts import (DataPeriod, MaterialUse, ObjectKind,
                                    PermissionState, Precision, Representation,
                                    RightsBasis, RightsGrant, Scope, ScopeMode,
                                    TimePoint, UseContext, UsePermission,
                                    ValidityMode, VersionSubmission)
from intelligence.discovery import (CandidateHint, EventClusterController, EventClusterer,
                                    LineageRole)
from intelligence.editorial import (ArticleType, DecisionStage, EditorialController,
                                    PublicationBasis, TopicDecision,
                                    TopicDecisionCode, ValueBasis)
from intelligence.evidence import (CalculationController, CalculationError,
                                   CalculationOperation, CalculationRequest,
                                   ClaimEvidenceRequest, ClaimEvidenceAssessment,
                                   ClaimScope, ClaimType, ClaimVersion,
                                   EvidenceController, EvidenceError,
                                   EvidenceNature, EvidenceRelation,
                                   EvidenceRequest, SupplementController,
                                   SupplementGapType, SupplementImpact,
                                   SupplementMethod, SupplementRequest,
                                   SupplementResult, SupplementStatus,
                                   SupplementError, CalculationInput)
from intelligence.original import (AcquisitionMethod, AcquisitionPurpose,
                                   AcquisitionRequest, AcquisitionScope,
                                   OriginalMaterialController, SourceFormat)
from intelligence.research import ResearchRevision, ResearchRevisionController
from intelligence.sources import (PermissionStateW20, SourceAdapter,
                                  SourceAdapterController, SourceDescriptor, SourceType)

BASE = datetime(2026, 10, 31, 0, 0, tzinfo=timezone.utc)
SPEC = "a" * 64
PERIOD = DataPeriod(
    start=datetime(2026, 9, 1, tzinfo=timezone.utc),
    end_exclusive=datetime(2026, 10, 1, tzinfo=timezone.utc),
    source_timezone="UTC", provenance="Owned W25 September fixture")
SOURCES = {
    "SRC-W25-A": (
        "Owned source A",
        "https://example.invalid/w25-a",
        b"Owned source A reports 100 tonnes in September 2026."),
    "SRC-W25-B": (
        "Owned source B",
        "https://example.invalid/w25-b",
        b"Owned source B reports 120 tonnes in September 2026."),
}


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Archive(Path(self.temp.name) / "archive")
        self.addCleanup(self.archive.close)
        self.journal_rights = self.rights(
            "RIGHTS-W25-JOURNAL", "Owned W25 journal", SPEC,
            allowed={MaterialUse.INDEX, MaterialUse.STORE_BODY})
        self.original = OriginalMaterialController(
            self.archive, self.journal_rights)
        self.evidence = EvidenceController(
            self.archive, self.journal_rights, self.original)
        self.calculation = CalculationController(
            self.archive, self.journal_rights, self.original)
        self.supplement = SupplementController(
            self.archive, self.journal_rights, self.evidence)
        self.question = self.archive.append(VersionSubmission(
            object_id="QUESTION-W25", version_id="QUESTION-W25-v001",
            kind=ObjectKind.QUESTION_VERSION, title="Owned W25 question",
            spec_sha256=SPEC, created_at=BASE,
            rights=self.journal_rights,
            representation=Representation.FULL_BODY),
            b"Owned W25 question fixture")
        self.index_a = self.candidate_index("SRC-W25-A")
        self.index_b = self.candidate_index("SRC-W25-B")
        source_controller = SourceAdapterController(
            self.archive, self.journal_rights)
        source_controller.append_index(self.index_a)
        source_controller.append_index(self.index_b)
        candidate_a = self.index_a.candidates[0]
        candidate_b = self.index_b.candidates[0]
        self.proposal = EventClusterer().build(
            (self.index_a, self.index_b),
            (
                CandidateHint(
                    candidate_index_id=self.index_a.index_id,
                    candidate_id=candidate_a.candidate_id,
                    event_key="EVENT-W25", lineage_role=LineageRole.ORIGINAL,
                    lineage_root_ids=("ROOT-W25-A",),
                    note="Owned root A"),
                CandidateHint(
                    candidate_index_id=self.index_b.index_id,
                    candidate_id=candidate_b.candidate_id,
                    event_key="EVENT-W25", lineage_role=LineageRole.ORIGINAL,
                    lineage_root_ids=("ROOT-W25-B",),
                    note="Owned root B"),
            ),
            proposal_id="DISCOVERY-W25", spec_sha256=SPEC,
            created_at=BASE + timedelta(seconds=1))
        EventClusterController(
            self.archive, self.journal_rights).append_proposal(self.proposal)
        self.cluster = self.proposal.clusters[0]
        self.decision = TopicDecision(
            decision_id="DECISION-W25-S7", topic_id="TOPIC-W25",
            theme_id="THEME-W25", edition_id="EDITION-W42",
            spec_sha256=SPEC,
            discovery_proposal_id=self.proposal.proposal_id,
            question_version_id="QUESTION-W25-v001",
            candidate_index_ids=(self.index_a.index_id, self.index_b.index_id),
            candidate_ids=(candidate_a.candidate_id, candidate_b.candidate_id),
            cluster_ids=(self.cluster.cluster_id,),
            stage=DecisionStage.S7,
            publication_basis=PublicationBasis.CURRENT_WEEK,
            article_type=ArticleType.DEEP_THEME,
            value_bases=(ValueBasis.RESEARCH_VALUE,),
            decision=TopicDecisionCode.WATCH,
            reasons=("Owned evidence acquisition required",),
            next_action="Acquire exact owned sources",
            created_at=BASE + timedelta(seconds=2))
        EditorialController(
            self.archive, self.journal_rights).append_decision(self.decision)
        self.acquired_at = BASE + timedelta(minutes=1)
        self.intake_a = self.acquire("SRC-W25-A", self.acquired_at)
        self.intake_b = self.acquire(
            "SRC-W25-B", self.acquired_at + timedelta(seconds=10))
        self.intake_a_version = self.original._version(
            "SOURCE-INTAKE-", self.intake_a.intake_id)
        self.intake_b_version = self.original._version(
            "SOURCE-INTAKE-", self.intake_b.intake_id)
        self.use_context = UseContext(
            at=BASE + timedelta(minutes=3), provider="owned-local",
            territory="NZ", content=("owned-w25",))
        self.claim = ClaimVersion(
            claim_version_id="CLAIM-W25-v001", theme_id="THEME-W25",
            spec_sha256=SPEC, question_version_id="QUESTION-W25-v001",
            claim_text="Owned production was 100 tonnes in A and 120 tonnes in B.",
            claim_type=ClaimType.OBSERVED_FACT,
            scope=ClaimScope(
                subjects=("owned production",), metric="production",
                period=PERIOD, unit="tonnes", denominator="September 2026",
                comparison_basis="Owned sources A and B"),
            created_at=BASE + timedelta(minutes=2))
        self.claim_stored = self.evidence.append_claim(self.claim)

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
            evidence="Owned synthetic source rights", checked_by="test fixture",
            checked_at=BASE, work_title=title, source_locator=url,
            terms_url="https://example.invalid/w25-terms",
            terms_version="fixture-v1", grantor="Owned source author",
            permissions=permissions)

    def candidate_index(self, source_id):
        title, url, raw_text = SOURCES[source_id]
        source = SourceDescriptor(
            source_id=source_id, name=title,
            source_url=url, source_type=SourceType.JSON_API,
            language="en", region="NZ", sector="fixture",
            ownership="Owned source owner",
            permission_state=PermissionStateW20.CLEARED,
            permission_evidence="Owned synthetic candidate")
        raw = json.dumps({"items": [{
            "id": source_id, "title": title, "url": url,
            "summary": raw_text.decode(), "published_at": "2026-10-30"}]}).encode()
        return SourceAdapter().parse(
            source, raw, acquired_at=BASE, content_type="application/json",
            spec_sha256=SPEC)

    def acquire(self, source_id, acquired_at):
        title, url, raw = SOURCES[source_id]
        rights = self.rights(
            "RIGHTS-" + source_id, title, url,
            allowed={MaterialUse.INDEX, MaterialUse.STORE_BODY,
                     MaterialUse.MODEL_PROCESS})
        request = AcquisitionRequest(
            request_id="REQUEST-" + source_id, spec_sha256=SPEC,
            topic_id="TOPIC-W25", topic_decision_id=self.decision.decision_id,
            purpose=AcquisitionPurpose.S8_PREREQUISITE,
            source_id=source_id, title=title, original_url=url,
            creator="Owned source author", institution="Owned source institution",
            language="en", version_label="fixture-v1",
            media_type="text/plain", expected_format=SourceFormat.TEXT,
            expected_sha256=hashlib.sha256(raw).hexdigest(),
            method=AcquisitionMethod.PROVIDED_BYTES,
            acquired_at=acquired_at, scope=AcquisitionScope.FULL_DOCUMENT,
            published_at=TimePoint(precision=Precision.DATE, value="2026-10-30"),
            data_period=PERIOD,
            rights=rights,
            use_context=UseContext(
                at=acquired_at, provider="owned-local", territory="NZ",
                content=("owned-w25",)),
            created_at=acquired_at)
        stored = self.original.ingest(request, raw)
        return self.original.load_intake_version(stored.submission.version_id)

    def evidence_request(self, evidence_id, intake):
        structure = self.original.load_structure(intake.structure_version_id)
        return EvidenceRequest(
            evidence_id=evidence_id, theme_id="THEME-W25",
            spec_sha256=SPEC,
            intake_version_id=self.original._version(
                "SOURCE-INTAKE-", intake.intake_id),
            structure_version_id=intake.structure_version_id,
            lineage_proposal_id=self.proposal.proposal_id,
            cluster_id=self.cluster.cluster_id,
            node_ids=(structure.nodes[0].node_id,),
            nature=EvidenceNature.DOCUMENTED_FACT, use_context=self.use_context,
            created_at=BASE + timedelta(minutes=2, seconds=30))

    def make_evidence(self, evidence_id, intake):
        return self.evidence.append_evidence(
            self.evidence_request(evidence_id, intake))

    def make_assessment(self, assessment_id, evidence_ids, relation,
                        *, unsupported=()):
        stored = self.evidence.assess_claim(ClaimEvidenceRequest(
            assessment_id=assessment_id, theme_id="THEME-W25",
            spec_sha256=SPEC, claim_version_id=self.claim.claim_version_id,
            evidence_version_ids=tuple(evidence_ids), relation=relation,
            supported_scope=self.claim.scope,
            unsupported_aspects=tuple(unsupported),
            reviewed_by="owned test reviewer",
            reviewed_at=BASE + timedelta(minutes=3),
            use_context=self.use_context,
            created_at=BASE + timedelta(minutes=3)))
        return stored

    def test_claim_evidence_and_independence_roundtrip(self):
        evidence_a = self.evidence.append_evidence(
            self.evidence_request("EVIDENCE-W25-A", self.intake_a))
        evidence_b = self.evidence.append_evidence(
            self.evidence_request("EVIDENCE-W25-B", self.intake_b))
        assessment_request = ClaimEvidenceRequest(
            assessment_id="ASSESSMENT-W25-001",
            theme_id="THEME-W25", spec_sha256=SPEC,
            claim_version_id=self.claim.claim_version_id,
            evidence_version_ids=(evidence_a.submission.version_id,
                                  evidence_b.submission.version_id),
            relation=EvidenceRelation.SUPPORTS,
            supported_scope=self.claim.scope,
            reviewed_by="owned test reviewer",
            reviewed_at=BASE + timedelta(minutes=3),
            use_context=self.use_context,
            created_at=BASE + timedelta(minutes=3))
        stored = self.evidence.assess_claim(assessment_request)
        assessment = self.evidence.load_assessment(
            stored.submission.version_id)
        self.assertEqual(assessment.independent_root_count, 2)
        self.assertEqual(assessment.same_root_duplicate_count, 0)
        self.assertEqual(
            set(assessment.independent_root_ids),
            {"ROOT-W25-A", "ROOT-W25-B"})
        self.assertFalse(assessment.facts_verified)
        evidence_record = self.evidence.load_evidence(
            evidence_a.submission.version_id)
        self.assertEqual(evidence_record.content_verification,
                         "LOCATOR_REPLAY_ONLY")

    def test_exact_evidence_is_consumable_by_w16_research_revision(self):
        evidence_a = self.make_evidence("EVIDENCE-W25-W16", self.intake_a)
        revision = ResearchRevision(
            revision_id="REV-W25-v001", theme_id="THEME-W25",
            spec_sha256=SPEC,
            input_version_ids=(evidence_a.submission.version_id,),
            evidence_version_ids=(evidence_a.submission.version_id,),
            reason="Bind exact W25 evidence to the shared research revision",
            created_at=BASE + timedelta(minutes=3))
        stored = ResearchRevisionController(
            self.archive, self.journal_rights).append_revision(revision, None)
        self.assertEqual(stored.submission.kind, ObjectKind.RESEARCH_REVISION)
        loaded = ResearchRevisionController(
            self.archive, self.journal_rights).load_revision(
                stored.submission.version_id)
        self.assertEqual(loaded.evidence_version_ids,
                         (evidence_a.submission.version_id,))

    def test_same_root_duplicates_do_not_inflate_independence(self):
        first = self.evidence.append_evidence(
            self.evidence_request("EVIDENCE-W25-DUP-A", self.intake_a))
        second = self.evidence.append_evidence(
            self.evidence_request("EVIDENCE-W25-DUP-B", self.intake_a))
        request = ClaimEvidenceRequest(
            assessment_id="ASSESSMENT-W25-DUP",
            theme_id="THEME-W25", spec_sha256=SPEC,
            claim_version_id=self.claim.claim_version_id,
            evidence_version_ids=(first.submission.version_id,
                                  second.submission.version_id),
            relation=EvidenceRelation.PARTIALLY_SUPPORTS,
            supported_scope=self.claim.scope,
            unsupported_aspects=("Second independent observation is absent",),
            reviewed_by="owned test reviewer",
            reviewed_at=BASE + timedelta(minutes=3),
            use_context=self.use_context,
            created_at=BASE + timedelta(minutes=3))
        stored = self.evidence.assess_claim(request)
        assessment = self.evidence.load_assessment(stored.submission.version_id)
        self.assertEqual(assessment.independent_root_count, 1)
        self.assertEqual(assessment.same_root_duplicate_count, 1)

    def test_partial_claim_scope_requires_unsupported_aspect_and_wrong_kind_fails(self):
        evidence_a = self.evidence.append_evidence(
            self.evidence_request("EVIDENCE-W25-PARTIAL", self.intake_a))
        with self.assertRaises(ValidationError):
            ClaimEvidenceRequest(
                assessment_id="ASSESSMENT-W25-PARTIAL",
                theme_id="THEME-W25", spec_sha256=SPEC,
                claim_version_id=self.claim.claim_version_id,
                evidence_version_ids=(evidence_a.submission.version_id,),
                relation=EvidenceRelation.PARTIALLY_SUPPORTS,
                supported_scope=self.claim.scope,
                reviewed_by="owned test reviewer",
                reviewed_at=BASE + timedelta(minutes=3),
                use_context=self.use_context,
                created_at=BASE + timedelta(minutes=3))
        with self.assertRaises(EvidenceError):
            self.evidence.load_evidence(self.claim.claim_version_id)

    def test_irrelevant_evidence_remains_irrelevant_in_the_record(self):
        evidence_a = self.make_evidence(
            "EVIDENCE-W25-IRRELEVANT", self.intake_a)
        stored = self.evidence.assess_claim(ClaimEvidenceRequest(
            assessment_id="ASSESSMENT-W25-IRRELEVANT",
            theme_id="THEME-W25", spec_sha256=SPEC,
            claim_version_id=self.claim.claim_version_id,
            evidence_version_ids=(evidence_a.submission.version_id,),
            relation=EvidenceRelation.IRRELEVANT,
            reviewed_by="owned test reviewer",
            reviewed_at=BASE + timedelta(minutes=3),
            use_context=self.use_context,
            created_at=BASE + timedelta(minutes=3)))
        assessment = self.evidence.load_assessment(
            stored.submission.version_id)
        self.assertEqual(assessment.relation, EvidenceRelation.IRRELEVANT)
        self.assertIsNone(assessment.supported_scope)

    def test_calculation_executes_exact_values_and_records_units_period(self):
        structure_a = self.original.load_structure(self.intake_a.structure_version_id)
        structure_b = self.original.load_structure(self.intake_b.structure_version_id)
        request = CalculationRequest(
            calculation_id="CALC-W25-001", theme_id="THEME-W25",
            spec_sha256=SPEC, claim_version_id=self.claim.claim_version_id,
            operation=CalculationOperation.PERCENT_CHANGE,
            inputs=(
                CalculationInput(
                    input_id="BASELINE", intake_version_id=self.intake_a_version,
                    node_id=structure_a.nodes[0].node_id,
                    node_text_sha256=structure_a.nodes[0].text_sha256,
                    value_text="100", unit="tonnes", dimension="MASS",
                    period=PERIOD),
                CalculationInput(
                    input_id="CURRENT", intake_version_id=self.intake_b_version,
                    node_id=structure_b.nodes[0].node_id,
                    node_text_sha256=structure_b.nodes[0].text_sha256,
                    value_text="120", unit="tonnes", dimension="MASS",
                    period=PERIOD),
            ),
            output_unit="%", output_dimension="RATIO",
            rounding_places=2, expected_result=Decimal("20.00"),
            use_context=self.use_context,
            created_at=BASE + timedelta(minutes=4))
        stored = self.calculation.calculate(request)
        record = self.calculation.load_calculation(
            stored.submission.version_id)
        self.assertEqual(record.result, Decimal("20.00"))
        self.assertEqual(record.declared_expected_result, Decimal("20.00"))
        self.assertEqual(record.execution_status, "EXECUTED")
        self.assertEqual(record.evaluator, "LOCAL_DECIMAL_EVALUATOR")
        self.assertEqual(record.inputs[0].period, PERIOD)
        self.assertEqual(record.output_unit, "%")
        self.assertFalse(record.facts_verified)
        self.assertFalse(record.causal_support)

    def test_wrong_calculation_period_value_or_unit_is_rejected(self):
        structure = self.original.load_structure(self.intake_a.structure_version_id)
        structure_b = self.original.load_structure(self.intake_b.structure_version_id)
        base = CalculationRequest(
            calculation_id="CALC-W25-BAD",
            theme_id="THEME-W25", spec_sha256=SPEC,
            operation=CalculationOperation.SUM,
            inputs=(
                CalculationInput(
                    input_id="A", intake_version_id=self.intake_a_version,
                    node_id=structure.nodes[0].node_id,
                    node_text_sha256=structure.nodes[0].text_sha256,
                    value_text="100", unit="tonnes", dimension="MASS",
                    period=PERIOD),
                CalculationInput(
                    input_id="B", intake_version_id=self.intake_b_version,
                    node_id=structure_b.nodes[0].node_id,
                    node_text_sha256=structure_b.nodes[0].text_sha256,
                    value_text="120", unit="tonnes", dimension="MASS",
                    period=PERIOD),
            ),
            output_unit="tonnes", output_dimension="MASS",
            use_context=self.use_context,
            created_at=BASE + timedelta(minutes=4))
        with self.assertRaises(ValidationError):
            CalculationRequest.model_validate_json(
                base.model_copy(update={"inputs": (base.inputs[0],)}).model_dump_json())
        bad_period = base.inputs[0].model_copy(update={
            "period": DataPeriod(
                start=datetime(2026, 8, 1, tzinfo=timezone.utc),
                end_exclusive=datetime(2026, 9, 1, tzinfo=timezone.utc))})
        with self.assertRaises(CalculationError):
            self.calculation.calculate(base.model_copy(update={
                "calculation_id": "CALC-W25-PERIOD",
                "inputs": (bad_period, base.inputs[1])}))
        wrong_value = base.inputs[0].model_copy(update={"value_text": "999"})
        with self.assertRaises(CalculationError):
            self.calculation.calculate(base.model_copy(update={
                "calculation_id": "CALC-W25-VALUE",
                "inputs": (wrong_value, base.inputs[1])}))
        wrong_unit = base.inputs[0].model_copy(update={"unit": "kg"})
        with self.assertRaises(CalculationError):
            self.calculation.calculate(base.model_copy(update={
                "calculation_id": "CALC-W25-UNIT",
                "inputs": (wrong_unit, base.inputs[1])}))

    def test_formula_result_mismatch_and_generated_code_are_not_accepted(self):
        structure = self.original.load_structure(self.intake_a.structure_version_id)
        structure_b = self.original.load_structure(self.intake_b.structure_version_id)
        request = CalculationRequest(
            calculation_id="CALC-W25-EXPECTED",
            theme_id="THEME-W25", spec_sha256=SPEC,
            operation=CalculationOperation.SUM,
            inputs=(
                CalculationInput(
                    input_id="A", intake_version_id=self.intake_a_version,
                    node_id=structure.nodes[0].node_id,
                    node_text_sha256=structure.nodes[0].text_sha256,
                    value_text="100", unit="tonnes", dimension="MASS",
                    period=PERIOD),
                CalculationInput(
                    input_id="B", intake_version_id=self.intake_b_version,
                    node_id=structure_b.nodes[0].node_id,
                    node_text_sha256=structure_b.nodes[0].text_sha256,
                    value_text="120", unit="tonnes", dimension="MASS",
                    period=PERIOD),
            ),
            output_unit="tonnes", output_dimension="MASS",
            expected_result=Decimal("999"), use_context=self.use_context,
            created_at=BASE + timedelta(minutes=4))
        with self.assertRaises(CalculationError):
            self.calculation.calculate(request)
        raw = json.loads(request.model_dump_json())
        with self.assertRaises(ValidationError):
            CalculationRequest.model_validate_json(json.dumps({
                **raw,
                "generated_code": "print('unexecuted')",
            }))

    def test_supplement_request_and_actual_no_new_result_roundtrip(self):
        evidence_a = self.evidence.append_evidence(
            self.evidence_request("EVIDENCE-W25-SUPP", self.intake_a))
        assessment_stored = self.evidence.assess_claim(ClaimEvidenceRequest(
            assessment_id="ASSESSMENT-W25-SUPP",
            theme_id="THEME-W25", spec_sha256=SPEC,
            claim_version_id=self.claim.claim_version_id,
            evidence_version_ids=(evidence_a.submission.version_id,),
            relation=EvidenceRelation.PARTIALLY_SUPPORTS,
            supported_scope=self.claim.scope,
            unsupported_aspects=("Second observation missing",),
            reviewed_by="owned test reviewer",
            reviewed_at=BASE + timedelta(minutes=3),
            use_context=self.use_context,
            created_at=BASE + timedelta(minutes=3)))
        request_stored = self.supplement.append_request(SupplementRequest(
            supplement_request_id="SUPPLEMENT-W25-REQ",
            theme_id="THEME-W25", spec_sha256=SPEC,
            claim_version_id=self.claim.claim_version_id,
            assessment_version_id=assessment_stored.submission.version_id,
            gap_type=SupplementGapType.PARTIAL_SUPPORT,
            missing_information="A second independent observation",
            distinguishing_evidence="A different lineage root with the same metric",
            next_owner="T04",
            continuation_trigger="New source with independent root arrives",
            created_at=BASE + timedelta(minutes=4)))
        result_stored = self.supplement.append_result(SupplementResult(
            result_id="SUPPLEMENT-W25-NO-NEW", theme_id="THEME-W25",
            spec_sha256=SPEC,
            supplement_request_version_id=request_stored.submission.version_id,
            status=SupplementStatus.NO_NEW_EVIDENCE,
            method=SupplementMethod.MANUAL,
            before_relation=EvidenceRelation.PARTIALLY_SUPPORTS,
            after_relation=EvidenceRelation.PARTIALLY_SUPPORTS,
            impact=SupplementImpact.UNCHANGED,
            affected_claim_version_ids=(self.claim.claim_version_id,),
            reason="The bounded follow-up found no new admissible evidence",
            continuation_trigger="Reopen when a qualifying source is found",
            created_at=BASE + timedelta(minutes=5)))
        result = self.supplement.load_result(result_stored.submission.version_id)
        self.assertEqual(result.before_relation, result.after_relation)
        self.assertFalse(result.publication_authorized)

    def test_supplement_actual_added_evidence_changes_relation(self):
        evidence_a = self.make_evidence("EVIDENCE-W25-ADD-A", self.intake_a)
        evidence_b = self.make_evidence("EVIDENCE-W25-ADD-B", self.intake_b)
        before = self.make_assessment(
            "ASSESSMENT-W25-ADD-BEFORE", (evidence_a.submission.version_id,),
            EvidenceRelation.PARTIALLY_SUPPORTS,
            unsupported=("A second independent observation is missing",))
        after = self.make_assessment(
            "ASSESSMENT-W25-ADD-AFTER",
            (evidence_a.submission.version_id, evidence_b.submission.version_id),
            EvidenceRelation.SUPPORTS)
        request_stored = self.supplement.append_request(SupplementRequest(
            supplement_request_id="SUPPLEMENT-W25-ADD-REQ",
            theme_id="THEME-W25", spec_sha256=SPEC,
            claim_version_id=self.claim.claim_version_id,
            assessment_version_id=before.submission.version_id,
            gap_type=SupplementGapType.PARTIAL_SUPPORT,
            missing_information="Independent second observation",
            distinguishing_evidence="Different lineage root with same metric",
            next_owner="T04",
            continuation_trigger="Independent source acquired",
            created_at=BASE + timedelta(minutes=4)))
        result_stored = self.supplement.append_result(SupplementResult(
            result_id="SUPPLEMENT-W25-ADD-RESULT",
            theme_id="THEME-W25", spec_sha256=SPEC,
            supplement_request_version_id=request_stored.submission.version_id,
            status=SupplementStatus.EVIDENCE_ADDED,
            method=SupplementMethod.MANUAL,
            source_intake_version_ids=(self.intake_a_version,
                                       self.intake_b_version),
            evidence_version_ids=(evidence_a.submission.version_id,
                                  evidence_b.submission.version_id),
            assessment_version_ids=(after.submission.version_id,),
            before_relation=EvidenceRelation.PARTIALLY_SUPPORTS,
            after_relation=EvidenceRelation.SUPPORTS,
            impact=SupplementImpact.STRENGTHENED,
            affected_claim_version_ids=(self.claim.claim_version_id,),
            reason="A second exact observation from a distinct lineage root was added",
            continuation_trigger="Reopen if either source is revised or withdrawn",
            created_at=BASE + timedelta(minutes=5)))
        result = self.supplement.load_result(result_stored.submission.version_id)
        assessment = self.evidence.load_assessment(
            result.assessment_version_ids[0])
        self.assertEqual(result.after_relation, EvidenceRelation.SUPPORTS)
        self.assertEqual(assessment.independent_root_count, 2)
        self.assertFalse(result.facts_verified)

    def test_added_evidence_result_needs_actual_assessment_and_gpt_trial_is_unavailable(self):
        with self.assertRaises(ValidationError):
            SupplementResult(
                result_id="SUPPLEMENT-W25-FAKE",
                supplement_request_version_id="SUPPLEMENT-W25-REQ",
                theme_id="THEME-W25", spec_sha256=SPEC,
                status=SupplementStatus.EVIDENCE_ADDED,
                method=SupplementMethod.MANUAL,
                impact=SupplementImpact.STRENGTHENED,
                reason="Claimed evidence without actual records",
                continuation_trigger="None", created_at=BASE)
        request = SupplementRequest(
            supplement_request_id="SUPPLEMENT-W25-GPT",
            theme_id="THEME-W25", spec_sha256=SPEC,
            claim_version_id=self.claim.claim_version_id,
            gap_type=SupplementGapType.MISSING_SOURCE,
            missing_information="Independent source",
            distinguishing_evidence="Actual original with exact support",
            next_owner="T04", continuation_trigger="Controlled adapter approved",
            created_at=BASE + timedelta(minutes=4))
        request_stored = self.supplement.append_request(request)
        trial = SupplementResult(
            result_id="SUPPLEMENT-W25-GPT-RESULT",
            supplement_request_version_id=request_stored.submission.version_id,
            theme_id="THEME-W25", spec_sha256=SPEC,
            status=SupplementStatus.NO_NEW_EVIDENCE,
            method=SupplementMethod.GPT_RESEARCHER_TRIAL,
            impact=SupplementImpact.UNCHANGED,
            affected_claim_version_ids=(self.claim.claim_version_id,),
            reason="Owned trial fixture",
            continuation_trigger="Controlled adapter approval",
            created_at=BASE + timedelta(minutes=5))
        with self.assertRaisesRegex(SupplementError, "not implemented"):
            self.supplement.append_result(trial)

    def test_object_change_requires_s8_review(self):
        with self.assertRaises(ValidationError):
            SupplementResult(
                result_id="SUPPLEMENT-W25-CHANGED",
                supplement_request_version_id="SUPPLEMENT-W25-REQ",
                theme_id="THEME-W25", spec_sha256=SPEC,
                status=SupplementStatus.PARTIAL,
                method=SupplementMethod.MANUAL,
                impact=SupplementImpact.OBJECT_OR_SCOPE_CHANGED,
                object_or_scope_changed=True,
                s8_review_required=False,
                affected_claim_version_ids=(self.claim.claim_version_id,),
                reason="Object changed", continuation_trigger="S8 review",
                created_at=BASE)


if __name__ == "__main__":
    unittest.main()
