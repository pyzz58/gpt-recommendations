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
import director_sound

FIXTURE = ROOT / "examples/sound-f03/public_dialogue_sound.json"


class DirectorSoundContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def inspect(self, payload=None):
        base = deepcopy(self.data["base"])
        return base, director_sound.inspect_delivery(
            base, payload or deepcopy(self.data["sound"]))

    def test_public_two_shot_sound_passes(self):
        _, report = self.inspect()
        self.assertEqual(report["blockers"], [])

    def test_missing_mix_blocks(self):
        payload = deepcopy(self.data["sound"])
        payload["shots"]["S01"]["sound"].pop("mix")
        _, report = self.inspect(payload)
        self.assertIn("SOUND_MIX_MISSING",
                      {row["code"] for row in report["blockers"]})

    def test_cleared_music_without_license_reference_blocks(self):
        payload = deepcopy(self.data["sound"])
        music = payload["shots"]["S01"]["sound"]["music_plan"]
        music["rights_status"] = "cleared"
        music["license_ref"] = ""
        _, report = self.inspect(payload)
        self.assertIn("SOUND_MUSIC_LICENSE_EVIDENCE_MISSING",
                      {row["code"] for row in report["blockers"]})

    def test_onscreen_lip_sync_and_offscreen_policy_are_enforced(self):
        payload = deepcopy(self.data["sound"])
        payload["shots"]["S01"]["speech"]["dialogue"][0]["lip_sync"] = "none"
        _, report = self.inspect(payload)
        self.assertIn("SOUND_DIALOGUE_LIPSYNC_REQUIRED",
                      {row["code"] for row in report["blockers"]})
        payload = deepcopy(self.data["sound"])
        payload["shots"]["S02"]["speech"]["dialogue"][0]["lip_sync"] = "required"
        _, report = self.inspect(payload)
        self.assertIn("SOUND_OFFSCREEN_LIPSYNC_FORBIDDEN",
                      {row["code"] for row in report["blockers"]})

    def test_subtitle_must_match_spoken_text(self):
        payload = deepcopy(self.data["sound"])
        payload["shots"]["S01"]["speech"]["subtitle_cues"][1]["text"] = "Different line."
        _, report = self.inspect(payload)
        self.assertIn("SOUND_SUBTITLE_CUE_INVALID",
                      {row["code"] for row in report["blockers"]})

    def test_generic_music_language_is_review(self):
        payload = deepcopy(self.data["sound"])
        payload["shots"]["S01"]["sound"]["music_plan"]["purpose"] = "电影感氛围"
        _, report = self.inspect(payload)
        self.assertEqual(report["blockers"], [])
        self.assertIn("SOUND_MUSIC_GENERIC_LANGUAGE",
                      {row["code"] for row in report["reviews"]})

    def test_missing_sound_bridge_blocks(self):
        payload = deepcopy(self.data["sound"])
        payload["shots"]["S01"]["sound"].pop("sound_bridge")
        _, report = self.inspect(payload)
        self.assertIn("SOUND_BRIDGE_MISSING",
                      {row["code"] for row in report["blockers"]})

    def test_schema_requires_sound_contract_fields(self):
        base = deepcopy(self.data["base"])
        state = agent_team.start(base, source_text="Public F03 sound scene")
        schema = roles.execution_output_schema(base, state, "sound")
        shot = schema["properties"]["shots"]["properties"]["S01"]
        self.assertIn("mix", shot["properties"]["sound"]["required"])
        self.assertIn("music_plan", shot["properties"]["sound"]["required"])
        self.assertIn("sound_bridge", shot["properties"]["sound"]["required"])
        self.assertIn("lip_sync", shot["properties"]["speech"]["properties"][
            "dialogue"]["items"]["required"])

    def test_strict_sound_validation_is_wired(self):
        base = deepcopy(self.data["base"])
        state = agent_team.start(base, source_text="Public F03 sound scene")
        payload = deepcopy(self.data["sound"])
        with patch.object(roles.executor, "_check"), \
             patch.object(roles.team, "ready", return_value=["sound"]), \
             patch.object(roles, "parse_strict_json", return_value=payload), \
             patch.object(roles.sound_contract, "inspect_delivery",
                          return_value={"blockers": [{"code": "TEST"}]}):
            with self.assertRaisesRegex(ValueError, "CREW_SOUND_CONTRACT_BLOCKED"):
                roles.validate_role_output(
                    base, state, "sound", "{}",
                    source_text="Public F03 sound scene")

    def test_legacy_mode_is_not_forced(self):
        base = deepcopy(self.data["base"])
        base.pop("sound_contract_mode")
        report = director_sound.inspect_delivery(
            base, deepcopy(self.data["sound"]))
        self.assertTrue(report.get("not_required"))


if __name__ == "__main__":
    unittest.main()
