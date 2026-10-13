"""Public HTML news discovery for non-RSS Chinese publications.

No login, unofficial/private endpoint, PDF extraction or paywall bypass.
Xueqiu special editions are OPINION, not market-moving verified news.
The People's Overseas daily has day-level dating, explicitly marked.
"""
from __future__ import annotations
import datetime as dt
import logging
import re
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

LOG=logging.getLogger("daily-news")
HEAD={"User-Agent":"PersonalNewsReader/0.1 (private RSS digest)","Accept":"text/html"}

def _get(url):
    r=requests.get(url,timeout=14,headers=HEAD)
    r.raise_for_status()
    if "html" not in r.headers.get("Content-Type","text/html").lower():
        raise ValueError("Not HTML")
    return BeautifulSoup(r.text,"html.parser")

def _day_links(url,soup,kind):
    result=[]
    for anchor in soup.select("a[href]"):
        title=anchor.get_text(" ",strip=True)
        href=urljoin(url,anchor.get("href",""))
        if not 6 <= len(title) <= 190: continue
        if kind=="xueqiu_special":
            match=re.search(r"/3746414875/(\d+)",urlparse(href).path)
            if not match or "雪球专刊" not in title and "雪球特别版" not in title:continue
        else:
            if "/rmrbhwb/pc/content/" not in urlparse(href).path:continue
            if any(x in title for x in ("图片报道","广告","责编","PDF下载")):continue
        if href not in {x[1] for x in result}:
            result.append((title,href))
    return result

def _xueqiu(feed,start,end):
    soup=_get(feed["url"])
    output=[]
    for title,url in _day_links(feed["url"],soup,"xueqiu_special")[:7]:
        try:
            article=_get(url)
            m=re.search(r"发布于\s*[:：]\s*(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})",
                        article.get_text(" ",strip=True)[:700])
            if not m: continue
            stamp=dt.datetime.strptime(m.group(1)+" "+m.group(2),"%Y-%m-%d %H:%M")
            stamp=stamp.replace(tzinfo=start.tzinfo)
            if not start <= stamp < end:continue
            output.append({"source":feed["name"],"category":"美股与投资","title":title,
                "summary":"雪球官方投资主题专刊。内容属于投资观点，非交易所或监管机构公告。",
                "url":url,"date":stamp,"author":"雪球专刊","language":"zh",
                "source_kind":"investment_opinion","date_precision":"minute"})
        except (requests.RequestException,ValueError):
            continue
    return output,True

def _peoples(feed,start,end):
    base="https://paper.people.com.cn/rmrbhwb/pc/layout/"
    date_candidates=list(dict.fromkeys((end-dt.timedelta(hours=h)).date() for h in (1,24)))
    items=[]
    # Publication date only, not a fabricated 24-hour post timestamp.
    # An edition dated on the day crossing the cutoff qualifies for daily
    # discovery, but retains date_precision=day for transparent labeling.
    for date in date_candidates:
        stem=f"{date:%Y%m}/{date:%d}/"
        for page in (1,3):
            url=base+stem+f"node_{page:02d}.html"
            try:
                soup=_get(url)
            except requests.RequestException:continue
            for title,href in _day_links(url,soup,"peoples_overseas")[:16]:
                items.append({"source":feed["name"],"category":"全球新闻",
                    "title":title,"summary":"人民日报海外版报纸报道；仅核实出版日期，未核实具体发布时刻。",
                    "url":href,"date":dt.datetime.combine(date,dt.time.min,tzinfo=start.tzinfo),
                    "publication_date":date.isoformat(),"date_precision":"day",
                    "language":"zh","source_kind":"daily_paper"})
    # Unknown posting times cannot strictly establish inclusion in [start,end).
    # Keep day-stamped newspaper items separate from 24h breaking-news candidates.
    return items, True

def fetch_publication(feed,start,end):
    kind=feed.get("kind")
    try:
        if kind=="xueqiu_special":return _xueqiu(feed,start,end)
        if kind=="peoples_overseas":return _peoples(feed,start,end)
        return [],False
    except (requests.RequestException,ValueError) as exc:
        LOG.warning("Public-source monitor unavailable: %s (%s)",feed["name"],type(exc).__name__)
        return [],False
