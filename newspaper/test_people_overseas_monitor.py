"""People's Daily Overseas Edition monitoring safety and date regressions."""
import unittest
from people_overseas import parse_edition


class OverseasEditionTests(unittest.TestCase):
    def test_dated_layout_url_and_article_link(self):
        html = '<html><body><a href="../content/202610/13/content_123456.html">这是一个超过八个字的新闻标题</a></body></html>'
        data = parse_edition(html, "https://paper.people.com.cn/rmrbhwb/pc/layout/202610/13/node_01.html")
        self.assertEqual(data["issue_date"], "2026-10-13")
        self.assertEqual(len(data["items"]), 1)
        self.assertFalse(data["issue_date_is_publication_timestamp"])

    def test_malicious_domain_is_not_accepted(self):
        html = '<html><body>2026年10月13日 <a href="https://people.com.cn.attacker.invalid/content_123.html">这是一条长度足够的伪造文章标题</a></body></html>'
        data = parse_edition(html)
        self.assertEqual(data["items"], [])


if __name__ == "__main__":
    unittest.main()
