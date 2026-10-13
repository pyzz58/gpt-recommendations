"""Live public RSS source-health audit for CI, no mail or model requests.

Each configured feed is one discovery endpoint, not one independent newsroom.
The report distinguishes reachable, freshly active, unique publishers and
materiality-eligible headlines. Failures are diagnostic rather than fabricated.
"""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import json
import logging
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo

from digest import fetch_one, ROOT
from newsroom import publisher, sections
from source_quality import newsworthiness
from people_overseas import audit_edition
from xueqiu_magazine import audit_public_journal

LOG = logging.getLogger("newspaper.source_audit")


def audit(settings, start, end, worker=fetch_one):
    sources = [
        (category, item)
        for category, entries in settings["feeds"].items()
        for item in entries if not item.get("disabled", False)
    ]
    disabled = [
        f["name"] for arr in settings["feeds"].values()
        for f in arr if f.get("disabled", False)
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        reports = list(executor.map(
            lambda pair: worker(pair[0], pair[1], start, end), sources))
    articles = [item for entries, ok in reports for item in entries]
    by_family = Counter(publisher(a) for a in articles)
    by_section = Counter()
    noise = Counter()
    eligible = []
    for a in articles:
        rating = newsworthiness(a)
        noise[rating["reason"]] += 1
        if not rating["eligible"]:
            continue
        eligible.append(a)
        for section in sections(a):
            by_section[section] += 1
    feed_details = [{
        "source": pair[1]["name"],
        "origin_type": pair[1].get("source_type", "editorial_media_or_institution"),
        "reachable": bool(result[1]),
        "items_last_24h": len(result[0])
    } for pair, result in zip(sources, reports)]
    try:
        people = audit_edition()
        people_health = {"reachable": True, "issue_date": people["issue_date"],
                         "linked_articles": len(people["items"]), "monitor_only": True}
    except Exception as exc:
        people_health = {"reachable": False, "error": type(exc).__name__, "monitor_only": True}
    try:
        journal = audit_public_journal()
        journal_health = {"reachable": True, "page_identified": journal["page_identified"],
                          "visible_issue_titles": journal["visible_issue_titles"],
                          "monitor_only": True}
    except Exception as exc:
        journal_health = {"reachable": False, "error": type(exc).__name__, "monitor_only": True}
    return {
        "xueqiu_journal_monitor": journal_health,
        "people_overseas_monitor": people_health,
        "window_start_beijing": start.isoformat(),
        "window_end_beijing": end.isoformat(),
        "feed_endpoints_configured": len(sources) + len(disabled),
        "feed_endpoints_enabled": len(sources),
        "feeds_http_reachable": sum(ok for _, ok in reports),
        "feeds_with_fresh_items": sum(bool(articles) for articles, ok in reports),
        "disabled": disabled,
        "raw_articles_last_24h": len(articles),
        "independent_publisher_families_with_fresh_articles": len(by_family),
        "by_publisher_family": dict(sorted(by_family.items())),
        "eligible_by_section_before_dedup": dict(sorted(by_section.items())),
        "quality_gate_reasons": dict(sorted(noise.items())),
        "feed_details": feed_details,
        "notes": [
            "Different feeds from the same publisher are not independent coverage.",
            "Titles matching a topic are not automatically important or fact-checked.",
            "Empty feeds may be healthy but have no fresh in-window releases.",
            "RSS-only coverage cannot guarantee no major global event is missed.",
        ],
    }


def main():
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    end = dt.datetime.now(ZoneInfo("Asia/Shanghai"))
    start = end - dt.timedelta(hours=24)
    settings = json.loads((ROOT / "feeds.json").read_text(encoding="utf8"))
    report = audit(settings, start, end)
    dest = Path("/tmp/newspaper-source-audit.json")
    dest.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf8")
    print("NEWSROOM_SOURCE_AUDIT=" + json.dumps({
        k:v for k,v in report.items() if k not in
        ("by_publisher_family", "feed_details", "notes")
    }, ensure_ascii=False, sort_keys=True))
    print("NEWSROOM_SOURCE_AUDIT_PATH=" + str(dest))
    if report["feeds_http_reachable"] == 0:
        raise RuntimeError("No public RSS feeds reachable")
if __name__ == "__main__":
    main()
