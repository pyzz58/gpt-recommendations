"""W27 owned-fixture M01-M12 dependency, invalidation and checkpoint tests."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from pydantic import ValidationError

from intelligence.archive import Archive
from intelligence.contracts import (MaterialUse, ObjectKind, PermissionState,
                                    ReferenceUse, Representation, RightsBasis,
                                    RightsGrant, Scope, ScopeMode, UsePermission,
                                    ValidityMode, VersionReference,
                                    VersionSubmission)
from intelligence.research import ResearchRevision, ResearchRevisionController
from intelligence.workflow import (DEPENDENCIES, DossierCycleState,
                                   DossierStartRequest, ExecutionMethod,
                                   MethodUseRecord, Participant,
                                   ParticipantQuestion, ResearchClosure,
                                   ResearchStep, ResearchStepSubmission,
                                   ResearchWorkflowController, StepDisposition,
                                   StepOwner, WorkflowError)

AT = datetime(2026, 10, 31, 0, 0, tzinfo=timezone.utc)
SPEC = "a" * 64


class ResearchWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Archive(Path(self.temp.name) / "archive")
        self.addCleanup(self.archive.close)
        self.rights = RightsGrant(
            rights_id="RIGHTS-W27", basis=RightsBasis.OWN_WORK,
            allowed_uses=frozenset({MaterialUse.INDEX, MaterialUse.STORE_BODY}),
            evidence="Owned W27 workflow fixtures", checked_by="test fixture",
            checked_at=AT,
            permissions=(UsePermission(
                use=MaterialUse.STORE_BODY, state=PermissionState.ALLOWED,
                validity=ValidityMode.OPEN_ENDED,
                territories=Scope(mode=ScopeMode.ANY),
                providers=Scope(mode=ScopeMode.ANY),
                content_scope=Scope(mode=ScopeMode.ANY)),))
        self.question = self.record(
            "QUESTION-W27", "QUESTION-W27-v001", ObjectKind.QUESTION_VERSION)
        self.evidence = self.record(
            "EVIDENCE-W27", "EVIDENCE-W27-v001", ObjectKind.EVIDENCE)
        self.method_source = self.record(
            "METHOD-SOURCE-W27", "METHOD-SOURCE-W27-v001", ObjectKind.DOCUMENT)
        self.research = ResearchRevisionController(self.archive, self.rights)
        revision = ResearchRevision(
            revision_id="REV-W27-v001", theme_id="THEME-W27",
            spec_sha256=SPEC,
            input_version_ids=(
                self.question.submission.version_id,
                self.evidence.submission.version_id),
            question_version_id=self.question.submission.version_id,
            evidence_version_ids=(self.evidence.submission.version_id,),
            reason="Owned W27 shared research revision", created_at=AT)
        self.research.append_revision(revision, None)
        self.controller = ResearchWorkflowController(self.archive, self.rights)
        self.started = self.controller.start_dossier(DossierStartRequest(
            dossier_id="DOSSIER-W27", theme_id="THEME-W27",
            spec_sha256=SPEC, revision_id=revision.revision_id,
            question_version_id=self.question.submission.version_id,
            knowledge_cutoff=AT, created_at=AT + timedelta(seconds=1)))
        self.time = AT + timedelta(seconds=2)
        self.methods = []
        self.step_records = {}

    def record(self, object_id, version_id, kind, references=()):
        return self.archive.append(VersionSubmission(
            object_id=object_id, version_id=version_id, kind=kind,
            title=f"Owned {object_id}", spec_sha256=SPEC, created_at=AT,
            rights=self.rights, representation=Representation.FULL_BODY,
            references=tuple(references)), f"Owned {object_id} body".encode())

    def artifact(self, step, suffix="v001"):
        return self.record(
            "ARTIFACT-" + step.value + "-" + suffix,
            "ARTIFACT-" + step.value + "-" + suffix,
            ObjectKind.ARTICLE,
            references=(VersionReference(
                target_version_id="REV-W27-v001",
                use=ReferenceUse.BASIS, locator="exact research revision"),))

    def method(self, introduced_at):
        record = MethodUseRecord(
            method_use_id=f"METHOD-W27-{introduced_at.value}",
            theme_id="THEME-W27", spec_sha256=SPEC,
            introduced_at=introduced_at,
            proposition="Owned distinction method",
            source_version_ids=(self.method_source.submission.version_id,),
            read_scope="Owned method source relevant subsection",
            applicability_conditions=("The observed difference is comparable",),
            expected_effect="Changes which evidence distinguishes the explanation",
            misuse_or_limit="The method cannot establish facts without source evidence",
            created_at=self.time)
        stored = self.controller.append_method(record)
        self.methods.append(stored.submission.version_id)
        return stored.submission.version_id

    def current(self):
        return self.controller.current_snapshot("DOSSIER-W27")

    def submit(self, step, *, disposition=StepDisposition.READY_FOR_NEXT,
               methods=(), participants=(), closure=None, limitations=(),
               next_action=None, previous=None, artifact_suffix="v001"):
        snapshot_stored, snapshot = self.current()
        self.time += timedelta(seconds=1)
        if previous is None and step in {
                binding.step for binding in snapshot.active_steps}:
            previous = next(
                binding.record_version_id for binding in snapshot.active_steps
                if binding.step is step)
        result = self.controller.submit_step(ResearchStepSubmission(
            step_record_id=f"STEP-{step.value}-{int(self.time.timestamp())}",
            previous_step_record_version_id=previous,
            dossier_id="DOSSIER-W27",
            expected_snapshot_version_id=snapshot_stored.submission.version_id,
            theme_id="THEME-W27", spec_sha256=SPEC,
            revision_id="REV-W27-v001", step=step,
            owner={
                ResearchStep.M10: StepOwner.ADVISER,
                ResearchStep.M11: StepOwner.TEACHER,
                ResearchStep.M12: StepOwner.CONDITIONS,
            }.get(step, StepOwner.JOINT),
            disposition=disposition,
            artifact_version_ids=(self.artifact(
                step, artifact_suffix).submission.version_id,),
            method_use_version_ids=tuple(methods),
            participant_questions=tuple(participants),
            closure=closure, limitations=tuple(limitations),
            next_action=next_action, created_at=self.time))
        latest = self.controller.load_snapshot(result.submission.version_id)
        binding = next(
            item for item in latest.active_steps if item.step is step)
        self.step_records[step] = binding.record_version_id
        return result

    @staticmethod
    def participants():
        return (
            ParticipantQuestion(
                participant=Participant.B1,
                question="What action/choice does this difference alter?",
                rationale="B1 joins at M02"),
            ParticipantQuestion(
                participant=Participant.B2,
                question="What mechanism should the reader learn to distinguish?",
                rationale="B2 joins at M02"),
        )

    def test_dependencies_allow_parallel_independent_steps_without_full_sequence_gate(self):
        self.submit(ResearchStep.M01)
        self.submit(
            ResearchStep.M02, participants=self.participants())
        self.submit(ResearchStep.M03)
        self.submit(ResearchStep.M04)
        # M06 depends on facts/conditions but not M05; it can advance before M05.
        self.submit(ResearchStep.M06)
        _, snapshot = self.current()
        active = {item.step for item in snapshot.active_steps}
        self.assertIn(ResearchStep.M06, active)
        self.assertNotIn(ResearchStep.M05, active)

    def test_m02_needs_both_b1_and_b2_and_later_step_cannot_skip_dependencies(self):
        self.submit(ResearchStep.M01)
        with self.assertRaisesRegex(WorkflowError, "B1 and B2"):
            self.submit(ResearchStep.M02)
        with self.assertRaisesRegex(WorkflowError, "dependencies"):
            self.submit(ResearchStep.M04)

    def test_method_can_start_at_m02_but_m07_cannot_be_first_method_step(self):
        self.submit(ResearchStep.M01)
        method_id = self.method(ResearchStep.M02)
        self.submit(
            ResearchStep.M02, methods=(method_id,),
            participants=self.participants())
        self.submit(ResearchStep.M03)
        self.submit(ResearchStep.M04)
        self.submit(ResearchStep.M05)
        self.submit(ResearchStep.M06)
        self.submit(ResearchStep.M07, methods=(method_id,))
        _, snapshot = self.current()
        self.assertIn(method_id, snapshot.method_use_version_ids)

    def test_m07_rejects_a_method_first_introduced_at_m07(self):
        self.submit(ResearchStep.M01)
        self.submit(ResearchStep.M02, participants=self.participants())
        self.submit(ResearchStep.M03)
        self.submit(ResearchStep.M04)
        self.submit(ResearchStep.M05)
        self.submit(ResearchStep.M06)
        method_id = self.method(ResearchStep.M07)
        with self.assertRaisesRegex(WorkflowError, "first point"):
            self.submit(ResearchStep.M07, methods=(method_id,))

    def test_full_cycle_integrates_b1_b2_closure_and_official_checkpoint(self):
        self.submit(ResearchStep.M01)
        method_id = self.method(ResearchStep.M02)
        self.submit(
            ResearchStep.M02, methods=(method_id,),
            participants=self.participants())
        self.submit(ResearchStep.M03)
        self.submit(ResearchStep.M04)
        self.submit(ResearchStep.M05)
        self.submit(ResearchStep.M06)
        self.submit(ResearchStep.M07, methods=(method_id,))
        self.submit(ResearchStep.M08)
        self.submit(ResearchStep.M09)
        self.submit(
            ResearchStep.M10, disposition=StepDisposition.LIMITED,
            limitations=("Professional premise remains unresolved",))
        self.submit(ResearchStep.M11)
        closure = ResearchClosure(
            supported_scope="Owned bounded mechanism claim",
            remaining_unknowns=("Professional premise remains unresolved",),
            stop_reason="No more admissible owned evidence distinguishes the mechanism",
            next_trigger="A new professional source resolves the premise",
            reopen_owner="T04")
        final = self.submit(ResearchStep.M12, closure=closure)
        snapshot = self.controller.load_snapshot(final.submission.version_id)
        self.assertEqual(len(snapshot.active_steps), 12)
        self.assertEqual(snapshot.cycle_state, DossierCycleState.LIMITED_CLOSURE)
        self.assertEqual(
            self.controller.load_step_record(
                next(item for item in snapshot.active_steps
                     if item.step is ResearchStep.M12).record_version_id).closure,
            closure)
        checkpoint = self.controller.checkpoint_values(snapshot.graph_thread_id)
        self.assertEqual(checkpoint["last_step"], "M12")
        self.assertEqual(len(checkpoint["completed_steps"]), 12)

    def test_rework_invalidates_only_dependency_descendants(self):
        self.submit(ResearchStep.M01)
        method_id = self.method(ResearchStep.M02)
        self.submit(
            ResearchStep.M02, methods=(method_id,),
            participants=self.participants())
        self.submit(ResearchStep.M03)
        self.submit(ResearchStep.M04)
        self.submit(ResearchStep.M05)
        self.submit(ResearchStep.M06)
        self.submit(ResearchStep.M07, methods=(method_id,))
        self.submit(ResearchStep.M08)
        self.submit(ResearchStep.M09)
        self.submit(ResearchStep.M10)
        self.submit(ResearchStep.M11)
        self.submit(ResearchStep.M12, closure=ResearchClosure(
            supported_scope="Owned bounded closure",
            stop_reason="Owned fixture completed",
            next_trigger="Owned trigger",
            reopen_owner="T04"))
        self.submit(
            ResearchStep.M05, previous=self.step_records[ResearchStep.M05],
            artifact_suffix="rework-v002")
        _, snapshot = self.current()
        active = {item.step for item in snapshot.active_steps}
        self.assertEqual(
            active,
            {ResearchStep.M01, ResearchStep.M02, ResearchStep.M03,
             ResearchStep.M04, ResearchStep.M05, ResearchStep.M06})
        self.assertTrue({
            ResearchStep.M07, ResearchStep.M08, ResearchStep.M09,
            ResearchStep.M10, ResearchStep.M11, ResearchStep.M12,
        } <= set(snapshot.stale_steps))
        self.assertEqual(snapshot.cycle_state, DossierCycleState.OPEN)

    def test_checkpoint_can_be_rebuilt_from_authoritative_dossier(self):
        self.submit(ResearchStep.M01)
        _, snapshot = self.current()
        restarted = ResearchWorkflowController(self.archive, self.rights)
        restarted.restore_checkpoint(
            self.controller.current_snapshot("DOSSIER-W27")[0].submission.version_id)
        values = restarted.checkpoint_values(snapshot.graph_thread_id)
        self.assertEqual(values["completed_steps"], ["M01"])
        self.assertEqual(values["active_steps"][0][0], "M01")

    def test_wrong_artifact_revision_and_unconfigured_model_are_rejected(self):
        artifact = self.record(
            "BAD-W27-ART", "BAD-W27-ART-v001", ObjectKind.ARTICLE)
        snapshot_stored, _ = self.current()
        bad = ResearchStepSubmission(
            step_record_id="STEP-W27-BAD",
            dossier_id="DOSSIER-W27",
            expected_snapshot_version_id=snapshot_stored.submission.version_id,
            theme_id="THEME-W27", spec_sha256=SPEC,
            revision_id="REV-W27-v001", step=ResearchStep.M01,
            owner=StepOwner.JOINT,
            disposition=StepDisposition.READY_FOR_NEXT,
            artifact_version_ids=(artifact.submission.version_id,),
            created_at=self.time)
        with self.assertRaisesRegex(WorkflowError, "exact research revision"):
            self.controller.submit_step(bad)
        with self.assertRaises(ValidationError):
            ResearchStepSubmission(
                step_record_id="STEP-W27-MODEL-MISSING",
                dossier_id="DOSSIER-W27",
                expected_snapshot_version_id=snapshot_stored.submission.version_id,
                theme_id="THEME-W27", spec_sha256=SPEC,
                revision_id="REV-W27-v001", step=ResearchStep.M01,
                owner=StepOwner.JOINT,
                disposition=StepDisposition.READY_FOR_NEXT,
                artifact_version_ids=(artifact.submission.version_id,),
                execution_method=ExecutionMethod.ADMITTED_MODEL,
                created_at=self.time)


if __name__ == "__main__":
    unittest.main()
