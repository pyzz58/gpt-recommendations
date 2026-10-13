"""Regression checks for dated market-source provenance in the daily briefing."""
import datetime as dt
import unittest
from unittest.mock import patch

from market_snapshot import fetch_market_snapshot


class FakeResponse:
    headers = {"Content-Type": "text/csv"}

    def __init__(self, body):
        self.text = body

    @property
    def content(self):
        return self.text.encode('utf-8')

    def raise_for_status(self):
        pass


class MarketProvenanceTests(unittest.TestCase):
    def test_fred_and_stooq_are_not_mislabeled(self):
        when = dt.datetime(2026, 10, 13, 20, 0, tzinfo=dt.timezone.utc)

        def fake_get(url, params=None, **kwargs):
            if "fredgraph.csv" in url:
                if params["id"] == "DGS10":
                    return FakeResponse("observation_date,DGS10\n2026-10-12,4.10\n")
                return FakeResponse("observation_date," + params["id"] + "\n")
            if "stooq.com" in url:
                ticker = params["s"]
                if ticker == "^spx":
                    return FakeResponse("Date,Close\n2026-10-09,6700\n2026-10-12,6710\n")
                return FakeResponse("Date,Close\n")
            if "home.treasury.gov" in url:
                return FakeResponse('<feed xmlns="http://www.w3.org/2005/Atom" />')
            if "google.com/finance/quote/" in url:
                return FakeResponse("<html><body>public quote unavailable</body></html>")
            raise AssertionError("Unexpected external request")

        with patch("market_snapshot.requests.get", side_effect=fake_get):
            result = fetch_market_snapshot(now=when)
        self.assertEqual(result["backup_observations"], 1)
        self.assertEqual(result["sources"], ["FRED", "Stooq"])
        self.assertIn("Stooq", result["warning"])
        self.assertEqual(len(result["values"]), 2)
        self.assertTrue(all(row.get("as_of") and row.get("source_url") for row in result["values"]))

    def test_missing_values_are_not_invented(self):
        when = dt.datetime(2026, 10, 13, 20, 0, tzinfo=dt.timezone.utc)

        def fake_get(url, params=None, **kwargs):
            return FakeResponse("Date,Close\n" if "stooq" in url else "observation_date,SP500\n")

        with patch("market_snapshot.requests.get", side_effect=fake_get):
            result = fetch_market_snapshot(now=when)
        self.assertFalse(result["values"])
        self.assertFalse(result["sources"])
        self.assertEqual(result["backup_observations"], 0)
        self.assertEqual(len(result["missing"]), 6)


if __name__ == "__main__":
    unittest.main()
