"""Conservative official SEC EDGAR submissions discovery.

Source: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
A filing notification is NOT an earnings beat, recommendation or verified
interpretation of the attached financial statements.
"""
from __future__ import annotations
import concurrent.futures
import datetime as dt
import logging
import os
import re
from urllib.parse import urlparse
import requests

LOG=logging.getLogger("newspaper.sec_edgar")
BASE="https://data.sec.gov/submissions/CIK{cik:010d}.json"
ISSUERS={
    "AAPL":("Apple",320193),
    "MSFT":("Microsoft",789019),
    "NVDA":("NVIDIA",1045810),
    "AMZN":("Amazon",1018724),
    "GOOGL":("Alphabet",1652044),
    "META":("Meta Platforms",1326801),
    "TSLA":("Tesla",1318605),
    "JPM":("JPMorgan Chase",19617),
}
ALLOWED_FORMS={"10-Q","10-K","8-K"}
MAX_PER_ISSUER=2


def official_link(cik,accession):
    if not re.fullmatch(r"\d{10}-\d{2}-\d{6}",accession):
        return None
    return "https://www.sec.gov/Archives/edgar/data/{}/{}/{}-index.htm".format(
        int(cik),accession.replace("-",""),accession)


def parse_submissions(payload,ticker,name,cik,start,end):
    if not isinstance(payload,dict) or not isinstance(payload.get("filings"),dict):
        raise ValueError("Invalid official submissions payload")
    recent=payload["filings"].get("recent",{})
    keys=("accessionNumber","form","filingDate","acceptanceDateTime")
    lengths={len(recent.get(k,[])) for k in keys}
    if len(lengths)!=1:
        raise ValueError("SEC submissions arrays differ in length")
    n=lengths.pop()
    items=recent.get("items",[])
    if items and len(items)!=n:
        raise ValueError("SEC 8-K item metadata length differs")
    seen=set()
    out=[]
    for i in range(n):
        form=recent["form"][i]
        if form not in ALLOWED_FORMS:
            continue
        if form=="8-K" and (not items or "2.02" not in str(items[i])):
            # Do not label ordinary executive changes or arbitrary 8-K filings earnings.
            continue
        stamp=str(recent["acceptanceDateTime"][i])
        try:
            # SEC acceptanceDateTime is an Eastern local timestamp, not UTC.
            accepted=dt.datetime.fromisoformat(stamp)
            if accepted.tzinfo is None:
                from zoneinfo import ZoneInfo
                accepted=accepted.replace(tzinfo=ZoneInfo("America/New_York"))
        except (ValueError,TypeError):
            continue
        if not start <= accepted.astimezone(start.tzinfo) < end:
            continue
        accession=str(recent["accessionNumber"][i])
        link=official_link(cik,accession)
        if not link or link in seen:
            continue
        seen.add(link)
        kind="quarterly report" if form=="10-Q" else ("annual report" if form=="10-K" else "results-related Form 8-K (Item 2.02)")
        out.append({
            "category":"美股与投资",
            "source":"SEC EDGAR - "+ticker,
            "source_type":"primary_company_filing",
            "source_language":"en",
            "title":f"{name} ({ticker}) files {kind} with SEC",
            "summary":f"SEC official filing notice for {name}, form {form}, accession {accession}. This notice confirms a filing, not the financial results or their significance.",
            "url":link,
            "date":accepted,
            "filing_form":form,
            "issuer_ticker":ticker,
            "filing_accession":accession,
            "filing_notice_only":True,
        })
        if len(out)>=MAX_PER_ISSUER:
            break
    return out


def fetch_filings(start,end,*,getter=None,issuers=None,contact=None):
    """Bounded public-data scan. Missing identification => explicit disabled state."""
    contact=contact if contact is not None else os.environ.get("NEWSPAPER_SEC_CONTACT","")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",contact):
        return [],{"status":"disabled_missing_contact_email","issuers_configured":len(ISSUERS),"issuer_success":0,"notices":0}
    getter=getter or requests.get
    chosen=issuers or ISSUERS
    headers={"User-Agent":f"NewspaperResearch/1.0 ({contact})","Accept":"application/json"}
    def one(p):
        ticker,(name,cik)=p
        try:
            response=getter(BASE.format(cik=cik),headers=headers,timeout=12)
            response.raise_for_status()
            # Enforce response size to avoid unexpected huge or HTML payloads.
            body=response.content
            if len(body)>8_000_000:
                raise ValueError("Oversized SEC response")
            rows=parse_submissions(response.json(),ticker,name,cik,start,end)
            return rows,None
        except (requests.RequestException,ValueError,KeyError,TypeError) as exc:
            LOG.warning("SEC EDGAR %s unavailable: %s",ticker,type(exc).__name__)
            return [],type(exc).__name__
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(one,chosen.items()))
    records=[a for rows,error in results for a in rows]
    success=sum(error is None for rows,error in results)
    return records,{
        "status":"ok" if success==len(chosen) else ("partial" if success else "unavailable"),
        "issuers_configured":len(chosen),
        "issuer_success":success,
        "notices":len(records),
        "errors":[error for rows,error in results if error],
        "filing_notices_not_confirmed_earnings":True,
    }
