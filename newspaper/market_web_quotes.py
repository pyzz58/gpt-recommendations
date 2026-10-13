"""Conservative public HTML backup for major U.S. stock index quotations.

This adapter reads only public, visible Google Finance quote pages. It does not
use hidden APIs, paid services, browser automation, session spoofing or bypass
CAPTCHAs. Reject challenge pages, stale quotes, redirects and missing timestamps.
A post-close *web quote* is NOT labeled an official exchange closing price.
"""
from __future__ import annotations

import datetime as dt
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

LOG = logging.getLogger("newspaper.market_web_quotes")
NY = ZoneInfo("America/New_York")
QUOTE_PAGES = {
    "SP500": (".INX:INDEXSP", "S&P 500"),
    "NASDAQCOM": (".IXIC:INDEXNASDAQ", "Nasdaq Composite"),
    "DJIA": (".DJI:INDEXDJX", "Dow Jones Industrial Average"),
}
MONTHS = {m: i for i, m in enumerate(
    ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
     "Aug", "Sep", "Oct", "Nov", "Dec"), 1)}
STAMP = re.compile(
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
    r"(\d{1,2}),\s+(\d{1,2}:\d{2}(?::\d{2})?)\s*"
    r"(AM|PM)\s+GMT([+-]\d{1,2})(?::?(\d{2}))?\b",
    re.I,
)
PRICE = re.compile(r"^\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?$|^\d{1,7}(?:\.\d{1,2})?$")


def _timestamp(text, now):
    match = STAMP.search(text)
    if not match:
        return None
    month, day, clock, ampm, offset_hour, offset_minute = match.groups()
    clock_parts = list(map(int, clock.split(":")))
    hour = clock_parts[0] % 12 + (12 if ampm.upper() == "PM" else 0)
    minute = clock_parts[1]
    second = clock_parts[2] if len(clock_parts) > 2 else 0
    hours = int(offset_hour)
    mins = int(offset_minute or 0)
    if abs(hours) > 12 or mins >= 60:
        return None
    fixed = dt.timezone(dt.timedelta(
        minutes=(1 if hours >= 0 else -1) * (abs(hours)*60+mins)))
    ny_now = now.astimezone(NY)
    possible = []
    for year in (ny_now.year-1, ny_now.year, ny_now.year+1):
        try:
            stamp = dt.datetime(year, MONTHS[month.title()], int(day),
                                hour, minute, second, tzinfo=fixed)
            # US quote pages should report a valid NY offset, not another market.
            ny_stamp = stamp.astimezone(NY)
            if ny_stamp.utcoffset() == fixed.utcoffset(stamp):
                possible.append(ny_stamp)
        except ValueError:
            pass
    eligible = [t for t in possible if
                dt.timedelta(minutes=-5) <= now.astimezone(NY)-t <= dt.timedelta(days=7)]
    return min(eligible, key=lambda t: abs((now.astimezone(NY)-t).total_seconds())) if eligible else None


def parse_google_finance_page(raw, series, now):
    """Return a precisely labeled quote, or None; never extrapolate values."""
    if series not in QUOTE_PAGES or now.tzinfo is None:
        raise ValueError("Unknown series or naive timestamp")
    symbol, title = QUOTE_PAGES[series]
    soup = BeautifulSoup(raw or "", "html.parser")
    for tag in soup(("script", "style", "noscript")):
        tag.decompose()
    summary = " ".join(soup.stripped_strings).replace("\u202f", " ").replace("\xa0", " ")
    # Verify the instrument identity near the quote header, not related assets.
    header = summary[:900]
    if (title.lower() not in header.lower()
            or symbol.lower() not in header.lower()
            or "Before you continue" in header or "unusual traffic" in header.lower()):
        return None
    price_tag = soup.select_one("div.YMlKec.fxKbKc, span.YMlKec.fxKbKc")
    if price_tag is None:
        return None
    price_text = price_tag.get_text(strip=True)
    if not PRICE.fullmatch(price_text):
        return None
    value = float(price_text.replace(",", ""))
    if not 100 <= value <= 1000000:
        return None
    # Restrict matching to the first part of page: avoids old story timestamps.
    observed = _timestamp(summary[:1800], now)
    if observed is None:
        return None
    post_session = observed.time() >= dt.time(16, 15)
    # A post-session quote can be displayed, but is NOT exchange-certified EOD.
    observation_type = ("post_session_web_quote" if post_session
                        else "intraday_web_quote")
    url = "https://www.google.com/finance/quote/" + symbol + "?hl=en"
    return {
        "series": series,
        "name": {"SP500": "标普500", "NASDAQCOM": "纳斯达克综合指数",
                 "DJIA": "道琼斯工业指数"}[series],
        "value": value,
        "as_of": observed.date().isoformat(),
        "observed_at_ny": observed.isoformat(),
        "previous": None,
        "change_percent": None,
        "source": "Google Finance public HTML quotation",
        "source_url": url,
        "observation_type": observation_type,
        "stale": False,
    }


def fetch_public_index_quotes(now, getter=None):
    """Fetch each index once without cookies/UA circumvention or retries."""
    if now.tzinfo is None:
        raise ValueError("An aware time is required")
    def one(pair):
        series, (symbol, _) = pair
        url = "https://www.google.com/finance/quote/" + symbol + "?hl=en"
        try:
            response = (getter or requests.get)(
                url, timeout=10,
                headers={"User-Agent": "PersonalNewspaper/1.0 (public quotes)"})
            response.raise_for_status()
            location = urlparse(getattr(response, "url", url))
            if location.hostname != "www.google.com":
                LOG.warning("Google Finance %s redirected away from public quote page", series)
                return None
            result = parse_google_finance_page(response.text, series, now)
            if result is None:
                LOG.warning("Google Finance %s: public HTML quote/date unavailable or stale", series)
            return result
        except (requests.RequestException, ValueError, TypeError) as exc:
            LOG.warning("Google Finance %s unavailable (%s)", series, type(exc).__name__)
            return None

    with ThreadPoolExecutor(max_workers=3) as pool:
        return [v for v in pool.map(one, QUOTE_PAGES.items()) if v]
