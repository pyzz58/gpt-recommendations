"""Read-only, budget-free probes for unapproved US-market source candidates.

Probe endpoints from the *GitHub Actions runner* before enabling them.
HTTP 200 alone is never classified as a healthy RSS. No SMTP or LLM calls.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import logging
from pathlib import Path

import feedparser
import requests

from digest import published_at, clean
from market_headline import market_evidence
from source_quality import newsworthiness
from production_policy import BEIJING

LOG=logging.getLogger("newspaper.market_source_probe")
ROOT=Path(__file__).resolve().parent
CANDIDATES=ROOT/"market_source_candidates.json"
REPORT=Path("/tmp/newspaper-market-source-probe.json")
MAX_BODY_BYTES=3_000_000


def probe_one(feed:dict, start:dt.datetime, end:dt.datetime, *, getter=None) -> dict:
    getter=getter or requests.get
    output={
        "name":feed["name"],"url":feed["url"],
        "source_type":feed.get("source_type","financial_media"),
        "priority":feed.get("priority","unknown"),
        "http_ok":False,"valid_rss_or_atom":False,"dated_entries":0,
        "fresh24":0,"fresh7d":0,"relevant24":0,
        "editorially_eligible24":0,"sample_market_headlines":[],
    }
    try:
        response=getter(feed["url"],timeout=15,headers={
            "User-Agent":"BilingualPersonalNewspaper/0.2",
            "Accept":"application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        })
        response.raise_for_status()
        output["http_ok"]=True
        raw=response.content[:MAX_BODY_BYTES+1]
        if len(raw)>MAX_BODY_BYTES:
            output["error"]="rss_too_large"
            return output
        parsed=feedparser.parse(raw)
        if not parsed.entries or (parsed.get("bozo") and not parsed.feed):
            output["error"]="no_parseable_rss_entries"
            return output
        output["valid_rss_or_atom"]=True
        for entry in parsed.entries:
            when=published_at(entry)
            if when is None:
                continue
            output["dated_entries"]+=1
            when=when.astimezone(BEIJING)
            if end-dt.timedelta(days=7)<=when<end:
                output["fresh7d"]+=1
            if not start<=when<end:
                continue
            output["fresh24"]+=1
            title=clean(entry.get("title",""),230)
            link=str(entry.get("link",""))
            if not title or not link.startswith(("https://","http://")):
                continue
            item={"title":title,"summary":clean(entry.get("summary","")),
                  "url":link,"source":feed["name"],
                  "source_type":feed.get("source_type","financial_media"),
                  "source_language":"en"}
            signal=market_evidence(item)
            if signal["eligible"]:
                output["relevant24"]+=1
                if newsworthiness(item)["eligible"]:
                    output["editorially_eligible24"]+=1
                if len(output["sample_market_headlines"])<5:
                    output["sample_market_headlines"].append({
                        "title":title,"url":link,"beijing_published":when.isoformat(),
                        "reason":signal["reason"],
                    })
        return output
    except Exception as exc:
        output["error"]=type(exc).__name__
        return output


def probe_all(spec:dict, now:dt.datetime, *, worker=probe_one) -> dict:
    if spec.get("schema")!=1 or spec.get("scope")!="newspaper-only":
        raise ValueError("Unrecognized newspaper source candidate configuration")
    if now.tzinfo is None:
        raise ValueError("Probe requires timezone-aware current time")
    end=now.astimezone(BEIJING)
    start=end-dt.timedelta(days=1)
    feeds=spec["feeds"]
    if len({f["name"] for f in feeds})!=len(feeds):
        raise ValueError("Duplicate source candidate name")
    if len({f["url"] for f in feeds})!=len(feeds):
        raise ValueError("Duplicate source candidate URL")
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        rows=list(executor.map(lambda feed:worker(feed,start,end),feeds))
    return {
        "schema":1,"scope":"newspaper_source_candidate_probe_only",
        "window_start_beijing":start.isoformat(),
        "window_end_beijing":end.isoformat(),
        "source_count":len(rows),
        "http_ok":sum(x["http_ok"] for x in rows),
        "valid_rss_or_atom":sum(x["valid_rss_or_atom"] for x in rows),
        "feeds_with_relevant_market_news_24h":sum(x["relevant24"]>0 for x in rows),
        "relevant_market_articles_24h_total":sum(x["relevant24"] for x in rows),
        "entries_fresh24_total":sum(x["fresh24"] for x in rows),
        "entries_fresh7d_total":sum(x["fresh7d"] for x in rows),
        "sources":rows,
        "warning":"These sources remain disabled until their per-feed evidence is reviewed. RSS dates, source rights, story readability and significance all require separate gates.",
    }


def main():
    args=argparse.ArgumentParser()
    args.add_argument("--strict",action="store_true",
                      help="Fail CI only if no candidate source is valid")
    p=args.parse_args()
    data=json.loads(CANDIDATES.read_text(encoding="utf-8"))
    report=probe_all(data,dt.datetime.now(BEIJING))
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("NEWSPAPER_MARKET_PROBE_SUMMARY="+json.dumps({
        k:v for k,v in report.items() if k not in ("sources","warning")
    },ensure_ascii=False))
    for item in report["sources"]:
        print("NEWSPAPER_MARKET_PROBE_FEED="+json.dumps({
            k:v for k,v in item.items() if k!="sample_market_headlines"
        },ensure_ascii=False))
    print("NEWSPAPER_MARKET_PROBE_REPORT="+str(REPORT))
    if p.strict and report["valid_rss_or_atom"]==0:
        raise RuntimeError("All candidate finance RSS sources unusable")


if __name__=="__main__":
    main()
