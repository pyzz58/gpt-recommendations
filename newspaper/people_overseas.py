"""Read People's Daily Overseas Edition public contents page for monitoring.

This is an official HTML edition, NOT RSS. Expose verified issue metadata
and links for source-health auditing, not fabricated 01:00 publish timestamps.
"""
import re
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

URL = "https://paper.people.com.cn/rmrbhwb/pc/layout/index.html"


def parse_edition(html, base_url=URL):
    soup = BeautifulSoup(html or "", "html.parser")
    text = soup.get_text(" ", strip=True)
    m = re.search(r"(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日", text)
    issue = None
    if m:
        try:
            issue = date(*map(int, m.groups())).isoformat()
        except ValueError:
            pass
    links = []
    for a in soup.select("a[href]"):
        title = a.get_text(" ", strip=True)
        href = a.get("href") or ""
        if len(title) < 8 or len(title) > 180 or not href:
            continue
        # Official table-of-contents article links use content URLs.
        if not re.search(r"(content_\d+|content/|content_)", href):
            continue
        url = urljoin(base_url, href)
        if "people.com.cn" not in url:
            continue
        links.append({"title": title, "url": url})
    unique = list({v["url"]: v for v in links}.values())
    if not issue:
        pathdate = re.search(r"/(20\\d{2})(\\d{2})/(\\d{2})/", base_url)
        if pathdate:
            try: issue = date(*map(int, pathdate.groups())).isoformat()
            except ValueError: pass
    return {"issue_date": issue, "items": unique,
            "issue_date_is_publication_timestamp": False}


def audit_edition(fetcher=None, now=None):
    """Check official dated section pages, not undated generic index.html.

    An issue's DATE is not an article's publication timestamp. That date is
    used for passive monitoring only until article-level times are verified.
    """
    fetcher = fetcher or requests.get
    today = (now or datetime.now(ZoneInfo("Asia/Shanghai"))).date()
    failures = []
    for ago in (0, 1, 2):
        day = today - timedelta(days=ago)
        found = []
        for edition in ("node_01.html", "node_03.html", "node_10.html"):
            path = f"https://paper.people.com.cn/rmrbhwb/pc/layout/{day:%Y%m}/{day:%d}/{edition}"
            try:
                response = fetcher(path, timeout=10,
                                   headers={"User-Agent":"PersonalNewspaperMonitoring/1.0"})
                response.raise_for_status()
                item = parse_edition(response.text, response.url)
                if item["issue_date"] == day.isoformat():
                    found.extend(item["items"])
            except requests.RequestException as exc:
                failures.append(type(exc).__name__)
        if found:
            return {"issue_date": day.isoformat(),
                    "items": list({item["url"]:item for item in found}.values()),
                    "issue_date_is_publication_timestamp": False,
                    "issue_is_from_official_dated_pages": True}
    return {"issue_date": None, "items": [],
            "issue_date_is_publication_timestamp": False,
            "issue_is_from_official_dated_pages": False,
            "error_codes": sorted(set(failures))}
