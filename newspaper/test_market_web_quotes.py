"""Public Google Finance HTML fallback is conservative and date-verified."""
import datetime as dt
import unittest
from zoneinfo import ZoneInfo

from market_web_quotes import parse_google_finance_page, fetch_public_index_quotes

NY = ZoneInfo("America/New_York")


def page(symbol=".INX:INDEXSP", title="S&P 500", price="7,765.43",
         stamped="Oct 13, 12:59:13 PM GMT-4"):
    return (f'<html><body><h1>{title}</h1><div>{symbol}</div>'
            f'<div class="YMlKec fxKbKc">{price}</div>'
            f'<p>{stamped}</p><p>Related assets</p></body></html>')


class PublicWebMarketTests(unittest.TestCase):
    def test_dated_intraday_quote_is_not_mislabeled_close(self):
        now = dt.datetime(2026, 10, 13, 13, 5, tzinfo=NY)
        data = parse_google_finance_page(page(), "SP500", now)
        self.assertIsNotNone(data)
        self.assertEqual(data["value"], 7765.43)
        self.assertEqual(data["as_of"], "2026-10-13")
        self.assertEqual(data["observation_type"], "intraday_web_quote")
        self.assertIsNone(data["change_percent"])
        self.assertIn("Google Finance", data["source"])

    def test_post_session_web_quote_is_still_not_certified_close(self):
        now = dt.datetime(2026, 10, 13, 17, 5, tzinfo=NY)
        data = parse_google_finance_page(
            page(stamped="Oct 13, 4:59:13 PM GMT-4"), "SP500", now)
        self.assertEqual(data["observation_type"], "post_session_web_quote")

    def test_rejects_stale_wrong_symbol_or_unverifiable_quote(self):
        now = dt.datetime(2026, 10, 13, 13, 5, tzinfo=NY)
        self.assertIsNone(parse_google_finance_page(
            page(stamped="Oct 2, 4:59:13 PM GMT-4"), "SP500", now))
        self.assertIsNone(parse_google_finance_page(
            page(symbol=".DJI:INDEXDJX"), "SP500", now))
        self.assertIsNone(parse_google_finance_page(
            page(stamped="October 13 sometime"), "SP500", now))
        self.assertIsNone(parse_google_finance_page(
            page(price="n/a"), "SP500", now))
        self.assertIsNone(parse_google_finance_page(
            "<html><body>Before you continue to Google</body></html>",
            "SP500", now))

    def test_redirect_outside_expected_host_fails_closed(self):
        class Response:
            url = "https://example.invalid/finance"
            text = page()
            def raise_for_status(self):
                pass
        result = fetch_public_index_quotes(
            dt.datetime(2026, 10, 13, 18, 0, tzinfo=dt.timezone.utc),
            getter=lambda *args, **kwargs: Response())
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
