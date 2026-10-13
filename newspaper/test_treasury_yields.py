"""Official Treasury daily par-yield XML fallback regression tests."""
import datetime as dt
import unittest
from zoneinfo import ZoneInfo

from market_snapshot import parse_treasury_yield_xml, fetch_treasury_yields

NY = ZoneInfo("America/New_York")
XML = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"
      xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">
 <entry><content><m:properties>
  <d:NEW_DATE>2026-10-09T00:00:00</d:NEW_DATE>
  <d:BC_2YEAR>3.51</d:BC_2YEAR><d:BC_10YEAR>4.12</d:BC_10YEAR>
 </m:properties></content></entry>
 <entry><content><m:properties>
  <d:NEW_DATE>2026-10-12T00:00:00</d:NEW_DATE>
  <d:BC_2YEAR>3.54</d:BC_2YEAR><d:BC_10YEAR>4.16</d:BC_10YEAR>
 </m:properties></content></entry>
 <entry><content><m:properties>
  <d:NEW_DATE>2026-10-13T00:00:00</d:NEW_DATE>
  <d:BC_2YEAR>3.98</d:BC_2YEAR><d:BC_10YEAR>4.77</d:BC_10YEAR>
 </m:properties></content></entry>
</feed>
"""


class TreasuryYieldTests(unittest.TestCase):
    def test_uses_only_published_completed_daily_observations(self):
        # 13:00 New York: same-day observation is not a completed session.
        when = dt.datetime(2026, 10, 13, 13, 0, tzinfo=NY)
        out = parse_treasury_yield_xml(XML, when)
        self.assertEqual({p["series"] for p in out}, {"DGS2", "DGS10"})
        self.assertTrue(all(p["as_of"] == "2026-10-12" for p in out))
        self.assertEqual({p["series"]: p["value"] for p in out},
                         {"DGS2": 3.54, "DGS10": 4.16})
        self.assertTrue(all(p["source"].startswith("US Treasury") for p in out))
        self.assertTrue(all(p["change_percent"] is None for p in out))

    def test_rejects_stale_and_invalid_data(self):
        when = dt.datetime(2026, 10, 22, 13, 0, tzinfo=NY)
        self.assertEqual(parse_treasury_yield_xml(XML, when), [])
        invalid_xml = XML.replace("3.54", "-100").replace("4.16", "500")
        out = parse_treasury_yield_xml(invalid_xml, dt.datetime(2026, 10, 13, 13, 0, tzinfo=NY))
        self.assertEqual({row["as_of"] for row in out}, {"2026-10-09"})

    def test_bad_xml_fails_closed(self):
        class Response:
            content = b"<html>not treasury data"
            def raise_for_status(self):
                pass
        got = fetch_treasury_yields(
            dt.datetime(2026, 10, 13, tzinfo=dt.timezone.utc),
            getter=lambda *args, **kwargs: Response())
        self.assertEqual(got, [])


if __name__ == "__main__":
    unittest.main()
