"""Offline tests for immutable edition bundles and SMTP acceptance handling."""
import datetime as dt
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
from prepared_delivery import write_bundle, read_bundle, send_bundle, BEIJING


class DummySMTP:
    def __init__(self,*args,**kwargs):
        self.messages=[]
        self.refuse={}
    def __enter__(self): return self
    def __exit__(self,*args): return None
    def login(self,*args): pass
    def send_message(self,msg):
        self.messages.append(msg)
        return self.refuse


class PreparedDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name)/"ready"
        self.pdf=Path(self.temp.name)/"report.pdf"
        self.pdf.write_bytes(b"%PDF-1.4\n"+b"x"*130)
        self.day=dt.date(2026,10,14)
        self.subject="全球新闻选编｜2026-10-14 00:00截稿"
        write_bundle(self.directory,self.day,self.subject,
                     "<html>"+("来源核实报道"*35)+"</html>","完整新闻报道"*45,self.pdf)

    def test_bundle_integrity(self):
        subject, files=read_bundle(self.directory,self.day)
        self.assertEqual(subject,self.subject)
        self.assertTrue(files["edition.pdf"].startswith(b"%PDF-"))
        self.assertIn(b"mail.html",str(sorted(files)).encode())

    def test_brief_cover_is_allowed_when_commentary_unavailable(self):
        short_text = "全球新闻选编｜2026-10-14。本期报道详见附件 PDF。"
        write_bundle(self.directory, self.day, self.subject,
                     "<html><body><h2>全球新闻选编</h2><p>今日报道请见PDF附件。</p></body></html>",
                     short_text, self.pdf)
        _, files = read_bundle(self.directory, self.day)
        self.assertIn("详见附件", files["mail.txt"].decode("utf-8"))

    def test_tamper_detected(self):
        (self.directory/"mail.txt").write_text("altered",encoding="utf8")
        with self.assertRaises(ValueError):
            read_bundle(self.directory,self.day)

    def test_wrong_edition_cannot_send(self):
        with self.assertRaises(ValueError):
            read_bundle(self.directory,dt.date(2026,10,15))

    def test_smtp_acceptance_and_message_id(self):
        smtp=DummySMTP()
        now=dt.datetime(2026,10,14,1,2,tzinfo=BEIJING)
        with patch.dict(os.environ,{"SMTP_FROM":"sender@example.com",
                     "SMTP_PASSWORD":"dummy","NEWSPAPER_TO":"reader@example.com"}):
            message_id=send_bundle(self.directory,self.day,now=now,
                                  smtp_factory=lambda *a,**kw:smtp)
        self.assertIn("newspaper-20261014",message_id)
        self.assertEqual(len(smtp.messages),1)
        self.assertEqual(smtp.messages[0]["Subject"],self.subject)

    def test_partial_recipient_refusal_is_not_a_success(self):
        smtp=DummySMTP()
        smtp.refuse={"reader@example.com":(550,b"refused")}
        now=dt.datetime(2026,10,14,1,2,tzinfo=BEIJING)
        with patch.dict(os.environ,{"SMTP_FROM":"sender@example.com",
                      "SMTP_PASSWORD":"dummy","NEWSPAPER_TO":"reader@example.com"}):
            with self.assertRaises(RuntimeError):
                send_bundle(self.directory,self.day,now=now,
                            smtp_factory=lambda *a,**kw:smtp)

    def test_send_early_is_refused_without_smtp(self):
        with self.assertRaises(RuntimeError):
            send_bundle(self.directory,self.day,
                        now=dt.datetime(2026,10,14,0,59,tzinfo=BEIJING))


if __name__=="__main__":
    unittest.main()
