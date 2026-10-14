#!/usr/bin/env python3
"""QO-D10: one director's source-locked WHOLE-FILM artistic self-critique.

Unlike a QA scorecard this is a reasoned, genre-dependent comparison of actual
director choices, their counterfactual cost, and what is worth preserving.
Only reviews SCRIPT + ARTISTIC PLANS + supplied CREW DESIGNS. No footage,
audience data, visual judgments, model calls, automatic revision or approval.
Works with the EXISTING director lock, meeting, QO-D03 and QO-D17 plans.
"""
from __future__ import annotations

from copy import deepcopy
import json

import agent_team as team
import director_department_command as department
import director_visual_language as language
import director_artistic_methods as methods

VERSION = "director-holistic-creative-critique-v1"
PHASES = frozenset({"preproduction_plan", "post_department_design"})
CORE_LENSES = (
    "source_meaning_and_integrity",
    "audience_comprehension_or_deliberate_ambiguity",
    "visible_causality_not_illustrative_voiceover",
    "emotional_or_intellectual_progression",
    "visual_motif_transformation",
    "sound_silence_and_perceptual_attention",
    "cut_hold_and_runtime",
    "ending_payoff_or_purposeful_open_question",
)
GENRE_LENSES = {
    "fiction": ("human_desire_choice_consequence",
                "performable_behavior_and_relationships"),
    "documentary": ("source_evidence_and_observation_ethics",
                    "subject_agency_and_truthful_context"),
    "essay": ("argument_fairness_and_qualifications",
              "idea_to_specific_visible_relationship"),
    "hybrid": ("fiction_nonfiction_boundary_and_disclosure",
               "form_changes_and_audience_orientation"),
}
RESULTS = frozenset({
    "supported_on_paper", "plausible_problem", "needs_actual_media",
    "not_applicable_with_reason",
})
REVISIONS = frozenset({
    "director_revise", "return_to_screenwriter",
    "department_refine", "defer_until_media_review",
})
OWNERS = frozenset({
    "director", "screenwriter", "acting", "camera_art", "sound",
    "editing_animation", "ai_technical", "quality_review",
})
OVERALL = frozenset({
    "keep_with_open_questions", "revise_director_plan",
    "return_to_screenwriter", "await_department_design",
})
EVIDENCE_SOURCES = frozenset({
    "audiovisual_shot", "director_department_shot",
    "submitted_department_shot",
})
LENS_FIELDS = (
    "lens", "judgment", "shot_ids", "evidence",
    "concrete_reason", "probable_audience_effect",
    "alternative_and_cost", "limit_of_this_assessment",
)
CHOICE_FIELDS = (
    "shot_ids", "evidence", "distinctive_choice_to_keep",
    "why_it_serves_the_piece", "generic_replacement",
    "irrecoverable_loss_if_replaced",
)
ISSUE_FIELDS = (
    "issue_id", "shot_ids", "evidence", "severity", "diagnosis",
    "viewer_consequence", "alternatives", "owner", "response",
    "exact_next_action", "how_to_review", "uncertainty",
)
ALT_FIELDS = ("approach", "probable_gain", "artistic_cost")
DISSENT_FIELDS = (
    "shot_ids", "approach_a", "approach_b",
    "directors_conditional_preference", "when_to_reverse_preference",
    "question_for_independent_review",
)
LIMITATIONS = {
    "actual_media_seen": False,
    "real_audience_tested": False,
    "independent_craft_review_completed": False,
    "author_change_approved": False,
    "render_or_publish_authorized": False,
}


class WholeFilmCritiqueError(ValueError):
    """Stable error codes never echo script text, quotes or private content."""


def _need(value, code):
    if not value:
        raise WholeFilmCritiqueError(code)


def _shape(value, fields, code):
    _need(isinstance(value, dict) and set(value) == set(fields), code)


def _text(value, code, minimum=22, maximum=3000):
    _need(isinstance(value, str) and
          minimum <= len(value.strip()) <= maximum and
          "\0" not in value, code)


