"""Budget and editorial orchestration contract for <=1 CNY per edition."""
from __future__ import annotations

import datetime as dt
import json
import unittest
from decimal import Decimal
from unittest.mock import Mock

from edition_budget import BudgetExhausted, EditionBudget, EDITION_CAP_RMB
from news_editor import edit_reports_in_batches, write_compact_commentary, build_report_messages
from brief_editor import apply_reports


def mock_response(body, prompt=2500, completion=700):
    m = Mock(status_code=200)
    m.json.return_value = {
        "choices": [{"finish_reason": "stop",
                     "message": {"content": json.dumps(body, ensure_ascii=False)}}],
        "usage": {"prompt_tokens": prompt, "completion_tokens": completion},
    }
    return m


def article(i):
    paragraphs = [
        ("The regulator said a proposal involving 500 people may be approved "
         "after a public consultation; it has not yet taken effect. " * 10),
        ("Officials presented a timetable and said the proposal would remain "
         "subject to parliamentary scrutiny. " * 12),
        ("The company disputed the economic impact and questioned whether "
         "the regulation could change employment conditions. " * 12),
        ("However, experts cautioned the available evidence is preliminary and "
         "does not establish the forecast effects. " * 10),
    ]
    return {
        "event_key": "event-" + str(i), "title": "Regulatory proposal " + str(i),
        "source": "Verified publisher", "category": "国际政治与全球事件",
        "url": "https://publisher.test/story/" + str(i),
        "reading_en": "\n\n".join(paragraphs), "importance_score": 78,
    }


class OneYuanTests(unittest.TestCase):
    def test_user_authorized_cap_cannot_be_raised_by_caller(self):
        self.assertEqual(EDITION_CAP_RMB, Decimal("1.00"))
        with self.assertRaises(ValueError):
            EditionBudget(cap="1.01")

    def test_budget_blocks_before_any_billable_request(self):
        ledger = EditionBudget(cap="0.03")
        send = Mock()
        with self.assertRaises(BudgetExhausted):
            ledger.request([
                {"role": "system", "content": "edit"},
                {"role": "user", "content": "a" * 10000},
            ], 4200, "dummy", purpose="report", transport=send)
        send.assert_not_called()
        self.assertEqual(ledger.requests, 0)

    def test_peak_priced_reservation_not_offpeak_guess(self):
        ledger = EditionBudget()
        send = Mock(return_value=mock_response({"reports": {}}, 2000, 200))
        value = ledger.request(
            [{"role": "user", "content": "source material"}], 1000, "dummy",
            purpose="report", transport=send)
        self.assertIn("reports", value)
        self.assertEqual(ledger.requests, 1)
        self.assertLess(ledger.spent_ceiling, Decimal("0.10"))
        self.assertLessEqual(ledger.spent_ceiling, EDITION_CAP_RMB)

    def test_uncertain_provider_timeout_uses_reservation_without_retry(self):
        ledger = EditionBudget()
        send = Mock(side_effect=TimeoutError("API reply lost"))
        with self.assertRaises(TimeoutError):
            ledger.request([{"role": "user", "content": "story"}], 2500, "dummy",
                           purpose="report", transport=send)
        send.assert_called_once()
        self.assertEqual(ledger.requests, 1)
        self.assertGreater(ledger.spent_ceiling, Decimal("0"))
        self.assertEqual(ledger.breakdown[0]["status"], "uncertain")

    def test_two_article_batch_has_source_spans_and_wont_mix_events(self):
        batch = [article(1), article(2)]
        msgs = build_report_messages(batch)
        data = json.loads(msgs[1]["content"])
        self.assertEqual(len(data["articles"]), 2)
        self.assertEqual([x["id"] for x in data["articles"]], ["event-1", "event-2"])
        self.assertTrue(all(x["protected_ids"] for x in data["articles"]))
        # Missing result for story 2 falls back only that story, without
        # deleting or corrupting the other one.
        report = [{"en": p, "source_ids": [i]}
                  for i, p in enumerate(batch[0]["reading_en"].split("\n\n"))]
        transport = Mock(return_value=mock_response(
            {"reports": {"event-1": report}}, 6000, 1000))
        ledger = EditionBudget()
        proposals, errors = edit_reports_in_batches(
            {"中国与美国": batch}, "dummy", ledger, transport=transport)
        result = apply_reports({"中国与美国": batch}, proposals)["中国与美国"]
        self.assertEqual(result[0]["editing_mode"], "evidence_mapped_edited_report")
        self.assertEqual(result[1]["editing_mode"], "source_faithful_edited_report")
        self.assertEqual(ledger.requests, 1)
        transport.assert_called_once()
        self.assertTrue(errors)

    def test_commentary_is_separate_small_request_with_budget_ledger(self):
        ledger = EditionBudget()
        commentary = "根据已有公开资料，政策演变仍有多方面的条件需要进一步核实。" * 35
        response = mock_response({"commentary": commentary}, 2000, 1600)
        api = Mock(return_value=response)
        result = write_compact_commentary(
            {"国际政治与全球事件": [article(4)]},
            dt.date(2026, 10, 13), "dummy", ledger, transport=api)
        self.assertEqual(result, commentary)
        sent = api.call_args.kwargs["json"]
        self.assertEqual(sent["model"], "deepseek-flash")
        self.assertEqual(sent["max_tokens"], 2100)
        self.assertLess(ledger.spent_ceiling, Decimal("0.10"))

    def test_budgeted_many_calls_stop_before_crossing_ceiling(self):
        ledger = EditionBudget()
        transport = Mock(return_value=mock_response({"reports": {}}, 1100, 1300))
        for i in range(80):
            try:
                ledger.request(
                    [{"role": "user", "content": "verified source material " * 100}],
                    4200, "dummy", purpose="report", transport=transport)
            except BudgetExhausted:
                break
        self.assertLessEqual(ledger.spent_ceiling, EDITION_CAP_RMB)
        self.assertLess(ledger.requests, 80)
        self.assertEqual(transport.call_count, ledger.requests)


if __name__ == "__main__":
    unittest.main()
