"""Adversarial tests for stocks-first edition, FRED provenance and Chinese feeds."""
import datetime as dt
import json
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from zoneinfo import ZoneInfo

from newsroom import SECTIONS, sections, countries, prepare_pool
from market_snapshot import parse_fred_csv, fetch_market_snapshot
from people_overseas import parse_edition
from xueqiu_magazine import parse_public_journal
from clippings import build_clippings_html
from digest import bilingualize

class FrontPageTests(unittest.TestCase):
    def test_us_stocks_is_first_not_china_us(self):
        self.assertEqual(list(SECTIONS)[0],"美股·全球金融市场")
        self.assertEqual(SECTIONS["美股·全球金融市场"],4)
        self.assertEqual(SECTIONS["中国与美国"],3)

    def test_all_four_requested_sources_accounted_without_fake_xueqiu_feed(self):
        j=json.loads(Path(__file__).with_name("feeds.json").read_text())
        names={f["name"] for x in j["feeds"].values() for f in x}
        for n in ("36氪文章","新华网时政","新华网财经","US SEC Press Releases - Stocks"):
            self.assertIn(n,names)
        watch={x["name"]:x for x in j["source_watchlist"]}
        self.assertEqual(watch["雪球专刊（雪球杂志）"]["mode"],"public_page_monitor")
        self.assertEqual(watch["人民日报海外版电子报"]["mode"],"public_edition_monitor")

    def test_chinese_business_discovery_without_hallucinating_translation(self):
        a={"title":"中国出台半导体产业政策","summary":"国家出台芯片相关政策",
           "url":"https://36kr.com/p/123","source":"36氪文章","source_language":"zh"}
        self.assertIn("中国",countries(a))
        self.assertIn("科技、能源与前沿科学",sections(a))
        self.assertIn("中国与美国",prepare_pool([a])["中国与美国"])
        grouped={"中国与美国":[{
            **a,"reading_en":"中国出台新产业政策。政策将分阶段实施。"}]}
        translator=Mock()
        result=bilingualize(grouped,translator)["中国与美国"][0]
        self.assertEqual(result["reading_zh"],grouped["中国与美国"][0]["reading_en"])
        self.assertEqual(result["bilingual_pairs"][0]["en"],"")
        translator.translate.assert_not_called()

    def test_market_snapshot_rejects_old_or_missing_fred_prices(self):
        today=dt.date(2026,10,13)
        csv="observation_date,SP500\n2026-10-01,7600\n2026-10-02,.\n"
        self.assertIsNone(parse_fred_csv(csv,"SP500",today))
        recent="observation_date,SP500\n2026-10-09,7500\n2026-10-12,7650\n"
        q=parse_fred_csv(recent,"SP500",today)
        self.assertEqual(q["value"],7650)
        self.assertEqual(q["as_of"],"2026-10-12")
        self.assertEqual(q["change_percent"],2.0)

    def test_missing_fred_data_does_not_make_up_market_numbers(self):
        bad=Mock(status_code=500)
        bad.raise_for_status.side_effect=ValueError("No series")
        snap=fetch_market_snapshot(
            dt.datetime(2026,10,13,0,0,tzinfo=dt.timezone.utc),
            getter=Mock(return_value=bad))
        self.assertFalse(snap["values"])
        self.assertEqual(len(snap["missing"]),6)

    def test_market_heading_prints_dated_only_not_intraday(self):
        snap={"values":[{"name":"标普500","series":"SP500","value":7520.0,
                        "as_of":"2026-10-12","change_percent":0.5}],
              "missing":["DJIA"]}
        html,txt=build_clippings_html({},dt.date(2026,10,13),snap)
        self.assertIn("美股头版",html)
        self.assertIn("2026-10-12",html)
        self.assertIn("非实时行情",html)
        self.assertNotIn("实时涨幅",html)

    def test_xueqiu_journal_monitors_only_public_issue_titles(self):
        page = "<html><body>雪球专刊 雪球专刊382期——硅基新纪元｜AI</body></html>"
        result = parse_public_journal(page)
        self.assertTrue(result["page_identified"])
        self.assertTrue(result["not_daily_publication"])
        self.assertIn("雪球专刊382期",result["visible_issue_titles"][0])

    def test_overseas_edition_parser_does_not_invent_article_publish_time(self):
        html='<html><body>人民日报海外版 2026年10月13日 星期二' + \
             '<a href="../content_12345.html">美国市场影响中国企业海外发展</a></body></html>'
        result=parse_edition(html)
        self.assertEqual(result["issue_date"],"2026-10-13")
        self.assertFalse(result["issue_date_is_publication_timestamp"])
        self.assertEqual(len(result["items"]),1)

if __name__=="__main__":
    unittest.main()
