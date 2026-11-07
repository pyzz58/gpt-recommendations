"""W15 adoption boundary tests using explicitly synthetic internal records."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from pydantic import ValidationError

from intelligence.adoption import (AdoptionController, AdoptionDecision, AdoptionError,
                                   CheckerRole, DecisionRequest, DependencyDecision,
                                   StepState, StepSubmission)
from intelligence.archive import Archive, ArchiveError, MissingVersion
from intelligence.contracts import (MaterialUse, ObjectKind, PermissionState, Representation,
                                    ReviewCoverage, RightsBasis, RightsGrant, Scope, ScopeMode,
                                    UsePermission, ValidityMode, VersionSubmission)

AT=datetime(2026,10,25,0,0,tzinfo=timezone.utc)
SPEC="a"*64
BODY=b"Owned synthetic internal adoption fixture\n"
PROJECT=Path(__file__).resolve().parents[1]


class AdoptionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.archive=Archive(Path(self.temp.name)/"archive");self.addCleanup(self.archive.close)
        self.rights=RightsGrant(rights_id="RIGHTS-INTERNAL",basis=RightsBasis.OWN_WORK,
            allowed_uses=frozenset({MaterialUse.INDEX,MaterialUse.STORE_BODY}),
            evidence="Owned synthetic journal fixture",checked_by="test fixture",checked_at=AT,
            permissions=(UsePermission(use=MaterialUse.STORE_BODY,state=PermissionState.ALLOWED,
                validity=ValidityMode.OPEN_ENDED,territories=Scope(mode=ScopeMode.ANY),
                providers=Scope(mode=ScopeMode.ANY),content_scope=Scope(mode=ScopeMode.ANY)),))
        self.controller=AdoptionController(self.archive,self.rights)
        self.append_record("TASK-W15","TASK-W15-v001",ObjectKind.TASK)
        self.append_record("ARTICLE-1","ARTICLE-1-v001",ObjectKind.ARTICLE)
        self.append_record("REVIEW-1","REVIEW-1-v001",ObjectKind.REVIEW,
            coverage=(ReviewCoverage(task_version_id="TASK-W15-v001",
                subject_version_id="ARTICLE-1-v001",
                reviewed_scope=("CLAIM-ANALYSIS",)),))

    def append_record(self, object_id, version_id, kind, *, coverage=(), rights=None,
                      parent=None):
        return self.archive.append(VersionSubmission(
            object_id=object_id,version_id=version_id,parent_version_id=parent,
            kind=kind,title=object_id,
            spec_sha256=SPEC,created_at=AT,rights=rights or self.rights,
            representation=Representation.FULL_BODY,
            review_coverage=tuple(coverage)),BODY)

    def submission(self, suffix="1", *, evidence=("REVIEW-1-v001",),
                   dependencies=(), task="TASK-W15-v001", subject="ARTICLE-1-v001",
                   proposed=StepState.READY, created_at=AT, step="M01"):
        return StepSubmission(submission_id=f"SUBMISSION-{suffix}",work_id="W15",step_id=step,
            spec_sha256=SPEC,task_version_id=task,subject_version_id=subject,
            producer_id="writer",proposed_state=proposed,claimed_scope=("CLAIM-ANALYSIS",),
            input_version_ids=(subject,),evidence_version_ids=tuple(evidence),
            dependency_decisions=tuple(dependencies),gaps=(),created_at=created_at)

    def request(self, submission_id, *, decision="DEC-W15-M01-v001", state=StepState.READY,
                checker="checker",role=CheckerRole.L5,review="REVIEW-1-v001",
                scope=("CLAIM-ANALYSIS",),reason="Independent check recorded",
                decided_at=AT+timedelta(minutes=1),expires_at=AT+timedelta(hours=2)):
        return DecisionRequest(decision_id=decision,submission_version_id=submission_id,
            state=state,checker_id=checker,checker_role=role,review_version_id=review,
            allowed_scope=scope,reason=reason,decided_at=decided_at,expires_at=expires_at)

    def test_submission_does_not_become_authority_until_separate_decision(self):
        self.assertEqual(self.controller.current_state("W15","M01","TASK-W15"),StepState.PENDING)
        stored=self.controller.submit(self.submission())
        self.assertEqual(stored.submission.kind,ObjectKind.STEP_SUBMISSION)
        self.assertIsNone(self.controller.current("W15","M01","TASK-W15"))
        decision=self.controller.decide(self.request("SUBMISSION-1"))
        self.assertEqual(decision.submission.kind,ObjectKind.ADOPTION_DECISION)
        current=self.controller.current("W15","M01","TASK-W15")
        self.assertEqual(current.state,StepState.READY)
        self.assertTrue(self.controller.is_current(current.decision_id,AT+timedelta(minutes=2)))
        self.assertTrue(self.controller.authorizes(current.decision_id,("CLAIM-ANALYSIS",),
            AT+timedelta(minutes=2)))
        self.assertFalse(self.controller.authorizes(current.decision_id,("UNRECORDED-SCOPE",),
            AT+timedelta(minutes=2)))
        self.assertFalse(self.controller.is_current(current.decision_id,AT+timedelta(hours=3)))

    def test_self_signature_missing_review_and_wrong_record_kind_are_rejected(self):
        self.controller.submit(self.submission())
        with self.assertRaisesRegex(AdoptionError,"producer cannot"):
            self.controller.decide(self.request("SUBMISSION-1",checker="writer"))
        missing=self.submission("2",evidence=())
        self.controller.submit(missing)
        with self.assertRaisesRegex(AdoptionError,"declared submission evidence"):
            self.controller.decide(self.request("SUBMISSION-2",decision="DEC-W15-M01-v002"))
        wrong=self.submission("3",evidence=("ARTICLE-1-v001",))
        self.controller.submit(wrong)
        with self.assertRaisesRegex(AdoptionError,"not an archived Review"):
            self.controller.decide(self.request("SUBMISSION-3",decision="DEC-W15-M01-v003",
                review="ARTICLE-1-v001"))

    def test_missing_input_and_invalid_decision_contract_are_rejected(self):
        with self.assertRaises(Exception):
            self.controller.submit(self.submission(task="TASK-MISSING-v001"))
        with self.assertRaises(ValidationError):
            self.request("SUBMISSION-1",state=StepState.READY,scope=())
        with self.assertRaises(ValidationError):
            self.request("SUBMISSION-1",state=StepState.RETURN,scope=("CLAIM-ANALYSIS",))
        with self.assertRaises(ValidationError):
            self.request("SUBMISSION-1",state=StepState.PENDING,scope=())
        with self.assertRaises(ValidationError):
            self.request("SUBMISSION-1",decided_at=AT,expires_at=AT)

    def test_dependency_must_bind_exact_adopted_subject_and_expiry(self):
        upstream=self.controller.submit(self.submission("10",subject="ARTICLE-1-v001"))
        self.controller.decide(self.request("SUBMISSION-10",decision="DEC-W15-M10-v001",
            decided_at=AT+timedelta(minutes=1),expires_at=AT+timedelta(minutes=30)))
        downstream=self.submission("11",dependencies=(DependencyDecision(
            decision_id="DEC-W15-M10-v001",expected_subject_version_id="ARTICLE-1-v001"),),
            created_at=AT+timedelta(minutes=20))
        stored=self.controller.submit(downstream)
        self.assertEqual(stored.submission.version_id,"SUBMISSION-11")
        changed=self.submission("12",dependencies=(DependencyDecision(
            decision_id="DEC-W15-M10-v001",expected_subject_version_id="ARTICLE-1-v001"),),
            created_at=AT+timedelta(minutes=31))
        with self.assertRaisesRegex(AdoptionError,"expired"):
            self.controller.submit(changed)
        mismatch=self.submission("13",dependencies=(DependencyDecision(
            decision_id="DEC-W15-M10-v001",expected_subject_version_id="TASK-W15-v001"),),
            created_at=AT+timedelta(minutes=20))
        with self.assertRaisesRegex(AdoptionError,"different subject"):
            self.controller.submit(mismatch)
        self.controller.submit(self.submission("14",created_at=AT+timedelta(minutes=21)))
        self.controller.decide(self.request("SUBMISSION-14",decision="DEC-W15-M10-v002",
            state=StepState.RETURN,scope=(),reason="Superseding rework decision",
            decided_at=AT+timedelta(minutes=22)))
        superseded=self.submission("15",dependencies=(DependencyDecision(
            decision_id="DEC-W15-M10-v001",expected_subject_version_id="ARTICLE-1-v001"),),
            created_at=AT+timedelta(minutes=23))
        with self.assertRaisesRegex(AdoptionError,"superseded"):
            self.controller.submit(superseded)

    def test_not_applicable_dependency_remains_explicit_but_not_ready(self):
        self.controller.submit(self.submission("20"))
        self.controller.decide(self.request("SUBMISSION-20",decision="DEC-W15-M20-v001",
            state=StepState.NOT_APPLICABLE,scope=(),reason="No applicable action for this form"))
        decision=self.controller.current("W15","M01","TASK-W15")
        self.assertEqual(decision.state,StepState.NOT_APPLICABLE)
        self.assertFalse(self.controller.is_current(decision.decision_id))
        dependent=self.submission("21",dependencies=(DependencyDecision(
            decision_id="DEC-W15-M20-v001",expected_subject_version_id="ARTICLE-1-v001"),),
            created_at=AT+timedelta(minutes=2))
        self.assertEqual(self.controller.submit(dependent).submission.version_id,"SUBMISSION-21")

    def test_review_must_cover_the_exact_task_subject_and_scope(self):
        with self.assertRaises(MissingVersion):
            self.append_record("REVIEW-DANGLING","REVIEW-DANGLING-v001",ObjectKind.REVIEW,
                coverage=(ReviewCoverage(task_version_id="TASK-W15-v001",
                    subject_version_id="ARTICLE-MISSING-v001",
                    reviewed_scope=("CLAIM-ANALYSIS",)),))
        self.append_record("DOCUMENT-NOT-TASK","DOCUMENT-NOT-TASK-v001",ObjectKind.DOCUMENT)
        with self.assertRaisesRegex(ArchiveError,"not a Task"):
            self.append_record("REVIEW-WRONGTASK","REVIEW-WRONGTASK-v001",ObjectKind.REVIEW,
                coverage=(ReviewCoverage(task_version_id="DOCUMENT-NOT-TASK-v001",
                    subject_version_id="ARTICLE-1-v001",
                    reviewed_scope=("CLAIM-ANALYSIS",)),))
        self.append_record("ARTICLE-OTHER","ARTICLE-OTHER-v001",ObjectKind.ARTICLE)
        self.append_record("REVIEW-OTHER","REVIEW-OTHER-v001",ObjectKind.REVIEW,
            coverage=(ReviewCoverage(task_version_id="TASK-W15-v001",
                subject_version_id="ARTICLE-OTHER-v001",
                reviewed_scope=("CLAIM-ANALYSIS",)),))
        self.controller.submit(self.submission("40",evidence=("REVIEW-OTHER-v001",)))
        with self.assertRaisesRegex(AdoptionError,"structurally cover"):
            self.controller.decide(self.request("SUBMISSION-40",
                decision="DEC-W15-M40-v001",review="REVIEW-OTHER-v001"))
        self.assertEqual(self.controller.current_state(
            "W15","M01","TASK-W15"),StepState.PENDING)

        self.append_record("REVIEW-SCOPED","REVIEW-SCOPED-v001",ObjectKind.REVIEW,
            coverage=(ReviewCoverage(task_version_id="TASK-W15-v001",
                subject_version_id="ARTICLE-1-v001",
                reviewed_scope=("DIFFERENT-SCOPE",)),))
        self.controller.submit(self.submission("41",evidence=("REVIEW-SCOPED-v001",)))
        with self.assertRaisesRegex(AdoptionError,"structurally cover"):
            self.controller.decide(self.request("SUBMISSION-41",
                decision="DEC-W15-M41-v001",review="REVIEW-SCOPED-v001"))

        self.append_record("REVIEW-MULTI","REVIEW-MULTI-v001",ObjectKind.REVIEW,
            coverage=(
                ReviewCoverage(task_version_id="TASK-W15-v001",
                    subject_version_id="ARTICLE-1-v001",
                    reviewed_scope=("CLAIM-ANALYSIS",)),
                ReviewCoverage(task_version_id="TASK-W15-v001",
                    subject_version_id="ARTICLE-OTHER-v001",
                    reviewed_scope=("OTHER-SCOPE",)),
            ))
        self.controller.submit(self.submission("42",evidence=("REVIEW-MULTI-v001",)))
        decision=self.controller.decide(self.request("SUBMISSION-42",
            decision="DEC-W15-M42-v001",review="REVIEW-MULTI-v001"))
        self.assertEqual(decision.submission.version_id,"DEC-W15-M42-v001")

    def test_parallel_tasks_keep_independent_authoritative_decision_chains(self):
        self.append_record("TASK-W15-B","TASK-W15-B-v001",ObjectKind.TASK)
        self.append_record("REVIEW-B","REVIEW-B-v001",ObjectKind.REVIEW,
            coverage=(ReviewCoverage(task_version_id="TASK-W15-B-v001",
                subject_version_id="ARTICLE-1-v001",
                reviewed_scope=("CLAIM-ANALYSIS",)),))
        self.controller.submit(self.submission("50"))
        self.controller.decide(self.request("SUBMISSION-50",decision="DEC-TASK-A-v001"))
        self.controller.submit(self.submission("51",task="TASK-W15-B-v001",
            evidence=("REVIEW-B-v001",)))
        self.controller.decide(self.request("SUBMISSION-51",decision="DEC-TASK-B-v001",
            state=StepState.RETURN,scope=(),review="REVIEW-B-v001",
            reason="Independent task returned for rework"))

        task_a=self.controller.current("W15","M01","TASK-W15")
        task_b=self.controller.current("W15","M01","TASK-W15-B")
        self.assertEqual(task_a.decision_id,"DEC-TASK-A-v001")
        self.assertEqual(task_b.decision_id,"DEC-TASK-B-v001")
        self.assertTrue(self.controller.authorizes("DEC-TASK-A-v001",("CLAIM-ANALYSIS",),AT))
        self.assertFalse(self.controller.is_current("DEC-TASK-B-v001",AT))
        self.assertNotEqual(task_a.decision_id,task_b.decision_id)

    def test_legacy_shared_slot_is_filtered_by_task_without_rewriting_history(self):
        self.append_record("TASK-W15-B","TASK-W15-B-v001",ObjectKind.TASK)
        parent=None
        for decision_id,task_version in (
                ("LEGACY-TASK-A","TASK-W15-v001"),
                ("LEGACY-TASK-B","TASK-W15-B-v001")):
            decision=AdoptionDecision(schema_version=1,decision_id=decision_id,
                submission_version_id="LEGACY-SUBMISSION-"+decision_id,
                work_id="W15",step_id="M01",spec_sha256=SPEC,
                task_version_id=task_version,subject_version_id="ARTICLE-1-v001",
                state=StepState.READY,checker_id="legacy-checker",
                checker_role=CheckerRole.L5,review_version_id="REVIEW-1-v001",
                allowed_scope=("CLAIM-ANALYSIS",),reason="Legacy shared-slot fixture",
                input_version_ids=("ARTICLE-1-v001",),
                evidence_version_ids=("REVIEW-1-v001",),dependency_decisions=(),
                decided_at=AT,expires_at=AT+timedelta(hours=1))
            self.archive.append(VersionSubmission(
                object_id="DEC-W15-M01",version_id=decision_id,
                parent_version_id=parent,kind=ObjectKind.ADOPTION_DECISION,
                title="Legacy adoption decision",spec_sha256=SPEC,created_at=AT,
                rights=self.rights,representation=Representation.FULL_BODY),
                decision.model_dump_json().encode())
            parent=decision_id
        self.assertEqual(
            self.controller.current("W15","M01","TASK-W15").decision_id,
            "LEGACY-TASK-A")
        self.assertEqual(
            self.controller.current("W15","M01","TASK-W15-B").decision_id,
            "LEGACY-TASK-B")

    def test_required_dependencies_invalidate_recursively_and_unrelated_branch_survives(self):
        self.controller.submit(self.submission("60",step="M01"))
        self.controller.decide(self.request("SUBMISSION-60",decision="DEC-W15-M01-v001"))
        dep_a=DependencyDecision(decision_id="DEC-W15-M01-v001",
            expected_subject_version_id="ARTICLE-1-v001")
        self.controller.submit(self.submission("61",step="M02",dependencies=(dep_a,)))
        self.controller.decide(self.request("SUBMISSION-61",decision="DEC-W15-M02-v001"))
        dep_b=DependencyDecision(decision_id="DEC-W15-M02-v001",
            expected_subject_version_id="ARTICLE-1-v001")
        self.controller.submit(self.submission("62",step="M03",dependencies=(dep_b,)))
        self.controller.decide(self.request("SUBMISSION-62",decision="DEC-W15-M03-v001"))
        self.controller.submit(self.submission("63",step="M04"))
        self.controller.decide(self.request("SUBMISSION-63",decision="DEC-W15-M04-v001"))
        self.assertTrue(self.controller.authorizes("DEC-W15-M03-v001",("CLAIM-ANALYSIS",),AT))

        self.controller.submit(self.submission("64",step="M01"))
        self.controller.decide(self.request("SUBMISSION-64",decision="DEC-W15-M01-v002",
            state=StepState.RETURN,scope=(),reason="Upstream evidence returned"))
        self.assertFalse(self.controller.is_current("DEC-W15-M02-v001",AT))
        self.assertFalse(self.controller.is_current("DEC-W15-M03-v001",AT))
        self.assertTrue(self.controller.authorizes("DEC-W15-M04-v001",("CLAIM-ANALYSIS",),AT))

        self.controller.submit(self.submission("65",step="M01"))
        self.controller.decide(self.request("SUBMISSION-65",decision="DEC-W15-M01-v003"))
        dep_a_new=DependencyDecision(decision_id="DEC-W15-M01-v003",
            expected_subject_version_id="ARTICLE-1-v001")
        self.controller.submit(self.submission("66",step="M02",dependencies=(dep_a_new,)))
        self.controller.decide(self.request("SUBMISSION-66",decision="DEC-W15-M02-v002"))
        dep_b_new=DependencyDecision(decision_id="DEC-W15-M02-v002",
            expected_subject_version_id="ARTICLE-1-v001")
        self.controller.submit(self.submission("67",step="M03",dependencies=(dep_b_new,)))
        self.controller.decide(self.request("SUBMISSION-67",decision="DEC-W15-M03-v002"))
        self.assertTrue(self.controller.authorizes("DEC-W15-M03-v002",("CLAIM-ANALYSIS",),AT))
        self.assertFalse(self.controller.is_current("DEC-W15-M03-v001",AT))

    def test_subject_withdrawal_blocks_adoption_until_a_new_checked_version_is_decided(self):
        subject_rights=RightsGrant(rights_id="RIGHTS-ADOPTION-SUBJECT",basis=RightsBasis.OWN_WORK,
            allowed_uses=frozenset({MaterialUse.INDEX,MaterialUse.STORE_BODY}),
            evidence="Owned synthetic withdrawal fixture",checked_by="test fixture",checked_at=AT,
            permissions=self.rights.permissions)
        self.append_record("ARTICLE-W","ARTICLE-W-v001",ObjectKind.ARTICLE,
            rights=subject_rights)
        self.append_record("REVIEW-W","REVIEW-W-v001",ObjectKind.REVIEW,
            coverage=(ReviewCoverage(task_version_id="TASK-W15-v001",
                subject_version_id="ARTICLE-W-v001",
                reviewed_scope=("CLAIM-ANALYSIS",)),))
        self.controller.submit(self.submission("70",subject="ARTICLE-W-v001",
            evidence=("REVIEW-W-v001",)))
        self.controller.decide(self.request("SUBMISSION-70",decision="DEC-W15-M70-v001",
            review="REVIEW-W-v001"))
        self.assertTrue(self.controller.is_current("DEC-W15-M70-v001",AT))
        self.archive.revoke_body_retention("RIGHTS-ADOPTION-SUBJECT",
            "Owned synthetic subject withdrawal")
        self.assertFalse(self.controller.is_current("DEC-W15-M70-v001",AT))

        replacement_rights=RightsGrant(rights_id="RIGHTS-ADOPTION-SUBJECT-REPLACEMENT",
            basis=RightsBasis.OWN_WORK,
            allowed_uses=frozenset({MaterialUse.INDEX}),
            evidence="Owned synthetic replacement locator",checked_by="test fixture",
            checked_at=AT)
        self.archive.append(VersionSubmission(
            object_id="ARTICLE-W",version_id="ARTICLE-W-v002",
            parent_version_id="ARTICLE-W-v001",kind=ObjectKind.ARTICLE,
            title="ARTICLE-W",spec_sha256=SPEC,created_at=AT,
            rights=replacement_rights,representation=Representation.POINTER_ONLY,
            source_locator="https://example.invalid/owned-replacement"),None)
        self.append_record("REVIEW-W2","REVIEW-W2-v001",ObjectKind.REVIEW,
            coverage=(ReviewCoverage(task_version_id="TASK-W15-v001",
                subject_version_id="ARTICLE-W-v002",
                reviewed_scope=("CLAIM-ANALYSIS",)),))
        self.controller.submit(self.submission("71",subject="ARTICLE-W-v002",
            evidence=("REVIEW-W2-v001",)))
        self.controller.decide(self.request("SUBMISSION-71",decision="DEC-W15-M70-v002",
            review="REVIEW-W2-v001"))
        self.assertTrue(self.controller.is_current("DEC-W15-M70-v002",AT))

    def test_task_revision_requires_a_new_decision_on_the_new_exact_version(self):
        self.controller.submit(self.submission("80"))
        self.controller.decide(self.request("SUBMISSION-80",decision="DEC-W15-M80-v001"))
        self.assertTrue(self.controller.is_current("DEC-W15-M80-v001",AT))
        self.append_record("TASK-W15","TASK-W15-v002",ObjectKind.TASK,
            parent="TASK-W15-v001")
        self.assertFalse(self.controller.is_current("DEC-W15-M80-v001",AT))
        self.append_record("REVIEW-TASK2","REVIEW-TASK2-v001",ObjectKind.REVIEW,
            coverage=(ReviewCoverage(task_version_id="TASK-W15-v002",
                subject_version_id="ARTICLE-1-v001",
                reviewed_scope=("CLAIM-ANALYSIS",)),))
        self.controller.submit(self.submission("81",task="TASK-W15-v002",
            evidence=("REVIEW-TASK2-v001",)))
        self.controller.decide(self.request("SUBMISSION-81",decision="DEC-W15-M80-v002",
            review="REVIEW-TASK2-v001"))
        self.assertTrue(self.controller.is_current("DEC-W15-M80-v002",AT))

    def test_cli_records_submission_and_decision_without_publication_authority(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);rights=base/"rights.json";submission=base/"submission.json"
            decision=base/"decision.json"
            rights.write_text(self.rights.model_dump_json())
            submission.write_text(self.submission("30").model_dump_json())
            prefix=[sys.executable,"-m","intelligence","--root",str(self.archive.root)]
            submitted=subprocess.run(prefix+["submit-step","--record",str(submission),
                "--rights",str(rights)],cwd=PROJECT,capture_output=True,text=True)
            self.assertEqual(submitted.returncode,0,submitted.stderr)
            self.assertEqual(json.loads(submitted.stdout)["adoption"],"NOT_DECIDED")
            decision.write_text(self.request("SUBMISSION-30",decision="DEC-W15-M01-v030").model_dump_json())
            decided=subprocess.run(prefix+["decide-step","--record",str(decision),
                "--rights",str(rights)],cwd=PROJECT,capture_output=True,text=True)
            self.assertEqual(decided.returncode,0,decided.stderr)
            result=json.loads(decided.stdout)
            self.assertEqual(result["state"],"READY")
            self.assertFalse(result["publication_authorized"])
            missing_task=subprocess.run(prefix+["current-decision","W15","M01"],
                cwd=PROJECT,capture_output=True,text=True)
            self.assertEqual(missing_task.returncode,2)
            current=subprocess.run(prefix+["current-decision","W15","M01","TASK-W15"],
                cwd=PROJECT,capture_output=True,text=True)
            self.assertEqual(current.returncode,0,current.stderr)
            self.assertEqual(json.loads(current.stdout)["decision"]["decision_id"],"DEC-W15-M01-v030")


if __name__=="__main__":
    unittest.main()
