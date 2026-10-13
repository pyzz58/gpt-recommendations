"""One-off public endpoint health probe, no credentials or newsletter delivery."""
import concurrent.futures
import json
import requests
import feedparser

URLS={
    "fred_single":"https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500",
    "stooq_quote":"https://stooq.com/q/l/?s=%5Espx&f=sd2t2c&h&e=csv",
    "stooq_daily":"https://stooq.com/q/d/l/?s=%5Espx&i=d&d1=20261001&d2=20261014",
    "yahoo_chart_1":"https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?range=5d&interval=1d",
    "yahoo_chart_2":"https://query2.finance.yahoo.com/v8/finance/chart/%5EGSPC?range=5d&interval=1d",
    "36kr_rss":"https://36kr.com/feed",
    "36kr_article":"https://36kr.com/feed-article",
    "36kr_flash":"https://36kr.com/feed-newsflash",
    "36kr_www":"https://www.36kr.com/feed",
}
def check(arg):
    name,url=arg
    try:
        r=requests.get(url,timeout=8,headers={"User-Agent":"Mozilla/5.0 (compatible; PublicPrivateNewsReader/1.0)","Accept":"*/*"})
        ctype=r.headers.get("Content-Type","")
        answer={"key":name,"status":r.status_code,"content_type":ctype,
                "bytes":len(r.content),"resolved_host":requests.utils.urlparse(r.url).hostname}
        if name.startswith("36kr") and r.ok:
            parsed=feedparser.parse(r.content)
            answer["rss_entries"]=len(parsed.entries)
            answer["rss_bozo"]=bool(parsed.get("bozo"))
        if name.startswith("stooq") and r.ok:
            answer["csv_lines"]=len(r.text.splitlines())
        if name.startswith("yahoo") and r.ok:
            answer["chart_data"]=r.text.startswith('{"chart":')
        return answer
    except requests.RequestException as exc:
        return {"key":name,"status":"unavailable","error":type(exc).__name__}
with concurrent.futures.ThreadPoolExecutor(max_workers=9) as pool:
    results=list(pool.map(check,URLS.items()))
print("PUBLIC_MARKET_PROVIDER_PROBE="+json.dumps(results,sort_keys=True))
open("/tmp/newspaper-market-source-probe.json","w").write(json.dumps(results,indent=2))
