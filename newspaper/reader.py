"""Download accessible news articles and prepare a substantive, self-contained email reading view.

No paywall circumvention, login bypass, or headless-browser evasion.
Not all publishers permit automated reuse; evaluate source terms before broad deployment.
"""
from __future__ import annotations

import html
import logging
import re
from urllib.parse import urlparse

import requests
import trafilatura

LOG = logging.getLogger("daily-news")

def _usable_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return (
        parsed.scheme == "https" and bool(host) and "." in host
        and host not in {"localhost", "127.0.0.1", "169.254.169.254"}
    )

def _normalize_paragraphs(text: str) -> list[str]:
    text = html.unescape(text or "")
    parts = re.split(r"\n+", text)
    result = []
    for piece in parts:
        piece = re.sub(r"\s+", " ", piece).strip()
        if len(piece) > 20 and (not result or result[-1] != piece):
            result.append(piece)
    return result

def _long_read(paragraphs: list[str], max_chars: int) -> tuple[str, bool]:
    """Select opening, middle and closing *paragraphs*, preserving original order.

    This is an extractive reading edition rather than an LLM-generated summary;
    it is not equivalent to the publisher's full article.
    """
    if not paragraphs:
        return "", False
    full = "\n\n".join(paragraphs)
    if len(full) <= max_chars:
        return full, False
    n = len(paragraphs)
    # Prioritize the lead and include context from the middle and ending.
    sequence = list(range(min(n, 5)))
    middle_start = max(5, n // 3)
    sequence += list(range(middle_start, min(n, middle_start + 5)))
    tail_start = max(0, n - 4)
    sequence += list(range(tail_start, n))
    chosen = set()
    used = 0
    for idx in sequence:
        if idx in chosen:
            continue
        p = paragraphs[idx]
        if used + len(p) + 2 > max_chars:
            continue
        chosen.add(idx)
        used += len(p) + 2
    if not chosen:  # One exceptionally large paragraph.
        return full[:max_chars].rsplit(" ", 1)[0], True
    return "\n\n".join(paragraphs[i] for i in sorted(chosen)), True

def fetch_reading(article: dict, min_chars: int = 450, max_chars: int = 4200) -> dict | None:
    """Return enriched article or None; never substitute the RSS abstract for a real article."""
    url = article["url"]
    if not _usable_url(url):
        LOG.warning("Skipping unsupported article URL: %s", url)
        return None
    try:
        response = requests.get(
            url,
            timeout=22,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; PersonalNewsReader/0.1; non-commercial)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        response.raise_for_status()
        if "html" not in response.headers.get("Content-Type", "").lower():
            LOG.warning("Non-HTML article: %s", url)
            return None
        raw = trafilatura.extract(
            response.text, include_comments=False, include_tables=False,
            favor_precision=True, output_format="txt",
        )
        paragraphs = _normalize_paragraphs(raw or "")
        if len("\n".join(paragraphs)) < min_chars:
            LOG.warning("Article text not available: %s", url)
            return None
        excerpt, abbreviated = _long_read(paragraphs, max_chars=max_chars)
        enriched = dict(article)
        enriched["reading_en"] = excerpt
        enriched["reading_abbreviated"] = abbreviated
        enriched["article_chars"] = len("\n\n".join(paragraphs))
        return enriched
    except Exception as exc:
        LOG.warning("Article unavailable: %s: %s", url, exc)
        return None
