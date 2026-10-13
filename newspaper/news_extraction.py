"""Optional Newspaper4k extraction fallback using the original downloaded HTML.

No second network request, paywall/login bypass, or attempt to synthesize text.
Newspaper4k is used strictly to recover publicly supplied article-body text
when the primary Trafilatura extractor cannot yield a sufficient reading.
"""
from __future__ import annotations

import logging

LOG = logging.getLogger("daily-news")


def newspaper4k_from_html(url: str, html_text: str) -> str:
    if not html_text or len(html_text) > 5_000_000:
        return ""
    try:
        from newspaper import article as parse_article
        result = parse_article(url, input_html=html_text, language="en")
        text = result.text or ""
        return text.strip()
    except Exception as exc:
        LOG.info("Secondary news extraction unavailable for %s (%s)",
                 url, type(exc).__name__)
        return ""
