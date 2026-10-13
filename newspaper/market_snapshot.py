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

import requests

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
            return parse_stooq_daily(response.text, series, ny_local)
        except (requests.RequestException, ValueError, TypeError):
            return None
    with ThreadPoolExecutor(max_workers=3) as pool:
        return [value for value in pool.map(one, STOOQ_DAILY.items()) if value]


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
    return {
        "as_of_request_utc": now.isoformat(),
        "kind": "latest_FRED_published_daily_close_not_intraday",
        "values": [q for q in quotes if q],
        "missing": [s for s,q in zip(SERIES,quotes) if not q],
        "warning": "仅为FRED已发布的最近一次收盘/官方日值；不是实时行情。缺失数据不得推算。",
    }
