"""Newsroom source-quality adversarial regressions; all tests require no API keys."""
from __future__ import annotations
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock,patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
import reader
from newsroom import score,prepare_pool,select_readable
from source_quality import newsworthiness
from news_extraction import newspaper4k_from_html

def a(title,n,summary=""):
    return {"title":title,"summary":summary,"source":"Publisher "+str(n),
            "url":"https://example"+str(n)+".org/2026/news"}


class SourceQualityUpgradeTests(unittest.TestCase):
    def test_advertising_and_entertainment_cannot_fill_newsroom(self):
        for title in (
            "Sponsored: new global AI gadget review with 40% discount",
            "Celebrity gossip: pop star dating rumours this weekend",
            "Watch the trailer for an AI movie",
            "Premier league match latest football scores",
            "Your daily horoscope for October 13",
            "Best deals on AI headphones this week",
        ):
            with self.subTest(title=title):
                self.assertFalse(newsworthiness(a(title,1))["eligible"])
                self.assertFalse(any(prepare_pool([a(title,1)]).values()))

    def test_soft_clickbait_is_strongly_downgraded(self):
        teaser=a("Startup launches a new AI app for celebrities",1)
        policy=a("US Federal Reserve approves new monetary policy regulation",2)
        s1,e1=score(teaser,1)
        s2,e2=score(policy,1)
        self.assertLess(s1,s2)
        self.assertGreaterEqual(e1["editorial_noise_penalty"],-42)
        self.assertEqual(e2["editorial_noise_penalty"],0)
        self.assertEqual(len(prepare_pool([teaser])["AI与数字产业"]),0)
        self.assertTrue(prepare_pool([policy])["中国与美国"])

    def test_material_regulation_about_pop_culture_is_not_censored(self):
        important=a("US government regulation of viral video platforms to protect national security",3)
        decision=newsworthiness(important)
        self.assertTrue(decision["eligible"])
        self.assertEqual(decision["penalty"],0)
        self.assertTrue(prepare_pool([important])["中国与美国"])

    def test_global_grain_and_policy_beat_local_fluff(self):
        major=a("India announces grain export ban affecting global food supply chain",4)
        fluff=a("Local concert influencer goes viral with new fashion app",5)
        self.assertGreater(score(major,1)[0],score(fluff,8)[0])
        self.assertTrue(prepare_pool([major])["国际政治与全球事件"] == []
                        or score(major,1)[0] >= 60)
        self.assertLess(score(fluff,8)[0],35)

    def test_official_feeds_are_present_and_broken_404_sources_gone(self):
        feeds=json.loads(Path(__file__).with_name("feeds.json").read_text())
        enabled=[f for group in feeds["feeds"].values() for f in group if not f.get("disabled")]
        urls={x["url"] for x in enabled}
        self.assertIn("https://www.sec.gov/news/pressreleases.rss",urls)
        self.assertIn("https://www.ecb.europa.eu/rss/press.html",urls)
        self.assertFalse(any("rssindex" in u or "feedbuilder" in u for u in urls))
        self.assertFalse(any(f["name"]=="VentureBeat" for f in enabled))

    def test_secondary_parser_reuses_supplied_html_without_download(self):
        import newspaper
        with patch.object(newspaper,"article",return_value=Mock(text="Original extracted factual reporting")) as parse:
            result=newspaper4k_from_html("https://news.example/story","<html>story</html>")
        self.assertEqual(result,"Original extracted factual reporting")
        self.assertEqual(parse.call_args.kwargs["input_html"],"<html>story</html>")
        self.assertEqual(parse.call_count,1)

    def test_secondary_parser_used_only_when_primary_body_short(self):
        article=a("Central bank report released",11)
        response=Mock(status_code=200,text="<html>source article</html>",
                      headers={"Content-Type":"text/html"})
        long_body="A national central bank published the final terms of the decision. "*30
        with patch.object(reader.requests,"get",return_value=response), \
             patch.object(reader.trafilatura,"extract",return_value="Not enough text"), \\
             patch.object(reader,"newspaper4k_from_html",return_value=long_body) as fallback:
            result=reader.fetch_reading(article,min_chars=180,max_chars=2100)
        self.assertIsNotNone(result)
        self.assertEqual(result["extraction_engine"],"newspaper4k_fallback")
        fallback.assert_called_once()

    def test_paywall_text_rejected_even_by_secondary_parser(self):
        article=a("Central bank report released",12)
        response=Mock(status_code=200,text="<html>subscription</html>",
                      headers={"Content-Type":"text/html"})
        fallback_text="Subscribe to continue reading the article. " * 18
        with patch.object(reader.requests,"get",return_value=response), \
             patch.object(reader.trafilatura,"extract",return_value=""), \\
             patch.object(reader,"newspaper4k_from_html",return_value=fallback_text):
            self.assertIsNone(reader.fetch_reading(article,min_chars=180,max_chars=2000))

    def test_strong_primary_does_not_call_secondary(self):
        article=a("US Congress approves national regulation",13)
        response=Mock(status_code=200,text="<html>public</html>",
                      headers={"Content-Type":"text/html"})
        text="This is the complete important public account of a government rule. "*24
        with patch.object(reader.requests,"get",return_value=response), \
             patch.object(reader.trafilatura,"extract",return_value=text), \\
             patch.object(reader,"newspaper4k_from_html") as fallback:
            result=reader.fetch_reading(article,min_chars=180,max_chars=2100)
        self.assertEqual(result["extraction_engine"],"trafilatura")
        fallback.assert_not_called()

if __name__=="__main__":
    unittest.main()
