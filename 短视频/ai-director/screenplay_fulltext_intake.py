#!/usr/bin/env python3
"""Complete-text intake solely for the screenplay writer.

Unlike article_intake.prepare_episode this indexes the ENTIRE chosen source
scope before adapting anything. Units are source paragraphs/clauses, NOT
narration, facts, model shots or approved script. No model/network/file writes.
The old director crew is reused only after a reviewable screenplay is produced.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re

import agent_team
import article_intake
import director
import screenplay_adaptation
import screenplay_director_handoff

VERSION = "screenwriter-fulltext-intake-v1"
MAX_UNITS_PER_SCREENPLAY = 100
MAX_UNIT_CHARS = 180
BREAK_CHARS = frozenset("。！？!?；;\n")
MIN_SOFT_BREAK = 65


class FulltextIntakeError(ValueError):
    """Stable codes; source text is never reproduced in errors."""


def _require(condition, code):
    if not condition:
        raise FulltextIntakeError(code)


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _units(source, start, end):
    """Exact Python character offsets; ignore whitespace only for coverage.

    Segmentation is for source reference and explanation, never for shot timing.
    Long unpunctuated paragraphs remain fully represented via hard splits.
    """
    units = []
    cursor = start
    while cursor < end:
        while cursor < end and source[cursor].isspace():
            cursor += 1
        if cursor >= end:
            break
        left = cursor
        right = min(left + MAX_UNIT_CHARS, end)
        selected = right
        for i in range(left, right):
            if i - left + 1 >= MIN_SOFT_BREAK and source[i] in BREAK_CHARS:
                selected = i + 1
                break
        cursor = selected
        while cursor > left and source[cursor - 1].isspace():
            cursor -= 1
        _require(cursor > left, "FULLTEXT_EMPTY_UNIT")
        fragment = source[left:cursor]
        units.append({
            "id": "U%04d" % (len(units) + 1),
            "span": [left, cursor], "sha256": _sha(fragment),
            "chars": len(fragment), "text": fragment,
        })
        cursor = selected
    # Check ALL original non-whitespace characters, in exact order. A model
    # must still read them; this deterministic gate only catches text loss.
    expected = "".join(c for c in source[start:end] if not c.isspace())
    actual = "".join(c for u in units for c in u["text"] if not c.isspace())
    _require(expected == actual, "FULLTEXT_UNCOVERED_SOURCE")
    _require(bool(units), "FULLTEXT_EMPTY_SCOPE")
    return units


def _scope(source, episode_id):
    if episode_id == "FULL":
        return [0, len(source)], "FULL", "完整文案"
    _require(isinstance(episode_id, str), "FULLTEXT_SCOPE_INVALID")
    sections = article_intake.split_article(source)
    section = next((s for s in sections if s.key == episode_id), None)
    _require(section is not None, "FULLTEXT_UNKNOWN_SECTION")
    return [section.start, section.end], episode_id, section.title


def prepare_fulltext(source, *, episode_id="FULL", risk_domain=None):
    """Return PRIVATE intake with exact content spans and placeholder base.

    For long books require explicit chapter selection; don't silently shorten
    the source to an acceptable runtime. Source 250k maximum matches reader.
    """
    try:
        article_intake._article(source)
    except ValueError:
        raise FulltextIntakeError("FULLTEXT_SOURCE_INVALID") from None
    _require(risk_domain is None or risk_domain in director.RISK_DOMAINS,
             "FULLTEXT_RISK_DOMAIN_INVALID")
    # Index full manuscript first, including material before first heading.
    entire = _units(source, 0, len(source))
    span, selected_id, title = _scope(source, episode_id)
    chosen = _units(source, *span)
    _require(len(chosen) <= MAX_UNITS_PER_SCREENPLAY,
             "FULLTEXT_SELECT_CHAPTER_OR_SHORTER_SCOPE")
    selected_text = source[span[0]:span[1]]
    # Extract only URLs literally present in the selected author text.
    # They are candidates for manual verification, not fabricated citations.
    evidence_links = []
    for match in re.finditer(r"https?://[^\s<>）)]+", selected_text):
        link = match.group().rstrip(".,;。")
        if link:
            evidence_links.append({
                "url": link,
                "source_span": [span[0] + match.start(),
                                span[0] + match.start() + len(link)],
                "status": "source_supplied_unverified",
            })
    if risk_domain is None:
        # Metadata only: risk classification does not manufacture references.
        chapter = article_intake.Section(
            selected_id, title, span[0], span[1], selected_text, False)
        risk_domain = article_intake._risk(chapter)
    shots = []
    for i, unit in enumerate(chosen):
        # Only a 1-second virtual reference slot; NOT a film shot or VO.
        shot = article_intake._shot_template(
            unit["id"], i, i, 1, "", None, numeric=False)
        shot["claim_ids"] = []
        shot["purpose"] = "screenwriter_source_unit_not_a_film_shot"
        shot["visual"] = "来源文本单元，不代表分镜、视觉方案或演员表演"
        shot["source_span"] = list(unit["span"])
        shot["source_excerpt"] = unit["text"]
        shot["source_excerpt_sha256"] = unit["sha256"]
        shots.append(shot)
    plan = {
        "schema_version": "0.1", "title": title, "platform": "douyin",
        "aspect_ratio": "9:16", "duration": len(shots),
        "risk_domain": risk_domain, "core_message": "待编剧基于全文提炼",
        "audience": "待编剧确定",
        "editorial": {
            "hook": "待编剧根据完整稿件确定",
            "narration_script": "",
            "omissions": [],
        },
        "claims": [], "references": [],
        "visual_bible": {
            "style": "待总导演在编剧完成后设计",
            "palette": "待设计", "lighting": "待设计",
            "typography": "准确文字交给后期", "avoid": "不得编造原稿没有的事实或出处",
        },
        "characters": [],
        "scenes": [{"id": "LOC01", "description":
                    "纯文本来源索引占位；剧本场景尚未形成"}],
        "shots": shots,
        "production": {"voice": "尚无旁白，需编剧完成",
                       "music_license_check": True,
                       "asset_license_check": True,
                       "publishing_status": "source_intake_only"},
    }
    _require(not director.validate(plan)[0], "FULLTEXT_BASE_INVALID")
    return {
        "kind": VERSION, "status": "whole_scope_indexed_not_screenplay",
        "episode_id": selected_id,
        "document_digest": _sha(source), "document_chars": len(source),
        "document_units_indexed": len(entire),
        "document_exact_nonwhitespace_coverage": True,
        "scope_span": span, "scope_digest": _sha(selected_text),
        "scope_chars": len(selected_text), "scope_units": deepcopy(chosen),
        "scope_exact_nonwhitespace_coverage": True,
        "entire_document_selected": span == [0, len(source)],
        "source_supplied_reference_urls": evidence_links,
        "source_supplied_reference_url_count": len(evidence_links),
        "evidence_page_requirement": "optional_if_original_has_evidence",
        "base": plan, "base_digest": agent_team.fingerprint(plan),
        "source_content_is_private": True, "video_shots_created": False,
        "real_narration_selected": False, "claims_or_citations_invented": False,
        "paid_text_model_authorized": False, "director_called": False,
    }


def editor_request(intake, document, *, mode="auto"):
    """Build an UNSENT complete screenplay request, never a short preview."""
    _require(mode in ("auto", "fiction", "documentary"), "FULLTEXT_MODE_INVALID")
    _verify_intake(intake, document)
    scoped = document[slice(*intake["scope_span"])]
    task = screenplay_adaptation.build_editor_request(intake["base"], scoped)
    task["messages"][0]["content"] += (
        "\n【完整文案编剧】source 为已索引的完整选定文案，base_shots 仅是"
        "全文素材单元，不是摄影镜头，也不是限定旁白的185字缩略版。"
        "必须逐一阅读下方 source_units，覆盖所有单元或者逐项记录省略理由，"
        "保留全稿核心思想与原作者意图。根据体裁作必要的改编；纪录类内容"
        "不杜撰史实或名人对白，小说类才可提出戏剧对白，全部按提案审阅。"
        "资料、数据、论据或出处仅在原文确有这些内容时保留并要求核查；"
        "原文没有就不要强加参考文献、证据卡或假造引用。"
        "建议的时长和结构须按内容确定；不能因为旁白预览上限而丢失内容。")
    payload = json.loads(task["messages"][1]["content"])
    payload["source_units"] = deepcopy(intake["scope_units"])
    payload["source_scope_span"] = list(intake["scope_span"])
    payload["source_scope_sha256"] = intake["scope_digest"]
    task["messages"][1]["content"] = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"))
    task["fulltext_source_units"] = deepcopy(intake["scope_units"])
    task["adaptation_mode"] = mode
    task["whole_scope_indexed"] = True
    task["source_document_digest"] = intake["document_digest"]
    task["source_scope_digest"] = intake["scope_digest"]
    task["unverified_source_reference_candidates"] = deepcopy(
        intake["source_supplied_reference_urls"])
    task["citation_policy"] = "use_source_materials_if_present_never_invent"
    task["dispatch_allowed"] = False
    return task


def _verify_intake(intake, source):
    _require(isinstance(intake, dict) and intake.get("kind") == VERSION and
             isinstance(source, str), "FULLTEXT_INTAKE_REQUIRED")
    _require(intake.get("document_digest") == _sha(source),
             "FULLTEXT_DOCUMENT_STALE")
    recomputed = prepare_fulltext(
        source, episode_id=intake["episode_id"],
        risk_domain=intake["base"]["risk_domain"])
    _require(agent_team.fingerprint(recomputed) == agent_team.fingerprint(intake),
             "FULLTEXT_INTAKE_TAMPERED")


def review_packet(intake, document, proposal):
    """Bridge to existing screenplay review without accepting a shorter text."""
    _verify_intake(intake, document)
    selected = document[slice(*intake["scope_span"])]
    packet = screenplay_adaptation.build_review_packet(
        intake["base"], selected, proposal)
    return {
        "kind": "fulltext_screenplay_review_wrapper_v1",
        "scope_document_digest": intake["document_digest"],
        "intake_digest": agent_team.fingerprint(intake),
        "episode_id": intake["episode_id"],
        "source_unit_count": len(intake["scope_units"]),
        "full_nonwhitespace_source_coverage": True,
        "scope_vs_document": ("complete_document" if intake["entire_document_selected"]
                              else "selected_chapter_only"),
        "screenplay_review_packet": packet,
        "critical_ideas_retained": "requires_human_editorial_review",
        "evidence_card_required": False,  # only actual source references trigger it
        "human_approval_authenticated": False,
        "external_calls": 0,
    }


def director_handoff(intake, document, wrapper, decisions, cast_bindings):
    """Existing director contract, tied to revalidated exact fulltext intake."""
    _verify_intake(intake, document)
    _require(isinstance(wrapper, dict) and
             wrapper.get("kind") == "fulltext_screenplay_review_wrapper_v1" and
             wrapper.get("scope_document_digest") == intake["document_digest"] and
             wrapper.get("intake_digest") == agent_team.fingerprint(intake),
             "FULLTEXT_REVIEW_WRONG_SOURCE")
    packet = wrapper.get("screenplay_review_packet")
    _require(isinstance(packet, dict), "FULLTEXT_PACKET_MISSING")
    fresh = review_packet(intake, document, packet.get("proposal"))
    _require(agent_team.fingerprint(fresh) == agent_team.fingerprint(wrapper),
             "FULLTEXT_REVIEW_TAMPERED")
    selected = document[slice(*intake["scope_span"])]
    downstream = screenplay_director_handoff.prepare_handoff(
        intake["base"], selected, packet, decisions, cast_bindings)
    downstream["fulltext_source_document_digest"] = intake["document_digest"]
    downstream["fulltext_review_scope_digest"] = intake["scope_digest"]
    downstream["fulltext_scope_vs_document"] = wrapper["scope_vs_document"]
    downstream["fulltext_critical_ideas_retained_verified"] = False
    downstream["source_units_covered_or_explicitly_omitted"] = True
    downstream["human_approval_authenticated"] = False
    return downstream
