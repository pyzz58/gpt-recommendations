import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import director_acting

MANIFEST = ROOT / "quality-optimization/F01_STAGE_HANDOFF_2026-10-31.json"
QO = ROOT / "quality-optimization/QUALITY_ISSUES.json"


class F01StageHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.qo = json.loads(QO.read_text(encoding="utf-8"))

    def test_manifest_matches_open_qo_status_and_next_stage(self):
        item = next(i for i in self.qo["items"] if i["id"] == "QO-F01")
        self.assertEqual(self.manifest["qo_status"], "audit_pending")
        self.assertEqual(item["status"], self.manifest["qo_status"])
        self.assertEqual(self.manifest["substages"]["F01-08"],
                         "blocked_real_media")
        self.assertEqual(self.manifest["substages"]["F01-09"],
                         "review_ready_handoff")
        self.assertEqual(self.manifest["next_stage"]["id"], "F02")
        self.assertFalse(self.manifest["real_media"]["authorized_evidence"])
        self.assertFalse(self.manifest["real_media"]["human_approval"])

    def test_real_media_evidence_absent_is_blocked(self):
        report = director_acting.inspect_media_readiness(None)
        self.assertEqual(report["status"], "blocked")
        self.assertIn("F01_REAL_MEDIA_NOT_PROVIDED",
                      {row["code"] for row in report["blockers"]})
        self.assertFalse(report["complete"])
        self.assertFalse(report["human_approval"])

    def test_completion_claim_without_evidence_is_blocked(self):
        report = director_acting.inspect_media_readiness({
            "claimed_complete": True,
        })
        codes = {row["code"] for row in report["blockers"]}
        self.assertIn("F01_MEDIA_EVIDENCE_TYPE_INVALID", codes)
        self.assertIn("F01_MEDIA_AUTHORIZATION_MISSING", codes)
        self.assertIn("F01_MEDIA_DECODE_EVIDENCE_MISSING", codes)
        self.assertEqual(report["status"], "blocked")

    def test_complete_synthetic_evidence_is_review_ready_not_approved(self):
        report = director_acting.inspect_media_readiness({
            "evidence_type": "real_authorized_media",
            "authorization_ref": "synthetic://authorization/f01",
            "decoded_frame_paths": ["synthetic://frames/0001"],
            "hand_face_mouth_review": "Synthetic review notes for the named shots.",
            "cross_shot_emotion_review": "Synthetic continuity notes across shots.",
            "independent_reviewer_ref": "synthetic://reviewer/f01",
            "rework_log": [{"shot_id": "S01", "action": "synthetic rework note"}],
        })
        self.assertEqual(report["status"], "review_ready")
        self.assertFalse(report["complete"])
        self.assertFalse(report["human_approval"])
        self.assertFalse(report["real_media_verified"])

    def test_partial_real_media_evidence_is_blocked(self):
        report = director_acting.inspect_media_readiness({
            "evidence_type": "real_authorized_media",
            "authorization_ref": "synthetic://authorization/f01",
        })
        self.assertEqual(report["status"], "blocked")
        self.assertTrue(report["blockers"])


if __name__ == "__main__":
    unittest.main()
