"""FRED verified daily close snapshot, never an intraday index quote.

Daily edition at 01:00 Beijing occurs during prior US market hours. The
latest FRED close is an earlier completed session; always show as-of dates.
Fail closed for absent, stale, nonnumerical or unverified observations.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import logging
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor
from xml.etree import ElementTree as ET

import requests
from market_web_quotes import fetch_public_index_quotes

SERIES = {
    "SP500": "标普500",
    "NASDAQCOM": "纳斯达克综合指数",
    "DJIA": "道琼斯工业指数",
    "VIXCLS": "VIX波动率",
    "DGS10": "美国10年期国债收益率",
    "DGS2": "美国2年期国债收益率",
}
SOURCE = "https://fred.stlouisfed.org/series/{series}"
LOG = logging.getLogger("newspaper.market_snapshot")


def parse_fred_csv(raw, series, today):
    if series not in SERIES:
        raise ValueError("Unknown FRED series")
    reader = csv.DictReader(io.StringIO(raw))
    if series not in (reader.fieldnames or []):
        return None
    points = []
    for row in reader:
        try:
            day = dt.date.fromisoformat(row.get("observation_date", row.get("DATE", "")))
            value = float(row[series])
            if value == value and day <= today:
                points.append((day, value))
        except (ValueError, TypeError, OverflowError):
            continue
    if not points:
        return None
    points.sort()
    last = points[-1]
    if (today - last[0]).days > 6:
        return None
    previous = points[-2] if len(points) > 1 else None
    return {
        "series": series, "name": SERIES[series],
        "as_of": last[0].isoformat(), "value": last[1],
        "previous": previous[1] if previous else None,
        "change_percent": round((last[1]/previous[1]-1)*100,2)
          if previous and previous[1] else None,
        "source_url": SOURCE.format(series=series),
        "source": "FRED",
        "stale": False,
    }


STOOQ_DAILY = {
    "SP500": "^spx",
    "NASDAQCOM": "^ndq",
    "DJIA": "^dji",
}


def parse_stooq_daily(raw, series, ny_local):
    """Only fully completed New York trading sessions, with explicit dates."""
    if series not in STOOQ_DAILY:
        raise ValueError("Unsupported Stooq index")
    rows = csv.DictReader(io.StringIO(raw))
    if not {"Date", "Close"} <= set(rows.fieldnames or []):
        return None
    cutoff = ny_local.date() if ny_local.time() >= dt.time(16, 15) else ny_local.date() - dt.timedelta(days=1)
    valid = []
    for row in rows:
        try:
            day = dt.date.fromisoformat(row["Date"])
            value = float(row["Close"])
            if 0 < value < 1000000 and value == value and day <= cutoff:
                valid.append((day, value))
        except (ValueError, TypeError, KeyError):
            continue
    if not valid:
        return None
    valid.sort()
    day, value = valid[-1]
    if (cutoff - day).days > 7:
        return None
    prev = valid[-2][1] if len(valid)>1 else None
    return {
        "series": series, "name": SERIES[series],
        "as_of": day.isoformat(), "value": value,
        "previous": prev,
        "change_percent": round((value/prev - 1) * 100, 2) if prev else None,
        "source_url": "https://stooq.com/q/d/?s=" + STOOQ_DAILY[series],
        "source": "Stooq published daily close, not exchange real-time data",
        "stale": False,
    }


def fetch_stooq_completed_closes(now, getter=None):
    """Optional public CSV fallback; never guess an unavailable index."""
    ny_local = now.astimezone(ZoneInfo("America/New_York"))
    end_date = ny_local.date()
    start_date = end_date - dt.timedelta(days=14)
    def one(pair):
        series, ticker = pair
        try:
            response = (getter or requests.get)(
                "https://stooq.com/q/d/l/",
                params={"s": ticker, "i": "d",
                        "d1": start_date.strftime("%Y%m%d"),
                        "d2": end_date.strftime("%Y%m%d")},
                timeout=8, headers={"User-Agent": "PersonalNewspaper/1.0"})
            response.raise_for_status()
            parsed = parse_stooq_daily(response.text, series, ny_local)
            if parsed is None:
                LOG.warning("Stooq %s returned no valid dated CSV (may require API access)", series)
            return parsed
        except (requests.RequestException, ValueError, TypeError) as exc:
            LOG.warning("Stooq %s feed unavailable (%s)", series, type(exc).__name__)
            return None
    with ThreadPoolExecutor(max_workers=3) as pool:
        return [value for value in pool.map(one, STOOQ_DAILY.items()) if value]




TREASURY_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/"
    "interest-rates/pages/xml"
)
TREASURY_FIELDS = {"DGS2": "BC_2YEAR", "DGS10": "BC_10YEAR"}


def parse_treasury_yield_xml(raw, ny_local):
    """Parse Treasury's dated daily *par* yield curve (percent), not bond prices.

    We conservatively use the previous New York day until 16:15 local time,
    never claim an in-progress daily market observation is completed.
    """
    if ny_local.tzinfo is None:
        raise ValueError("Treasury cutoff requires timezone-aware New York time")
    root = ET.fromstring(raw)
    cutoff = (ny_local.date() if ny_local.time() >= dt.time(16, 15)
              else ny_local.date() - dt.timedelta(days=1))
    histories = {code: [] for code in TREASURY_FIELDS}
    atom_entry = "{http://www.w3.org/2005/Atom}entry"
    for entry in root.findall(atom_entry):
        fields = {node.tag.rsplit("}", 1)[-1]: (node.text or "").strip()
                  for node in entry.iter()}
        try:
            day = dt.date.fromisoformat(fields.get("NEW_DATE", "").split("T")[0])
        except ValueError:
            continue
        if day > cutoff:
            continue
        for code, field in TREASURY_FIELDS.items():
            try:
                value = float(fields.get(field, ""))
            except ValueError:
                continue
            if 0 < value < 30 and value == value:
                histories[code].append((day, value))
    results = []
    for code, points in histories.items():
        if not points:
            continue
        points.sort()
        day, value = points[-1]
        if (cutoff - day).days > 7:
            continue
        results.append({
            "series": code, "name": SERIES[code], "as_of": day.isoformat(),
            "value": value,
            "previous": points[-2][1] if len(points) > 1 else None,
            "change_percent": None,  # A yield delta should be in bp, not % of yield.
            "source": "US Treasury official daily par yield curve",
            "source_url": TREASURY_URL + "?data=daily_treasury_yield_curve",
            "stale": False,
        })
    return results


def fetch_treasury_yields(now, getter=None):
    """Official, key-free alternative for missing FRED 2Y and 10Y par yields."""
    ny_local = now.astimezone(ZoneInfo("America/New_York"))
    try:
        response = (getter or requests.get)(
            TREASURY_URL,
            params={"data": "daily_treasury_yield_curve",
                    "field_tdr_date_value_month": ny_local.strftime("%Y%m")},
            timeout=15, headers={"User-Agent": "PersonalNewspaper/1.0"})
        response.raise_for_status()
        values = parse_treasury_yield_xml(response.content, ny_local)
        if not values:
            LOG.warning("US Treasury feed contained no fresh dated 2Y/10Y yield observations")
        return values
    except (requests.RequestException, ET.ParseError, ValueError, TypeError) as exc:
        LOG.warning("US Treasury official yield feed unavailable (%s)", type(exc).__name__)
        return []

def fetch_market_snapshot(now=None, getter=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Market snapshot must have aware time")
    today = now.date()
    def fetch(series):
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
        try:
            response = (getter or requests.get)(
                url, params={"id":series,
                             "cosd":(today-dt.timedelta(days=13)).isoformat()},
                timeout=10, headers={"User-Agent":"PersonalNewspaper/1.0"})
            response.raise_for_status()
            item = parse_fred_csv(response.text, series, today)
            if item is None:
                LOG.warning("FRED %s returned no fresh numeric observations; content_type=%s",
                            series, response.headers.get("Content-Type","unknown"))
            return item
        except requests.RequestException as exc:
            code = getattr(getattr(exc,"response",None),"status_code",None)
            LOG.warning("FRED %s source unavailable (%s HTTP=%s)",series,type(exc).__name__,code)
            return None
        except (ValueError, TypeError) as exc:
            LOG.warning("FRED %s invalid source data (%s)",series,type(exc).__name__)
            return None
    with ThreadPoolExecutor(max_workers=6) as pool:
        quotes = list(pool.map(fetch, SERIES))
    # FRED's unauthenticated graph endpoint may time out on GH-hosted runners.
    # Fill only missing historical major indices via dated, validated Stooq
    # CSV; never overwrite an official/FRED observation with a fallback.
    missing_indices = [s for s in STOOQ_DAILY if quotes[list(SERIES).index(s)] is None]
    if missing_indices:
        backups = fetch_stooq_completed_closes(now, getter=getter)
        for backup in backups:
            code = backup["series"]
            idx = list(SERIES).index(code)
            if quotes[idx] is None:
                quotes[idx] = backup
    # The US Treasury publishes a separate official XML feed for par yields.
    # Never replace any valid FRED observation.
    if any(quotes[list(SERIES).index(code)] is None for code in TREASURY_FIELDS):
        for backup in fetch_treasury_yields(now, getter=getter):
            idx = list(SERIES).index(backup["series"])
            if quotes[idx] is None:
                quotes[idx] = backup
    # Public-page backup for three headline indices when FRED/Stooq provide
    # no verifiable figure. The observation type records whether the quote
    # was intraday or post-session; it is NEVER silently labeled EOD.
    if any(quotes[list(SERIES).index(code)] is None
           for code in ("SP500", "NASDAQCOM", "DJIA")):
        for quote in fetch_public_index_quotes(now, getter=getter):
            idx = list(SERIES).index(quote["series"])
            if quotes[idx] is None:
                quotes[idx] = quote
    values = [q for q in quotes if q]
    backup_count = sum(q.get("source") != "FRED" for q in values)
    return {
        "as_of_request_utc": now.isoformat(),
        "kind": "dated_published_daily_observations_not_intraday",
        "values": values,
        "missing": [s for s,q in zip(SERIES,quotes) if not q],
        "sources": sorted({"Stooq" if q["source"].startswith("Stooq") else "US Treasury" if q["source"].startswith("US Treasury") else "Google Finance" if q["source"].startswith("Google Finance") else q["source"] for q in values}),
        "backup_observations": backup_count,
        "warning": "每项数值按实际来源及时间标注；Google Finance网页报价可能为盘中或盘后观察值，不能当作官方收盘数据；FRED、Stooq及美国财政部为带日期历史观测。缺失不可推算。",
    }