def _ids(value, allowed, code):
    _need(isinstance(value, list) and 1 <= len(value) <= len(allowed) and
          len(set(value)) == len(value) and set(value) <= set(allowed), code)


def _shot_context(base, state, meeting, av_plan, genre,
                  artistic_method_plan, phase):
    _need(phase in PHASES, "WHOLE_FILM_UNKNOWN_PHASE")
    m = department.validate_command(base, state, meeting)
    vision = language.validate(
        base, state, meeting, av_plan,
        artistic_method_plan=artistic_method_plan)
    _need(genre == av_plan["genre"] and genre in GENRE_LENSES,
          "WHOLE_FILM_GENRE_INCONSISTENT")
    artistic = (methods.validate(base, state, meeting, artistic_method_plan)
                if artistic_method_plan is not None else None)
    depts = {}
    for name in department.DEPARTMENTS:
        if name == "director_final":
            continue
        item = state["tasks"][name]
        _need(item["status"] in ("pending", "completed", "stale", "needs_revision"),
              "WHOLE_FILM_UNRECOGNIZED_DEPARTMENT_STATUS")
        completed = item["status"] == "completed"
        depts[name] = {
            "status": item["status"],
            "revision": item["revision"],
            "deliverable_digest": (team.fingerprint(item["deliverable"])
                                   if completed else None),
        }
    return {
        "phase": phase,
        "source_digest": state["source_digest"],
        "episode_base_digest": state["base_digest"],
        "director_lock_digest": m["director_lock_digest"],
        "department_command_digest": m["command_digest"],
        "audiovisual_language_digest": vision["plan_digest"],
        "artistic_methods_digest": (
            artistic["plan_digest"] if artistic else None),
        "genre": genre,
        "department_state": depts,
        "shot_ids": list(state["shot_ids"]),
    }


def _evidence(value, snap, meeting, av_plan, state, *, phase):
    _shape(value, ("source", "shot_id", "department", "exact_excerpt"),
           "WHOLE_FILM_EVIDENCE_SHAPE")
    sid = value["shot_id"]
    _need(sid in snap["shot_ids"] and value["source"] in EVIDENCE_SOURCES,
          "WHOLE_FILM_EVIDENCE_TARGET")
    origin = value["source"]
    dept = value["department"]
    if origin == "audiovisual_shot":
        _need(dept is None, "WHOLE_FILM_PLAN_EVIDENCE_DEPT")
        source = next(s for s in av_plan["shots"] if s["shot_id"] == sid)
    elif origin == "director_department_shot":
        _need(dept in department.DEPARTMENTS,
              "WHOLE_FILM_UNKNOWN_DEPARTMENT")
        source = meeting["departments"][dept]["per_shot"][sid]
    else:
        _need(phase == "post_department_design" and
              dept in snap["department_state"] and
              snap["department_state"][dept]["status"] == "completed",
              "WHOLE_FILM_FAKE_CREW_DELIVERY")
        job = state["tasks"][dept]["deliverable"]
        _need(isinstance(job, dict), "WHOLE_FILM_BAD_CREW_DELIVERY")
        if team.SPECS[dept]["kind"] == "shots":
            _need(isinstance(job.get("shots"), dict) and
                  isinstance(job["shots"].get(sid), dict),
                  "WHOLE_FILM_CREW_SHOT_NOT_DELIVERED")
            source = job["shots"][sid]
        else:
            source = job
    excerpt = value["exact_excerpt"]
    _need(isinstance(excerpt, str) and
          8 <= len(excerpt) <= 240 and
          excerpt in json.dumps(source, ensure_ascii=False),
          "WHOLE_FILM_EVIDENCE_NOT_IN_REAL_SOURCE")
    return sid


