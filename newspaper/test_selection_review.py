"""Bounded editorial review and specific false-rejection regression cases.

Transport replies below are synthetic test doubles, never measured AI quality.
"""
import copy
import importlib.util
import json
import unittest
from decimal import Decimal
from unittest.mock import Mock, patch
import requests
from edition_budget import EditionBudget
from selection_review import review_candidates, MAX_CANDIDATES
from brief_editor import validate_rewritten_report, apply_reports, numeric_claims
from newsroom import prepare_pool, select_readable
from news_editor import build_report_messages


def reply(items):
    response = Mock(status_code=200)
    response.json.return_value = {
        "choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"items": items})}}],
        "usage": {"prompt_tokens": 800, "completion_tokens": 200}}
    return response


def grade(i, score=3, completeness=3):
    return {"id": str(i), "impact": score, "novelty": score,
            "evidence": score, "relevance": score, "completeness": completeness}


class SelectionReviewTests(unittest.TestCase):
    def setUp(self):
        self.rows = [{"url": f"https://source.test/{i}", "title": "Regulator approves policy",
                      "reading_en": "A sourced policy change with a clear timetable.",
                      "importance_score": 60, "event_key": str(i)} for i in range(3)]
        self.pool = {"desk": self.rows}
        self.enriched = {r["url"]: r for r in self.rows}

    def test_single_review_uses_shared_ledger_and_does_not_mutate_evidence(self):
        ledger, api = EditionBudget(), Mock(return_value=reply([grade(i) for i in range(3)]))
        original = copy.deepcopy(self.enriched)
        result = review_candidates(self.pool, self.enriched, "dummy", ledger, transport=api)
        api.assert_called_once()
        self.assertEqual(ledger.requests, 1)
        self.assertEqual(ledger.breakdown[0]["purpose"], "selection")
        self.assertLess(ledger.spent_ceiling, Decimal("1"))
        self.assertEqual(self.enriched, original)
        for url, row in result.items():
            self.assertEqual(row["reading_en"], original[url]["reading_en"])
            self.assertEqual(row["importance_score"], 60)
            self.assertIn("selection_review", row)

    def test_partial_duplicate_unknown_or_invalid_reply_reverts_atomically(self):
        for items in ([grade(0)], [grade(0), grade(0), grade(2)],
                      [grade(0), grade(1), grade(99)], [grade(0), grade(1), grade(2, True)]):
            with self.subTest(items=items):
                result = review_candidates(self.pool, self.enriched, "dummy", EditionBudget(),
                                           transport=Mock(return_value=reply(items)))
                self.assertIs(result, self.enriched)

    def test_cost_budget_and_timeout_fall_back_without_retries(self):
        for ledger, effect in ((EditionBudget(cap="0.03"), None),
                               (EditionBudget(), requests.Timeout("secret response must not be logged"))):
            api = Mock(side_effect=effect)
            with self.assertLogs("newspaper.selection") as logs:
                result = review_candidates(self.pool, self.enriched, "dummy", ledger, transport=api)
            self.assertIs(result, self.enriched)
            self.assertLessEqual(api.call_count, 1)
            self.assertNotIn("secret response", "".join(logs.output))

    def test_preview_never_calls_api(self):
        api = Mock()
        self.assertIs(review_candidates(self.pool, self.enriched, "", None, transport=api), self.enriched)
        api.assert_not_called()

    def test_round_robin_limit_and_unreadable_not_reviewed(self):
        rows = [{**self.rows[0], "url": f"https://a.test/{i}"} for i in range(40)]
        other = {**self.rows[0], "url": "https://b.test/one"}
        enriched = {r["url"]: r for r in rows + [other]}
        enriched[rows[0]["url"]] = None
        api = Mock(return_value=reply([grade(i) for i in range(MAX_CANDIDATES)]))
        result = review_candidates({"first": rows, "second": [other]}, enriched,
                                   "dummy", EditionBudget(), transport=api)
        reviewed = [r for r in result.values() if r and "selection_review" in r]
        self.assertEqual(len(reviewed), MAX_CANDIDATES)
        self.assertIn("selection_review", result[other["url"]])
        self.assertIsNone(result[rows[0]["url"]])

    def test_representative_quality_breaks_event_tie_but_dedup_remains(self):
        rows = [dict(title="FDA approves new cancer treatment after clinical trial",
                     summary="Regulator approves cancer medicine", source=f"Outlet {i}",
                     url=f"https://source{i}.test/one") for i in range(2)]
        pool = prepare_pool(rows)
        enriched = {r["url"]: {**r, "reading_en": "Regulator approved a treatment."}
                    for arr in pool.values() for r in arr}
        reviewed = review_candidates(pool, enriched, "dummy", EditionBudget(),
                                    transport=Mock(return_value=reply([grade(0, 3, 1), grade(1, 3, 5)])))
        result, diagnostics = select_readable(pool, reviewed)
        selected = [r for arr in result.values() for r in arr]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["url"], rows[1]["url"])
        self.assertTrue(any(d["candidate_decisions"] for d in diagnostics.values()))


