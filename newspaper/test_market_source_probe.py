"""No-network validation of candidate-source audit and date strictness."""
import datetime as dt
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0,str(Path(__file__).resolve().parent))
from probe_market_sources import probe_one,probe_all


def make_response(body:bytes,status=200):
    obj=Mock()
    obj.content=body
    obj.raise_for_status.side_effect=(None if status==200 else ValueError("HTTP 403"))
    return obj


def xml(title,published):
    return ("""<?xml version="1.0"?>
    <rss version="2.0"><channel><title>test</title>
    <item><title>"""+title+"""</title><link>https://example.org/one</link>
    <description>Quarterly investor results</description><pubDate>"""+published+"""</pubDate></item>
    </channel></rss>""").encode("utf-8")


class MarketFeedProbeTests(unittest.TestCase):
    feed={"name":"Probe Test","url":"https://rss.example.org/feed","source_type":"financial_media"}
    now=dt.datetime(2026,10,14,15,0,tzinfo=dt.timezone(dt.timedelta(hours=8)))

    def test_24_hour_gate_uses_publication_not_fetch_time(self):
        recent=xml("Nvidia quarterly earnings beat estimates",
                   "Wed, 14 Oct 2026 00:30:00 GMT")
        r=probe_one(self.feed,self.now-dt.timedelta(days=1),self.now,
                    getter=lambda *args,**kwargs:make_response(recent))
        self.assertTrue(r["valid_rss_or_atom"])
        self.assertEqual(r["dated_entries"],1)
        self.assertEqual(r["fresh24"],1)
        self.assertEqual(r["relevant24"],1)
        self.assertEqual(r["editorially_eligible24"],1)
        self.assertEqual(len(r["sample_market_headlines"]),1)

    def test_old_news_cannot_be_mislabeled_today(self):
        old=xml("Nvidia quarterly earnings beat estimates",
                "Tue, 06 Oct 2026 00:30:00 GMT")
        r=probe_one(self.feed,self.now-dt.timedelta(days=1),self.now,
                    getter=lambda *args,**kwargs:make_response(old))
        self.assertTrue(r["valid_rss_or_atom"])
        self.assertEqual(r["fresh24"],0)
        self.assertEqual(r["fresh7d"],0)

    def test_http_ok_html_is_not_healthy_feed(self):
        r=probe_one(self.feed,self.now-dt.timedelta(days=1),self.now,
                    getter=lambda *args,**kwargs:make_response(b"<html>access denied</html>"))
        self.assertTrue(r["http_ok"])
        self.assertFalse(r["valid_rss_or_atom"])
        self.assertEqual(r["fresh24"],0)
        self.assertEqual(r["error"],"no_parseable_rss_entries")

    def test_access_denied_kept_as_explicit_failure(self):
        r=probe_one(self.feed,self.now-dt.timedelta(days=1),self.now,
                    getter=lambda *args,**kwargs:make_response(b"",403))
        self.assertFalse(r["http_ok"])
        self.assertIn("error",r)

    def test_empty_dates_are_not_fresh(self):
        data=b"""<rss version="2.0"><channel><title>x</title>
        <item><title>Wall Street stocks rise</title>
        <link>https://example.org/undated</link></item></channel></rss>"""
        r=probe_one(self.feed,self.now-dt.timedelta(days=1),self.now,
                    getter=lambda *args,**kwargs:make_response(data))
        self.assertTrue(r["valid_rss_or_atom"])
        self.assertEqual(r["dated_entries"],0)
        self.assertEqual(r["fresh24"],0)

    def test_aggregate_is_not_an_approval_for_production(self):
        a={**self.feed}
        b={**self.feed,"name":"Second","url":"https://rss2.example.org/feed"}
        def worker(feed,start,end):
            return {"http_ok":True,"valid_rss_or_atom":True,
                    "relevant24":1 if feed["name"]=="Second" else 0,
                    "fresh24":1,"fresh7d":1}
        r=probe_all({"schema":1,"scope":"newspaper-only",
                     "feeds":[a,b]},self.now,worker=worker)
        self.assertEqual(r["http_ok"],2)
        self.assertEqual(r["feeds_with_relevant_market_news_24h"],1)
        self.assertEqual(r["relevant_market_articles_24h_total"],1)
        self.assertIn("disabled",r["warning"])
        with self.assertRaises(ValueError):
            probe_all({"schema":1,"scope":"newspaper-only","feeds":[a,a]},
                      self.now,worker=worker)


if __name__=="__main__":
    unittest.main()
