"""Regression cases taken from a real October 2026 newspaper preview."""
import unittest
from unittest.mock import patch

from newsroom import sections, near_duplicate_titles


class ActualEditionEditorialTests(unittest.TestCase):
    def _classify(self, title, summary):
        item = {"title": title, "summary": summary, "source_language": "en"}
        with patch("newsroom.newsworthiness", return_value={"eligible": True}):
            return sections(item)

    def test_prior_false_stock_frontpage_stories_excluded(self):
        titles = [
            "India's retail inflation jumps to 5.54% in September, above estimates",
            "What does a PhD pay? Data reveal huge gaps across Europe",
            "Trump faces growing backlash over plans to import diesel from Russia",
            "EU to limit Chinese hybrid vehicle imports to 350,000 a year",
        ]
        for title in titles:
            with self.subTest(title=title):
                result = self._classify(title, "Financial markets trade energy company import policy.")
                self.assertNotIn("美股·全球金融市场", result)

    def test_war_ceasefire_does_not_become_frontier_science(self):
        title = "Ukraine says Russia launched strikes hours after Trump announced an energy ceasefire"
        result = self._classify(title, "Russian energy power grid attacks and diplomatic events.")
        self.assertNotIn("科技、能源与前沿科学", result)
        self.assertIn("国际政治与全球事件", result)

    def test_political_adviser_not_entrepreneurship(self):
        title = "Revealed: Nigel Farage adviser had unpublicised role at polling firm"
        result = self._classify(title, "Companies and campaign polling businesses are mentioned.")
        self.assertNotIn("创业、商业与企业竞争", result)

    def test_positive_us_markets_science_and_enterprise_still_qualify(self):
        self.assertIn("美股·全球金融市场", self._classify(
            "S&P 500 rises after Federal Reserve announces policy decision",
            "Stock market reaction to U.S. interest rates."))
        self.assertIn("科技、能源与前沿科学", self._classify(
            "Scientists demonstrate new quantum computing milestone",
            "Researchers make a technology breakthrough."))
        self.assertIn("创业、商业与企业竞争", self._classify(
            "Startup raises $100 million in funding round",
            "Investors back a new company."))

    def test_market_desk_keeps_fed_and_dedicated_finance_feeds(self):
        self.assertIn("美股·全球金融市场", self._classify(
            "Fed announces a rate decision after its policy meeting",
            "U.S. investors await the monetary policy release."))
        sample = {
            "title": "Nvidia quarterly earnings send shares higher",
            "summary": "Technology company reports results.",
            "source": "CNBC Markets",
            "source_language": "en",
        }
        with patch("newsroom.newsworthiness", return_value={"eligible": True}):
            self.assertIn("美股·全球金融市场", sections(sample))

    def test_same_microsoft_ai_regulation_story_discouraged(self):
        self.assertTrue(near_duplicate_titles(
            "AI is less regulated than milk, says Microsoft president",
            "Microsoft president says UK is best placed to drive AI regulation"))
        self.assertFalse(near_duplicate_titles(
            "Microsoft president says UK is best placed to drive AI regulation",
            "New semiconductor export rules reshape global chip manufacturing"))


if __name__ == "__main__":
    unittest.main()
