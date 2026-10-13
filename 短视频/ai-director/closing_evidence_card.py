#!/usr/bin/env python3
"""One-page, 1–2 second FINAL evidence/credits card (postproduction only).

Never feeds exact Chinese text to a generative-video model. No verified source
is invented. Full reference details belong in publication notes; a 1.8-second
screen cannot carry a readable bibliography of unlimited length.
"""
from __future__ import annotations

from copy import deepcopy
from html import escape
from urllib.parse import urlparse

VERSION = "closing-evidence-card-v1"
DURATION_S = 1.8
MAX_VISIBLE_LINES = 7
MAX_LINE_CHARS = 54


class ClosingCardError(ValueError):
    pass


def build_card(plan):
    """Append AFTER the last story shot. Return None for pure fiction/no claims."""
    if not isinstance(plan, dict) or not isinstance(plan.get("claims"), list):
        raise ClosingCardError("CLOSING_CARD_PLAN_INVALID")
    series = plan.get("series_context")
    if series is not None:
        if (not isinstance(series, dict) or
                type(series.get("include_final_evidence_card")) is not bool):
            raise ClosingCardError("CLOSING_CARD_SERIES_EXPLICIT_CHOICE_REQUIRED")
        if not series["include_final_evidence_card"]:
            return None
    claims = plan["claims"]
    refs = plan.get("references", [])
    # Claims are NOT citations. The legacy article intake creates a claim for
    # every narration fragment, which does not authorize an evidence roll.
    # Risk-domain labels and unsourced numbers cannot imply source materials.
    identifiers = [c.get("id") for c in claims if isinstance(c, dict)]
    if len(identifiers) != len(claims) or len(set(identifiers)) != len(claims) or (
            not all(isinstance(x, str) and x for x in identifiers)):
        raise ClosingCardError("CLOSING_CARD_CLAIMS_INVALID")
    refs = plan.get("references", [])
    if not isinstance(refs, list):
        raise ClosingCardError("CLOSING_CARD_REFERENCES_INVALID")
    by_claim = {}
    for r in refs:
        if not isinstance(r, dict) or not isinstance(r.get("claim_id"), str) or (
                r["claim_id"] in by_claim):
            raise ClosingCardError("CLOSING_CARD_REFERENCE_MAPPING")
        by_claim[r["claim_id"]] = r
    if set(by_claim) - set(identifiers):
        raise ClosingCardError("CLOSING_CARD_UNKNOWN_REFERENCE")
    visible, details = [], []
    for c in claims:
        cid = c["id"]
        ref = by_claim.get(cid)
        url = c.get("evidence_url")
        if ref is None and not url:
            continue  # no placeholder source for claims lacking real material
        if ref is None:
            if not isinstance(url, str) or urlparse(url).scheme not in ("http", "https") or not urlparse(url).netloc:
                raise ClosingCardError("CLOSING_CARD_EVIDENCE_URL_INVALID")
            label = cid + "｜原文附有来源链接 · 待核查"
        else:
            # These fields are metadata supplied in the source, not invented
            # bibliographic facts or independently verified publications.
            author = str(ref.get("author") or "作者未提供")
            year = str(ref.get("year") or "年份未提供")
            journal = str(ref.get("journal") or "出处待补")
            label = cid + "｜" + author + " " + year + " · " + journal
        visible.append(label)
        details.append({
            "claim_id": cid, "source_quote": c.get("source_quote", ""),
            "review_state": c.get("status", "needs_review"),
            "reference": deepcopy(ref), "original_evidence_url": url,
            "reference_reviewed": False,
        })
    if not visible:
        return None
    # One and only one end card. Do not split to extra pages, silently truncate
    # citations or falsely mark an overcrowded page as legible.
    too_dense = len(visible) > MAX_VISIBLE_LINES or any(
        len(line) > MAX_LINE_CHARS for line in visible)
    return {
        "version": VERSION, "kind": "final_single_page_evidence_credits",
        "shot_id": "POST_END_CREDITS", "production_route": "postproduction_only",
        "position": "after_all_story_shots", "start_s": plan["duration"],
        "duration_s": DURATION_S, "end_s": round(plan["duration"] + DURATION_S, 2),
        "layout": {"aspect_ratio": "9:16", "width": 1080, "height": 1920,
                   "background": "#111111", "foreground": "#FFFFFF",
                   "static_page": True, "scroll": False, "fade": False},
        "title": "依据与鸣谢", "visible_lines": visible,
        "full_reference_details_for_description": details,
        "requires_human_relayout": too_dense,
        "all_references_verified": False,  # source status is NOT independent fact-checking
        "rendering": "offline_svg_then_editor_composite",
        "audio": "silent_no_voiceover",
        "video_model_prompt": None,
        "external_model_call_allowed": False,
        "publication_approval": False,
    }


def render_svg(card):
    """Escaped, standalone SVG draft; requires QC before burning into video."""
    if not isinstance(card, dict) or card.get("version") != VERSION:
        raise ClosingCardError("CLOSING_CARD_INVALID")
    if card["requires_human_relayout"]:
        raise ClosingCardError("CLOSING_CARD_DENSITY_REQUIRES_RELAYOUT")
    title = escape(card["title"], quote=True)
    lines = card["visible_lines"]
    if not isinstance(lines, list) or not 1 <= len(lines) <= MAX_VISIBLE_LINES:
        raise ClosingCardError("CLOSING_CARD_VISIBLE_LINES_INVALID")
    elements = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">',
        '<rect width="1080" height="1920" fill="#111111"/>',
        '<text x="100" y="620" font-family="Noto Sans CJK SC, sans-serif" font-size="62" font-weight="bold" fill="white">' + title + '</text>',
    ]
    for idx, item in enumerate(lines):
        if not isinstance(item, str) or len(item) > MAX_LINE_CHARS:
            raise ClosingCardError("CLOSING_CARD_VISIBLE_LINE_INVALID")
        elements.append(
            '<text x="100" y="' + str(720 + idx * 76) +
            '" font-family="Noto Sans CJK SC, sans-serif" font-size="36" fill="white">' +
            escape(item, quote=True) + '</text>')
    elements += [
        '<text x="100" y="1660" font-family="Noto Sans CJK SC, sans-serif" font-size="28" fill="#BBBBBB">完整出处及核查状态见发布说明</text>',
        '</svg>',
    ]
    return "\n".join(elements)
