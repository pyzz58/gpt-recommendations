"""Independent, offline cross-department handoff audit and revision planning.

Checks only explicit, machine-comparable evidence. It cannot infer whether a
performance, visual style, physical movement or final rendered shot is good.
No API calls, spending, external services, file writes or approval.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import math


PRODUCTION_ROUTES = frozenset({
    "ai_video", "static_post", "edit_composite",
    "live_action_insert", "post_production",
})
CREATIVE_TASKS = frozenset({
    "script_edit", "director_lock", "acting", "camera_art",
    "sound", "editing_animation", "ai_technical",
})


def _issue(code, owner, shots, detail, severity="blocker"):
    return {"code": code, "task_id": owner, "shot_ids": list(shots),
            "detail": detail, "severity": severity}


def _shot(state, task_id, sid):
    task = state.get("tasks", {}).get(task_id, {})
    payload = task.get("deliverable") or {}
    return (payload.get("shots") or {}).get(sid, {}) if isinstance(payload, dict) else {}


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _section(state, task_id, sid, field):
    item = _shot(state, task_id, sid)
    return item.get(field) if isinstance(item, dict) else None


def audit_handoffs(state, base=None):
    """Return deterministic cross-department issues, without changing a ledger.

    When base is supplied, compare voiceover against authoritative narration,
    duration and claim references. Base-free checks can also run at QA submit.
    """
    if not isinstance(state, dict) or not isinstance(state.get("tasks"), dict):
        raise ValueError("invalid team ledger")
    ids = state.get("shot_ids")
    if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
        raise ValueError("invalid shot IDs")
    source = {}
    if base is not None:
        if not isinstance(base, dict) or not isinstance(base.get("shots"), list):
            raise ValueError("invalid source plan")
        source = {s["id"]: s for s in base["shots"]}
        if set(source) != set(ids):
            raise ValueError("source shot IDs differ from team ledger")
    issues = []
    claim_ids = set()
    if base is not None:
        claim_ids = {c.get("id") for c in base.get("claims", [])
                     if isinstance(c, dict)}

    for i, sid in enumerate(ids):
        acting_beats = _section(state, "acting", sid, "beats")
        edit = _section(state, "editing_animation", sid, "editing")
        speech = _section(state, "sound", sid, "speech")
        sound = _section(state, "sound", sid, "sound")
        camera = _section(state, "camera_art", sid, "camera")
        graphics = _section(state, "editing_animation", sid, "graphics")
        animation = _section(state, "editing_animation", sid, "animation")
        gen = _section(state, "ai_technical", sid, "generation")
        source_shot = source.get(sid, {})
        duration = source_shot.get("duration")
        if not _number(duration):
            duration = None

        # Spoken text is owned by the source; the sound department can time it,
        # not silently rewrite it. Do not include private text in audit reports.
        if base is not None and isinstance(speech, dict):
            voice = speech.get("voiceover")
            if isinstance(voice, dict) and "text" in voice:
                if voice["text"] != source_shot.get("narration", ""):
                    issues.append(_issue("SOURCE_VOICEOVER_DRIFT", "sound", [sid],
                                         "配音文本与权威分镜 narration 不一致"))
            else:
                issues.append(_issue("SOURCE_VOICEOVER_UNCHECKED", "sound", [sid],
                                     "缺少可核对的 voiceover.text", "review"))

        # Exact, not semantic, cross-role constraint: the outgoing editor's
        # beat_link must reference acting's last beat and the next first beat.
        if isinstance(edit, dict) and "narrative_bridge" in edit and i < len(ids)-1:
            bridge = edit["narrative_bridge"]
            if isinstance(bridge, dict) and "beat_link" in bridge:
                link = bridge["beat_link"]
                next_beats = _section(state, "acting", ids[i+1], "beats")
                if not isinstance(link, dict) or not isinstance(acting_beats, list) or not isinstance(next_beats, list) or not acting_beats or not next_beats:
                    issues.append(_issue("HANDOFF_BEAT_LINK_INVALID", "editing_animation",
                                         [sid, ids[i+1]], "切点引用缺少真实相邻动作节拍"))
                else:
                    out_i, in_i = link.get("outgoing_beat_index"), link.get("incoming_beat_index")
                    if (type(out_i) is not int or type(in_i) is not int or
                            out_i != len(acting_beats)-1 or in_i != 0):
                        issues.append(_issue("HANDOFF_BEAT_INDEX_CONFLICT", "editing_animation",
                                             [sid, ids[i+1]], "剪辑切点索引与动作部末/首节拍不一致"))
                    elif duration is not None:
                        last, first = acting_beats[-1], next_beats[0]
                        if not isinstance(last, dict) or not isinstance(first, dict) or (
                                not _number(last.get("to_s")) or
                                not _number(first.get("from_s")) or
                                abs(last["to_s"] - duration) > 0.02 or
                                abs(first["from_s"]) > 0.02):
                            issues.append(_issue("HANDOFF_BEAT_TIME_CONFLICT", "editing_animation",
                                                 [sid, ids[i+1]], "引用节拍没有到达前镜尾/后镜零秒"))

        if isinstance(gen, dict) and "route" in gen and gen["route"] not in PRODUCTION_ROUTES:
            issues.append(_issue("HANDOFF_INVALID_PRODUCTION_ROUTE", "ai_technical", [sid],
                                 "制作路线不是已支持的规范值"))

        if isinstance(animation, dict) and animation.get("mode") == "none" and animation.get("elements"):
            issues.append(_issue("HANDOFF_ANIMATION_CONFLICT", "editing_animation", [sid],
                                 "声明 animation.mode=none 却交付了动画图层"))

        if base is not None and isinstance(graphics, dict):
            used = graphics.get("claims_used")
            if isinstance(used, list):
                unknown = [x for x in used if not isinstance(x, str) or x not in claim_ids]
                if unknown:
                    issues.append(_issue("HANDOFF_UNKNOWN_CLAIM", "editing_animation", [sid],
                                         "图表引用了未在权威 base.claims 登记的论据"))

        if duration is not None and isinstance(acting_beats, list):
            for beat in acting_beats:
                if isinstance(beat, dict) and ("from_s" in beat or "to_s" in beat):
                    a, b = beat.get("from_s"), beat.get("to_s")
                    if not _number(a) or not _number(b) or a < 0 or b <= a or b > duration + 0.02:
                        issues.append(_issue("HANDOFF_ACTING_TIME_CONFLICT", "acting", [sid],
                                             "动作节拍的起止时间超出本镜头或顺序无效"))
                        break
        if duration is not None and isinstance(camera, dict) and "move_trigger_s" in camera:
            trigger = camera["move_trigger_s"]
            if not _number(trigger) or trigger < 0 or trigger > duration + 0.02:
                issues.append(_issue("HANDOFF_CAMERA_TIME_CONFLICT", "camera_art", [sid],
                                     "运镜触发时间不在当前镜头范围内"))
        if duration is not None and isinstance(sound, dict):
            effects = sound.get("effects")
            if isinstance(effects, list):
                for effect in effects:
                    if isinstance(effect, dict) and "time_s" in effect:
                        at = effect["time_s"]
                        if not _number(at) or at < 0 or at > duration + 0.02:
                            issues.append(_issue("HANDOFF_SOUND_TIME_CONFLICT", "sound", [sid],
                                                 "音效 cue 时间不在镜头范围内"))
                            break
        if base is not None and isinstance(edit, dict) and "outgoing_transition" in edit:
            if edit["outgoing_transition"] != source_shot.get("transition"):
                issues.append(_issue("HANDOFF_SOURCE_CUT_CONFLICT", "editing_animation", [sid],
                                     "剪辑转场与锁定的 base.transition 不一致，需要原稿变更审批"))

    counts = dict(Counter(i["severity"] for i in issues))
    return {"version": "0.1", "status": "blocked" if counts.get("blocker", 0)
            else "review_required" if issues else "no_explicit_conflicts",
            "issues": issues, "counts": counts,
            "human_approved": False, "media_verified": False,
            "semantic_consistency_proven": False,
            "note": "仅检查明确定义且可比较的时码、索引、文本、路线和事实引用；没有进行影视审美或语义推理。"}


def propose_revisions(state, base=None, *, include_reviews=False):
    """Non-mutating, showrunner-facing scoped revision suggestions.

    An approved proposal can be handed to agent_team.request_revision.
    It is NOT an instruction to execute LLM work or authority to spend.
    """
    report = audit_handoffs(state, base)
    findings = list(report["issues"])
    qa = state.get("tasks", {}).get("quality_review", {})
    authored = (qa.get("deliverable") or {}).get("qa_report", {})
    for finding in authored.get("blockers", []):
        if isinstance(finding, dict) and finding.get("task_id") in CREATIVE_TASKS:
            findings.append(_issue("QA_AUTHORED_BLOCKER", finding["task_id"],
                                   finding.get("shot_ids", []),
                                   str(finding.get("detail", "QA要求处理的问题"))))
    if include_reviews:
        import agent_creative_review
        for f in agent_creative_review.review_team(state)["findings"]:
            if f["severity"] == "review" and f["task_id"] in CREATIVE_TASKS:
                findings.append(_issue(f["code"], f["task_id"],
                                       [f["shot_id"]] if f.get("shot_id") else [],
                                       f["detail"], "review"))
    groups = defaultdict(list)
    order = {sid: i for i, sid in enumerate(state["shot_ids"])}
    for f in findings:
        if f["severity"] != "blocker" and not include_reviews:
            continue
        owner = f.get("task_id")
        if owner not in CREATIVE_TASKS:
            continue
        shots = f.get("shot_ids", [])
        if not isinstance(shots, list) or any(sid not in order for sid in shots):
            continue
        if owner not in ("script_edit", "director_lock") and not shots:
            continue  # Unsupported/unspecific issue requires director triage
        groups[owner].append(f)

    proposals = []
    for owner in sorted(groups):
        entry = state["tasks"].get(owner, {})
        if entry.get("status") != "completed":
            continue
        items = groups[owner]
        scope = [] if owner in ("script_edit", "director_lock") else sorted(
            {sid for issue in items for sid in issue["shot_ids"]},
            key=order.__getitem__)
        codes = sorted(set(x["code"] for x in items))
        proposals.append({
            "task_id": owner, "shot_ids": scope,
            "base_digest": state.get("base_digest"),
            "expected_task_revision": entry.get("revision"),
            "codes": codes, "reason": "; ".join(
                dict.fromkeys(x["detail"] for x in items)),
            "status": "proposed_only", "showrunner_approved": False,
            "user_approved": False, "execution_authorized": False,
        })
    return {"status": "director_decision_required", "proposals": proposals,
            "handoff_report": report, "ledger_unchanged": True,
            "no_model_calls": True}
