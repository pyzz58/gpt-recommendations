"""Acceptance: NEVER substitute source articles with invented English or boilerplate.
PDF uses original-worded sentences and directly adjacent source translations,
only within explicit reuse permissions or a conservative short-quote limit.
"""
import datetime as dt
import sys
import unittest
from pathlib import Path
from pypdf import PdfReader
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parent))
from clippings import (
    attach_rights, approved_full_text, _choose_original_lines,
    build_clippings_html, mail_cover_clippings, MAX_UNLICENSED_WORDS,
)
from print_report import write_pdf


class OriginalClippingTests(unittest.TestCase):
    def setUp(self):
        date=dt.datetime(2026,10,11,14,tzinfo=dt.timezone.utc)
        self.item={
            "source":"EXAMPLE RIGHTS TEST ONLY",
            "category":"全球新闻",
            "url":"https://example.com/news/2026/001",
            "title":"Original reporting from journalist",
            "title_zh":"记者写的原始报道",
            "date":date,
            "reading_abbreviated":False,
            "bilingual_pairs":[
                {"en":"Original sentence one gives the opening facts exactly as written.", "zh":"原句一是记者所写的开头事实。", "paragraph_id":0},
                {"en":"A second original sentence offers background that matters to the reader.", "zh":"原句二为读者提供重要背景。", "paragraph_id":0},
                {"en":"Finally, a separate paragraph expands the investigation further.", "zh":"最后，另一段深入调查。", "paragraph_id":1},
            ],
            "grammar_lessons":[
                {"type":"present_perfect","sentence_en":"Original sentence one gives the opening facts exactly as written.","explanation":"现在完成时结构"}
            ],
        }
        self.day=date.date()

    def test_default_requires_real_permission(self):
        output=attach_rights({"全球新闻":[self.item]}, {})
        item=output["全球新闻"][0]
        self.assertFalse(approved_full_text(item))
        lines,full=_choose_original_lines(item)
        self.assertFalse(full)
        self.assertEqual(lines,[self.item["bilingual_pairs"][0],self.item["bilingual_pairs"][1]])
        self.assertLessEqual(sum(len(x["en"].split()) for x in lines),MAX_UNLICENSED_WORDS)

    def test_no_orphan_english_ending_and_no_middle_jump(self):
        item=dict(self.item)
        item["bilingual_pairs"]=[
            {"en":"Very long editorial sentence "+"unbroken "+("text "*55)+".","zh":"中文", "paragraph_id":0},
            self.item["bilingual_pairs"][-1],
        ]
        a,b=_choose_original_lines(item)
        self.assertEqual(a,[])
        self.assertFalse(b)

    def test_verified_permission_allows_all_original_with_translations(self):
        licenses={
            "example.com":{
                "evidence_url":"https://example.com/license",
                "allow_full_republication":True,
                "allow_chinese_translation":True,
            }
        }
        item=attach_rights({"全球新闻":[self.item]},licenses)["全球新闻"][0]
        self.assertTrue(approved_full_text(item))
        lines,full=_choose_original_lines(item)
        self.assertTrue(full)
        self.assertEqual(lines,self.item["bilingual_pairs"])
        html,plain=build_clippings_html({"全球新闻":[item]},self.day)
        self.assertIn("记者写的原始报道",html)
        self.assertIn(self.item["bilingual_pairs"][-1]["en"],html)
        self.assertIn(self.item["bilingual_pairs"][-1]["zh"],html)
        self.assertLess(html.index("Original sentence one"),html.index("原句一"))
        self.assertLess(html.index("原句一"),html.index("A second original"))
        self.assertIn("已登记全文和中文翻译使用许可",html)
        self.assertNotIn("编者导语",html)
        self.assertNotIn("顾问观察",html)
        self.assertNotIn("后续应核对",html)
        self.assertNotIn("安全与政策事件的经济影响",html)
        self.assertNotIn("英语阅读附录",html)

    def test_unlicensed_has_only_original_short_quote_and_link(self):
        it=attach_rights({"全球新闻":[self.item]}, {})["全球新闻"][0]
        html,plain=build_clippings_html({"全球新闻":[it]},self.day)
        self.assertIn("Original sentence one gives the opening facts exactly as written.",html)
        self.assertNotIn("Finally, a separate paragraph",html)
        self.assertIn("原始英文短摘",html)
        self.assertIn("阅读全文",html)
        self.assertIn("https://example.com/news/2026/001",html)
        self.assertNotIn("据EXAMPLE RIGHTS TEST ONLY报道",html)
        self.assertNotIn("后续应核对",html)
        self.assertNotIn("以下首先陈述报道中出现的事件",html)

    def test_missing_zh_never_renders_misaligned_pair(self):
        it=dict(self.item)
        it["bilingual_pairs"]=[{"en":"This English has no translation.","zh":"","paragraph_id":0}]
        html,_=build_clippings_html({"全球新闻":[it]},self.day)
        self.assertNotIn("This English has no translation.",html)
        self.assertIn("没有符合短摘限制",html)

    def test_cover_stays_typeset_and_pdf_is_searchable(self):
        it=attach_rights({"全球新闻":[self.item]}, {})["全球新闻"][0]
        page,_=build_clippings_html({"全球新闻":[it]},self.day)
        with tempfile.TemporaryDirectory() as tmp:
            pdf=write_pdf(page,Path(tmp)/"clippings.pdf")
            txt="\n".join(p.extract_text() or "" for p in PdfReader(str(pdf)).pages)
            self.assertIn("全球新闻",txt)
            self.assertIn("Original sentence",txt)
            self.assertIn("原句一",txt)

    def test_email_preface_is_in_email_not_pdf(self):
        it=attach_rights({"全球新闻":[self.item]}, {})["全球新闻"][0]
        html,_=build_clippings_html({"全球新闻":[it]},self.day)
        mail_html,mail_txt=mail_cover_clippings(self.day,{"全球新闻":[it]})
        self.assertNotIn("编者导语",html)
        self.assertIn("PDF",mail_html)
        self.assertIn("未",mail_txt) # no fabricated commentary

if __name__=="__main__":
    unittest.main()
