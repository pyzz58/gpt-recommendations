"""Cost and safety tests; NEVER call DeepSeek's live network in CI."""
import datetime as dt
from zoneinfo import ZoneInfo
from decimal import Decimal
from unittest.mock import Mock
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from llm_budget import (MAX_RMB, OPERATIONAL_RMB, preflight,
                        conservative_input_tokens, estimate_peak_cost,
                        actual_cost_ceiling, estimate_window_cost, beijing_offpeak)
from ai_commentary import analyze_one_call, email_commentary, preferred_model_for_commentary, prepare_messages


class OneCallCostTests(unittest.TestCase):
    def setUp(self):
        self.news = {"AI与科技": [
            {"source":"Test Publisher", "title":"AI supply chain expands",
             "reading_en":("The company announced higher investment in computers. "
                           "Power and cooling costs remain important for business models. ")*20,
             "date": dt.datetime(2026,10,11,12,tzinfo=dt.timezone.utc)}
        ]}
        self.day=dt.date(2026,10,11)

    def test_prices_use_peak_not_discount(self):
        self.assertEqual(estimate_peak_cost("deepseek-flash",1000000,0), Decimal("2"))
        self.assertEqual(estimate_peak_cost("deepseek-flash",0,1000000), Decimal("8"))
        self.assertEqual(estimate_peak_cost("deepseek-v4-pro",1000000,0), Decimal("9"))
        self.assertEqual(estimate_peak_cost("deepseek-v4-pro",0,1000000), Decimal("27"))

    def test_offpeak_at_seven_am_beijing_and_peak_at_afternoon(self):
        tz=ZoneInfo("Asia/Shanghai")
        morning=dt.datetime(2026,10,13,7,0,tzinfo=tz)
        afternoon=dt.datetime(2026,10,13,16,0,tzinfo=tz)
        self.assertTrue(beijing_offpeak(morning))
        self.assertFalse(beijing_offpeak(afternoon))
        self.assertEqual(estimate_window_cost("deepseek-flash",1_000_000,0,morning),Decimal("1"))
        self.assertEqual(estimate_window_cost("deepseek-flash",1_000_000,0,afternoon),Decimal("2"))
        self.assertEqual(estimate_window_cost("deepseek-flash",0,1_000_000,morning),Decimal("4"))
        self.assertEqual(estimate_window_cost("deepseek-flash",0,1_000_000,afternoon),Decimal("8"))
        request=[{"role":"user","content":"A"*5000}]
        _,lo=preflight(request,at=morning)
        _,hi=preflight(request,at=afternoon)
        self.assertLess(lo,hi)

    def test_small_request_passes_and_is_below_20_cent(self):
        words=[{"role":"user","content":"这是一段已核实的素材。"}]
        tokens, estimate=preflight(words)
        self.assertGreater(tokens,1024)
        self.assertLess(estimate, OPERATIONAL_RMB)
        self.assertLess(estimate, MAX_RMB)

    def test_oversize_request_fails_closed(self):
        with self.assertRaises(ValueError):
            preflight([{"role":"user","content":"a"*100000}])
        with self.assertRaises(ValueError):
            preflight([{"role":"user","content":"a"*65000}],model="deepseek-v4-pro")
        with self.assertRaises(ValueError):
            preflight([{"role":"user","content":"short"}],output_limit=1000000)
        with self.assertRaises(ValueError):
            preflight([{"role":"user","content":"short"}],model="unknown-model")

    def test_input_bound_uses_utf8_bytes_for_chinese(self):
        messages=[{"role":"user","content":"中文"*200}]
        self.assertGreater(conservative_input_tokens(messages), 2200)

    def test_only_one_paid_call_mocked(self):
        response=Mock()
        response.status_code=200
        response.json.return_value={
            "choices":[{"message":{"content":"真实材料支持的审慎分析："+"市场存在不确定性。"*70},
                        "finish_reason":"stop"}],
            "usage":{"prompt_tokens":2100, "completion_tokens":700},
        }
        fake=Mock(return_value=response)
        body, audit=analyze_one_call(self.news,self.day,"fake-credential",transport=fake)
        self.assertIn("真实材料",body)
        self.assertEqual(fake.call_count,1)
        self.assertEqual(audit["request_count"],1)
        self.assertLess(Decimal(audit["predicted_peak_rmb"]),Decimal("0.20"))
        self.assertLess(Decimal(audit["reported_peak_cost_rmb"]),Decimal("0.20"))
        payload=fake.call_args.kwargs["json"]
        self.assertEqual(payload["model"],"deepseek-flash")
        self.assertEqual(payload["max_tokens"],3400)
        self.assertEqual(payload["thinking"],{"type":"disabled"})
        self.assertTrue(fake.call_args.kwargs["headers"]["Authorization"].startswith("Bearer "))

    def test_skill_included_in_model_messages(self):
        msgs=prepare_messages(self.news,self.day)
        instructions=msgs[0]["content"]
        self.assertIn("因果",instructions)
        self.assertIn("二阶",instructions)
        self.assertIn("反例",instructions)
        self.assertIn("GLOBAL-STRATEGY-EDITOR",instructions)
        selected=preferred_model_for_commentary(self.news,self.day)
        self.assertIn(selected,{"deepseek-flash","deepseek-v4-pro"})

    def test_one_failure_no_retry_and_no_secret_leak(self):
        fail=Mock()
        fail.status_code=429
        fake=Mock(return_value=fail)
        with self.assertRaisesRegex(RuntimeError,"HTTP 429") as cm:
            analyze_one_call(self.news,self.day,"private-should-not-appear",transport=fake)
        self.assertNotIn("private-should-not-appear",str(cm.exception))
        self.assertEqual(fake.call_count,1)

    def test_reject_overspending_report_and_missing_usage(self):
        self.assertEqual(actual_cost_ceiling("deepseek-flash",
             {"prompt_tokens":1000,"completion_tokens":300}),
             Decimal("0.0044"))
        with self.assertRaises(ValueError):
            actual_cost_ceiling("deepseek-flash",None)
        fake=Mock()
        fake.status_code=200
        fake.json.return_value={
            "choices":[{"message":{"content":"合理的经济评论："+"讨论政策变化对企业的影响。"*55},"finish_reason":"stop"}],
            "usage":{"prompt_tokens":200000,"completion_tokens":10000},
        }
        with self.assertRaisesRegex(RuntimeError,"0.20 RMB"):
            analyze_one_call(self.news,self.day,"mock",transport=Mock(return_value=fake))

    def test_commentary_is_email_only(self):
        html,plain=email_commentary(self.day,"观察到若干相反趋势。",3)
        self.assertIn("观察到若干相反趋势",html)
        self.assertIn("PDF",html)
        self.assertNotIn("http://",html)
        self.assertNotIn("https://",plain)


if __name__=="__main__":
    unittest.main()
