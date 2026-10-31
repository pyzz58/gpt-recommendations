from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import agent_role_contracts as roles
import agent_team
import director_acting

FIXTURE = ROOT / "examples/acting-f01/public_letter_strict_contract.json"


class DirectorActingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def bound_state_and_bible(self):
        base = deepcopy(self.data["base"])
        state = agent_team.start(base, source_text=self.data["source_text"])
        bible = deepcopy(
            self.data["director_lock"]["global_direction"]["performance_bible"])
        bible["source_digest"] = state["source_digest"]
        state["tasks"]["director_lock"]["deliverable"] = {
            "global_direction": {"performance_bible": bible},
        }
        return base, state, bible

    def inspect(self, base=None, state=None, acting=None):
        base = base or deepcopy(self.data["base"])
        state = state or agent_team.start(base, source_text=self.data["source_text"])
        bible = deepcopy(
            self.data["director_lock"]["global_direction"]["performance_bible"])
        bible["source_digest"] = state["source_digest"]
        state["tasks"]["director_lock"]["deliverable"] = {
            "global_direction": {"performance_bible": bible},
        }
        acting = acting or deepcopy(self.data["acting"])
        return base, state, bible, director_acting.inspect_delivery(base, state, acting)

    def test_positive_strict_contract_passes(self):
        base, state, bible = self.bound_state_and_bible()
        bible_report = director_acting.inspect_bible(
            base, state, {"performance_bible": bible})
        self.assertEqual(bible_report["blockers"], [])
        delivery = director_acting.inspect_delivery(
            base, state, deepcopy(self.data["acting"]))
        self.assertEqual(delivery["blockers"], [])

    def test_missing_character_contracts_blocks(self):
        base, state, _ = self.bound_state_and_bible()
        acting = deepcopy(self.data["acting"])
        acting["shots"]["S01"]["performance"].pop("character_contracts")
        report = director_acting.inspect_delivery(base, state, acting)
        self.assertIn("ACTING_CHARACTER_CONTRACTS_MISSING",
                      {row["code"] for row in report["blockers"]})

    def test_stale_bible_blocks(self):
        base, state, bible = self.bound_state_and_bible()
        bible["source_digest"] = "f" * 64
        report = director_acting.inspect_bible(
            base, state, {"performance_bible": bible})
        self.assertIn("ACTING_BIBLE_SOURCE_STALE",
                      {row["code"] for row in report["blockers"]})

    def test_overlapping_hand_prop_blocks(self):
        base, state, _ = self.bound_state_and_bible()
        acting = deepcopy(self.data["acting"])
        acting["shots"]["S01"]["staging"]["hand_prop"].append({
            "actor_id": "CH_DAUGHTER",
            "hand": "right",
            "prop_id": "PROP_LETTER",
            "from_s": 4.5,
            "to_s": 5.5,
            "action": "hold the letter with the same right hand",
            "visible_result": "letter remains below the table edge",
        })
        report = director_acting.inspect_delivery(base, state, acting)
        self.assertIn("ACTING_HAND_OVERLAP",
                      {row["code"] for row in report["blockers"]})

    def test_generic_language_is_review_not_automatic_block(self):
        base, state, _ = self.bound_state_and_bible()
        acting = deepcopy(self.data["acting"])
        acting["shots"]["S01"]["performance"]["character_contracts"][
            "CH_DAUGHTER"]["tactic"] = "自然地表演"
        report = director_acting.inspect_delivery(base, state, acting)
        self.assertEqual(report["blockers"], [])
        self.assertIn("ACTING_GENERIC_LANGUAGE",
                      {row["code"] for row in report["reviews"]})

    def test_zero_actor_shot_needs_reason_and_passes(self):
        base, state, _ = self.bound_state_and_bible()
        base["shots"][0]["character_ids"] = []
        acting = deepcopy(self.data["acting"])
        performance = acting["shots"]["S01"]["performance"]
        performance["character_contracts"] = {}
        performance["no_performer_reason"] = "Pure tabletop insert; no performer enters this diagram shot."
        report = director_acting.inspect_delivery(base, state, acting)
        self.assertEqual(report["blockers"], [])

    def test_schema_requires_strict_fields(self):
        base, state, _ = self.bound_state_and_bible()
        lock_schema = roles.execution_output_schema(base, state, "director_lock")
        self.assertIn(
            "performance_bible",
            lock_schema["properties"]["global_direction"]["required"])
        acting_schema = roles.execution_output_schema(base, state, "acting")
        shot_schema = acting_schema["properties"]["shots"]["properties"]["S01"]
        self.assertIn(
            "character_contracts",
            shot_schema["properties"]["performance"]["required"])

    def test_legacy_mode_is_not_forced(self):
        base = deepcopy(self.data["base"])
        base.pop("acting_contract_mode")
        state = agent_team.start(base, source_text=self.data["source_text"])
        report = director_acting.inspect_delivery(
            base, state, deepcopy(self.data["acting"]))
        self.assertTrue(report.get("not_required"))


if __name__ == "__main__":
    unittest.main()
