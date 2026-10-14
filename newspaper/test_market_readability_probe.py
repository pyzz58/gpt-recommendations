"""Offline deterministic regression of the market-news article readability probe."""
import datetime as dt
import json
import unittest
from zoneinfo import ZoneInfo
from market_readability_probe import check_one,probe_readability,NAMES

BJT=ZoneInfo("Asia/Shanghai")
NOW=dt.datetime(2026,10,14,15,0,tzinfo=BJT)


def verified_rss(feed,start,end):
    return {
        "valid_rss_or_atom":True,
        "editorially_eligible24":1,
        "sample_market_headlines":[{
            "url":"https://www.example.org/market/123",
            "title":"US stock market reacts to quarterly earnings",
            "beijing_published":"2026-10-14T10:00:00+08:00",
        }],
    }


class FinanceArticleProbeTests(unittest.TestCase):
    def test_reader_success_counts_without_returning_article_body(self):
        def reader(article,min_chars,max_chars):
            self.assertEqual(min_chars,450)
            self.assertEqual(max_chars,1800)
            return {**article,"reading_en":"a"*500,
                    "article_chars":920,"extraction_engine":"trafilatura"}
        result=check_one({"name":"CNBC Earnings"},NOW-dt.timedelta(days=1),
                         NOW,rss_probe=verified_rss,article_reader=reader)
        self.assertEqual(result["readable_articles"],1)
        self.assertEqual(result["failed_articles"],0)
        self.assertEqual(result["status"],"has_readable_market_article")
        self.assertNotIn("reading_en",json.dumps(result))

    def test_paywall_or_short_article_does_not_count(self):
        result=check_one({"name":"Financial Times US"},NOW-dt.timedelta(days=1),NOW,
            rss_probe=verified_rss,article_reader=lambda *a,**k:None)
        self.assertEqual(result["tested_articles"],1)
        self.assertEqual(result["readable_articles"],0)
        self.assertEqual(result["status"],"market_article_not_readable")

    def test_invalid_rss_never_calls_reader(self):
        result=check_one({"name":"FT"},NOW-dt.timedelta(days=1),NOW,
            rss_probe=lambda *a:{},article_reader=lambda *a,**k:
                self.fail("reader must not run"))
        self.assertEqual(result["status"],"invalid_rss_or_unreachable")

    def test_exactly_five_prior_verified_sources_are_probed(self):
        names=[{"name":n} for n in sorted(NAMES)]
        names+=[{"name":"Nasdaq Investor Financial Releases"}]
        spec={"feeds":names}
        record=probe_readability(spec,NOW,
            rss_probe=verified_rss,article_reader=lambda a,**k:{
                **a,"reading_en":"text "*150,"article_chars":750,
                "extraction_engine":"fixture"})
        self.assertEqual(record["probed_sources"],5)
        self.assertEqual(record["tested_articles"],5)
        self.assertEqual(record["readable_articles"],5)
        self.assertEqual(record["status"],"READ_ONLY_NEVER_PRODUCTION_SOURCE_PROMOTION")
        self.assertNotIn("reading_en",json.dumps(record))
        with self.assertRaises(ValueError):
            probe_readability({"feeds":names[:-2]},NOW,rss_probe=verified_rss)

if __name__=="__main__":
    unittest.main()
