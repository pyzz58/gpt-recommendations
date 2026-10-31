from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import agent_role_contracts as roles
import agent_team
import director_photography

FIXTURE = ROOT / "examples/photography-f02/public_dialogue_scene.json"


class DirectorPhotographyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def inspect(self, payload=None):
        base = deepcopy(self.data["base"])
        state = agent_team.start(base, source_text="Public F02 dialogue scene")
        return base, state, director_photography.inspect_delivery(
            base, payload or deepcopy(self.data["camera_art"]))

    def test_public_dialogue_scene_passes(self):
        _, _, report = self.inspect()
        self.assertEqual(report["blockers"], [])

    def test_axis_break_blocks_without_reason_and_reviews_with_reason(self):
        payload = deepcopy(self.data["camera_art"])
        payload["shots"]["S02"]["camera"]["camera_side"] = "right"
        _, _, report = self.inspect(payload)
        self.assertIn("PHOTOGRAPHY_AXIS_JUMP",
                      {row["code"] for row in report["blockers"]})
        payload["shots"]["S02"]["camera"]["axis_break_reason"] = (
            "Intentional reverse angle to show B taking control; the cut is motivated by B's reach.")
        _, _, report = self.inspect(payload)
        self.assertNotIn("PHOTOGRAPHY_AXIS_JUMP",
                         {row["code"] for row in report["blockers"]})
        self.assertIn("PHOTOGRAPHY_AXIS_BREAK_REVIEW",
                      {row["code"] for row in report["reviews"]})

    def test_light_direction_jump_requires_motivated_change(self):
        payload = deepcopy(self.data["camera_art"])
        second = payload["shots"]["S02"]["art"]
        second["key_light_direction"] = "From screen-right toward screen-left"
        second["lighting_change_reason"] = "unchanged"
        _, _, report = self.inspect(payload)
        self.assertIn("PHOTOGRAPHY_LIGHT_SOURCE_JUMP",
                      {row["code"] for row in report["blockers"]})
        second["lighting_change_reason"] = (
            "B switches on a practical desk lamp from screen-right, motivating the new direction.")
        _, _, report = self.inspect(payload)
        self.assertNotIn("PHOTOGRAPHY_LIGHT_SOURCE_JUMP",
                         {row["code"] for row in report["blockers"]})
        self.assertIn("PHOTOGRAPHY_LIGHT_CHANGE_REVIEW",
                      {row["code"] for row in report["reviews"]})

    def test_scene_geometry_drift_blocks(self):
        payload = deepcopy(self.data["camera_art"])
        payload["shots"]["S02"]["art"]["scene_geometry"]["anchor_positions"]["CH_A"] = (
            "screen-right chair")
        _, _, report = self.inspect(payload)
        self.assertIn("PHOTOGRAPHY_GEOMETRY_DRIFT",
                      {row["code"] for row in report["blockers"]})

    def test_missing_focal_length_blocks(self):
        payload = deepcopy(self.data["camera_art"])
        payload["shots"]["S01"]["camera"].pop("focal_length_mm")
        _, _, report = self.inspect(payload)
        self.assertIn("PHOTOGRAPHY_FOCAL_LENGTH_INVALID",
                      {row["code"] for row in report["blockers"]})

    def test_generic_photography_language_is_review(self):
        payload = deepcopy(self.data["camera_art"])
        payload["shots"]["S01"]["camera"]["lens_feel"] = "电影感很强的高级质感"
        _, _, report = self.inspect(payload)
        self.assertEqual(report["blockers"], [])
        self.assertIn("PHOTOGRAPHY_GENERIC_LANGUAGE",
                      {row["code"] for row in report["reviews"]})

    def test_schema_requires_photography_fields(self):
        base = deepcopy(self.data["base"])
        state = agent_team.start(base, source_text="Public F02 dialogue scene")
        schema = roles.execution_output_schema(base, state, "camera_art")
        shot = schema["properties"]["shots"]["properties"]["S01"]
        self.assertIn("focal_length_mm", shot["properties"]["camera"]["required"])
        self.assertIn("scene_geometry", shot["properties"]["art"]["required"])

    def test_strict_photography_validation_is_wired(self):
        base = deepcopy(self.data["base"])
        state = agent_team.start(base, source_text="Public F02 dialogue scene")
        payload = deepcopy(self.data["camera_art"])
        with patch.object(roles.executor, "_check"), \
             patch.object(roles.team, "ready", return_value=["camera_art"]), \
             patch.object(roles, "parse_strict_json", return_value=payload), \
             patch.object(roles.photography_contract, "inspect_delivery",
                          return_value={"blockers": [{"code": "TEST"}]}):
            with self.assertRaisesRegex(ValueError, "CREW_PHOTOGRAPHY_CONTRACT_BLOCKED"):
                roles.validate_role_output(
                    base, state, "camera_art", "{}",
                    source_text="Public F02 dialogue scene")

    def test_legacy_mode_is_not_forced(self):
        base = deepcopy(self.data["base"])
        base.pop("photography_contract_mode")
        report = director_photography.inspect_delivery(
            base, deepcopy(self.data["camera_art"]))
        self.assertTrue(report.get("not_required"))


if __name__ == "__main__":
    unittest.main()
