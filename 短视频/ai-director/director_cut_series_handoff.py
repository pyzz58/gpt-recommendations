#!/usr/bin/env python3
"""QO-D13/D14: selected auteur cut -> screened writer rewrite -> fresh series.

NO new screenplay editor or series scheduler. Existing director_creative_cut,
screenplay_director_handoff, screenplay_series_delivery and the absolute
post-production timeline remain authoritative. The bridge audits each omitted
or rewritten SOURCE BEAT and prevents a selected short cut being silently
replaced by a longer/renumbered or differently split screenplay. No side
effects, model calls, forged author identity or production approval.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import math

import agent_team as team
import director_creative_cut as creative
import screenplay_series_delivery as series
import screenplay_director_handoff as screenplay
import series_final_timeline as final_timeline
import closing_evidence_card as evidence

VERSION = "director-selected-cut-to-screenwriter-series-v1"
EXTRAS = ("intro_s", "recap_s", "bridge_s", "outro_s", "evidence_s")
FIELDS = (
    "source_beat_id", "operation", "new_beat_ids",
    "writer_explanation", "meaning_and_character_or_fact_risk",
    "why_this_is_faithful_or_director_must_reconsider",
)
MAX_NOTE = 2200
EPS = 1e-4


class CutSeriesHandoffError(ValueError):
    """Opaque codes never disclose a manuscript or actor name."""


def _need(flag, code):
    if not flag:
        raise CutSeriesHandoffError(code)


def _text(value, code):
    _need(isinstance(value, str) and
          24 <= len(value.strip()) <= MAX_NOTE and "\0" not in value, code)


def _selected(original_handoff, original_dossier, candidate_cuts, choice):
    report = creative.validate_cut_comparison(
        original_handoff, original_dossier, candidate_cuts, choice)
    chosen = next(
        x for x in candidate_cuts
        if team.fingerprint(x) == report["selected_cut_digest"])
    cut_proof = creative.validate_cut(
        original_handoff, original_dossier, chosen)
    return report, chosen, cut_proof


def _beats(handoff):
    beats = series._handoff(handoff)
    return {row["id"]: row for _, row in beats}, [row["id"] for _, row in beats]


def _exact_credits(ep):
    v = ep["evidence_s"]
    _need(type(v) in (int, float) and math.isfinite(v)
          and (abs(v) <= EPS or abs(v - evidence.DURATION_S) <= EPS),
          "CUT_SERIES_SOURCE_CREDITS_MUST_BE_ZERO_OR_EXACTLY_1_8S")


def director_selection_packet(original_handoff, original_dossier,
                              candidate_cuts, choice):
    """Unsent director selection; writer route is canonical existing module."""
    comparison, selected, proposal = _selected(
        original_handoff, original_dossier, candidate_cuts, choice)
    for ep in selected["episodes"]:
        _exact_credits(ep)
    writer_request = (
        creative.writer_revision_request(
            original_handoff, original_dossier, selected)
        if proposal["script_revision_required"] else None)
    return {
        "kind": "unsent_authored_director_cut_selection_for_writer_or_series",
        "version": VERSION,
        "original_screenplay_digest": proposal["source_digest"],
        "director_cut_choice_digest": comparison["choice_digest"],
        "selected_cut_digest": proposal["director_cut_digest"],
        "selected_story_seconds": proposal["proposed_story_seconds"],
        "selected_episode_count": proposal["proposed_episode_count"],
        "selected_original_episode_boundaries": deepcopy(
            proposal["episode_budgets"]),
        "writer_revision_necessary": proposal["script_revision_required"],
        "unsent_original_screenwriter_revision_work_order": writer_request,
        "next_step": ("writer_independent_rewrite_and_new_source_review"
                      if writer_request else
                      "validate_direct_series_from_same_screenplay"),
        "director_choice_does_not_authenticate_author_consent": True,
        "old_source_and_original_crews_left_unchanged": True,
        "media_generation_or_dispatch_authorized": False,
    }


def rewrite_reconciliation_request(original_handoff, original_dossier,
                                   candidate_cuts, choice, new_handoff,
                                   new_dossier):
    """Ask for origin-to-new beat links after the NORMAL screenplay review.

    The new text is NOT accepted merely because a director preferred the cut.
    A distinct source-locked, structurally reviewed new handoff is necessary.
    """
    chosen_receipt = director_selection_packet(
        original_handoff, original_dossier, candidate_cuts, choice)
    _need(chosen_receipt["writer_revision_necessary"],
          "CUT_SERIES_ORIGINAL_SELECTION_DID_NOT_REQUIRE_REWRITE")
    old, _ = _beats(original_handoff)
    new, _ = _beats(new_handoff)
    _need(new_handoff["screenplay_text_digest"] !=
          original_handoff["screenplay_text_digest"],
          "CUT_SERIES_OLD_SCREENPLAY_NOT_REWRITTEN")
    series.validate_dossier(new_handoff, new_dossier)
    _need(new_handoff["screenplay_quality_human_verified"] is False and
          new_handoff["reviewer_identity_authenticated"] is False and
          new_handoff["publication_allowed"] is False,
          "CUT_SERIES_FALSE_AUTHOR_OR_PUBLICATION_RIGHTS")
    return {
        "kind": "unsent_writer_director_origin_beat_reconciliation",
        "version": VERSION,
        "model_dispatch_authorized": False,
        "messages": [
            {"role": "system", "content": (
                "你是负责新拍摄剧本的专业编剧及总导演对稿助手，"
                "不是可改写既有已审定剧本的第二导演。"
                "将原导演选中的逐节拍删减/压缩计划和新完整剧本"
                "逐项映射。每个原节拍都要说明保留、压缩或省略后，"
                "准确落在新版哪一个或哪几个beat；合并源beat允许"
                "多对一，但要把每条因果和事实交代清楚；省略的"
                "必须没有暗中复活。未说明来源的新节拍也不能"
                "秘密混入，若是编剧新提案请返回总导演重审。"
                "完全保留的节拍必须与原事件、台词、旁白和时长"
                "逐字段相同，否则不能谎称保持原样。"
                "总导演原来三集的方案不能因新稿重新变成四集而"
                "悄悄通过，更不能把片尾来源页预算从1.8秒改成1秒。"
                "所有工作是对稿草案，作者同意、真人编剧评审、"
                "模型调用、生成媒资、付费与发行一律未获授权。")},
            {"role": "user", "content": __import__("json").dumps({
                "original_screenplay_digest": original_handoff[
                    "screenplay_text_digest"],
                "new_screenplay_digest": new_handoff[
                    "screenplay_text_digest"],
                "selected_cut_digest": chosen_receipt["selected_cut_digest"],
                "original_beats": old,
                "new_beats": new,
                "selected_cut": next(x for x in candidate_cuts
                                     if team.fingerprint(x) ==
                                     chosen_receipt["selected_cut_digest"]),
                "required_output_keys": [
                    "version", "original_screenplay_digest",
                    "new_screenplay_digest", "selected_cut_digest",
                    "decisions", "independent_author_review_authenticated"],
                "each_mapping_fields": list(FIELDS),
                "no_real_human_approval_is_claimed": True,
            }, ensure_ascii=False, separators=(",", ":"))},
        ],
    }


def _verify_mapping(original_handoff, new_handoff, cut, mapping):
    old, old_ids = _beats(original_handoff)
    new, new_ids = _beats(new_handoff)
    _need(type(mapping) is dict and set(mapping) == {
        "version", "original_screenplay_digest", "new_screenplay_digest",
        "selected_cut_digest", "decisions",
        "independent_author_review_authenticated"},
        "CUT_SERIES_ORIGIN_MAPPING_SHAPE")
    _need(mapping["version"] == VERSION and
          mapping["original_screenplay_digest"] ==
          original_handoff["screenplay_text_digest"] and
          mapping["new_screenplay_digest"] ==
          new_handoff["screenplay_text_digest"] and
          mapping["selected_cut_digest"] == team.fingerprint(cut) and
          mapping["independent_author_review_authenticated"] is False,
          "CUT_SERIES_MAPPING_STALE_OR_FORGED_APPROVAL")
    rows = mapping["decisions"]
    _need(isinstance(rows, list) and len(rows) == len(cut["decisions"]),
          "CUT_SERIES_ORIGINAL_BEAT_DECISION_COVERAGE")
    forward, inverse = {}, defaultdict(list)
    for original, actual in zip(cut["decisions"], rows):
        _need(type(actual) is dict and set(actual) == set(FIELDS) and
              actual["source_beat_id"] == original["beat_id"] and
              actual["operation"] == original["operation"],
              "CUT_SERIES_REWRITE_MAPPING_NOT_FROM_SELECTED_CUT")
        for key in ("writer_explanation", "meaning_and_character_or_fact_risk",
                    "why_this_is_faithful_or_director_must_reconsider"):
            _text(actual[key], "CUT_SERIES_WRITER_SOURCE_LINK_REASON_MISSING")
        ids = actual["new_beat_ids"]
        _need(isinstance(ids, list) and
              all(isinstance(x, str) and x in new for x in ids)
              and len(ids) == len(set(ids)),
              "CUT_SERIES_UNKNOWN_OR_DUPLICATED_NEW_BEAT_ID")
        if actual["operation"] == "omit":
            _need(not ids, "CUT_SERIES_OMITTED_BEAT_SECRETLY_REAPPEARED")
        else:
            _need(bool(ids), "CUT_SERIES_RETAINED_BEAT_HAS_NO_REWRITE_LINEAGE")
        if actual["operation"] == "retain":
            _need(len(ids) == 1 and ids[0] == original["beat_id"] and
                  all(new[ids[0]].get(k) == old[original["beat_id"]].get(k)
                      for k in ("action", "dialogue", "voiceover", "duration_s")),
                  "CUT_SERIES_RETAINED_BEAT_WAS_ACTUALLY_REWRITTEN")
        forward[original["beat_id"]] = list(ids)
        for ident in ids:
            inverse[ident].append(original["beat_id"])
    _need(set(inverse) == set(new_ids),
          "CUT_SERIES_UNACCOUNTED_OR_INVENTED_NEW_STORY_BEATS")
    for target, origins in inverse.items():
        if len(origins) > 1:
            _need(all(next(row["operation"] for row in cut["decisions"]
                           if row["beat_id"] == origin) == "condense"
                      for origin in origins),
                  "CUT_SERIES_ONLY_CONDENSED_SOURCE_CAN_SHARE_NEW_BEAT")
    old_sequence = [row["beat_id"] for row in cut["decisions"]
                    if row["operation"] != "omit"]
    projected = []
    for bid in new_ids:
        for source_id in inverse[bid]:
            if not projected or projected[-1] != source_id:
                projected.append(source_id)
    _need(projected == old_sequence,
          "CUT_SERIES_REWRITE_REORDERED_DIRECTOR_SELECTED_CAUSAL_BEATS")
    return forward, inverse, old_sequence


def _episode_origins(episode, inverse):
    ordered = []
    for bid in episode["beat_ids"]:
        for old in inverse[bid]:
            if not ordered or ordered[-1] != old:
                ordered.append(old)
    return ordered


def series_from_selected_cut(original_handoff, original_dossier,
                             candidate_cuts, choice, *,
                             final_handoff, final_dossier, final_breakdown,
                             rewrite_mapping=None):
    """Reconstruct a completely FRESH per-episode DAG from selected cut.

    Old cut numbers are proposals only. If the writer changed any timing or
    chapter boundary, we surface drift and do NOT authenticate that the
    director accepted it. The new handoff's original screenplay review is
    reused; no prior crew deliverable or human approval is migrated.
    """
    comparison, cut, proposed = _selected(
        original_handoff, original_dossier, candidate_cuts, choice)
    original, _ = _beats(original_handoff)
    for ep in cut["episodes"]:
        _exact_credits(ep)
    original_digest = original_handoff["screenplay_text_digest"]
    is_rewrite = proposed["script_revision_required"]
    if is_rewrite:
        _need(final_handoff["screenplay_text_digest"] != original_digest,
              "CUT_SERIES_SCRIPT_REWRITE_WAS_NOT_PERFORMED")
        _need(rewrite_mapping is not None,
              "CUT_SERIES_REWRITTEN_SCRIPT_NEEDS_ORIGIN_AUDIT")
        _, inverted, _ = _verify_mapping(
            original_handoff, final_handoff, cut, rewrite_mapping)
    else:
        _need(final_handoff["screenplay_text_digest"] == original_digest
              and rewrite_mapping is None,
              "CUT_SERIES_UNCHANGED_CUT_CANNOT_SWAP_SOURCE")
        _need(final_handoff["director_base_digest"] ==
              original_handoff["director_base_digest"],
              "CUT_SERIES_NO_REWRITE_REQUIRES_SAME_BASE")
        inverted = {bid: [bid] for bid in original}
    _need(final_handoff.get("status") == "director_planning_intake_only" and
          final_handoff.get("screenplay_quality_human_verified") is False and
          final_handoff.get("reviewer_identity_authenticated") is False and
          final_handoff.get("publication_allowed") is False,
          "CUT_SERIES_AUTHOR_APPROVAL_NOT_AUTHENTICATED")
    original_dossier_check = series.validate_dossier(
        original_handoff, original_dossier)
    new_dossier_check = series.validate_dossier(final_handoff, final_dossier)
    current_breakdown = series.validate_breakdown(
        final_handoff, final_dossier, final_breakdown)
    _need(len(final_breakdown["episodes"]) == len(cut["episodes"]),
          "CUT_SERIES_EPISODE_COUNT_CHANGED_WITHOUT_NEW_DIRECTOR_CHOICE")
    required_copy = {
        "intro_s", "recap_s", "bridge_s", "outro_s", "evidence_s"
    }
    drift = []
    for index, (before, after, report) in enumerate(zip(
            cut["episodes"], final_breakdown["episodes"],
            current_breakdown["episodes"]), start=1):
        _exact_credits(after)
        expected = before["beat_ids"]
        actual = _episode_origins(after, inverted)
        _need(actual == expected,
              "CUT_SERIES_SELECTED_BREAKPOINT_CHANGED_OR_BEAT_REORDERED")
        for key in sorted(required_copy):
            _need(abs(before[key] - after[key]) < EPS,
                  "CUT_SERIES_SELECTED_EXTRA_OR_CREDITS_TIME_CHANGED")
        before_budget = proposed["episode_budgets"][index-1]["total_seconds"]
        current_budget = report["total_s"]
        if abs(current_budget - before_budget) >= EPS:
            drift.append({
                "episode_id": after["episode_id"],
                "director_selected_budget_s": before_budget,
                "rewritten_plan_budget_s": current_budget,
                "difference_s": round(current_budget-before_budget, 4),
                "director_reconfirmation_required": True,
            })
    # If the writer changes the selected episode timing, no new crew may be
    # handed out: the real director must re-select a truthful new cut FIRST.
    # This prevents consumers from reading a planning-only warning but then
    # accidentally dispatching the attached, unreviewed production packets.
    new_series = None
    absolute = []
    if not drift:
        new_series = series.build_per_episode_crew(
            final_handoff, final_dossier, final_breakdown)
        for episode in new_series["episodes"]:
            epbase = episode["authoritative_episode_base"]
            try:
                card = evidence.build_card(epbase)
                timeline = final_timeline.compile_final_timeline(epbase, card)
            except (evidence.ClosingCardError,
                    final_timeline.SeriesTimelineError):
                raise CutSeriesHandoffError(
                    "CUT_SERIES_FINAL_ABSOLUTE_EDITOR_TIMELINE_REJECTED") from None
            _need(timeline is not None and
                  timeline["fits_90_second_budget"] is True and
                  timeline["last_card_is_final_segment"] is True and
                  timeline["actual_final_media_verified"] is False,
                  "CUT_SERIES_FALSE_COMPLETE_EPISODE_BUDGET")
            absolute.append({
                "episode_id": episode["episode_id"],
                "final_duration_s": timeline["planned_final_duration_s"],
                "final_absolute_editor_timeline_digest":
                    team.fingerprint(timeline),
                "media_verified": False,
            })
    return {
        "kind": "source_review_bound_selected_director_cut_series_preview",
        "version": VERSION,
        "selected_director_cut_digest": proposed["director_cut_digest"],
        "selected_director_choice_digest": comparison["choice_digest"],
        "original_screenplay_digest": original_digest,
        "new_screenplay_digest": final_handoff["screenplay_text_digest"],
        "old_writer_dossier_digest":
            original_dossier_check["dossier_digest"],
        "new_writer_dossier_digest":
            new_dossier_check["dossier_digest"],
        "reconciliation_digest": (team.fingerprint(rewrite_mapping)
                                  if rewrite_mapping is not None else None),
        "new_actual_series_breakdown_digest":
            current_breakdown["director_breakdown_digest"],
        "episodes_built_from_new_authoritative_script":
            deepcopy(new_series),
        "absolute_final_editor_timeline_receipts": absolute,
        "director_cut_budget_drift": drift,
        "must_reopen_director_selection_if_budget_drift": bool(drift),
        "new_team_state_pristine_and_unapproved": (
            new_series is not None and all(
                all(task["status"] == "pending" and task["revision"] == 0
                    and task["deliverable"] is None
                    for task in episode["crew"]["tasks"].values())
                for episode in new_series["episodes"])),
        "new_crew_packets_withheld_until_director_reconfirms": bool(drift),
        "next_step": (
            "return_to_director_cut_comparison_for_new_screenplay"
            if drift else
            "fresh_crew_planning_requires_separate_real_director_review"),
        "old_crews_not_migrated_to_new_script": True,
        "new_source_structural_review_does_not_prove_author_identity": True,
        "all_screenplay_beat_revisions_need_real_editorial_review": is_rewrite,
        "safe_to_use_as_automatically_approved_director_cut": False,
        "paid_generation_or_publication_authorized": False,
        "media_generated_or_art_quality_proven": False,
    }
