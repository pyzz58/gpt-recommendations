"""Tests of high-value newsroom policy, exact-source editing and translation QA."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from editorial_selection import is_tech_substantive, pick_politics, political_regions
from extractive_editor import trim_extracted_article
from translation_editor import polish_translation

def news(title,score=70,source="Example",summary=""):
    return {"title":title,"summary":summary,"source":source,
            "url":"https://example.org/"+str(abs(hash(title))),
            "importance_score":score}

def dup(item,picked):
    return any(x["url"]==item["url"] for x in picked)

class NewsroomTests(unittest.TestCase):
    def test_no_blade_runner_or_entertainment_promo(self):
        self.assertFalse(is_tech_substantive(news(
            'Prime Video debuts full trailer for Blade Runner 2099 at NYCC',
            summary="The streaming series premieres soon")))
        self.assertFalse(is_tech_substantive(news("Marvel film review and movie trailer")))
        self.assertTrue(is_tech_substantive(news(
            "Researchers demonstrate nuclear fusion plasma reactor breakthrough")))
        self.assertTrue(is_tech_substantive(news(
            "Scientists develop a quantum computing technique in a physics experiment")))
        self.assertTrue(is_tech_substantive(news(
            "AI researchers achieve a new model performance breakthrough")))
        self.assertFalse(is_tech_substantive(news(
            "A TV series actor discusses a new season at Comic Con")))

    def test_politics_keeps_separate_china_and_us_and_three_total(self):
        items=[
            news("Beijing and US governments debate China trade tariff policy",92),
            news("US Congress votes on national security policy",84,"Outlet A"),
            news("China president announces diplomatic treaty",85,"Outlet B"),
            news("European leaders discuss military security treaty",88,"Outlet C"),
            news("Middle East war ceasefire talks enter crucial phase",93,"Outlet D"),
        ]
        selected,report=pick_politics(items,3,[],dup,extra_limit=2)
        self.assertTrue(report["china_covered"])
        self.assertTrue(report["us_covered"])
        self.assertTrue(report["minimum_met"])
        self.assertGreaterEqual(len(selected),3)
        self.assertLessEqual(len(selected),5)
        self.assertEqual(len(set(x["url"] for x in selected)),len(selected))

    def test_insufficient_world_news_does_not_invent(self):
        selected,meta=pick_politics([news("New film trailer premieres")],3,[],dup)
        self.assertEqual(selected,[])
        self.assertFalse(meta["minimum_met"])
        self.assertTrue(meta["political_shortfall"])

    def test_china_unrelated_food_not_politics(self):
        self.assertFalse(political_regions(news("China opens film festival")))
        self.assertTrue(political_regions(news("China government announces foreign trade policy")))

    def test_source_retention_at_least_70_percent_no_paraphrase(self):
        paragraphs=["Intro reports the original important event with details and figures that must stay."]*2
        for i in range(10):
            paragraphs.append("The key policy has changed the costs and the impact on the regional market. "+("A factual description remains here. "*10))
            if i%2==0: paragraphs.append("Subscribe to our newsletter for more of our coverage.")
        article={"reading_en":"\n\n".join(paragraphs)}
        result=trim_extracted_article(article,min_retention=0.70)
        self.assertGreaterEqual(result["retention_rate"],0.70)
        self.assertEqual(result["editing_mode"],"extractive_only")
        original=article["reading_en"].split("\n\n")
        self.assertEqual(result["reading_en"].split("\n\n"),
                         [original[i] for i in result["original_paragraphs_kept"]])

    def test_translation_terminology_and_negation_alert(self):
        out,flags=polish_translation(
            "The Federal Reserve rejected a nuclear fusion clinical trial.",
            "联邦储备拒绝了核融合的临床实验 。")
        self.assertIn("美联储",out)
        self.assertIn("核聚变",out)
        self.assertIn("临床试验",out)
        self.assertNotIn(" 。",out)
        txt,alerts=polish_translation("The government did not approve the new AI project.",
                                      "政府批准了新人工智能项目。")
        self.assertIn("possible_negation_loss",alerts)

if __name__=="__main__":
    unittest.main()
