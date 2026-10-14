"""Adversarial market desk and real-funnel diagnostics; no paid API/network."""
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from market_headline import market_evidence
from market_funnel import report_market_funnel, save_market_funnel
from newsroom import sections,prepare_pool

MARKET="美股·全球金融市场"


def row(title,*,source="Global Desk",host="news.example.org",
        source_type="media",source_language="en"):
    return {
        "title":title,"summary":title,"source":source,
        "source_language":source_language,"source_type":source_type,
        "url":"https://"+host+"/article/"+str(abs(hash(title))),
        "category":"美股与投资"
    }


class MarketCoverageFunnelTests(unittest.TestCase):
    def test_market_issuer_earnings_and_announcements_that_affect_us_stocks(self):
        titles=[
            "Nvidia quarterly earnings send shares higher",
            "Microsoft reports quarterly revenue and operating profit",
            "Apple shares fall after quarterly earnings guidance cut",
            "Tesla stock declines after revenue misses forecasts",
            "Amazon announces $8 billion acquisition of a software firm",
            "Nasdaq stocks tumble after US jobs report",
            "Wall Street stocks rally as Treasury yields decline",
            "U.S. stocks fall after CPI inflation release",
            "JPMorgan raises Nvidia price target after earnings",
        ]
        for title in titles:
            with self.subTest(title=title):
                a=row(title,source="CNBC Tech")
                self.assertTrue(market_evidence(a)["eligible"])
                self.assertIn(MARKET,sections(a))

    def test_market_desk_can_surface_material_unlisted_issuer(self):
        item=row("Company shares drop after quarterly earnings guidance",
                 source="CNBC Markets")
        self.assertTrue(market_evidence(item)["eligible"])
        self.assertIn(MARKET,sections(item))

    def test_primary_sec_and_federal_reserve_require_real_market_substance(self):
        sec=row("SEC adopts new securities trading disclosure rules",
                host="www.sec.gov",source="US SEC Press Releases - Stocks",
                source_type="primary_regulator")
        fed=row("Fed announces rate decision after meeting",
                host="www.federalreserve.gov",source="Federal Reserve Monetary - Stocks",
                source_type="primary_central_bank")
        for a in (sec,fed):
            with self.subTest(title=a["title"]):
                self.assertTrue(market_evidence(a)["eligible"])
                self.assertIn(MARKET,sections(a))
        arbitrary=row("SEC hosts an employee arts charity gala",
                      host="www.sec.gov",source_type="primary_regulator")
        self.assertFalse(market_evidence(arbitrary)["eligible"])
        impostor=row("Securities regulation announcement from fake SEC",
                     host="www.sec.gov.evil.example.org",
                     source_type="primary_regulator")
        self.assertFalse(market_evidence(impostor)["eligible"])

    def test_generic_world_finance_does_not_fill_us_front_page(self):
        titles=[
            "India's retail inflation jumps to 5.54% in September, above estimates",
            "EU to limit Chinese hybrid vehicle imports to 350,000 a year",
            "Trump faces growing backlash over plans to import diesel from Russia",
            "IMF predicts slow euro area growth after war",
            "Nvidia unveils a new gaming graphics gadget",
            "Apple launches new movie streaming series",
            "Nasdaq hosts charity awards dinner",
        ]
        for title in titles:
            with self.subTest(title=title):
                a=row(title,source="CNBC Business")
                self.assertFalse(market_evidence(a)["eligible"])
                self.assertNotIn(MARKET,sections(a))

    def test_chinese_us_stock_news_but_not_generic_shares(self):
        for title in ("美股纳斯达克指数下跌","美联储公布新的利率政策",
                      "微软在美上市公司公布重要财报"):
            with self.subTest(title=title):
                self.assertTrue(market_evidence(
                    row(title,source_language="zh"))["eligible"])
        for title in ("中国新能源股票上涨","港股新能源企业公布财报","欧洲股市周报"):
            with self.subTest(title=title):
                self.assertFalse(market_evidence(
                    row(title,source_language="zh"))["eligible"])

    def test_market_desk_inclusion_uses_real_candidate_pool(self):
        items=[row("Nvidia quarterly earnings send shares higher",
                    source="CNBC Tech"),
               row("India inflation unexpectedly jumps",
                    source="Guardian Business"),
               row("Federal Reserve announces interest rate decision",
                    source_type="primary_central_bank",
                    host="federalreserve.gov")]
        pool=prepare_pool(items)
        market_urls={x["url"] for x in pool[MARKET]}
        self.assertIn(items[0]["url"],market_urls)
        self.assertIn(items[2]["url"],market_urls)
        self.assertNotIn(items[1]["url"],market_urls)

    def test_report_distinguishes_no_market_stories_from_unreadability(self):
        stock=row("Nvidia quarterly earnings send shares higher",source="CNBC Tech")
        global_noise=row("India retail inflation jumps",source="CNBC Business")
        candidate={**stock,"importance_score":78,"event_key":"event-one"}
        rep=report_market_funnel([stock,global_noise],
            {MARKET:[candidate]}, {MARKET:[]},limits={MARKET:4})
        self.assertEqual(rep["grounded_market_signal_count"],1)
        self.assertEqual(rep["routed_market_count"],1)
        self.assertEqual(rep["candidate_pool_count"],1)
        self.assertEqual(rep["printed"],0)
        self.assertEqual(rep["shortfall"],4)
        self.assertEqual(rep["stage_counts"]["pooled_not_printed"],1)
        self.assertEqual(rep["stage_counts"]["not_market_relevant"],1)
        self.assertIn("only_available_in_window_RSS_articles",rep["coverage_scope"])
        with tempfile.TemporaryDirectory() as folder:
            dest=save_market_funnel(rep,Path(folder)/"health.json")
            self.assertEqual(json.loads(dest.read_text(encoding="utf8"))["shortfall"],4)


if __name__=="__main__":
    unittest.main()
