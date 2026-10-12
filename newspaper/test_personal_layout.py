"""Verify bilingual A5 PDF assembly using synthetic, permitted test fixtures."""
import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path
from pypdf import PdfReader
sys.path.insert(0,str(Path(__file__).resolve().parent))
from clippings import build_clippings_html, mail_cover_clippings
from print_report import write_pdf

class NewsLayoutTests(unittest.TestCase):
    def test_original_line_below_translation_and_pdf(self):
        article={
          "category":"全球新闻","source":"TEST OUTLET","title":"Two short events",
          "title_zh":"两则简短事件",
          "date":dt.datetime(2026,10,11,tzinfo=dt.timezone.utc),
          "reading_abbreviated":False,
          "bilingual_pairs":[
            {"en":"The market opened.","zh":"市场开盘了。","paragraph_id":0},
            {"en":"Investors watched.","zh":"投资者在关注。","paragraph_id":0},
            {"en":"The company responded.","zh":"公司作出了回应。","paragraph_id":1},
          ],"grammar_lessons":[]
        }
        grouped={"全球新闻":[article]}
        page,plain=build_clippings_html(grouped,dt.date(2026,10,11))
        self.assertLess(page.index("The market opened."),page.index("市场开盘了。"))
        self.assertLess(page.index("市场开盘了。"),page.index("Investors watched."))
        self.assertIn("The company responded.",page)
        self.assertNotIn("阅读全文",page)
        self.assertNotIn("编者导语",page)
        with tempfile.TemporaryDirectory() as d:
            path=write_pdf(page,Path(d)/"preview.pdf")
            reader=PdfReader(str(path))
            doc="\n".join(p.extract_text() or "" for p in reader.pages)
            self.assertIn("全球新闻",doc)
            self.assertIn("Investors watched.",doc)
        body,text=mail_cover_clippings(dt.date(2026,10,11),grouped)
        self.assertIn("PDF",body)

if __name__=="__main__":
    unittest.main()