def request(base, state, meeting, av_plan, *, phase,
            artistic_method_plan=None):
    """Build the SAME showrunner's unsent, whole-piece artistic critique."""
    snap = _shot_context(
        base, state, meeting, av_plan, av_plan["genre"],
        artistic_method_plan, phase)
    crew = {}
    for name, receipt in snap["department_state"].items():
        crew[name] = {
            "status": receipt["status"],
            "submitted_design": deepcopy(state["tasks"][name]["deliverable"])
            if phase == "post_department_design" and
            receipt["status"] == "completed" else None,
        }
    return {
        "kind": "unsent_same_director_whole_film_critique",
        "version": VERSION,
        "dispatch_allowed": False,
        "media_viewed": False,
        "independent_artistic_quality_certified": False,
        "messages": [
            {"role": "system", "content": (
                "你是负责整部作品思想和观众体验的同一位总导演。现在请暂时把"
                "此前亲自设计的方案当作可以被质疑的假说，对整片作严谨的艺术复审。"
                "不是评分机器人：你必须找出真正成立、值得保护的非套路设计，"
                "也必须指出可能令人误解、疲倦、情感脱节的具体位置。"
                "你的证据只能来自已经提供的导演视听方案、导演会议指令和"
                "确实完成的专业岗位交付；引用其中原句，禁止虚构看过演员"
                "表演、实际成片、观众反馈或已试过的模型效果。"
                "每种判断同时写观众可能感知的事件、另一个可行手法、"
                "它可能改善什么、以及它牺牲的艺术品质。"
                "不要强迫剧情反转、高密度冲突、三秒快切或配乐。"
                "小说有人物选择和后果；纪录片有真实观察及伦理；"
                "论说片重思想转化与论证公平；混合作品谨防事实和戏构混淆。"
                "荒诞喜剧只在导演已有题材选择时分析人物的真实渴望、"
                "合理预期、因果升级、反转与情绪回声，不得硬塞名导风格。"
                "发现故事、事实、人物命运或原对白需要修改时，只能提出"
                "返还编剧的修改提案；视听层由导演提出修订，专业细节"
                "归既有部门，不要给缺席部门捏造交付。"
                "每条建议明确镜头、负责方、如何验证及不确定性，"
                "同时保留值得保护的独特选择。"
                "不许自动执行修改、不请求付费API、不产生或发布媒体，"
                "不能以表格完整认定优秀导演或真人审片已完成。")},
            {"role": "user", "content": json.dumps({
                "snapshot_provenance_copy_exact": snap,
                "phase": phase,
                "source_locked_episode": base,
                "director_meeting": meeting,
                "director_audiovisual_plan": av_plan,
                "selected_artistic_methods": artistic_method_plan,
                "actually_submitted_crew_designs": crew,
                "required_lenses_in_order": list(
                    CORE_LENSES + GENRE_LENSES[snap["genre"]]),
                "required_output_top_fields": [
                    "version", "snapshot", "whole_piece_thesis",
                    "audience_journey_diagnosis", "lens_judgments",
                    "protected_choices", "problems", "creative_disagreements",
                    "overall_next_step", "limitations"],
                "required_lens_fields": list(LENS_FIELDS),
                "required_choice_fields": list(CHOICE_FIELDS),
                "required_problem_fields": list(ISSUE_FIELDS),
                "required_alternative_fields": list(ALT_FIELDS),
                "required_dissent_fields": list(DISSENT_FIELDS),
                "exact_evidence_fields": [
                    "source", "shot_id", "department", "exact_excerpt"],
                "allowed_evidence_sources": sorted(EVIDENCE_SOURCES),
                "allowed_judgments": sorted(RESULTS),
                "allowed_problem_responses": sorted(REVISIONS),
                "allowed_owners": sorted(OWNERS),
                "allowed_overall_next_step": sorted(OVERALL),
                "immutable_limitation_flags": LIMITATIONS,
            }, ensure_ascii=False, separators=(",", ":"))},
        ],
    }


