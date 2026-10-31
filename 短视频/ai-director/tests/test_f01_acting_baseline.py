import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import agent_role_contracts as roles

FIXTURE = ROOT / "examples/acting-f01/public_letter_subtext_failure.json"


class F01ActingBaselineTests(unittest.TestCase):
    """F01-00 characterization baseline, not an acting-quality validator.

    When F01-02/F01-03 adds the causal performance contract, the third test
    below must be replaced with positive/negative tests for that contract.
    """

    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.acting = cls.fixture["acting_deliverable"]

    def test_public_fixture_is_synthetic_and_contains_no_private_paths(self):
        self.assertIs(self.fixture["fictional"], True)
        self.assertIs(self.fixture["public_synthetic"], True)
        raw = FIXTURE.read_text(encoding="utf-8")
        for forbidden in ("/Users/", "sk-", "private_", "jobs/"):
            self.assertNotIn(forbidden, raw)

    def test_fixture_satisfies_only_current_structural_acting_minimum(self):
        required = roles.REQUIRED_OBJECT_FIELDS["acting"]
        for section, fields in required.items():
            for field in fields:
                value = self.acting[section][field]
                self.assertIsInstance(value, str)
                self.assertTrue(value.strip(), f"{section}.{field} must be nonempty")
        self.assertGreaterEqual(len(self.acting["beats"]), 1)
        self.assertTrue(all(beat["visible_change"].strip()
                            for beat in self.acting["beats"]))
        self.assertEqual(abs(self.acting["beats"][-1]["to_s"] - 6), 0)

    def test_current_schema_lacks_professional_causal_fields(self):
        # This is the documented F01 gap, not a quality pass.
        performance_fields = set(roles.REQUIRED_OBJECT_FIELDS["acting"]["performance"])
        for field in ("objective", "obstacle", "tactic", "subtext",
                      "reaction", "relationship"):
            self.assertNotIn(field, performance_fields)
        gap = self.fixture["professional_gap"]["missing"]
        for phrase in ("objective", "obstacle", "tactic", "subtext",
                       "reaction", "hand", "prop"):
            self.assertTrue(any(phrase in item.lower() for item in gap),
                            f"fixture must document missing {phrase}")


if __name__ == "__main__":
    unittest.main()
