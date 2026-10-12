"""V0.5 editorial PDF / source / grammar / SMTP integration regression tests."""
import datetime as dt
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from pypdf import PdfReader
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import digest
import print_report

class PrintReportTests(unittest.TestCase):
    def setUp(self):
        self.day = dt.date(2026, 10, 11)
        self.when = dt.datetime(2026, 10, 11, 13, tzinfo=dt.timezone.utc)
        self.article = {
            "title": "Company has raised funds",
            "title_zh": "公司宣布完成融资",
            "category": "创业与商业模式",
            "source": "EXAMPLE OUTLET",
            "url": "https://example.org/story",
            "date": self.when,
            "reading_en": "The company has raised funds to expand its medical research.",
            "reading_zh": "该公司已筹集资金以扩大医学研究。",
            "bilingual_pairs": [{
                "en": "The company has raised funds to expand its medical research.",
                "zh": "该公司已筹集资金以扩大医学研究。",
                "paragraph_id":0,
            }],
            "grammar_lessons": [{
                "type":"present_perfect",
                "title":"现在完成时",
                "sentence_en": "The company has raised funds to expand its medical research.",
                "explanation":"表示过去发生的动作与现在有关。",
                "pattern":"has + 过去分词"
            }]
        }
        self.grouped = {"创业与商业模式":[self.article], "医疗与科学":[]}

    def test_main_body_has_no_raw_article_or_old_tool_labels(self):
        page,plain = print_report.build_editorial_html(self.grouped,self.day)
        self.assertIn("全球形势秘书简报", page)
        self.assertIn("编者导语", page)
        self.assertIn("英语阅读附录", page)
        self.assertNotIn("英文标题 · English title", page)
        self.assertNotIn("事实材料 · ", page)
        self.assertNotIn("Grammar Focus", page)
        self.assertNotIn("重点单词", page)
        # English appears only in appendix, after analysis.
        self.assertLess(page.index("公司宣布完成融资"), page.index("The company"))
        self.assertIn('<span class="grammar-mark">has<sup>1</sup></span>', page)
        self.assertIn("1. has</strong>", page)
        self.assertNotIn("The company has raised funds to expand its medical research.</strong>", page)
        self.assertIn("The company has raised funds", plain)
        self.assertIn("该公司已筹集资金", plain)

    def test_no_source_fabrication_for_empty_domain(self):
        page, _ = print_report.build_editorial_html(self.grouped,self.day)
        self.assertIn("未取得足够可验证且正文可读的该领域报道", page)
        self.assertIn("不做今日趋势判断", page)

    def test_pdf_bytes_and_searchable_chinese(self):
        page,_ = print_report.build_editorial_html(self.grouped,self.day)
        with tempfile.TemporaryDirectory() as d:
            path = print_report.write_pdf(page,Path(d)/"global-briefing.pdf")
            self.assertGreater(path.stat().st_size,4000)
            self.assertEqual(path.read_bytes()[:5], b"%PDF-")
            reader = PdfReader(str(path))
            self.assertGreaterEqual(len(reader.pages),2)
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
            self.assertIn("全球形势",text)
            self.assertIn("公司宣布完成融资",text)
            self.assertIn("The company",text)

    def test_smtp_contains_actual_pdf_attachment(self):
        with tempfile.TemporaryDirectory() as d:
            pdf = Path(d)/"report.pdf"
            pdf.write_bytes(b"%PDF-" + b"x"*6000)
            smtp = MagicMock()
            smtp.__enter__.return_value = smtp
            env={
                "SMTP_FROM":"sender@qq.com",
                "SMTP_PASSWORD":"example-auth-code-not-real",
                "NEWSPAPER_TO":"receiver@qq.com",
            }
            with patch.dict(os.environ,env), patch.object(digest.smtplib,"SMTP_SSL",return_value=smtp):
                digest.send_email("日报","<p>见附件</p>","见附件",pdf_attachment=pdf)
            args,kw=smtp.send_message.call_args
            message=args[0]
            attachments=list(message.iter_attachments())
            self.assertEqual(len(attachments),1)
            self.assertEqual(attachments[0].get_content_type(),"application/pdf")
            self.assertEqual(attachments[0].get_filename(),"report.pdf")

    def test_missing_pdf_must_not_send_anything(self):
        with patch.dict(os.environ,{
            "SMTP_FROM":"sender@qq.com",
            "SMTP_PASSWORD":"example-auth-code-not-real",
            "NEWSPAPER_TO":"receiver@qq.com",
        }),patch.object(digest.smtplib,"SMTP_SSL") as smtp:
            with self.assertRaises(RuntimeError):
                digest.send_email("日报","<p>example</p>","example",pdf_attachment="/tmp/nonexistent-report-18d822.pdf")
            smtp.assert_not_called()

if __name__ == "__main__":
    unittest.main()