def validate(base, state, meeting, av_plan, critique, *,
             artistic_method_plan=None):
    """Validate provenance, evidence and author boundaries; NOT taste or art."""
    _need(isinstance(critique, dict) and
          isinstance(critique.get("snapshot"), dict),
          "WHOLE_FILM_CRITIQUE_SHAPE")
    snap = _shot_context(base, state, meeting, av_plan,
                         av_plan["genre"], artistic_method_plan,
                         critique["snapshot"].get("phase"))
    _shape(critique, (
        "version", "snapshot", "whole_piece_thesis",
        "audience_journey_diagnosis", "lens_judgments",
        "protected_choices", "problems", "creative_disagreements",
        "overall_next_step", "limitations",
    ), "WHOLE_FILM_CRITIQUE_SHAPE")
    _need(critique["version"] == VERSION and critique["snapshot"] == snap,
          "WHOLE_FILM_STALE_OR_UNBOUND_PROVENANCE")
    _need(critique["limitations"] == LIMITATIONS,
          "WHOLE_FILM_FAKE_MEDIA_OR_ARTISTIC_CERTIFICATION")
    phase = snap["phase"]
    ids = snap["shot_ids"]
    for k in ("whole_piece_thesis", "audience_journey_diagnosis"):
        _text(critique[k], "WHOLE_FILM_NO_OVERALL_ARGUMENT", minimum=45)
    lens_rows = critique["lens_judgments"]
    expected = CORE_LENSES + GENRE_LENSES[snap["genre"]]
    _need(isinstance(lens_rows, list) and
          len(lens_rows) == len(expected),
          "WHOLE_FILM_LENS_COVERAGE_INCOMPLETE")
    for row, name in zip(lens_rows, expected):
        _shape(row, LENS_FIELDS, "WHOLE_FILM_LENS_SHAPE")
        _need(row["lens"] == name and row["judgment"] in RESULTS,
              "WHOLE_FILM_LENS_ORDER_OR_VERDICT")
        _ids(row["shot_ids"], ids, "WHOLE_FILM_LENS_SHOT_IDS")
        sid = _evidence(row["evidence"], snap, meeting, av_plan,
                        state, phase=phase)
        _need(sid in row["shot_ids"],
              "WHOLE_FILM_LENS_UNRELATED_EVIDENCE")
        for k in ("concrete_reason", "probable_audience_effect",
                  "alternative_and_cost", "limit_of_this_assessment"):
            _text(row[k], "WHOLE_FILM_LENS_EMPTY_REASON")
    keep = critique["protected_choices"]
    _need(isinstance(keep, list) and 1 <= len(keep) <= len(ids),
          "WHOLE_FILM_NO_DISTINCTIVE_CHOICES_PROTECTED")
    protected = set()
    for row in keep:
        _shape(row, CHOICE_FIELDS, "WHOLE_FILM_PROTECTED_CHOICE_SHAPE")
        _ids(row["shot_ids"], ids, "WHOLE_FILM_PROTECTED_SHOT_IDS")
        sid = _evidence(row["evidence"], snap, meeting, av_plan,
                        state, phase=phase)
        _need(sid in row["shot_ids"],
              "WHOLE_FILM_CHOICE_UNSUPPORTED_BY_EVIDENCE")
        signature = tuple(row["shot_ids"])
        _need(signature not in protected, "WHOLE_FILM_PROTECTED_CHOICE_DUPLICATE")
        protected.add(signature)
        for k in CHOICE_FIELDS:
            if k not in ("shot_ids", "evidence"):
                _text(row[k], "WHOLE_FILM_PROTECTED_CHOICE_VAGUE")
    problems = critique["problems"]
    _need(isinstance(problems, list) and len(problems) <= 50,
          "WHOLE_FILM_TOO_MANY_PROBLEMS")
    found = set()
    for row in problems:
        _shape(row, ISSUE_FIELDS, "WHOLE_FILM_PROBLEM_SHAPE")
        ident = row["issue_id"]
        _need(isinstance(ident, str) and 3 <= len(ident) <= 64
              and ident not in found,
              "WHOLE_FILM_DUPLICATE_PROBLEM_ID")
        found.add(ident)
        _ids(row["shot_ids"], ids, "WHOLE_FILM_PROBLEM_SHOT_IDS")
        sid = _evidence(row["evidence"], snap, meeting, av_plan,
                        state, phase=phase)
        _need(sid in row["shot_ids"],
              "WHOLE_FILM_PROBLEM_NOT_SOURCE_GROUNDED")
        _need(row["severity"] in ("critical", "significant", "local") and
              row["owner"] in OWNERS and
              row["response"] in REVISIONS,
              "WHOLE_FILM_PROBLEM_OWNER_OR_ACTION")
        if row["response"] == "return_to_screenwriter":
            _need(row["owner"] == "screenwriter",
                  "WHOLE_FILM_WRITER_AUTHORITY_REQUIRED")
        elif row["response"] == "director_revise":
            _need(row["owner"] == "director",
                  "WHOLE_FILM_DIRECTOR_OWNERSHIP_REQUIRED")
        elif row["response"] == "department_refine":
            _need(row["owner"] in (
                "acting", "camera_art", "sound", "editing_animation",
                "ai_technical"),
                "WHOLE_FILM_SPECIFIC_SPECIALIST_REQUIRED")
            _need(phase == "post_department_design" and
                  snap["department_state"][row["owner"]]["status"] == "completed",
                  "WHOLE_FILM_CANNOT_REVISE_MISSING_SPECIALIST")
        for k in ("diagnosis", "viewer_consequence", "exact_next_action",
                  "how_to_review", "uncertainty"):
            _text(row[k], "WHOLE_FILM_NOT_ACTIONABLE")
        alt = row["alternatives"]
        _need(isinstance(alt, list) and len(alt) == 2,
              "WHOLE_FILM_TWO_ALTERNATIVES_REQUIRED")
        different = set()
        for option in alt:
            _shape(option, ALT_FIELDS, "WHOLE_FILM_ALTERNATIVE_SHAPE")
            for k in ALT_FIELDS:
                _text(option[k], "WHOLE_FILM_ALTERNATIVE_COST_NOT_STATED")
            different.add(option["approach"].strip().casefold())
        _need(len(different) == 2,
              "WHOLE_FILM_IDENTICAL_FAKE_ALTERNATIVES")
    disagreements = critique["creative_disagreements"]
    _need(isinstance(disagreements, list) and len(disagreements) <= 12,
          "WHOLE_FILM_DISSENT_INVALID")
    for row in disagreements:
        _shape(row, DISSENT_FIELDS, "WHOLE_FILM_DISSENT_SHAPE")
        _ids(row["shot_ids"], ids, "WHOLE_FILM_DISSENT_SHOT_IDS")
        for k in DISSENT_FIELDS:
            if k != "shot_ids":
                _text(row[k], "WHOLE_FILM_DISSENT_EMPTY_TRADEOFF")
        _need(row["approach_a"].strip().casefold() !=
              row["approach_b"].strip().casefold(),
              "WHOLE_FILM_NO_GENUINE_ARTISTIC_CHOICE")
    decision = critique["overall_next_step"]
    _need(decision in OVERALL, "WHOLE_FILM_INVALID_OVERALL_STEP")
    if any(row["response"] == "return_to_screenwriter" for row in problems):
        _need(decision == "return_to_screenwriter",
              "WHOLE_FILM_WRITER_CHANGE_CANNOT_BE_APPROVED")
    if any(row["severity"] == "critical" for row in problems):
        _need(decision != "keep_with_open_questions",
              "WHOLE_FILM_CRITICAL_DEFECT_CANNOT_BE_PASSED")
    if any(row["response"] == "director_revise" for row in problems):
        _need(decision in ("revise_director_plan", "return_to_screenwriter"),
              "WHOLE_FILM_DIRECTOR_DEFECT_CANNOT_BE_SILENTLY_KEPT")
    if any(row["response"] == "department_refine" for row in problems):
        _need(decision in ("await_department_design",
                           "revise_director_plan", "return_to_screenwriter"),
              "WHOLE_FILM_SPECIALIST_DEFECT_CANNOT_BE_SILENTLY_KEPT")
    return {
        "kind": "source_locked_director_whole_film_critique_receipt",
        "critique_digest": team.fingerprint(critique),
        "snapshot": deepcopy(snap),
        "phase": phase,
        "lens_count": len(lens_rows),
        "protected_artistic_choices": len(keep),
        "localized_problems": len(problems),
        "writer_revision_proposals": sum(
            r["response"] == "return_to_screenwriter" for r in problems),
        "approved_screenplay_mutations": 0,
        "media_or_independent_art_verification": False,
        "downstream_model_calls": 0,
        "render_or_publish_authorized": False,
    }


