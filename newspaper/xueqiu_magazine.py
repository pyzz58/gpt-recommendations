"""Passive public-page monitoring for Snowball's official Investment Journal.

The official Snowball journal is periodic investment commentary, not newswire
and not an authoritative market data source. No login bypass, API emulation,
anti-bot evasion, hidden content retrieval or daily-date fabrication.
"""
from __future__ import annotations
import re
import requests
from bs4 import BeautifulSoup

URL = "https://xueqiu.com/u/3746414875"


def parse_public_journal(html):
    soup = BeautifulSoup(html or "", "html.parser")
    texts = soup.get_text(" ", strip=True)
    titles = []
    for match in re.findall(r"雪球专刊\s*\d+\s*期[^\n]{0,70}", texts):
        title = match.strip()
        if title not in titles:
            titles.append(title)
        if len(titles) == 10:
            break
    return {"visible_issue_titles": titles,
            "page_identified": "雪球专刊" in texts,
            "not_daily_publication": True}


def audit_public_journal(getter=None):
    response = (getter or requests.get)(
        URL, timeout=12,
        headers={"User-Agent":"PersonalNewspaperMonitoring/1.0"})
    response.raise_for_status()
    return parse_public_journal(response.text)
