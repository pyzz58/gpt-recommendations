import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from cra_core.issues import Action, Issue, confirm_pd_reported, make_snapshot, previsit_selection, record_reported_correction, verify_correction
from cra_core.laboratory import LabRecord, candidate_matches, compare_fields


class IssueTests(unittest.TestCase):
    def issue(self):
        return Issue("I1", "synthetic finding", "DEMO location", "synthetic advice",
                     [{"kind": "synthetic", "anchor": "demo"}],
                     [Action("A1", "pd_reporting"), Action("A2", "edc_correction")])

    def test_user_pd_confirmation_finishes_only_reporting(self):
        issue = self.issue()
        confirm_pd_reported(issue.actions[0], "已上报", "DEMO-CRA")
        self.assertEqual(issue.actions[0].status, "completed")
        self.assertFalse(issue.complete)
        self.assertEqual(issue.actions[1].status, "open")
        self.assertEqual(issue.actions[0].completion_basis["type"], "user_confirmation")

    def test_crc_report_is_not_cra_verification(self):
        action = self.issue().actions[1]
        record_reported_correction(action, "已更正", "DEMO-CRC")
        self.assertEqual(action.status, "reported_done")
        self.assertIsNone(action.completion_basis)
        verify_correction(action, False, "DEMO form/field", "DEMO-CRA", "仍未一致")
        self.assertEqual(action.status, "needs_correction")
        self.assertEqual(len(action.history), 2)

    def test_cra_can_finish_actual_correction(self):
        action = self.issue().actions[1]
        verify_correction(action, True, "DEMO form/field", "DEMO-CRA")
        self.assertEqual(action.status, "completed")

    def test_pd_does_not_require_extra_correction_gate(self):
        with self.assertRaises(ValueError):
            verify_correction(Action("A1", "pd_reporting"), True, "DEMO", "DEMO-CRA")

    def test_letter_selection_keeps_complete_issue_list(self):
        issues = [self.issue(), replace(self.issue(), id="I2"), replace(self.issue(), id="I3")]
        selected = previsit_selection(issues, ["I1", "I3"])
        self.assertEqual(len(issues), 3)
        self.assertEqual([x["id"] for x in selected], ["I1", "I3"])
        selected[0]["finding"] = "edited draft"
        self.assertEqual(issues[0].finding, "synthetic finding")

    def test_snapshot_is_not_rewritten_by_new_status(self):
        issue = self.issue()
        snapshot = make_snapshot([issue], {"reviewed": ["DEMO field"]})
        confirm_pd_reported(issue.actions[0], "已上报", "DEMO-CRA")
        payload = json.loads(snapshot.content_json)
        self.assertEqual(payload["issues"][0]["actions"][0]["status"], "open")
        self.assertEqual(issue.actions[0].status, "completed")


class LaboratoryTests(unittest.TestCase):
    def record(self):
        return LabRecord(site="DEMO", subject="SUBJ", visit="V1", analyte="TEST",
                         specimen="SAMPLE", collected_at="2026-01-01",
                         repeat_instance="initial", value="12.0", unit="U", report_revision="1")

    def test_equal_values_have_only_limited_scope(self):
        result = compare_fields(self.record(), replace(self.record(), value="12"))
        self.assertEqual(result["status"], "field_agreement")
        self.assertIn("medical_assessment", result["unverified_dimensions"])

    def test_initial_and_repeat_are_not_comparable(self):
        result = compare_fields(self.record(), replace(self.record(), repeat_instance="repeat"))
        self.assertEqual(result["status"], "not_comparable")

    def test_unknown_conversion_requires_review(self):
        self.assertEqual(compare_fields(self.record(), replace(self.record(), unit="OTHER"))["status"], "unit_review")

    def test_skipped_source_stays_unverified(self):
        self.assertEqual(compare_fields(replace(self.record(), source_state="user_skipped"), self.record())["status"], "unverified")

    def test_missing_export_row_is_not_declared_omission(self):
        self.assertEqual(compare_fields(self.record(), None)["status"], "not_seen_in_export")

    def test_duplicate_candidates_are_ambiguous(self):
        self.assertEqual(candidate_matches(self.record(), [self.record(), self.record()])["status"], "ambiguous")

    def test_report_revision_and_bound_values_are_not_guessed(self):
        self.assertEqual(compare_fields(self.record(), replace(self.record(), report_revision="2"))["status"], "not_comparable")
        self.assertEqual(compare_fields(replace(self.record(), value="<12"), self.record())["status"], "not_comparable")

    def test_unknown_revision_needs_explicit_instance_confirmation(self):
        self.assertEqual(compare_fields(replace(self.record(), report_revision=None), self.record())["status"], "identity_review")


if __name__ == "__main__":
    unittest.main()
