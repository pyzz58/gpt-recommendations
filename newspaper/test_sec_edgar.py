"""SEC EDGAR new-source negative tests: cutoff, provenance, filing types."""
import datetime as dt
import unittest
from unittest.mock import Mock
from zoneinfo import ZoneInfo
from sec_edgar import parse_submissions,fetch_filings,official_link
from market_headline import market_evidence

BJT=ZoneInfo("Asia/Shanghai")
start=dt.datetime(2026,10,13,0,0,tzinfo=BJT)
end=dt.datetime(2026,10,14,0,0,tzinfo=BJT)

def filing(form="10-Q",when="2026-10-13T11:30:00Z",items=""):
    return {"filings":{"recent":{
        "accessionNumber":["0000320193-26-000020"],
        "form":[form],"filingDate":["2026-10-13"],
        "acceptanceDateTime":[when],"items":[items],
    }}}

class EdgarTests(unittest.TestCase):
    def test_source_link_strict(self):
        self.assertEqual(official_link(320193,"0000320193-26-000020"),
            "https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/0000320193-26-000020-index.htm")
        self.assertIsNone(official_link(320193,"evil"))

    def test_confirmed_notice_not_fake_earnings(self):
        a=parse_submissions(filing(),"AAPL","Apple",320193,start,end)
        self.assertEqual(len(a),1)
        self.assertEqual(a[0]["filing_form"],"10-Q")
        self.assertIn("filing, not the financial results",a[0]["summary"])
        self.assertTrue(a[0]["filing_notice_only"])
        self.assertTrue(market_evidence(a[0])["eligible"])

    def test_skip_unrelated_8k_and_missing_items(self):
        self.assertEqual(parse_submissions(filing("8-K",items="5.02"),
            "AAPL","Apple",320193,start,end),[])
        valid=parse_submissions(filing("8-K",items="2.02,9.01"),
            "AAPL","Apple",320193,start,end)
        self.assertEqual(len(valid),1)
        self.assertTrue(market_evidence(valid[0])["eligible"])

    def test_strict_edition_cutoff_when_utc_and_et_disagree(self):
        self.assertEqual(parse_submissions(
            filing(when="2026-10-13T15:30:00Z"),
            "AAPL","Apple",320193,start,end),[])
        self.assertEqual(parse_submissions(
            filing(when="2026-10-13T10:30:00Z"),
            "AAPL","Apple",320193,start,end).__len__(),1)

    def test_explicit_missing_contact_disables_calls(self):
        getter=Mock(side_effect=AssertionError("network must not run"))
        items,stat=fetch_filings(start,end,getter=getter,contact="")
        self.assertEqual(items,[])
        self.assertEqual(stat["status"],"disabled_missing_contact_email")
        getter.assert_not_called()

    def test_bounded_live_requests_and_partial_failure(self):
        ok=Mock()
        ok.content=b"{}"
        ok.json.return_value=filing()
        ok.raise_for_status.return_value=None
        def getter(url,headers,timeout):
            self.assertEqual(timeout,12)
            self.assertIn("contact@example.org",headers["User-Agent"])
            if "CIK0000789019" in url:
                raise ValueError("unavailable")
            return ok
        rows,status=fetch_filings(start,end,getter=getter,contact="contact@example.org",
                   issuers={"AAPL":("Apple",320193),"MSFT":("Microsoft",789019)})
        self.assertEqual(status["status"],"partial")
        self.assertEqual(status["issuer_success"],1)
        self.assertEqual(len(rows),1)

if __name__=="__main__":
    unittest.main()
