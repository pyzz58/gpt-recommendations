import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "quality-optimization/F02_STAGE_HANDOFF_2026-10-31.json"
QO = ROOT / "quality-optimization/QUALITY_ISSUES.json"


class F02StageHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.qo = json.loads(QO.read_text(encoding="utf-8"))

    def test_manifest_matches_open_qo_status_and_f03_next_stage(self):
        item = next(i for i in self.qo["items"] if i["id"] == "QO-F02")
        self.assertEqual(self.manifest["qo_status"], "audit_pending")
        self.assertEqual(item["status"], self.manifest["qo_status"])
        self.assertEqual(self.manifest["next_stage"]["id"], "F03")
        self.assertEqual(self.manifest["substages"]["F02-02"],
                         "independent_dop_review_blocked")
        self.assertEqual(self.manifest["substages"]["F02-03"],
                         "real_media_optics_blocked")

    def test_real_media_and_independent_review_are_not_claimed(self):
        real = self.manifest["real_media"]
        self.assertEqual(real["status"], "blocked")
        for key in ("real_camera_or_lighting_evidence", "decoded_optical_media",
                    "independent_dop_review", "human_approval"):
            self.assertFalse(real[key])
        self.assertIn("independent DOP, gaffer or production-design review",
                      self.manifest["not_verified"])


if __name__ == "__main__":
    unittest.main()
