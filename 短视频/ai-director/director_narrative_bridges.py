"""Adjacent-shot narrative/edit/style bridges for an AI short-video DIRECTOR.

This does not write creative decisions, render a film or judge aesthetics.
Every bridge must be explicitly authored by the AI director or a human.
Missing/incomplete authored plans are distinguishable from contradictory plans.
No import of media libraries, no model calls, no downloads, no paid APIs.
"""
from __future__ import annotations

CUT_TYPES = {"cut", "match_action", "match_gaze", "match_shape",
             "contrast", "reveal", "establish", "intentional_jump"}
TEMPO_CHANGES = {"accelerate", "decelerate", "hold", "contrast"}
STYLE_HANDOFFS = {"preserve", "grade_to_match", "graphic_match",
                  "motivated_contrast"}
ROUTE_LABELS = {"ai_video", "static_post", "edit_composite",
                "live_action_insert", "post_production"}
PLACEHOLDERS = ("待设计", "待导演", "待填", "todo", "tbd", "placeholder", "稍后再说")


def _text(value):
    return (isinstance(value, str) and bool(value.strip())
            and not any(word in value.lower() for word in PLACEHOLDERS))


def review(base, direction, route_fn):
    """Return (explicit bridge sheet, pending/blocker findings).

    Schema v0.2 remains backwards-compatible. Missing narrative_bridge is a
    creative handoff gap, NOT a hard validation error for legacy drafts.
    A completed bridge only indicates well-formed design, never quality.
    """
    shots = base["shots"]
    directives = {item["shot_id"]: item for item in direction["shots"]}
    bridges, findings = [], []

    def issue(prev, nxt, code, severity, detail):
        findings.append({"shot_id": prev, "next_shot_id": nxt,
                         "code": code, "severity": severity, "detail": detail})

    def needed(prev, nxt, value, name):
        if not _text(value):
            issue(prev, nxt, "NARRATIVE_FIELD_MISSING", "pending", name)
            return False
        return True

    for a, b in zip(shots, shots[1:]):
        left_id, right_id = a["id"], b["id"]
        left, right = directives[left_id], directives[right_id]
        route_out = route_fn(a, left["generation"])
        route_in = route_fn(b, right["generation"])
        edit = left.get("editing")
        contract = edit.get("narrative_bridge") if isinstance(edit, dict) else None
        result = {
            "from_shot_id": left_id, "to_shot_id": right_id,
            "cut_at_s": a["start"] + a["duration"],
            "from_route": route_out, "to_route": route_in,
            "design_status": "missing",
            "cut_intention": None, "emotion_pacing": None,
            "visual_handoff": None, "style_handoff": None,
            "human_visual_review_required": True
        }
        if contract is None:
            issue(left_id, right_id, "NARRATIVE_BRIDGE_MISSING", "pending",
                  "director must write an adjacent-shot narrative and style handoff")
            bridges.append(result)
            continue
        if not isinstance(contract, dict):
            issue(left_id, right_id, "NARRATIVE_BRIDGE_INVALID", "blocker",
                  "editing.narrative_bridge must be a dictionary")
            bridges.append(result)
            continue

        cut = contract.get("cut_intention")
        emotion = contract.get("emotion_pacing")
        visual = contract.get("visual_handoff")
        style = contract.get("style_handoff")
        valid = True
        for key, obj in (("cut_intention", cut), ("emotion_pacing", emotion),
                         ("visual_handoff", visual), ("style_handoff", style)):
            if not isinstance(obj, dict):
                issue(left_id, right_id, "NARRATIVE_SECTION_MISSING", "pending", key)
                valid = False

        if isinstance(cut, dict):
            for name in ("viewer_question", "answer_or_reframe", "why_cut_here",
                         "information_change"):
                valid = needed(left_id, right_id, cut.get(name),
                               "cut_intention." + name) and valid
            if not isinstance(cut.get("cut_type"), str) or cut["cut_type"] not in CUT_TYPES:
                issue(left_id, right_id, "CUT_TYPE_INVALID", "blocker",
                      "cut_intention.cut_type must name a recognized edit intent")
                valid = False

        if isinstance(emotion, dict):
            for name in ("emotion_before", "emotion_after", "audience_effect",
                         "tempo_reason"):
                valid = needed(left_id, right_id, emotion.get(name),
                               "emotion_pacing." + name) and valid
            if not isinstance(emotion.get("tempo_change"), str) or emotion["tempo_change"] not in TEMPO_CHANGES:
                issue(left_id, right_id, "TEMPO_INVALID", "blocker",
                      "emotion_pacing.tempo_change must be an explicit choice")
                valid = False
            holds = (emotion.get("hold_before_s"), emotion.get("settle_after_s"))
            ok_holds = (all(isinstance(v, (int, float)) and not isinstance(v, bool)
                            for v in holds) and
                        0 <= holds[0] <= a["duration"] and
                        0 <= holds[1] <= b["duration"])
            if not ok_holds:
                issue(left_id, right_id, "RHYTHM_HOLD_INVALID", "blocker",
                      "holds must be seconds within adjacent shots")
                valid = False

        if isinstance(visual, dict):
            for name in ("outgoing_frame_anchor", "incoming_frame_anchor",
                         "axis_or_gaze_rule", "motion_or_prop_link"):
                valid = needed(left_id, right_id, visual.get(name),
                               "visual_handoff." + name) and valid
            if not isinstance(visual.get("relation"), str) or visual["relation"] not in CUT_TYPES:
                issue(left_id, right_id, "VISUAL_RELATION_INVALID", "blocker",
                      "visual_handoff.relation must explain the shot connection")
                valid = False

        if isinstance(style, dict):
            for name in ("palette_target", "lighting_logic", "composition_rule",
                         "texture_rule", "typography_rule", "implementation"):
                valid = needed(left_id, right_id, style.get(name),
                               "style_handoff." + name) and valid
            mode = style.get("strategy")
            if not isinstance(mode, str) or mode not in STYLE_HANDOFFS:
                issue(left_id, right_id, "STYLE_STRATEGY_INVALID", "blocker",
                      "style_handoff.strategy must be preserve/grade_to_match/"
                      "graphic_match/motivated_contrast")
                valid = False
            # When the source changes medium, the approach needs an explicit
            # operational handoff; a vague mode label is not enough.
            if route_out != route_in and mode == "preserve":
                issue(left_id, right_id, "MIXED_MEDIA_STYLE_REVIEW", "review",
                      "route changes; visually verify grade/layout/texture despite preserve strategy")

        result.update({"design_status": "authored" if valid else "incomplete",
                       "cut_intention": cut, "emotion_pacing": emotion,
                       "visual_handoff": visual, "style_handoff": style})
        bridges.append(result)
    return bridges, findings