class ReportRejectionTests(unittest.TestCase):
    def test_equivalent_numeric_formatting_accepted_changed_units_rejected(self):
        source = "Revenue rose 5 percent as 1,000 customers renewed contracts."
        article = {"reading_en": source}
        valid = [{"en": "Revenue rose 5.0% as 1000 customers renewed contracts.", "source_ids": [0]}]
        self.assertEqual(validate_rewritten_report(article, valid)["editing_mode"], "evidence_mapped_edited_report")
        self.assertNotEqual(numeric_claims("5%"), numeric_claims("5"))
        for text in (source.replace("5 percent", "6%"), source.replace("1,000", "1000%")):
            with self.assertRaisesRegex(ValueError, "numeric"):
                validate_rewritten_report(article, [{"en": text, "source_ids": [0]}])
        # Isolate numeric normalization from the separate short-source fix.
        long_source = [source * 12, "Customers renewed annual service contracts. " * 15,
                       "The report covers the latest quarterly results. " * 15]
        long_report = [{"en": text.replace("5 percent", "5.0%").replace("1,000", "1000"),
                        "source_ids": [i]} for i, text in enumerate(long_source)]
        self.assertEqual(validate_rewritten_report({"reading_en": "\n\n".join(long_source)},
                                                  long_report)["editing_mode"], "evidence_mapped_edited_report")

    def test_short_source_kept_complete_without_filler_and_prompt_matches(self):
        article = {"reading_en": "The regulator may approve the proposal. It has not taken effect.",
                   "url": "https://source.test/one", "title": "A proposal"}
        proposed = [{"en": article["reading_en"], "source_ids": [0]}]
        self.assertEqual(validate_rewritten_report(article, proposed)["retained_words"], 11)
        contract = json.loads(build_report_messages([article])[1]["content"])["articles"][0]["length_contract"]
        self.assertEqual(contract["min_paragraphs"], 1)
        for text in ("The regulator approved the measure. It has not taken effect.",
                     "The regulator may approve the proposal. It has taken effect."):
            with self.assertRaises(ValueError):
                validate_rewritten_report(article, [{"en": text, "source_ids": [0]}])

    def test_chinese_not_submitted_is_not_counted_as_editor_rejection(self):
        result = apply_reports({"desk": [{"source_language": "zh", "reading_en": "中文原稿"}]}, {})
        self.assertNotIn("editor_rejection_reason", result["desk"][0])

    @unittest.skipUnless(importlib.util.find_spec("feedparser") and importlib.util.find_spec("trafilatura"),
                         "requires newsroom dependencies; covered by complete PR suite")
    def test_main_build_passes_same_ledger_to_review_before_selection(self):
        import digest
        article = {"url": "https://source.test/one", "reading_en": "Sourced report"}
        ledger = EditionBudget()
        callback = Mock()
        with patch.object(digest, "fetch_reading", return_value=article), \
             patch.object(digest, "review_candidates", side_effect=lambda c, e, *a, **k: e) as review, \
             patch.object(digest, "select_readable", return_value=({}, {})) as selector:
            pool = {"中国与美国": [article]}
            digest.build_readings(pool, {"longread_min_chars": 1, "longread_max_chars": 500},
                                  key="dummy", ledger=ledger, before_request=callback)
        self.assertIs(review.call_args.args[3], ledger)
        self.assertIs(review.call_args.kwargs["before_request"], callback)
        selector.assert_called_once()


if __name__ == "__main__":
    unittest.main()
