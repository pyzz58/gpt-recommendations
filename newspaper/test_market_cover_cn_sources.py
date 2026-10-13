"""US-equities-first and new CN publishers: deterministic regressions, no API keys."""
import datetime as dt
import json
import unittest
from unittest.mock import Mock,patch
from zoneinfo import ZoneInfo

from market_snapshot import parse_fred_csv, get_market_snapshot
from newsroom import SECTIONS,prepare_pool,select_readable,sections,market_theme
from digest import bilingualize, fetch_one, edition_window
from chinese_publications import _day_links,fetch_publication
from source_quality import newsworthiness
from clippings import build_clippings_html


def item(title,i):
    return {"title":title,"url":f"https://source{i}.org/article/{i}",
            "summary":"Editorial report","source":f"Outlet {i}",
            "date":dt.datetime(2026,10,13,tzinfo=dt.timezone.utc)}

class MarketAndChineseTests(unittest.TestCase):
    def setUp(self):
        self.bj=ZoneInfo("Asia/Shanghai")

    def test_market_is_first_with_five_slots(self):
        self.assertEqual(list(SECTIONS)[0],"美股市场与机构观察")
        self.assertEqual(SECTIONS["美股市场与机构观察"],5)
        self.assertEqual(SECTIONS["中国与美国"],3)

    def test_market_breadth_classes(self):
        titles=[
            "S&P 500 closes higher as Nasdaq and Dow Jones diverge",
            "SEC announces new US securities exchange reporting rule",
            "Treasury yield curve and Federal Reserve rate decision",
            "Wall Street company quarterly earnings results and guidance",
            "US ETF institutional holdings and fund flows rotation",
        ]
        batch=[item(title,i) for i,title in enumerate(titles)]
        self.assertTrue(all("美股市场与机构观察" in sections(a) for a in batch))
        pool=prepare_pool(batch)
        enriched={a["url"]:{**a,"reading_en":"verified text "*85}
                  for block in pool.values() for a in block}
        selected,_=select_readable(pool,enriched)
        self.assertEqual(len(selected["美股市场与机构观察"]),5)
        themes={market_theme(a) for a in selected["美股市场与机构观察"]}
        self.assertGreaterEqual(len(themes),3)

    def test_chinese_coverage_and_noise_gate(self):
        a=item("中国人民银行发布货币政策报告",50)
        self.assertIn("中国与美国",sections(a))
        self.assertIn("全球宏观与金融政策",sections(a))
        b=item("36氪报道人工智能企业完成重大并购",51)
        self.assertIn("创业、商业与企业竞争",sections(b))
        self.assertFalse(newsworthiness(item("明星恋情八卦和新品种草",52))["eligible"])

    def test_fred_prices_have_dates_and_no_lookahead(self):
        csv="DATE,SP500,NASDAQCOM,DJIA,VIXCLS,DGS2,DGS10\n"
        csv+="2026-10-08,6700,22000,48000,19,3.4,4.2\n"
        csv+="2026-10-09,6750,22300,48100,18,3.3,4.1\n"
        csv+="2026-10-14,9999,9999,9999,99,99,99\n"
        values=parse_fred_csv(csv,dt.date(2026,10,13))
        self.assertEqual(len(values),6)
        sp=next(v for v in values if v["symbol"]=="SP500")
        self.assertEqual(sp["observation_date"],"2026-10-09")
        self.assertEqual(sp["value"],6750)
        self.assertEqual(sp["change_pct"],0.75)
        yield10=next(v for v in values if v["symbol"]=="DGS10")
        self.assertEqual(yield10["kind"],"yield")
        self.assertNotIn("change_pct",yield10)

    def test_failed_prices_are_never_fabricated(self):
        http=Mock(side_effect=ValueError("no public data"))
        snap=get_market_snapshot(dt.datetime(2026,10,14,1,tzinfo=self.bj),http_get=http)
        self.assertFalse(snap["available"])
        html,_=build_clippings_html({"美股市场与机构观察":[]},
                                     dt.date(2026,10,14),market_snapshot=snap)
        self.assertIn("不展示未经核实的指数数值",html)

    def test_source_lists_include_four_and_institutional(self):
        from pathlib import Path
        settings=json.loads(Path(__file__).with_name("feeds.json").read_text())
        feeds=[f for arr in settings["feeds"].values() for f in arr]
        names={f["name"] for f in feeds}
        for expected in ("36氪-综合","新华网-时政","人民日报海外版","雪球专刊",
                         "US Treasury Auction Results","US BLS Economic Releases"):
            self.assertIn(expected,names)
        self.assertEqual(settings["edition_target"]["us_market_cover"]["first_section"],True)

    def test_snowball_opinion_kept_distinct_from_exchange_facts(self):
        source=item("雪球专刊讨论美股投资哲学",60)
        source["source_kind"]="investment_opinion"
        self.assertNotIn("中国与美国",sections(source))

    def test_chinese_source_uses_original_and_offline_english_translation(self):
        translator=Mock(translate=lambda s:"中文译文")
        reverse=Mock(translate=lambda s:"English translation.")
        a={"title":"中国经济发展报告","reading_en":"中国经济发布新数据。","language":"zh",
           "source":"新华网","date":dt.datetime(2026,10,13,tzinfo=self.bj)}
        with patch("digest.english_parser",return_value=Mock()):
            result=bilingualize({"中国与美国":[a]},translator,reverse)["中国与美国"][0]
        self.assertEqual(result["title_zh"],"中国经济发展报告")
        self.assertEqual(result["bilingual_pairs"][0]["zh"],"中国经济发布新数据。")
        self.assertEqual(result["bilingual_pairs"][0]["en"],"English translation.")
        self.assertEqual(result["editing_mode"],"original_chinese_with_machine_english_translation")

    def test_preserve_0100_beijing_reporting(self):
        start,end,_=edition_window(dt.datetime(2026,10,14,1,30,tzinfo=self.bj))
        self.assertEqual(end-start,dt.timedelta(hours=24))
        self.assertEqual(start.hour,1)

if __name__=="__main__":unittest.main()
