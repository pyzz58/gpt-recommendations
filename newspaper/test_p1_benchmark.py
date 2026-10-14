"""P1 fixed headline fixture baseline and observed-news selection audit tests."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
from editorial_benchmark import load_cases,calculate_metrics,run_benchmark
from selection_audit import make_selection_audit,save_selection_audit


class P1BenchmarkTests(unittest.TestCase):
    def test_50_cases_are_explicit_about_provenance(self):
        data=load_cases()
        items=data["cases"]
        self.assertEqual(len(items),50)
        self.assertEqual(sum(c["kind"]=="historical_source_reference" for c in items),5)
        self.assertEqual(sum(c["kind"].startswith("synthetic") for c in items),45)
        self.assertEqual(len({c["id"] for c in items}),50)
        self.assertIn("NOT chronological historical news replays",data["description"])
        for case in items:
            if case["kind"]=="historical_source_reference":
                self.assertTrue(case["primary_source_url"].startswith("https://"))
                self.assertRegex(case["historical_event_date"],r"^20\d\d-\d\d-\d\d$")

    def test_event_level_math_does_not_count_syndication_twice(self):
        cases=[
            {"id":"a","url":"u1","gold_event_id":"one","expected_material":True},
            {"id":"b","url":"u2","gold_event_id":"one","expected_material":True},
            {"id":"c","url":"u3","gold_event_id":"two","expected_material":True},
            {"id":"d","url":"u4","gold_event_id":"noise","expected_material":False},
        ]
        result=calculate_metrics(cases,["u1","u2","u4"])
        self.assertEqual(result["expected_material_events"],2)
        self.assertEqual(result["selected_material_events"],1)
        self.assertEqual(result["duplicate_article_slots"],1)
        self.assertEqual(result["false_positive_selected_ids"],["d"])
        self.assertEqual(result["event_recall"],0.5)
        self.assertEqual(result["selection_precision"],0.3333)

    def test_selector_never_receives_gold_labels(self):
        data=load_cases()
        calls=[]
        def fake_pool(items,per_section=20):
            calls.extend(items)
            self.assertTrue(all(set(row)=={"title","summary","source","url"} for row in items))
            return {}
        with patch("editorial_benchmark.prepare_pool",side_effect=fake_pool):
            result=run_benchmark(data)
        self.assertEqual(len(calls),50)
        self.assertTrue(result["NOT_REAL_HISTORICAL_REPLAY"])
        self.assertEqual(result["selected_article_slots"],0)

    def test_actual_pipeline_scores_five_disjoint_editions(self):
        a=run_benchmark()
        b=run_benchmark()
        self.assertEqual(a,b)
        self.assertEqual(a["case_count"],50)
        self.assertEqual(a["episode_count"],5)
        self.assertEqual(a["historical_primary_source_reference_count"],5)
        self.assertEqual(a["synthetic_case_count"],45)
        for key in ("event_recall","selection_precision","duplicate_slot_rate"):
            self.assertGreaterEqual(a[key],0)
            self.assertLessEqual(a[key],1)
        self.assertGreater(a["expected_material_events"],0)
        self.assertTrue(all(len(e["by_section"])==7 for e in a["episodes"]))

    def test_audit_reports_within_feed_gaps_not_global_recall(self):
        raw=[
            {"url":"u1","title":"US Federal Reserve cuts interest rates after policy meeting",
             "summary":"Central bank lowers rates","source":"Agency"},
            {"url":"u2","title":"FDA approves new clinical trial drug after cancer study",
             "summary":"Government approves important cancer trial medicine","source":"Medical"},
            {"url":"u3","title":"Sponsored coupon codes for lifestyle tips",
             "summary":"ads","source":"Advertisement"},
        ]
        candidate={**raw[1],"event_key":"e2","importance_score":92,
                   "category":"医疗、生命科学与公共健康"}
        chosen={**raw[0],"event_key":"e1","importance_score":95,
                "category":"美股·全球金融市场"}
        report=make_selection_audit(raw,
            {"美股·全球金融市场":[chosen],"医疗、生命科学与公共健康":[candidate]},
            {"美股·全球金融市场":[chosen],"医疗、生命科学与公共健康":[]})
        self.assertEqual(report["coverage_scope"],"observed_RSS_items_only")
        self.assertEqual(report["independent_global_major_event_recall"],"NOT_MEASURED")
        self.assertEqual(report["selected_urls"],1)
        self.assertEqual(report["candidate_high_score_unselected_count"],1)
        self.assertEqual(report["candidate_high_score_unselected_top"][0]["url"],"u2")
        self.assertEqual(report["reasons_by_unique_url"]["hard_rejected_as_low_value"],1)
        self.assertNotIn("reading_en",json.dumps(report))

    def test_save_audit_without_network_and_original_body(self):
        report={"coverage_scope":"observed_RSS_items_only","selected_records":[]}
        with tempfile.TemporaryDirectory() as d:
            path=save_selection_audit(report,Path(d)/"audit.json")
            self.assertEqual(json.loads(path.read_text(encoding="utf8")),report)


if __name__=="__main__":
    unittest.main()
