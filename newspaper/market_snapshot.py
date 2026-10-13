"""US market cover from dated FRED published daily series, not intraday quotes.

No private API key or invented index values. FRED/S&P datasets may be delayed;
always state the actual observation date and only show verified values.
"""
from __future__ import annotations
import csv
import datetime as dt
import io
import logging
from urllib.parse import urlencode
import requests

LOG=logging.getLogger("newspaper.market")
FRED_SERIES={
    "SP500":("标普500","index"),
    "NASDAQCOM":("纳斯达克综合","index"),
    "DJIA":("道琼斯工业指数","index"),
    "VIXCLS":("VIX波动率","index"),
    "DGS2":("美国2年期国债收益率","yield"),
    "DGS10":("美国10年期国债收益率","yield"),
}
FRED_URL="https://fred.stlouisfed.org/graph/fredgraph.csv"

def parse_fred_csv(raw,cutoff:dt.date,maximum_lag_days=7):
    rows=list(csv.DictReader(io.StringIO(raw)))
    out=[]
    for code,(label,kind) in FRED_SERIES.items():
        samples=[]
        for row in rows:
            stamp=row.get("observation_date") or row.get("DATE")
            try:
                date=dt.date.fromisoformat(stamp)
                number=float(row.get(code,"").strip())
            except (ValueError,TypeError,AttributeError):
                continue
            if not 0 <= (cutoff-date).days <= maximum_lag_days:continue
            if number <= 0:continue
            samples.append((date,number))
        if not samples:continue
        samples.sort()
        date,value=samples[-1]
        previous=samples[-2][1] if len(samples)>1 else None
        result={"symbol":code,"label":label,"kind":kind,
                "observation_date":date.isoformat(),"value":round(value,3),
                "source":"FRED（美联储圣路易斯分行，原始指数归各提供者）",
                "source_url":"https://fred.stlouisfed.org/series/"+code}
        if previous and kind=="index":
            result["change_pct"]=round((value/previous-1)*100,2)
        out.append(result)
    return out


YAHOO_INDEX={
    "^GSPC":"标普500",
    "^IXIC":"纳斯达克综合",
    "^DJI":"道琼斯工业指数",
    "^VIX":"VIX波动率",
}

def _yahoo_dated_index_quotes(edition_end, http_get=None):
    """Use historical daily chart observations only after the U.S. session closed."""
    from concurrent.futures import ThreadPoolExecutor
    from urllib.parse import quote
    from zoneinfo import ZoneInfo

    et_now=edition_end.astimezone(ZoneInfo("America/New_York"))
    headers={"User-Agent":"Mozilla/5.0 (compatible; PersonalPrivateNews/1.0)",
             "Accept":"application/json"}
    def one(args):
        symbol,label=args
        url=("https://query1.finance.yahoo.com/v8/finance/chart/"
             +quote(symbol,safe="")+"?range=10d&interval=1d")
        try:
            r=(http_get or requests.get)(url,timeout=8,headers=headers)
            r.raise_for_status()
            record=(r.json().get("chart",{}).get("result") or [None])[0]
            if not record:return None
            stamp=record.get("timestamp") or []
            quotes=(record.get("indicators",{}).get("quote") or [{}])[0]
            closes=quotes.get("close") or []
            valid=[]
            for ts,close in zip(stamp,closes):
                if close is None or close<=0:continue
                observed=dt.datetime.fromtimestamp(ts,dt.timezone.utc).astimezone(
                    ZoneInfo("America/New_York")).date()
                if observed>et_now.date():continue
                # Yahoo daily bars can contain a partial intraday "close":
                # never present the unfinished U.S. trading day as EOD.
                if observed==et_now.date() and et_now.time()<dt.time(16,5):
                    continue
                if (et_now.date()-observed).days>7:continue
                valid.append((observed,float(close)))
            valid.sort()
            if not valid:return None
            date,value=valid[-1]
            result={"symbol":symbol,"label":label,"kind":"index",
                "value":round(value,3),"observation_date":date.isoformat(),
                "source":"Yahoo Finance历史日频报价（非交易所实时行情）",
                "source_url":"https://finance.yahoo.com/quote/"+symbol+"/"}
            if len(valid)>1:
                result["change_pct"]=round((value/valid[-2][1]-1)*100,2)
            return result
        except (requests.RequestException,ValueError,KeyError,TypeError,AttributeError):
            return None
    with ThreadPoolExecutor(max_workers=4) as pool:
        return [v for v in pool.map(one,YAHOO_INDEX.items()) if v]


def get_market_snapshot(edition_end:dt.datetime,http_get=None):
    """Yahoo daily EOD as available; FRED is a dated non-intraday backup."""
    cutoff=edition_end.date()
    prices=_yahoo_dated_index_quotes(edition_end,http_get=http_get)
    source="Yahoo Finance历史日频报价（非交易所实时行情）" if prices else "FRED公开日频数据"
    if not prices:
        params={"id":",".join(FRED_SERIES),
                "cosd":(cutoff-dt.timedelta(days=16)).isoformat(),
                "coed":cutoff.isoformat()}
        url=FRED_URL+"?"+urlencode(params)
        try:
            response=(http_get or requests.get)(
                url,timeout=6,headers={"User-Agent":"PersonalBilingualNewspaper/1.0"})
            response.raise_for_status()
            prices=parse_fred_csv(response.text,cutoff)
        except (requests.RequestException,ValueError,TypeError,AttributeError) as exc:
            LOG.warning("FRED fallback unavailable: %s",type(exc).__name__)
    return {"source":source,
        "requested_cutoff":cutoff.isoformat(),"items":prices,
        "disclaimer":("每个数字均标示实际数据日期。以最后已完成的美国交易时段为准；"
                      "非实时行情，可能有供应商延迟；缺失不补造。"),
        "available":bool(prices)}
