"""Reference provider-input preview: privacy, fail-closed and no model calls."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import director_v2 as v2
import reference_assets as assets
import reference_input_preview as preview


class ReferenceInputPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = v2.read_json(ROOT / "examples/quit-smoking/plan.json")
        cls.direction = v2.read_json(ROOT / "examples/quit-smoking/direction_v02.json")

    def fixtures(self):
        return (copy.deepcopy(self.base), copy.deepcopy(self.direction),
                assets.scaffold(self.base, self.direction))

    def test_missing_refs_stay_missing_and_no_api_claims(self):
        base, direction, catalog = self.fixtures()
        packet = preview.make_packet(base, direction, catalog)
        self.assertGreater(packet["reference_preflight"]["missing"], 0)
        self.assertFalse(packet["runtime_execution_allowed"])
        self.assertFalse(packet["actual_provider_request"])
        self.assertFalse(packet["images_uploaded"])
        self.assertFalse(packet["user_payment_authorized"])
        self.assertFalse(packet["reference_preflight"]["files_verified"])
        self.assertFalse(packet["reference_preflight"]["identity_consistency_verified"])

    def test_no_private_path_source_or_rights_evidence_is_exposed(self):
        base, direction, catalog = self.fixtures()
        ref = catalog["assets"]["CHAR01"]["views"]["three_quarter"]
        ref["path"] = "super-secret-photo.png"
        ref["source"] = "private-home-folder"
        ref["rights_evidence"] = "personal-contract"
        packet = preview.make_packet(base, direction, catalog)
        encoded = json.dumps(packet, ensure_ascii=False)
        for value in ("super-secret-photo.png", "private-home-folder", "personal-contract"):
            self.assertNotIn(value, encoded)

    def test_model_input_packet_uses_stable_ids_and_required_views(self):
        base, direction, catalog = self.fixtures()
        packet = preview.make_packet(base, direction, catalog)
        expected = [s["id"] for s in base["shots"]]
        self.assertEqual([s["shot_id"] for s in packet["jobs"]], expected)
        first = packet["jobs"][0]
        self.assertIn(("CHAR01", "three_quarter"),
            [(r["asset_id"], r["view"]) for r in first["reference_requirements"]])
        self.assertIn(("LOC01", "establishing"),
            [(r["asset_id"], r["view"]) for r in first["reference_requirements"]])
        self.assertTrue(all(not r["reference_uploaded_to_provider"]
                            for job in packet["jobs"] for r in job["reference_requirements"]))

    def test_offscreen_characters_not_injected(self):
        base, direction, catalog = self.fixtures()
        packet = preview.make_packet(base, direction, catalog)
        second = next(j for j in packet["jobs"] if j["shot_id"] == "S02")
        self.assertNotIn("CHAR01", [r["asset_id"] for r in second["reference_requirements"]])

    def test_new_model_routing_respected(self):
        base, direction, _ = self.fixtures()
        direction["shots"][0]["generation"]["route"] = "edit_composite"
        catalog = assets.scaffold(base, direction)
        packet = preview.make_packet(base, direction, catalog)
        self.assertEqual(packet["jobs"][0]["execution_route"], "edit_composite")
        self.assertEqual(packet["jobs"][0]["reference_requirements"], [])

    def test_unknown_asset_id_fails_without_silent_fix(self):
        base, direction, catalog = self.fixtures()
        catalog["shot_requirements"]["S01"].append(
            {"asset_id": "UNKNOWN_FACE", "view": "front", "role": "identity"})
        with self.assertRaises(ValueError):
            preview.make_packet(base, direction, catalog)

    def test_cannot_bypass_privacy_with_forged_catalog_policy(self):
        base, direction, catalog = self.fixtures()
        catalog["policy"]["private_media_in_public_repo"] = True
        with self.assertRaises(ValueError):
            preview.make_packet(base, direction, catalog)

    def test_read_only_input_objects(self):
        base, direction, catalog = self.fixtures()
        before = json.dumps([base, direction, catalog], sort_keys=True)
        preview.make_packet(base, direction, catalog)
        self.assertEqual(before, json.dumps([base, direction, catalog], sort_keys=True))

    def test_cli_never_overwrites_previous_output(self):
        base, direction, catalog = self.fixtures()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name, value in (("plan.json", base), ("direction.json", direction), ("catalog.json", catalog)):
                (root / name).write_text(json.dumps(value), encoding="utf-8")
            command = [sys.executable, str(ROOT/"reference_input_preview.py"),
                       "--base", str(root/"plan.json"),
                       "--direction", str(root/"direction.json"),
                       "--catalog", str(root/"catalog.json"),
                       "--out", str(root/"result.json")]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            original = (root/"result.json").read_bytes()
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(original, (root/"result.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
