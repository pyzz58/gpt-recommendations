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
from news_extraction import newspaper4k_from_html

LOG = logging.getLogger("daily-news")
PAYWALL_PATTERNS = [
    r"subscribe to (?:continue|read|unlock)",
    r"(?:this|the) (?:article|story) is (?:only )?for subscribers",
    r"subscription (?:is )?required",
    r"sign in to (?:continue|read) (?:the |this )?(?:article|story)",
    r"to continue reading,? (?:please )?subscribe",
    r"you have reached your (?:free )?article limit",
]


def looks_paywalled(text: str) -> bool:
    sample = (text[:850] + "\n" + text[-550:]).lower()
    return any(re.search(p, sample, re.I) for p in PAYWALL_PATTERNS)


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
    """Keep only consecutive, complete paragraphs from the article's beginning.

    Older versions jumped among opening/middle/ending paragraphs, which made
    the article read like random cut-and-paste fragments. Avoid that entirely.
    A quote-friendly reading selection is not a licensed full-text republication.
    """
    if not paragraphs or max_chars < 120:
        return "", bool(paragraphs)
    full = "\n\n".join(paragraphs)
    if len(full) <= max_chars:
        return full, False

    chosen = []
    length = 0
    for para in paragraphs:
        prospective = length + (2 if chosen else 0) + len(para)
        if prospective <= max_chars:
            chosen.append(para)
            length = prospective
            continue
        # Stop at the FIRST paragraph that will not fit. Never jump into the
        # middle or end of a story to fill the leftover character budget.
        break

    if chosen:
        return "\n\n".join(chosen), True

    # The article might be a single enormous paragraph. Prefer complete
    # sentences; do not cut in the middle of a sentence or quoted statement.
    candidate = paragraphs[0]
    sentences = re.split(r"(?<=[.!?])\s+(?=[\"'\u201c\u2018A-Z0-9])", candidate)
    complete = []
    used = 0
    for sent in sentences:
        if used + len(sent) + (1 if complete else 0) > max_chars:
            break
        complete.append(sent)
        used += len(sent) + (1 if len(complete) > 1 else 0)
    if not complete:
        # A single sentence exceeding max_chars does not produce an orphaned
        # half-sentence; skip this item so the next accessible article can win.
        return "", True
    return " ".join(complete), True


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
            favor_recall=True, output_format="txt",
        )
        paragraphs = _normalize_paragraphs(raw or "")
        # Mature Newspaper4k parser can recover metadata/article body missed
        # by Trafilatura. It receives the same public HTML, never re-fetches
        # blocked/paid pages and is only used when the primary body is short.
        extraction_engine = "trafilatura"
        if len("\n".join(paragraphs)) < min_chars:
            alternative = _normalize_paragraphs(
                newspaper4k_from_html(url, response.text))
            if len("\n".join(alternative)) > len("\n".join(paragraphs)):
                paragraphs = alternative
                extraction_engine = "newspaper4k_fallback"
        if looks_paywalled("\n".join(paragraphs)):
            LOG.warning("Likely paywall or partial subscription preview, skipping: %s", url)
            return None
        if len("\n".join(paragraphs)) < min_chars:
            LOG.warning("Article text not available via either extractor: %s", url)
            return None
        excerpt, abbreviated = _long_read(paragraphs, max_chars=max_chars)
        # Reject tiny leftovers rather than quietly sending a short article.
        if len(excerpt) < min_chars:
            LOG.warning("No coherent section long enough for a reading: %s", url)
            return None
        enriched = dict(article)
        enriched["reading_en"] = excerpt
        enriched["reading_abbreviated"] = abbreviated
        enriched["article_chars"] = len("\n\n".join(paragraphs))
        enriched["reading_chars"] = len(excerpt)
        enriched["reading_selection"] = "consecutive_from_lead"
        enriched["extraction_engine"] = extraction_engine
        return enriched
    except Exception as exc:
        LOG.warning("Article unavailable: %s: %s", url, exc)
        return None