def route_critique_proposals(base, state, meeting, av_plan, critique, *,
                             artistic_method_plan=None):
    """Produce scoped, UNSENT action briefs. Never edit state or dispatch."""
    proof = validate(base, state, meeting, av_plan, critique,
                     artistic_method_plan=artistic_method_plan)
    groups = {
        "director_revise": [], "return_to_screenwriter": [],
        "department_refine": [], "defer_until_media_review": [],
    }
    for issue in critique["problems"]:
        groups[issue["response"]].append({
            "issue_id": issue["issue_id"],
            "shot_ids": deepcopy(issue["shot_ids"]),
            "responsible_role": issue["owner"],
            "specific_change_or_review": issue["exact_next_action"],
            "source_grounded_diagnosis": issue["diagnosis"],
            "viewer_consequence": issue["viewer_consequence"],
            "creative_alternatives": deepcopy(issue["alternatives"]),
            "human_verification": issue["how_to_review"],
            "still_only_director_proposal": True,
        })
    return {
        "kind": "unsent_director_critique_artistic_revision_routes",
        "critique_digest": proof["critique_digest"],
        "source_digest": state["source_digest"],
        "director_lock_digest": proof["snapshot"]["director_lock_digest"],
        "actions_by_existing_role": groups,
        "choices_protected_against_generic_rewrites":
            deepcopy(critique["protected_choices"]),
        "existing_agent_ledger_unchanged": True,
        "script_changes_wait_for_screenwriter_and_author": True,
        "specialist_refinement_requires_specific_director_action": True,
        "no_existing_media_review_claim": True,
        "no_automatic_dispatch_or_publication": True,
    }


