"""Audit findings must never silently upgrade guesses to 'fixed'."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import audit_registry as audit


class AuditRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry=json.loads(audit.DEFAULT.read_text("utf-8"))

    def test_actual_master_register_has_all_important_categories(self):
        r=audit.validate_registry(self.registry)
        self.assertGreaterEqual(r["findings_total"],17)
        self.assertIn("AUD-002",r["open_p0"])
        self.assertEqual(r["real_model_calls_from_audit"],0)
        self.assertFalse(r["automated_artistic_quality_proven"])
        self.assertFalse(r["real_media_feasibility_proven"])

    def test_duplicate_issue_identifiers_are_rejected(self):
        data=deepcopy(self.registry)
        data["findings"][1]["id"]=data["findings"][0]["id"]
        with self.assertRaisesRegex(audit.AuditRegistryError,"DUPLICATE"):
            audit.validate_registry(data)

    def test_false_fix_without_regression_or_commit_is_rejected(self):
        for key in ("test_evidence","fix_commit"):
            data=deepcopy(self.registry)
            data["findings"][0][key]=""
            with self.subTest(key=key):
                with self.assertRaisesRegex(audit.AuditRegistryError,
                                            "FALSE_VERIFIED"):
                    audit.validate_registry(data)

    def test_claiming_media_verified_without_media_is_rejected(self):
        data=deepcopy(self.registry)
        media=next(x for x in data["findings"] if x["id"]=="AUD-004")
        media["evidence_type"]="synthetic_only"
        with self.assertRaisesRegex(audit.AuditRegistryError,"UNSUPPORTED_REAL_MEDIA"):
            audit.validate_registry(data)

    def test_external_issue_url_and_broken_payload_rejected(self):
        for url in ("https://github.com/random/victim/issues/100",
                    "https://example.com/wrong",
                    "https://github.com/pyzz58/gpt-recommendations/issues/1/extra"):
            data=deepcopy(self.registry)
            data["findings"][1]["issue_url"]=url
            with self.assertRaisesRegex(audit.AuditRegistryError,"OUT_OF_SCOPE"):
                audit.validate_registry(data)

    def test_open_critical_issue_must_remain_tracked(self):
        data=deepcopy(self.registry)
        data["findings"][1]["issue_url"]=""
        with self.assertRaisesRegex(audit.AuditRegistryError,"UNTRACKED"):
            audit.validate_registry(data)

    def test_audit_summary_is_public_and_only_reports_status_counts(self):
        r=audit.validate_registry(self.registry)
        raw=json.dumps(r,ensure_ascii=False)
        self.assertNotIn("api_key",raw)
        self.assertNotIn("source_script",raw)
        self.assertEqual(sum(r["status_counts"].values()),r["findings_total"])


if __name__=="__main__":
    unittest.main()
