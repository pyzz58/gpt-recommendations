"""W29 owned-fixture tests for B2 teaching, transfer and M11 submission."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from intelligence.advisor import (AdvisorController, AdvisorJudgment,
                                  AdvisorOutputRequest, BaselineUnderstanding,
                                  DecisionApplicability, JudgmentStrength,
                                  UnderstandingGain)
from intelligence.archive import Archive, PermissionDenied, canonical
from intelligence.contracts import (MaterialUse, ObjectKind, PermissionState,
                                    ReferenceUse, Representation, RightsBasis,
                                    RightsGrant, Scope, ScopeMode, UsePermission,
                                    ValidityMode, VersionReference,
                                    VersionSubmission)
from intelligence.discovery import LineageRole
from intelligence.evidence import (ClaimEvidenceAssessment, ClaimScope,
                                   ClaimType, ClaimVersion, EvidenceNature,
                                   EvidenceNodeBinding, EvidenceRecord,
                                   EvidenceRelation)
from intelligence.operations import (CostObservation, ObservationKind,
                                     OperationJournal, OperationKind,
                                     OperationRequest, OperationStatus,
                                     ToolResponse)
from intelligence.research import ResearchRevision, ResearchRevisionController
from intelligence.teacher import (ConceptReuseMode, ConceptUse, KnowledgeProposition,
                                  KnowledgePropositionType, KnowledgeQuestion,
                                  ProcessStep, TeacherController, TeacherError,
                                  TeacherOutput, TeacherOutputRequest,
                                  TeachingBoundary, TeachingGain, TeachingSection,
                                  TeachingDemonstration, TeachingSectionKind,
                                  TeachingStrength, TermExplanation,
                                  TransferCheck)
from intelligence.workflow import (DossierStartRequest, ExecutionMethod,
                                   MethodUseRecord, Participant,
                                   ParticipantQuestion, ResearchStep,
                                   ResearchStepSubmission,
                                   ResearchWorkflowController, StepDisposition,
                                   StepOwner, WorkflowError)

AT = datetime(2026, 10, 31, 0, 0, tzinfo=timezone.utc)
SPEC = "a" * 64
B2_QUESTION = "Which mechanism explains why the commitment did not become an outcome?"


def _version(prefix, identity):
    return prefix + hashlib.sha256(
        canonical([prefix, identity]).encode()).hexdigest()[:32]


class TeacherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Archive(Path(self.temp.name) / "archive")
        self.addCleanup(self.archive.close)
        self.rights = RightsGrant(
            rights_id="RIGHTS-W29", basis=RightsBasis.OWN_WORK,
            allowed_uses=frozenset({
                MaterialUse.INDEX, MaterialUse.STORE_BODY}),
            evidence="Owned W29 teacher fixtures", checked_by="test fixture",
            checked_at=AT,
            permissions=(UsePermission(
                use=MaterialUse.STORE_BODY,
                state=PermissionState.ALLOWED,
                validity=ValidityMode.OPEN_ENDED,
                territories=Scope(mode=ScopeMode.ANY),
                providers=Scope(mode=ScopeMode.ANY),
                content_scope=Scope(mode=ScopeMode.ANY)),))
        self.time = AT
        self.question = self.store(
            "QUESTION-W29", "QUESTION-W29-v001",
            ObjectKind.QUESTION_VERSION, b"Owned W29 question")
        self.baseline = self.store(
            "SOURCE-MATERIAL-W29", "SOURCE-MATERIAL-W29-v001",
            ObjectKind.SOURCE_MATERIAL, b"Owned original explanation")
        self.claim_scope = ClaimScope(
            subjects=("owned operator",),
            metric="commitment execution",
            comparison_basis="Owned original and follow-up text",
            conditions=("The same commitment and observation period apply",))
        self.claim = ClaimVersion(
            claim_version_id="CLAIM-W29-v001",
            theme_id="THEME-W29", spec_sha256=SPEC,
            question_version_id=self.question.submission.version_id,
            claim_text="The owned operator stated a commitment without observed execution.",
            claim_type=ClaimType.OBSERVED_FACT,
            scope=self.claim_scope, created_at=AT)
        self.store(
            "CLAIM-OBJECT-W29", self.claim.claim_version_id,
            ObjectKind.CLAIM,
            canonical(self.claim.model_dump(mode="json")).encode())
        self.evidence_id = "EVIDENCE-W29-v001"
        self.evidence_version_id = _version(
            "EVIDENCE-RECORD-", "EVIDENCE-W29")
        evidence = EvidenceRecord(
            evidence_id="EVIDENCE-W29", theme_id="THEME-W29",
            spec_sha256=SPEC,
            intake_version_id="INTAKE-W29",
            structure_version_id="STRUCTURE-W29",
            source_id="SOURCE-W29",
            source_sha256="b" * 64,
            lineage_proposal_id="LINEAGE-W29",
            cluster_id="CLUSTER-W29",
            lineage_role=LineageRole.ORIGINAL,
            lineage_root_ids=("ROOT-W29",),
            independence_known=True,
            nodes=(EvidenceNodeBinding(
                node_id="NODE-W29", locator="paragraph 1",
                text_sha256="c" * 64),),
            nature=EvidenceNature.DOCUMENTED_FACT,
            created_at=AT)
        self.store(
            "EVIDENCE-OBJECT-W29", self.evidence_version_id,
            ObjectKind.EVIDENCE,
            canonical(evidence.model_dump(mode="json")).encode())
        self.assessment_version_id = _version(
            "CLAIM-EVIDENCE-", "ASSESSMENT-W29")
        assessment = ClaimEvidenceAssessment(
            assessment_id="ASSESSMENT-W29",
            theme_id="THEME-W29", spec_sha256=SPEC,
            claim_version_id=self.claim.claim_version_id,
            evidence_version_ids=(self.evidence_version_id,),
            relation=EvidenceRelation.SUPPORTS,
            supported_scope=self.claim.scope,
            conditions=self.claim.scope.conditions,
            unsupported_aspects=(), counterevidence=(), unknowns=(),
            independent_root_ids=("ROOT-W29",),
            independent_root_count=1,
            same_root_duplicate_count=0,
            independence_unknown_count=0,
            reviewed_by="owned fixture reviewer",
            reviewed_at=AT + timedelta(seconds=2),
            created_at=AT + timedelta(seconds=2))
        self.store(
            "ASSESSMENT-OBJECT-W29", self.assessment_version_id,
            ObjectKind.CLAIM_EVIDENCE_ASSESSMENT,
            canonical(assessment.model_dump(mode="json")).encode())
        self.concept_version_id = "CONCEPT-W29-v001"
        self.store(
            "CONCEPT-OBJECT-W29", self.concept_version_id,
            ObjectKind.CONCEPT,
            b"Owned commitment/execution distinction concept")
        self.research = ResearchRevisionController(
            self.archive, self.rights)
        self.revision = ResearchRevision(
            revision_id="REV-W29-v001", theme_id="THEME-W29",
            spec_sha256=SPEC,
            input_version_ids=(
                self.question.submission.version_id,
                self.baseline.submission.version_id,
                self.claim.claim_version_id,
                self.evidence_version_id,
                self.assessment_version_id,
                self.concept_version_id),
            question_version_id=self.question.submission.version_id,
            evidence_version_ids=(self.evidence_version_id,),
            reason="Owned W29 exact teaching basis",
            created_at=AT + timedelta(seconds=3))
        self.research.append_revision(self.revision, None)
        self.workflow = ResearchWorkflowController(
            self.archive, self.rights)
        self.workflow.start_dossier(DossierStartRequest(
            dossier_id="DOSSIER-W29", theme_id="THEME-W29",
            spec_sha256=SPEC, revision_id=self.revision.revision_id,
            question_version_id=self.question.submission.version_id,
            knowledge_cutoff=AT,
            created_at=AT + timedelta(seconds=4)))
        self.time = AT + timedelta(seconds=5)
        self.step_records = {}
        self.method_version_id = self.append_method()
        self.complete_through_m09()
        self.teacher = TeacherController(
            self.archive, self.rights, self.workflow)
        self.advisor = AdvisorController(
            self.archive, self.rights, self.workflow)

    def store(self, object_id, version_id, kind, body):
        return self.archive.append(VersionSubmission(
            schema_version=2, object_id=object_id, version_id=version_id,
            kind=kind, title=object_id, spec_sha256=SPEC,
            created_at=AT, rights=self.rights,
            representation=Representation.FULL_BODY), body)

    def artifact(self, label):
        self.time += timedelta(seconds=1)
        return self.archive.append(VersionSubmission(
            schema_version=2, object_id="ARTIFACT-W29-" + label,
            version_id=f"ARTIFACT-W29-{label}-{int(self.time.timestamp())}",
            kind=ObjectKind.ARTICLE, title="ARTIFACT-W29-" + label,
            spec_sha256=SPEC, created_at=self.time, rights=self.rights,
            representation=Representation.FULL_BODY,
            references=(VersionReference(
                target_version_id=self.revision.revision_id,
                use=ReferenceUse.BASIS,
                locator="exact research revision"),)),
            f"Owned {label} artifact".encode())

    def append_method(self):
        method = MethodUseRecord(
            method_use_id="METHOD-W29",
            theme_id="THEME-W29", spec_sha256=SPEC,
            introduced_at=ResearchStep.M02,
            proposition="Separate a stated commitment from observed execution",
            source_version_ids=(self.baseline.submission.version_id,),
            read_scope="Owned original explanation",
            applicability_conditions=("The same actor and period are compared",),
            expected_effect="Keeps implementation an explicit unknown",
            misuse_or_limit="Cannot establish motive or unobserved action",
            created_at=self.time)
        return self.workflow.append_method(method).submission.version_id

    def submit(self, step, *, artifact, methods=(), participants=(),
               disposition=StepDisposition.READY_FOR_NEXT,
               limitations=(), previous=None):
        stored, snapshot = self.workflow.current_snapshot("DOSSIER-W29")
        self.time = max(
            self.time, stored.submission.created_at) + timedelta(seconds=1)
        active = {item.step: item for item in snapshot.active_steps}
        if previous is None and step in active:
            previous = active[step].record_version_id
        elif previous is None:
            for record_id in reversed(snapshot.record_history_version_ids):
                record = self.workflow.load_step_record(record_id)
                if record.step is step:
                    previous = record.step_record_version_id
                    break
        result = self.workflow.submit_step(ResearchStepSubmission(
            step_record_id=f"STEP-{step.value}-{int(self.time.timestamp())}",
            previous_step_record_version_id=previous,
            dossier_id="DOSSIER-W29",
            expected_snapshot_version_id=stored.submission.version_id,
            theme_id="THEME-W29", spec_sha256=SPEC,
            revision_id=self.revision.revision_id, step=step,
            owner={
                ResearchStep.M10: StepOwner.ADVISER,
                ResearchStep.M11: StepOwner.TEACHER,
                ResearchStep.M12: StepOwner.CONDITIONS,
            }.get(step, StepOwner.JOINT),
            disposition=disposition,
            artifact_version_ids=(artifact.submission.version_id,),
            method_use_version_ids=tuple(methods),
            participant_questions=tuple(participants),
            limitations=tuple(limitations),
            created_at=self.time))
        latest = self.workflow.load_snapshot(result.submission.version_id)
        binding = next(item for item in latest.active_steps if item.step is step)
        self.step_records[step] = binding.record_version_id
        return result

    def complete_through_m09(self):
        participants = (
            ParticipantQuestion(
                participant=Participant.B1,
                question="Which bounded case judgment is supported?",
                rationale="B1 joins at M02"),
            ParticipantQuestion(
                participant=Participant.B2,
                question=B2_QUESTION,
                rationale="B2 joins at M02"),
        )
        self.submit(ResearchStep.M01, artifact=self.artifact("M01"))
        self.submit(
            ResearchStep.M02, artifact=self.artifact("M02"),
            methods=(self.method_version_id,),
            participants=participants)
        self.submit(ResearchStep.M03, artifact=self.artifact("M03"))
        self.submit(ResearchStep.M04, artifact=self.artifact("M04"))
        self.submit(ResearchStep.M05, artifact=self.artifact("M05"))
        self.submit(ResearchStep.M06, artifact=self.artifact("M06"))
        self.submit(
            ResearchStep.M07, artifact=self.artifact("M07"),
            methods=(self.method_version_id,))
        self.submit(ResearchStep.M08, artifact=self.artifact("M08"))
        self.submit(ResearchStep.M09, artifact=self.artifact("M09"))

    @staticmethod
    def proposition():
        return KnowledgeProposition(
            proposition_id="PROPOSITION-W29",
            statement=(
                "A public commitment changes what can be expected only when "
                "implementation conditions and observable execution are checked."),
            proposition_type=KnowledgePropositionType.CONDITIONAL_MECHANISM,
            conditions=(
                "The actor has authority to execute",
                "The observation period is long enough for implementation",
            ),
            scope="The owned case and comparable commitment-to-execution problems",
            unknowns=("Internal intent and unreported implementation remain unknown",),
            falsifiers=(
                "Current execution evidence shows the commitment was fulfilled",
            ))

    @staticmethod
    def gain():
        return TeachingGain(
            before_explanation=(
                "The commitment alone appears to establish an outcome."),
            after_explanation=(
                "The commitment identifies an intended change, while execution "
                "requires a separate observable process."),
            case_specific_bridge=(
                "The problem pivots on what the original evidence actually observes."),
            knowledge_contribution=(
                "B2 explains why declaration and implementation are distinct "
                "processes with different evidence."),
            not_b1_restatement=(
                "The teaching contribution is a reusable evidence distinction, "
                "not a restatement of the case judgment."),
            what_reader_can_examine=(
                "Readers can ask whether authority, resources and observed action "
                "connect the announcement to implementation."),
            what_this_cannot_prove="This cannot prove motive or unobserved execution.")

    def sections(self):
        cid = self.claim.claim_version_id
        eid = self.evidence_version_id
        mid = self.method_version_id
        return (
            TeachingSection(
                section_id="C1", ordinal=1,
                kind=TeachingSectionKind.CASE_CONTEXT,
                plain_language_text=(
                    "The original records a promise by an operator whose later "
                    "actions are not in the selected evidence."),
                claim_version_ids=(cid,), evidence_version_ids=(eid,)),
            TeachingSection(
                section_id="B1", ordinal=2,
                kind=TeachingSectionKind.NECESSARY_BASIS,
                plain_language_text=(
                    "An announcement and an execution are different records: one "
                    "states intent, while the other shows an action and result."),
                claim_version_ids=(cid,), evidence_version_ids=(eid,),
                method_use_version_ids=(mid,)),
            TeachingSection(
                section_id="P1", ordinal=3,
                kind=TeachingSectionKind.PROCESS,
                plain_language_text=(
                    "For implementation, authority passes through budgeting and "
                    "staff action, and only then produces an observable result."),
                claim_version_ids=(cid,), evidence_version_ids=(eid,),
                method_use_version_ids=(mid,)),
            TeachingSection(
                section_id="D1", ordinal=4,
                kind=TeachingSectionKind.BOUNDARY,
                plain_language_text=(
                    "If implementation were directly observable in the same "
                    "record, the boundary between promise and outcome would narrow."),
                claim_version_ids=(cid,), evidence_version_ids=(eid,)),
            TeachingSection(
                section_id="K1", ordinal=5,
                kind=TeachingSectionKind.KNOWLEDGE_SUMMARY,
                plain_language_text=(
                    "The transferable knowledge is a commitment-implementation "
                    "distinction, not a claim about the actor's motive."),
                claim_version_ids=(cid,), evidence_version_ids=(eid,)),
            TeachingSection(
                section_id="T1", ordinal=6,
                kind=TeachingSectionKind.TRANSFER,
                plain_language_text=(
                    "In a new organisation, inspect who may spend, who acts and "
                    "what result is observable before carrying this distinction."),
                claim_version_ids=(cid,), evidence_version_ids=(eid,)),
        )

    def request(self, **updates):
        stored, _ = self.workflow.current_snapshot("DOSSIER-W29")
        created_at = max(
            self.time, stored.submission.created_at) + timedelta(seconds=3)
        base = TeacherOutputRequest(
            teaching_id="TEACHER-W29",
            dossier_id="DOSSIER-W29",
            expected_snapshot_version_id=stored.submission.version_id,
            revision_id=self.revision.revision_id,
            theme_id="THEME-W29", spec_sha256=SPEC,
            source_m02_record_version_id=self.step_records[ResearchStep.M02],
            source_m09_record_version_id=self.step_records[ResearchStep.M09],
            knowledge_question=KnowledgeQuestion(
                question_id="KQ-W29",
                early_question=B2_QUESTION,
                research_question=(
                    "What process separates a commitment from implementation?"),
                relation_to_early_question=(
                    "The early question asks for a mechanism; this narrows it "
                    "to the observable commitment-to-action connection."),
                why_material_requires_it=(
                    "The selected evidence includes the promise but not execution."),
                what_it_should_explain=(
                    "Why a promise cannot by itself establish an outcome.")),
            proposition=self.proposition(),
            claim_version_ids=(self.claim.claim_version_id,),
            evidence_version_ids=(self.evidence_version_id,),
            claim_evidence_assessment_version_ids=(
                self.assessment_version_id,),
            method_use_version_ids=(self.method_version_id,),
            concept_uses=(),
            sections=self.sections(),
            process_steps=(
                ProcessStep(
                    step_id="P-START", ordinal=1, section_id="P1",
                    from_condition="The actor has announced an intended change",
                    relation_or_action=(
                        "Authority and resources must be assigned to an executor"),
                    to_result="An implementation action becomes possible",
                    conditions=("The actor has the required formal authority",),
                    evidence_version_ids=(self.evidence_version_id,),
                    uncertainty="The selected evidence does not show the assignment"),
                ProcessStep(
                    step_id="P-RESULT", ordinal=2, section_id="P1",
                    from_condition="An implementation action has occurred",
                    relation_or_action=(
                        "Independent observation must record the resulting change"),
                    to_result="The announcement can be compared with an outcome",
                    conditions=("An observable result exists in the review period",),
                    evidence_version_ids=(self.evidence_version_id,),
                    uncertainty="No completed implementation result is selected"),
            ),
            boundaries=(
                TeachingBoundary(
                    boundary_id="BOUNDARY-W29", section_id="D1",
                    condition_that_changes_result=(
                        "Direct implementation evidence appears in the same record"),
                    counterexample_or_contrast=(
                        "A same-day procurement record could show action despite "
                        "an otherwise similar announcement."),
                    unsupported_scope="No inference about motive",
                    unknowns=("Actual implementation remains unobserved",)),
            ),
            transfers=(
                TransferCheck(
                    transfer_id="TRANSFER-W29", section_id="T1",
                    target_scenario=(
                        "A regulator announces a future enforcement programme"),
                    shared_relations=(
                        "A stated intention precedes an executable action",
                        "Execution requires authority and resources",
                    ),
                    changed_conditions=(
                        "Enforcement may require a separate legal instrument",
                    ),
                    facts_to_recheck=(
                        "The legal instrument",
                        "Budget and staffing decisions",
                        "Observed enforcement actions",
                    ),
                    what_must_not_be_assumed=(
                        "That a public announcement already changes enforcement",
                    )),
            ),
            terms=(
                TermExplanation(
                    term="implementation gap",
                    plain_explanation_section_id="P1",
                    named_in_section_id="K1",
                    definition=(
                        "The interval between a stated intention and an executable, "
                        "observable change."),
                    case_application=(
                        "The selected original supplies the intention, not execution."),
                    limits="The label does not identify motive or a universal cause.",
                    concept_version_id=None),
            ),
            gain=self.gain(),
            strength=TeachingStrength.BOUNDED_EXPLANATION,
            limitations=(),
            next_action="Send the continuous B2 teaching draft to content review.",
            created_at=created_at)
        return base.model_copy(update=updates)

    @staticmethod
    def revalidated(request):
        return TeacherOutputRequest.model_validate_json(
            request.model_dump_json(warnings=False))

    def test_complete_b2_teaching_and_m11_roundtrip_are_idempotent(self):
        request = self.request()
        result = self.teacher.record_teacher(request)
        output = self.teacher.load_teacher(result.teacher_output_version_id)
        self.assertEqual(output.role, "B2")
        self.assertIs(output.facts_verified, False)
        self.assertIs(output.causal_support, False)
        self.assertIs(output.reader_mastery_measured, False)
        self.assertIs(output.content_review_required, True)
        self.assertIs(output.publication_authorized, False)
        record = self.workflow.load_step_record(
            result.m11_step_record_version_id)
        self.assertIs(record.step, ResearchStep.M11)
        self.assertIs(record.disposition, StepDisposition.READY_FOR_NEXT)
        self.assertEqual(
            record.artifact_version_ids,
            (result.teacher_output_version_id,))
        self.assertEqual(
            self.teacher.record_teacher(request), result)
        _, snapshot = self.workflow.current_snapshot("DOSSIER-W29")
        self.assertEqual(
            sum(1 for item in snapshot.active_steps
                if item.step is ResearchStep.M11), 1)

    def test_teaching_requires_its_actual_m02_question_and_active_m09(self):
        wrong_question = self.request(
            knowledge_question=self.request().knowledge_question.model_copy(
                update={"early_question": "An invented B2 question"}))
        with self.assertRaisesRegex(TeacherError, "actual M02 B2 question"):
            self.teacher.record_teacher(wrong_question)
        stored, _ = self.workflow.current_snapshot("DOSSIER-W29")
        wrong_m09 = self.request(
            expected_snapshot_version_id=stored.submission.version_id,
            source_m09_record_version_id=self.step_records[ResearchStep.M08])
        with self.assertRaisesRegex(TeacherError, "active M09"):
            self.teacher.record_teacher(wrong_m09)

    def test_snapshot_and_revision_supersession_are_rejected(self):
        request = self.request()
        self.submit(
            ResearchStep.M10,
            artifact=self.artifact("M10"),
            previous=self.step_records.get(ResearchStep.M10))
        with self.assertRaisesRegex(WorkflowError, "stale dossier snapshot"):
            self.teacher.record_teacher(request)
        replacement = ResearchRevision(
            revision_id="REV-W29-v002", theme_id="THEME-W29",
            spec_sha256=SPEC, based_on_revision_id="REV-W29-v001",
            input_version_ids=self.revision.input_version_ids,
            question_version_id=self.revision.question_version_id,
            evidence_version_ids=self.revision.evidence_version_ids,
            reason="Owned W29 revision supersession",
            created_at=self.time + timedelta(minutes=1))
        self.research.append_revision(
            replacement, "REV-W29-v001")
        with self.assertRaisesRegex(TeacherError, "revision is stale"):
            self.teacher.record_teacher(self.request())

    def test_case_basis_process_boundary_and_transfer_paragraphs_are_required(self):
        required = {
            TeachingSectionKind.CASE_CONTEXT,
            TeachingSectionKind.NECESSARY_BASIS,
            TeachingSectionKind.PROCESS,
            TeachingSectionKind.BOUNDARY,
            TeachingSectionKind.KNOWLEDGE_SUMMARY,
            TeachingSectionKind.TRANSFER,
        }
        for missing in required:
            sections = tuple(
                item for item in self.sections() if item.kind is not missing)
            sections = tuple(item.model_copy(update={"ordinal": index + 1})
                             for index, item in enumerate(sections))
            with self.subTest(missing=missing), self.assertRaises(ValidationError):
                self.revalidated(self.request(sections=sections))

    def test_process_links_need_two_connected_steps_and_real_paragraphs(self):
        request = self.request()
        with self.assertRaisesRegex(ValidationError, "two connected"):
            self.revalidated(self.request(
                process_steps=(request.process_steps[0],)))
        wrong_section = request.process_steps[1].model_copy(
            update={"section_id": "K1"})
        with self.assertRaisesRegex(ValidationError, "PROCESS paragraph"):
            self.revalidated(self.request(
                process_steps=(request.process_steps[0], wrong_section)))
        empty_relation = request.process_steps[0].model_copy(
            update={"relation_or_action": " "})
        with self.assertRaises(ValidationError):
            self.revalidated(self.request(
                process_steps=(empty_relation, request.process_steps[1])))
        unbound_process_source = tuple(
            item.model_copy(update={"evidence_version_ids": ()})
            if item.section_id == "P1" else item
            for item in request.sections)
        with self.assertRaisesRegex(TeacherError, "not bound by its PROCESS"):
            self.teacher.record_teacher(self.request(
                sections=unbound_process_source))

    def test_transfer_needs_changed_conditions_and_recheck_steps(self):
        with self.assertRaisesRegex(ValidationError, "changed condition"):
            TransferCheck(
                transfer_id="BAD-TRANSFER", section_id="T1",
                target_scenario="A different institution",
                shared_relations=("A promise precedes action",),
                changed_conditions=(),
                facts_to_recheck=("The new legal authority",),
                what_must_not_be_assumed=("That execution already happened",))
        with self.assertRaisesRegex(ValidationError, "TRANSFER paragraph"):
            self.revalidated(self.request(transfers=(
                self.request().transfers[0].model_copy(
                    update={"section_id": "K1"}),)))

    def test_calculation_requires_units_assumptions_and_hypothetical_label(self):
        sections = []
        for item in self.sections():
            if item.ordinal >= 4:
                item = item.model_copy(update={"ordinal": item.ordinal + 1})
            sections.append(item)
        sections.insert(3, TeachingSection(
            section_id="E1", ordinal=4,
            kind=TeachingSectionKind.CALCULATION,
            plain_language_text=(
                "A deliberately hypothetical calculation shows why saved hours "
                "do not automatically become saved cash."),
            claim_version_ids=(self.claim.claim_version_id,),
            evidence_version_ids=(self.evidence_version_id,)))
        demonstration = TeachingDemonstration(
            demonstration_id="DEMO-W29", section_id="E1",
            hypothetical=True, hypothetical_label="Hypothetical demonstration",
            inputs_and_units=("100 saved hours", "20 currency units per hour"),
            assumptions=("The work is reassigned rather than removed",),
            steps=("Multiply hours by the hourly cost only as a hypothetical ceiling",),
            result="The numerical result is not an actual cash saving",
            limits="No payroll, demand or contract evidence is present")
        valid = self.revalidated(self.request(
            sections=tuple(sections), demonstrations=(demonstration,)))
        self.teacher.record_teacher(valid)
        with self.assertRaisesRegex(ValidationError, "explicit label"):
            TeachingDemonstration.model_validate_json(
                demonstration.model_copy(
                    update={"hypothetical_label": None}).model_dump_json())
        without_units = demonstration.model_copy(
            update={"inputs_and_units": ()})
        with self.assertRaisesRegex(ValidationError, "values and units"):
            self.revalidated(self.request(
                sections=tuple(sections),
                demonstrations=(without_units,)))

    def test_professional_term_must_follow_its_plain_explanation(self):
        reversed_term = self.request().terms[0].model_copy(update={
            "plain_explanation_section_id": "K1",
            "named_in_section_id": "P1"})
        with self.assertRaisesRegex(ValidationError, "named after"):
            self.revalidated(self.request(terms=(reversed_term,)))

    def test_method_and_concept_links_must_be_current_exact_revision_inputs(self):
        without_method = tuple(
            item.model_copy(update={"method_use_version_ids": ()})
            if item.method_use_version_ids else item
            for item in self.sections())
        with self.assertRaisesRegex(TeacherError, "exactly the declared MethodUse"):
            self.teacher.record_teacher(self.request(
                sections=without_method))
        base_sections = []
        for item in self.sections():
            if item.section_id == "K1":
                item = item.model_copy(update={"concept_version_ids": (
                    self.concept_version_id,)})
            if item.section_id == "T1":
                item = item.model_copy(update={"ordinal": 7})
            base_sections.append(item)
        base_sections.insert(5, TeachingSection(
            section_id="R1", ordinal=6,
            kind=TeachingSectionKind.RECAP,
            plain_language_text=(
                "Recap: a promise says what an actor intends, while execution "
                "requires a separate action and observable result."),
            claim_version_ids=(self.claim.claim_version_id,),
            evidence_version_ids=(self.evidence_version_id,),
            concept_version_ids=(self.concept_version_id,)))
        concept_sections = tuple(base_sections)
        concept_use = ConceptUse(
            concept_version_id=self.concept_version_id,
            reuse_mode=ConceptReuseMode.NECESSARY_RECAP,
            case_application=(
                "The distinction supplies the required basis for the case."),
            conditions_checked=(
                "The concept is used as a definition, not as execution evidence",),
            does_not_prove="The card does not show that implementation occurred.")
        result = self.teacher.record_teacher(self.request(
            sections=concept_sections, concept_uses=(concept_use,)))
        output = self.teacher.load_teacher(result.teacher_output_version_id)
        self.assertEqual(
            output.concept_uses[0].concept_version_id,
            self.concept_version_id)
        with self.assertRaisesRegex(TeacherError, "outside the exact research revision"):
            foreign = self.store(
                "CONCEPT-FOREIGN-W29", "CONCEPT-FOREIGN-W29-v001",
                ObjectKind.CONCEPT, b"Foreign concept")
            self.teacher.record_teacher(self.request(
                teaching_id="TEACHER-W29-FOREIGN",
                concept_uses=(concept_use.model_copy(update={
                    "concept_version_id": foreign.submission.version_id}),),
                sections=tuple(
                    item.model_copy(update={"concept_version_ids": (
                        foreign.submission.version_id,)})
                    if item.concept_version_ids else item
                    for item in concept_sections)))

    def test_claim_evidence_and_withdrawal_are_exact(self):
        wrong_evidence = self.request(
            evidence_version_ids=(self.claim.claim_version_id,))
        with self.assertRaises(Exception):
            self.teacher.record_teacher(wrong_evidence)
        request = self.request()
        self.archive.revoke_rights(
            self.rights.rights_id, (MaterialUse.STORE_BODY,),
            "Owned W29 withdrawal regression")
        with self.assertRaises(PermissionDenied):
            self.teacher.record_teacher(request)

    def test_partial_and_unknown_teaching_are_limited_not_pass(self):
        partial = self.request(
            teaching_id="TEACHER-W29-PARTIAL",
            strength=TeachingStrength.PARTIAL_EXPLANATION,
            limitations=("Execution evidence is not available",))
        result = self.teacher.record_teacher(partial)
        record = self.workflow.load_step_record(
            result.m11_step_record_version_id)
        self.assertIs(record.disposition, StepDisposition.LIMITED)
        with self.assertRaisesRegex(ValidationError, "explicit limitations"):
            self.revalidated(self.request(
                strength=TeachingStrength.PARTIAL_EXPLANATION))

    def test_optional_b1_source_requires_current_m10_and_distinct_b2_gain(self):
        advisor_request = self.advisor_request()
        advisor_result = self.advisor.record_advisor(advisor_request)
        _, snapshot = self.workflow.current_snapshot("DOSSIER-W29")
        m10 = next(
            item for item in snapshot.active_steps
            if item.step is ResearchStep.M10)
        self.step_records[ResearchStep.M10] = m10.record_version_id
        b1_gain = self.advisor.load_advisor(
            advisor_result.advisor_output_version_id).gain
        copied = self.request(
            source_m10_record_version_id=m10.record_version_id,
            source_advisor_output_version_id=(
                advisor_result.advisor_output_version_id),
            gain=self.gain().model_copy(update={
                "not_b1_restatement": b1_gain.journal_contribution}))
        with self.assertRaisesRegex(TeacherError, "cannot relabel"):
            self.teacher.record_teacher(copied)
        valid = self.request(
            teaching_id="TEACHER-W29-WITH-B1",
            source_m10_record_version_id=m10.record_version_id,
            source_advisor_output_version_id=(
                advisor_result.advisor_output_version_id))
        result = self.teacher.record_teacher(valid)
        output = self.teacher.load_teacher(result.teacher_output_version_id)
        self.assertEqual(
            output.source_advisor_output_version_id,
            advisor_result.advisor_output_version_id)
        with self.assertRaisesRegex(ValidationError, "both current M10"):
            self.revalidated(self.request(
                source_m10_record_version_id=m10.record_version_id))

    def advisor_request(self):
        stored, _ = self.workflow.current_snapshot("DOSSIER-W29")
        created_at = max(
            self.time, stored.submission.created_at) + timedelta(seconds=2)
        return AdvisorOutputRequest(
            advisory_id="ADVISOR-W29",
            dossier_id="DOSSIER-W29",
            expected_snapshot_version_id=stored.submission.version_id,
            revision_id=self.revision.revision_id,
            theme_id="THEME-W29", spec_sha256=SPEC,
            source_m09_record_version_id=self.step_records[ResearchStep.M09],
            baseline=BaselineUnderstanding(
                original_version_id=self.baseline.submission.version_id,
                original_scope="Owned original commitment",
                existing_explanation="The original states a commitment.",
                what_it_does_not_explain=(
                    "It does not establish execution or motive.",)),
            claim_version_ids=(self.claim.claim_version_id,),
            evidence_version_ids=(self.evidence_version_id,),
            claim_evidence_assessment_version_ids=(
                self.assessment_version_id,),
            judgment=AdvisorJudgment(
                core_judgment="Only a bounded commitment is supported.",
                strength=JudgmentStrength.BOUNDED_JUDGMENT,
                conditions=("The same statement remains the evidence object",),
                unknowns=("Execution remains unobserved",),
                falsifiers=("Current execution evidence appears",),
                evidence_sensitive_scope="The exact statement and period",
                decision_applicability=DecisionApplicability.NO_ACTION_DECISION,
                decision_effect="No case-specific action chooser is present."),
            gain=UnderstandingGain(
                before_summary="The commitment may appear to be an outcome.",
                after_summary="The judgment stops at a bounded commitment.",
                case_specific_gain=(
                    "B1 separates the announced commitment from an executed result."),
                original_contribution="The original states the commitment.",
                journal_contribution=(
                    "The journal limits the supported result and preserves unknown execution."),
                evidence_change_consequence=(
                    "Current execution evidence would change the judgment."),
                limits=("Execution and motive remain unknown",)),
            next_action="Send B1 to review.",
            created_at=created_at)

    def test_admitted_teacher_requires_w19_operation_inputs_and_receipt(self):
        configuration_sha256 = "f" * 64
        journal = OperationJournal(self.archive, self.rights)

        def operation(operation_id):
            return OperationRequest(
                operation_id=operation_id,
                idempotency_key="IDEM-" + operation_id,
                run_id="RUN-W29", task_version_id=self.question.submission.version_id,
                step_id="M11", spec_sha256=SPEC,
                kind=OperationKind.MODEL,
                tool_id="OWNED-MODEL", tool_version="fixture-v1",
                provider_id="owned-provider",
                configuration_sha256=configuration_sha256,
                request_sha256="d" * 64,
                material_use=MaterialUse.MODEL_PROCESS,
                input_version_ids=(
                    self.revision.revision_id,
                    self.step_records[ResearchStep.M02],
                    self.step_records[ResearchStep.M09],
                    self.claim.claim_version_id,
                    self.evidence_version_id,
                    self.assessment_version_id,
                    self.method_version_id,
                ),
                created_at=self.time)

        missing = journal.begin(operation("OP-W29-NO-RECEIPT"))
        fake_configuration = SimpleNamespace(
            configuration_sha256=configuration_sha256)
        missing_request = self.request(
            teaching_id="TEACHER-W29-MODEL-MISSING",
            execution_method=ExecutionMethod.ADMITTED_MODEL,
            model_admission_id="ADMISSION-W29",
            model_configuration_id="CONFIG-W29",
            operation_request_version_id=missing.submission.version_id,
            model_domains=("world-knowledge",))
        with patch.object(
                self.teacher.model_admission, "authorizes",
                return_value=True), patch.object(
                    self.teacher.model_admission, "load_configuration",
                    return_value=fake_configuration):
            with self.assertRaisesRegex(TeacherError, "successful operation receipt"):
                self.teacher.record_teacher(missing_request)

        success = journal.begin(operation("OP-W29-SUCCESS"))
        journal.record_receipt(ToolResponse(
            status=OperationStatus.SUCCEEDED,
            result_sha256="e" * 64,
            cost=CostObservation(
                kind=ObservationKind.UNKNOWN,
                basis="Owned fixture has no provider bill"),
            started_at=self.time,
            ended_at=self.time + timedelta(seconds=1)),
            operation_id=success.submission.version_id,
            recorded_at=self.time + timedelta(seconds=1))
        valid = self.request(
            teaching_id="TEACHER-W29-MODEL-SUCCESS",
            execution_method=ExecutionMethod.ADMITTED_MODEL,
            model_admission_id="ADMISSION-W29",
            model_configuration_id="CONFIG-W29",
            operation_request_version_id=success.submission.version_id,
            model_domains=("world-knowledge",),
            created_at=self.time + timedelta(seconds=2))
        with patch.object(
                self.teacher.model_admission, "authorizes",
                return_value=True), patch.object(
                    self.teacher.model_admission, "load_configuration",
                    return_value=fake_configuration), patch.object(
                    self.workflow.model_admission, "authorizes",
                    return_value=True), patch.object(
                    self.workflow.model_admission, "load_configuration",
                    return_value=fake_configuration):
            result = self.teacher.record_teacher(valid)
        output = self.teacher.load_teacher(result.teacher_output_version_id)
        self.assertEqual(
            output.operation_request_version_id,
            success.submission.version_id)

    def test_failed_m11_is_recoverable_without_active_half_output(self):
        request = self.request()
        with patch.object(
                self.teacher.workflow, "submit_step",
                side_effect=WorkflowError("owned simulated M11 failure")):
            with self.assertRaisesRegex(TeacherError, "unadopted attempt"):
                self.teacher.record_teacher(request)
        _, snapshot = self.workflow.current_snapshot("DOSSIER-W29")
        self.assertFalse(any(
            item.step is ResearchStep.M11 for item in snapshot.active_steps))
        result = self.teacher.record_teacher(request)
        self.assertEqual(
            self.workflow.load_step_record(
                result.m11_step_record_version_id).artifact_version_ids,
            (result.teacher_output_version_id,))

    def test_concurrent_exact_requests_leave_one_active_m11(self):
        request = self.request()

        def writer(_):
            with Archive(self.archive.root) as archive:
                controller = TeacherController(
                    archive, self.rights,
                    ResearchWorkflowController(archive, self.rights))
                try:
                    return controller.record_teacher(request)
                except Exception as exc:
                    return exc

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(writer, range(2)))
        self.assertTrue(outcomes)
        _, snapshot = self.workflow.current_snapshot("DOSSIER-W29")
        active_m11 = [
            item for item in snapshot.active_steps
            if item.step is ResearchStep.M11]
        self.assertEqual(len(active_m11), 1)
        history = [
            record_id
            for record_id in snapshot.record_history_version_ids
            if self.workflow.load_step_record(record_id).step is ResearchStep.M11]
        self.assertEqual(len(history), 1)

    def test_upstream_rework_links_new_m11_to_previous_teacher_history(self):
        first = self.teacher.record_teacher(self.request())
        self.submit(
            ResearchStep.M05,
            artifact=self.artifact("M05-rework"),
            previous=self.step_records[ResearchStep.M05])
        self.submit(
            ResearchStep.M07,
            artifact=self.artifact("M07-rework"),
            methods=tuple(
                self.workflow.current_snapshot("DOSSIER-W29")[1]
                .method_use_version_ids))
        self.submit(
            ResearchStep.M08,
            artifact=self.artifact("M08-rework"))
        self.submit(
            ResearchStep.M09,
            artifact=self.artifact("M09-rework"))
        second = self.teacher.record_teacher(self.request(
            previous_version_id=first.teacher_output_version_id,
            gain=self.gain().model_copy(update={
                "after_explanation": (
                    "The reworked process still separates intention from execution."),
            })))
        record = self.workflow.load_step_record(
            second.m11_step_record_version_id)
        self.assertEqual(
            record.previous_step_record_version_id,
            first.m11_step_record_version_id)
        output = self.teacher.load_teacher(second.teacher_output_version_id)
        self.assertEqual(
            output.previous_version_id, first.teacher_output_version_id)

    def test_reader_mastery_and_publication_claims_are_impossible(self):
        result = self.teacher.record_teacher(self.request())
        output = self.teacher.load_teacher(result.teacher_output_version_id)
        forged = output.model_dump(mode="json")
        forged.update({
            "reader_mastery_measured": True,
            "publication_authorized": True,
            "role": "GENERAL_TEACHER",
        })
        with self.assertRaises(ValidationError):
            TeacherOutput.model_validate_json(canonical(forged))
        payload = self.request().model_dump(mode="json")
        payload.update({"reader_score": 99, "mastery_confirmed": True})
        with self.assertRaisesRegex(ValidationError, "Extra inputs"):
            TeacherOutputRequest.model_validate_json(canonical(payload))


if __name__ == "__main__":
    unittest.main()
