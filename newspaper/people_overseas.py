"""Read People's Daily Overseas Edition public contents page for monitoring.

This is an official HTML edition, NOT RSS. Expose verified issue metadata
and links for source-health auditing, not fabricated 01:00 publish timestamps.
"""
import re
from datetime import date
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
    return {"issue_date": issue, "items": unique,
            "issue_date_is_publication_timestamp": False}


def audit_edition(fetcher=None):
    response = (fetcher or requests.get)(
        URL, timeout=15,
        headers={"User-Agent": "PersonalNewspaperMonitoring/1.0"})
    response.raise_for_status()
    return parse_edition(response.text, response.url)
