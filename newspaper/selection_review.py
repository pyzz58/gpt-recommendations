"""One bounded candidate review, using the existing issue ledger and selector.

Rules inspired by AIHOT's event scoring and BestBlogs' article assessment;
independently written for this newspaper. No upstream runtime dependency.
"""
from __future__ import annotations
import json
import logging
from decimal import Decimal
from pathlib import Path
import requests
from edition_budget import BudgetExhausted
from llm_budget import conservative_input_tokens, estimate_peak_cost, DEFAULT_MODEL

LOG = logging.getLogger("newspaper.selection")
MAX_CANDIDATES = 24
MAX_OUTPUT = 2800
REVIEW_CAP = Decimal("0.18")  # part of, never in addition to, the 1 CNY issue cap
AXES = ("impact", "novelty", "evidence", "relevance", "completeness")


def review_candidates(candidates, enriched, key, ledger, *, transport=None,
                      before_request=None):
    """Return URL->reviewed copies; failures leave the entire original order intact.

    Round-robin across existing desks; never reintroduce filtered/unreadable URLs.
    Scores can reorder only: quotas, topic eligibility and event dedup stay intact.
    """
    shortlist, seen = [], set()
    rows = list(candidates.values())
    for i in range(max((len(row) for row in rows), default=0)):
        for row in rows:
            if i >= len(row):
                continue
            url = row[i]["url"]
            if url not in seen and enriched.get(url):
                seen.add(url)
                shortlist.append(enriched[url])
                if len(shortlist) == MAX_CANDIDATES:
                    break
        if len(shortlist) == MAX_CANDIDATES:
            break
    if not shortlist or not key or ledger is None:
        return enriched
    records = []
    for i, article in enumerate(shortlist):
        body = str(article.get("reading_en") or "")
        # Clearly labelled sample: never claim to have assessed an unseen full text.
        excerpt = body if len(body) <= 1500 else body[:1000] + "\n[… omitted …]\n" + body[-500:]
        records.append({"id": str(i), "title": article.get("title", ""),
                        "excerpt": excerpt, "sampled": len(body) > 1500})
    messages = [
        {"role": "system", "content": Path(__file__).with_name(
            "SELECTION_REVIEW.md").read_text(encoding="utf-8")},
        {"role": "user", "content": json.dumps({"articles": records}, ensure_ascii=False)},
    ]
    if estimate_peak_cost(DEFAULT_MODEL, conservative_input_tokens(messages), MAX_OUTPUT) > REVIEW_CAP:
        LOG.warning("NEWSROOM_SELECTION_REVIEW=skipped_input_cost_cap")
        return enriched
    try:
        raw = ledger.request(messages, MAX_OUTPUT, key, purpose="selection",
                             transport=transport, before_request=before_request)
        items = json.loads(raw)["items"]
        if not isinstance(items, list) or len(items) != len(records):
            raise ValueError("Review must cover the exact shortlist")
        scores = {}
        for item in items:
            identifier = item["id"]
            if not isinstance(identifier, str) or identifier not in {r["id"] for r in records} or identifier in scores:
                raise ValueError("Invalid or repeated candidate ID")
            if any(type(item.get(axis)) is not int or not 0 <= item[axis] <= 5 for axis in AXES):
                raise ValueError("Invalid candidate score")
            scores[identifier] = {axis: item[axis] for axis in AXES}
        reviewed = dict(enriched)
        for i, article in enumerate(shortlist):
            axes = scores[str(i)]
            # Event value dominates; completeness is only a representative-story tie break.
            event_score = sum(axes[k] * w for k, w in
                              (("impact", 7), ("novelty", 5), ("evidence", 5), ("relevance", 3)))
            baseline = article.get("importance_score", 0)
            priority = max(baseline - 20, min(baseline + 20, event_score))
            reviewed[article["url"]] = {**article, "selection_review": axes,
                "selection_priority": priority, "representative_quality": axes["completeness"]}
        LOG.info("NEWSROOM_SELECTION_REVIEW=accepted candidates=%d", len(shortlist))
        return reviewed
    except (BudgetExhausted, RuntimeError, ValueError, TypeError, KeyError, requests.RequestException) as exc:
        # No raw provider response, prompt or exception message is logged.
        LOG.warning("NEWSROOM_SELECTION_REVIEW=fallback reason=%s", type(exc).__name__)
        return enriched
