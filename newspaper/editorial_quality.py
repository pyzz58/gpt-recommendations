"""Edition-level editorial diagnostics, not an automated fact-checking verdict.

Count only articles with actual bilingual/Chinese line pairs: the PDF renderer
silently skips stories without them. Report evidence gaps without padding news.
"""
from __future__ import annotations

from collections import Counter


def edition_quality_report(grouped: dict, *, expected_min: int = 13) -> dict:
    section_counts = {}
    outlets = set()
    seen_events = set()
    seen_urls = set()
    omissions = []
    repeats = []
    metadata_gaps = []
    short_articles = []
    title_translation_alerts = []
    printed = 0
    selected = 0

    for section, articles in grouped.items():
        printable = 0
        for item in articles:
            selected += 1
            title = str(item.get("title_zh") or item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            source = str(item.get("source") or "").strip()
            marker = {"section": section, "title": title[:120], "url": url}
            pairs = item.get("bilingual_pairs") or []
            if not pairs:
                omissions.append({**marker, "reason": "no_printable_paragraph_pairs"})
                continue
            printable += 1
            printed += 1
            outlets.add(item.get("publisher_family") or source)
            event = item.get("event_key")
            if event:
                if event in seen_events:
                    repeats.append({**marker, "reason": "duplicate_event_key"})
                seen_events.add(event)
            if url:
                if url in seen_urls:
                    repeats.append({**marker, "reason": "duplicate_article_url"})
                seen_urls.add(url)
            if not (title and url and source and item.get("date")):
                metadata_gaps.append(marker)
            if item.get("title_qa_flags"):
                title_translation_alerts.append({
                    **marker, "flags": item["title_qa_flags"]})
            content = str(item.get("reading_en") or item.get("reading_zh") or "")
            # Heuristic only, not a verdict on journalistic completeness.
            if len(content.strip()) < 450:
                short_articles.append({**marker, "body_chars": len(content.strip())})
        section_counts[section] = {
            "selected": len(articles), "printable": printable,
            "omitted": len(articles) - printable
        }

    warnings = []
    if printed < expected_min:
        warnings.append("below_usual_edition_volume_no_padding")
    if omissions:
        warnings.append("selected_articles_missing_printable_text")
    if repeats:
        warnings.append("possible_duplicate_published_events")
    if metadata_gaps:
        warnings.append("published_stories_missing_source_date_or_title")
    if short_articles:
        warnings.append("some_stories_need_length_review")
    if title_translation_alerts:
        warnings.append("machine_translated_titles_need_review")

    return {
        "selected_articles": selected,
        "printable_articles": printed,
        "expected_minimum_not_a_hard_quota": expected_min,
        "distinct_publisher_families_printable": len(outlets),
        "by_section": section_counts,
        "omitted": omissions,
        "possible_duplicates": repeats,
        "metadata_gaps": metadata_gaps,
        "short_article_candidates": short_articles,
        "title_translation_alerts": title_translation_alerts,
        "warnings": warnings,
        "limits": ("This is a structural and length audit, not independent "
                   "verification of facts, translation quality or significance."),
    }
