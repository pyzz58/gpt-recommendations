"""Owned tests for durable weekly-run checkpoints and resume planning."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from intelligence.archive import Archive, Conflict
from intelligence.contracts import (
    MaterialUse, ObjectKind, PermissionState, Representation, RightsBasis,
    RightsGrant, Scope, ScopeMode, UsePermission, ValidityMode,
    VersionSubmission,
)
from intelligence.weekly import (
    WeeklyCheckpointDisposition, WeeklyCheckpointRequest, WeeklyRunController,
    WeeklyRunError, WeeklyRunRequest, WeeklyRunState, WeeklyStage,
)


AT = datetime(2026, 11, 8, tzinfo=timezone.utc)


class WeeklyRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Archive(Path(self.temp.name) / "archive")
        self.addCleanup(self.archive.close)
        any_scope = Scope(mode=ScopeMode.ANY)
        self.rights = RightsGrant(
            rights_id="RIGHTS-WEEKLY-TEST", basis=RightsBasis.OWN_WORK,
            allowed_uses=frozenset({
                MaterialUse.INDEX, MaterialUse.STORE_BODY}),
            evidence="Owned weekly test journal",
            checked_by="test", checked_at=AT,
            permissions=(UsePermission(
                use=MaterialUse.STORE_BODY,
                state=PermissionState.ALLOWED,
                validity=ValidityMode.OPEN_ENDED,
                territories=any_scope, providers=any_scope,
                content_scope=any_scope),))
        self.task = self.archive.append(VersionSubmission(
            schema_version=2, object_id="TASK-WEEKLY", version_id="TASK-WEEKLY-v001",
            kind=ObjectKind.TASK, title="Weekly test task", spec_sha256="a" * 64,
            created_at=AT, rights=self.rights,
            representation=Representation.FULL_BODY), b"weekly task")
        self.artifact = self.archive.append(VersionSubmission(
            schema_version=2, object_id="ART-WEEKLY", version_id="ART-WEEKLY-v001",
            kind=ObjectKind.DOCUMENT, title="Weekly artifact", spec_sha256="a" * 64,
            created_at=AT + timedelta(seconds=1), rights=self.rights,
            representation=Representation.FULL_BODY), b"artifact")
        self.controller = WeeklyRunController(self.archive, self.rights)

    def request(self, **updates):
        values = dict(
            weekly_run_id="WEEKLY-2026-W46", issue_id="SI-2026-W46",
            source_week_start=AT - timedelta(days=7),
            source_week_end=AT, knowledge_cutoff=AT,
            source_timezone="Pacific/Auckland",
            task_version_id=self.task.submission.version_id,
            spec_sha256="a" * 64, purpose="Owned weekly checkpoint test",
            planned_stages=(WeeklyStage.SOURCE, WeeklyStage.PREPARE,
                            WeeklyStage.DRAFT),
            created_at=AT + timedelta(seconds=2))
        values.update(updates)
        return WeeklyRunRequest(**values)

    def checkpoint(self, expected, stage, disposition, **updates):
        values = dict(
            weekly_run_id="WEEKLY-2026-W46",
            expected_manifest_version_id=expected,
            stage=stage, disposition=disposition,
            artifact_version_ids=(self.artifact.submission.version_id,),
            external_operation_ids=(), note="Owned checkpoint",
            next_action=None, created_at=AT + timedelta(seconds=3))
        values.update(updates)
        return WeeklyCheckpointRequest(**values)

    def test_claim_is_idempotent_and_cannot_change_identity(self):
        first, record = self.controller.claim(self.request())
        second, same = self.controller.claim(self.request())
        self.assertEqual(first.submission.version_id, second.submission.version_id)
        self.assertEqual(record, same)
        with self.assertRaisesRegex(WeeklyRunError, "different inputs"):
            self.controller.claim(self.request(issue_id="OTHER"))

    def test_checkpoints_are_ordered_and_resume_from_last_artifact(self):
        stored, _ = self.controller.claim(self.request())
        checkpoint = self.checkpoint(
            stored.submission.version_id, WeeklyStage.SOURCE,
            WeeklyCheckpointDisposition.SUCCEEDED)
        stored, record = self.controller.checkpoint(checkpoint)
        repeated, same = self.controller.checkpoint(checkpoint)
        self.assertEqual(repeated.submission.version_id, stored.submission.version_id)
        self.assertEqual(same, record)
        self.assertEqual(record.next_stage, WeeklyStage.PREPARE)
        plan = self.controller.resume_plan("WEEKLY-2026-W46")
        self.assertEqual(plan["state"], "RUNNING")
        self.assertEqual(plan["next_stage"], "PREPARE")
        self.assertEqual(
            plan["checkpoints"][0]["artifact_version_ids"],
            (self.artifact.submission.version_id,))
        with self.assertRaisesRegex(WeeklyRunError, "Expected next weekly stage"):
            self.controller.checkpoint(self.checkpoint(
                stored.submission.version_id, WeeklyStage.DRAFT,
                WeeklyCheckpointDisposition.SUCCEEDED))

    def test_blocked_unknown_and_failed_keep_the_same_resume_stage(self):
        stored, _ = self.controller.claim(self.request())
        for disposition in (
                WeeklyCheckpointDisposition.BLOCKED,
                WeeklyCheckpointDisposition.UNKNOWN,
                WeeklyCheckpointDisposition.FAILED):
            stored, record = self.controller.checkpoint(self.checkpoint(
                stored.submission.version_id, WeeklyStage.SOURCE,
                disposition, next_action="Reconcile the provider result",
                created_at=stored.submission.created_at + timedelta(seconds=1)))
            self.assertEqual(record.state, WeeklyRunState.BLOCKED)
            self.assertEqual(record.next_stage, WeeklyStage.SOURCE)
        stored, record = self.controller.checkpoint(self.checkpoint(
            stored.submission.version_id, WeeklyStage.SOURCE,
            WeeklyCheckpointDisposition.SUCCEEDED,
            created_at=stored.submission.created_at + timedelta(seconds=1)))
        self.assertEqual(record.state, WeeklyRunState.RUNNING)
        self.assertEqual(record.next_stage, WeeklyStage.PREPARE)

    def test_success_requires_an_existing_artifact_and_skip_needs_no_artifact(self):
        stored, _ = self.controller.claim(self.request())
        with self.assertRaisesRegex(ValueError, "needs exact artifacts"):
            WeeklyCheckpointRequest(
                weekly_run_id="WEEKLY-2026-W46",
                expected_manifest_version_id=stored.submission.version_id,
                stage=WeeklyStage.SOURCE,
                disposition=WeeklyCheckpointDisposition.SUCCEEDED,
                artifact_version_ids=(), note="Missing artifact",
                created_at=AT + timedelta(seconds=3))
        stored, record = self.controller.checkpoint(WeeklyCheckpointRequest(
            weekly_run_id="WEEKLY-2026-W46",
            expected_manifest_version_id=stored.submission.version_id,
            stage=WeeklyStage.SOURCE,
            disposition=WeeklyCheckpointDisposition.SKIPPED,
            artifact_version_ids=(), note="No source stage in this fixture",
            created_at=AT + timedelta(seconds=3)))
        self.assertEqual(record.next_stage, WeeklyStage.PREPARE)

    def test_completes_in_plan_order_and_stale_checkpoint_conflicts(self):
        stored, _ = self.controller.claim(self.request())
        for stage in (WeeklyStage.SOURCE, WeeklyStage.PREPARE):
            old = stored
            stored, record = self.controller.checkpoint(self.checkpoint(
                stored.submission.version_id, stage,
                WeeklyCheckpointDisposition.SUCCEEDED,
                created_at=stored.submission.created_at + timedelta(seconds=1)))
        with self.assertRaises(Conflict):
            self.controller.checkpoint(self.checkpoint(
                old.submission.version_id, WeeklyStage.PREPARE,
                WeeklyCheckpointDisposition.SUCCEEDED,
                created_at=stored.submission.created_at + timedelta(seconds=1)))
        stored, record = self.controller.checkpoint(self.checkpoint(
            stored.submission.version_id, WeeklyStage.DRAFT,
            WeeklyCheckpointDisposition.SUCCEEDED,
            created_at=stored.submission.created_at + timedelta(seconds=1)))
        self.assertEqual(record.state, WeeklyRunState.COMPLETE)
        self.assertIsNone(record.next_stage)


if __name__ == "__main__":
    unittest.main()
