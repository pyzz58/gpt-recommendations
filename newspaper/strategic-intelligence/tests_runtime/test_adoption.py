"""W15 adoption boundary tests using explicitly synthetic internal records."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from pydantic import ValidationError

from intelligence.adoption import (AdoptionController, AdoptionError, CheckerRole,
                                   DecisionRequest, DependencyDecision, StepState,
                                   StepSubmission)
from intelligence.archive import Archive
from intelligence.contracts import (MaterialUse, ObjectKind, Representation, RightsBasis,
                                    RightsGrant, VersionSubmission)

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
            evidence="Owned synthetic journal fixture",checked_by="test fixture",checked_at=AT)
        self.controller=AdoptionController(self.archive,self.rights)
        self.append_record("TASK-W15","TASK-W15-v001",ObjectKind.TASK)
        self.append_record("ARTICLE-1","ARTICLE-1-v001",ObjectKind.ARTICLE)
        self.append_record("REVIEW-1","REVIEW-1-v001",ObjectKind.REVIEW)

    def append_record(self, object_id, version_id, kind):
        return self.archive.append(VersionSubmission(
            object_id=object_id,version_id=version_id,kind=kind,title=object_id,
            spec_sha256=SPEC,created_at=AT,rights=self.rights,
            representation=Representation.FULL_BODY),BODY)

    def submission(self, suffix="1", *, evidence=("REVIEW-1-v001",),
                   dependencies=(), task="TASK-W15-v001", subject="ARTICLE-1-v001",
                   proposed=StepState.READY, created_at=AT):
        return StepSubmission(submission_id=f"SUBMISSION-{suffix}",work_id="W15",step_id="M01",
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
        self.assertEqual(self.controller.current_state("W15","M01"),StepState.PENDING)
        stored=self.controller.submit(self.submission())
        self.assertEqual(stored.submission.kind,ObjectKind.STEP_SUBMISSION)
        self.assertIsNone(self.controller.current("W15","M01"))
        decision=self.controller.decide(self.request("SUBMISSION-1"))
        self.assertEqual(decision.submission.kind,ObjectKind.ADOPTION_DECISION)
        current=self.controller.current("W15","M01")
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
        decision=self.controller.current("W15","M01")
        self.assertEqual(decision.state,StepState.NOT_APPLICABLE)
        self.assertFalse(self.controller.is_current(decision.decision_id))
        dependent=self.submission("21",dependencies=(DependencyDecision(
            decision_id="DEC-W15-M20-v001",expected_subject_version_id="ARTICLE-1-v001"),),
            created_at=AT+timedelta(minutes=2))
        self.assertEqual(self.controller.submit(dependent).submission.version_id,"SUBMISSION-21")

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
            current=subprocess.run(prefix+["current-decision","W15","M01"],
                cwd=PROJECT,capture_output=True,text=True)
            self.assertEqual(current.returncode,0,current.stderr)
            self.assertEqual(json.loads(current.stdout)["decision"]["decision_id"],"DEC-W15-M01-v030")


if __name__=="__main__":
    unittest.main()
