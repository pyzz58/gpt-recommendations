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

def get_market_snapshot(edition_end:dt.datetime,http_get=None):
    cutoff=edition_end.date()
    params={"id":",".join(FRED_SERIES),"cosd":(cutoff-dt.timedelta(days=16)).isoformat(),
            "coed":cutoff.isoformat()}
    url=FRED_URL+"?"+urlencode(params)
    try:
        response=(http_get or requests.get)(url,timeout=11,
            headers={"User-Agent":"PersonalBilingualNewspaper/1.0"})
        response.raise_for_status()
        series=parse_fred_csv(response.text,cutoff)
        return {"source":"FRED公开日频数据（非实时行情）",
            "requested_cutoff":cutoff.isoformat(),
            "items":series,"disclaimer":"按各指标所标数据日期核对；公布存在延时。不能推断当前美股盘中价格，缺项不补造。",
            "available":bool(series)}
    except (requests.RequestException,ValueError) as exc:
        LOG.warning("FRED market snapshot unavailable: %s",type(exc).__name__)
        return {"source":"FRED公开日频数据（非实时行情）",
            "requested_cutoff":cutoff.isoformat(),"items":[],
            "disclaimer":"权威历史收盘数据暂不可核验，本期不展示数字。","available":False}
