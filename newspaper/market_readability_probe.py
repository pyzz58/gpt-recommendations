"""P1 editorial candidate article-access check using existing lawful reader.

Only headlines already screened as substantive US-market news are probed.
Retains *metadata and counts only*, not copyrighted article bodies.
Never uses credentials, model APIs, SMTP, login or paywall bypass.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

CANDIDATES=Path(__file__).resolve().parent / "market_source_candidates.json"

OUT=Path("/tmp/newspaper-market-readability.json")
BJT=ZoneInfo("Asia/Shanghai")
NAMES={
    "Financial Times Markets",
    "Financial Times US",
    "CNBC Earnings",
    "CNBC Finance",
    "CNBC Top News",
}
MAX_ARTICLES_PER_SOURCE=2


def check_one(feed,start,end,*,rss_probe=None,article_reader=None):
    if rss_probe is None:
        from probe_market_sources import probe_one as rss_probe
    if article_reader is None:
        from reader import fetch_reading as article_reader
    raw=rss_probe(feed,start,end)
    result={
        "name":feed["name"],
        "valid_rss":bool(raw.get("valid_rss_or_atom")),
        "eligible_market_headlines":int(raw.get("editorially_eligible24",0)),
        "tested_articles":0,
        "readable_articles":0,
        "failed_articles":0,
        "samples":[],
    }
    if not result["valid_rss"]:
        result["status"]="invalid_rss_or_unreachable"
        return result
    for entry in raw.get("sample_market_headlines",[])[:MAX_ARTICLES_PER_SOURCE]:
        candidate={
            "title":entry["title"],"url":entry["url"],
            "source":feed["name"],
            "source_language":"en",
        }
        # Extractor accepts only unpaywalled public HTML. No copyrighted
        # article text is retained in this report.
        try:
            article=article_reader(candidate,min_chars=450,max_chars=1800)
        except Exception:
            article=None
        result["tested_articles"]+=1
        ok=bool(article and article.get("reading_en") and
                len(str(article["reading_en"]))>=450)
        result["readable_articles"]+=int(ok)
        result["failed_articles"]+=int(not ok)
        result["samples"].append({
            "url":entry["url"],"title":entry["title"],
            "rss_published_bjt":entry["beijing_published"],
            "reader_pass":ok,
            "body_chars_if_readable":int(article.get("article_chars",0)) if ok else 0,
            "extraction_engine":str(article.get("extraction_engine","")) if ok else "",
        })
    result["status"]=(
        "has_readable_market_article" if result["readable_articles"]
        else ("market_article_not_readable" if result["tested_articles"]
              else "no_market_story_in_window"))
    return result


def probe_readability(spec,now,*,rss_probe=None,article_reader=None):
    if now.tzinfo is None: raise ValueError("A timezone-aware clock is required")
    listed=[f for f in spec["feeds"] if f["name"] in NAMES]
    if len(listed)!=len(NAMES): raise ValueError("Financial-source allowlist incomplete")
    start=now.astimezone(BJT)-dt.timedelta(days=1)
    end=now.astimezone(BJT)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(
            lambda feed:check_one(feed,start,end,
                                  rss_probe=rss_probe,article_reader=article_reader),
            listed))
    return {
        "schema":1,"status":"READ_ONLY_NEVER_PRODUCTION_SOURCE_PROMOTION",
        "window_start_bjt":start.isoformat(),
        "window_end_bjt":end.isoformat(),
        "probed_sources":len(results),
        "sources_with_readable_market_articles":sum(r["readable_articles"]>0 for r in results),
        "tested_articles":sum(r["tested_articles"] for r in results),
        "readable_articles":sum(r["readable_articles"] for r in results),
        "sources":results,
        "limits":[
            "One rolling 24-hour probe is not proof of stable long-term source availability.",
            "Readability is distinct from quality, copyright licensing and relevance.",
            "Paywalled or incomplete pages must not be bypassed.",
        ],
    }


def main():
    spec=json.loads(CANDIDATES.read_text(encoding="utf-8"))
    result=probe_readability(spec,dt.datetime.now(BJT))
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
    print("NEWSPAPER_MARKET_READABILITY_SUMMARY="+json.dumps(
        {k:v for k,v in result.items() if k not in ("sources","limits")},
        ensure_ascii=False,sort_keys=True))
    for src in result["sources"]:
        print("NEWSPAPER_MARKET_READABILITY_SOURCE="+json.dumps(
            {k:v for k,v in src.items() if k!="samples"},
            ensure_ascii=False,sort_keys=True))
    print("NEWSPAPER_MARKET_READABILITY_REPORT="+str(OUT))


if __name__=="__main__":
    main()