def request_existing_department_review_with_critique(
        base, state, meeting, av_plan, critique, *,
        artistic_method_plan=None):
    """Optional existing QO-D16 handoff; same director, no second reviewer Agent.

    Does not change the existing QO-D16 schema, agent ledger or legacy route.
    The critique is *prompt context*, not a fake already-approved decision.
    """
    _need(isinstance(critique, dict) and
          isinstance(critique.get("snapshot"), dict) and
          critique["snapshot"].get("phase") == "post_department_design",
          "WHOLE_FILM_DEPARTMENT_REVIEW_REQUIRES_POST_PHASE")
    receipt = validate(base, state, meeting, av_plan, critique,
                       artistic_method_plan=artistic_method_plan)
    import director_delivery_review as delivery
    result = delivery.request(base, state, meeting, av_plan,
                              artistic_method_plan=artistic_method_plan)
    payload = json.loads(result["messages"][1]["content"])
    payload["same_director_prior_holistic_critique"] = deepcopy(critique)
    payload["holistic_critique_digest"] = receipt["critique_digest"]
    payload["read_critique_as_proposal_not_verified_film_art"] = True
    result["messages"][1]["content"] = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"))
    result["whole_film_critique_digest"] = receipt["critique_digest"]
    result["directors_artistic_self_criticism_is_unsent"] = True
    result["ready_for_media_or_publication"] = False
    return result
