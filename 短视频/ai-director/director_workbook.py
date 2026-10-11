#!/usr/bin/env python3
"""The primary deliverable: script-to-AI-video DIRECTOR workbook.

Not a model runner. Never substitutes invented editing, animation or dialogue
decisions for a director's work. Legacy v0.2 directions produce a draft with
explicit missing-design findings; strict mode requires finished creative design.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

import director_v2
import director_timeline

EDIT_FIELDS = ("incoming_transition", "outgoing_transition", "cut_reason",
               "rhythm", "assembly_instructions")
ANIMATION_FIELDS = ("mode", "timing", "elements", "render_in_post", "style")
SPEECH_FIELDS = ("voiceover", "dialogue", "subtitle_direction", "lip_sync_policy")


def meaningful(value):
    return isinstance(value, str) and bool(value.strip()) and not any(
        token in value for token in ("待填", "待导演", "TODO", "TBD")
    )


def review_creative(shot, direction, preceding_shot, character_ids):
    findings = []
    sid = shot["id"]
    def flag(code, detail):
        findings.append({"shot_id": sid, "code": code, "detail": detail,
                         "severity": "needs_director_design"})

    edit = direction.get("editing")
    if not isinstance(edit, dict):
        flag("EDITING_MISSING", "Must design cuts, rhythm, linkage and assembly instructions")
    else:
        for key in EDIT_FIELDS:
            if not meaningful(edit.get(key)):
                flag("EDITING_FIELD_MISSING", "editing." + key)
        if meaningful(edit.get("outgoing_transition")):
            if edit["outgoing_transition"] != shot.get("transition"):
                flag("EDIT_CONFLICTS_BASE", "Out transition differs from base; revise base explicitly")
        if preceding_shot and meaningful(edit.get("incoming_transition")):
            if edit["incoming_transition"] != preceding_shot.get("transition"):
                flag("INCOMING_CUT_CONFLICT", "Incoming transition differs from previous shot")
        if not preceding_shot and edit.get("incoming_transition") != "start":
            flag("FIRST_SHOT_INCOMING", "First shot must use incoming_transition=start")

    anim = direction.get("animation")
    if not isinstance(anim, dict):
        flag("ANIMATION_MISSING", "Design motion/graphics/VFX or declare explicit none")
    else:
        for key in ANIMATION_FIELDS:
            value = anim.get(key)
            if key == "render_in_post":
                if not isinstance(value, bool):
                    flag("ANIMATION_FIELD_MISSING", "animation.render_in_post")
            elif key == "elements":
                if not isinstance(value, list):
                    flag("ANIMATION_FIELD_MISSING", "animation.elements, [] if none")
                else:
                    for idx, element in enumerate(value):
                        if not isinstance(element, dict) or any(
                            not meaningful(element.get(field))
                            for field in ("layer", "action", "timing")
                        ):
                            flag("ANIMATION_ELEMENT_INVALID", "elements[" + str(idx) + "]")
            elif not meaningful(value):
                flag("ANIMATION_FIELD_MISSING", "animation." + key)
        if anim.get("mode") == "none" and anim.get("elements"):
            flag("ANIMATION_CONTRADICTION", "mode=none but animation elements exist")
        if meaningful(anim.get("mode")) and anim["mode"] != "none" and anim.get("elements") == []:
            flag("ANIMATION_ELEMENTS_REQUIRED",
                 "an animated shot needs explicit layers and executable actions")

    speech = direction.get("speech")
    if not isinstance(speech, dict):
        flag("SPEECH_MISSING", "Design voiceover, dialogue, subtitles and lip-sync explicitly")
    else:
        for field in SPEECH_FIELDS:
            if field == "dialogue":
                if not isinstance(speech.get(field), list):
                    flag("SPEECH_FIELD_MISSING", "speech.dialogue list")
            elif field == "voiceover":
                if not isinstance(speech.get(field), dict):
                    flag("SPEECH_FIELD_MISSING", "speech.voiceover object")
            elif not meaningful(speech.get(field)):
                flag("SPEECH_FIELD_MISSING", "speech." + field)
        voice = speech.get("voiceover")
        if isinstance(voice, dict):
            if voice.get("text") != shot.get("narration", ""):
                flag("VOICEOVER_DRIFT", "Proposed voiceover differs from approved base narration")
            for field in ("delivery", "timing"):
                if not meaningful(voice.get(field)):
                    flag("VOICEOVER_FIELD_MISSING", "speech.voiceover." + field)
        dialogue = speech.get("dialogue")
        if isinstance(dialogue, list):
            for idx, line in enumerate(dialogue):
                prefix = "dialogue[" + str(idx) + "]"
                if not isinstance(line, dict) or any(
                    not meaningful(line.get(key)) for key in ("speaker_id", "text", "delivery")
                ):
                    flag("DIALOGUE_INVALID", prefix + " lacks actor/text/delivery")
                    continue
                if line["speaker_id"] not in character_ids:
                    flag("DIALOGUE_UNKNOWN_SPEAKER", prefix + " uses undeclared character")
                a, b = line.get("from_s"), line.get("to_s")
                if (not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (a, b))
                        or a < 0 or b > shot["duration"] or b <= a):
                    flag("DIALOGUE_TIME_INVALID", prefix + " outside shot duration")
    return findings


def compile_workbook(base, directions):
    errors, warnings = director_v2.validate(base, directions)
    if errors:
        raise ValueError("invalid director input: " + "; ".join(errors[:12]))
    compiled = director_v2.compile_package(base, directions)
    direction_map = {s["shot_id"]: s for s in directions["shots"]}
    compiled_map = {s["shot_id"]: s for s in compiled["shots"]}
    scene_map = {s["id"]: s for s in base.get("scenes", [])}
    actors = {c["id"] for c in base.get("characters", [])}
    shot_rows, timeline, findings = [], [], []
    expected_start = 0
    prev = None
    for shot in base["shots"]:
        sid = shot["id"]
        d, job = direction_map[sid], compiled_map[sid]
        start, end = shot["start"], shot["start"] + shot["duration"]
        if abs(start - expected_start) > 0.011:
            raise ValueError(sid + " has a non-contiguous base timeline")
        expected_start = end
        findings += review_creative(shot, d, prev, actors)
        shot_rows.append({
            "shot_id": sid, "start_s": start, "end_s": end, "duration_s": shot["duration"],
            "story": {"purpose": shot["purpose"], "visual": shot["visual"],
                      "emotion": d["objective"]["emotion"],
                      "visible_change": d["objective"]["observable_turn"]},
            "script": {"narration": shot["narration"], "narration_source": "base.shots[].narration",
                       "subtitle": shot["subtitles"], "speech": d.get("speech"),
                       "voiceover_director_note": d["sound"]["voiceover_note"]},
            "performance": {"action": shot["action"], "blocking": d["staging"],
                            "acting": d["performance"], "timed_beats": d["beats"]},
            "camera": d["camera"],
            "set_and_lighting": {"scene_id": shot.get("scene_id"),
                                 "scene_bible": scene_map.get(shot.get("scene_id")),
                                 "art_direction": d["art"], "base_set_props": shot["art"]["set_props"]},
            "editing": d.get("editing"), "animation": d.get("animation"),
            "graphics": {"base": shot["graphics"], "director": d["graphics"]},
            "sound": {"source": shot["audio"], "director": d["sound"]},
            "continuity": {"base": shot.get("continuity"), "direction": d["continuity"],
                           "state": shot.get("continuity_state")},
            "production": {"route": job["execution_route"],
                           "ai_prompt_candidates": job["prompts"],
                           "postproduction": job["postproduction_job"],
                           "reference_roles": d["generation"]["reference_roles"],
                           "fallback": d["generation"].get("fallback"),
                           "cost_note": d["generation"].get("cost_note")},
            "human_approved": False
        })
        timeline.append({"shot_id": sid, "start_s": start, "end_s": end,
                         "base_out_transition": shot["transition"],
                         "director_editing": d.get("editing")})
        prev = shot
    if abs(expected_start - base["duration"]) > 0.011:
        raise ValueError("final shot does not end at declared duration")
    edit_timeline, timeline_findings = director_timeline.assemble(base, directions)
    timeline_blockers = [f for f in timeline_findings if f["severity"] == "blocker"]
    # Creative fields can all be filled yet the result may still lack timed
    # voiceover, keyed animation or explicit cross-shot audio decisions.
    # Keep "concept complete" separate from "editor handoff ready".
    unfinished_codes = {"VOICEOVER_CUE_PENDING",
                        "ANIMATION_KEYFRAMES_NEED_TIMECODES",
                        "AUDIO_BRIDGE_DECISION_PENDING",
                        "MOTION_GRAPHIC_DESIGN_REVIEW"}
    handoff_pending = [f for f in timeline_findings if
                       f["severity"] == "blocker" or f["code"] in unfinished_codes]
    concept_complete = len(findings) == 0 and len(timeline_blockers) == 0
    handoff_ready = concept_complete and not handoff_pending
    return {
        "schema_version": "1.0", "kind": "script_to_short_video_director_workbook",
        "overview": {"title": base["title"], "core_message": base["core_message"],
                     "duration_s": base["duration"], "platform": base["platform"],
                     "aspect_ratio": base["aspect_ratio"], "editorial": base["editorial"],
                     "visual_bible": base["visual_bible"],
                     "series_direction": directions["global_direction"]},
        "assembly_timeline": timeline, "editor_decision_list": edit_timeline,
        "shots": shot_rows, "production_summary": compiled["production_summary"],
        "director_review": {"creative_design_complete": concept_complete,
                            "editor_handoff_ready": handoff_ready,
                            "editor_handoff_pending": len(handoff_pending),
                            "unresolved": len(findings) + len(timeline_blockers),
                            "findings": findings + timeline_blockers,
                            "handoff_findings": handoff_pending,
                            "timing_review_findings": [f for f in timeline_findings
                                                       if f["severity"] != "blocker"],
                            "technical_warnings": warnings},
        "is_video": False, "human_approved": False, "paid_api_authorized": False,
        "publishing_allowed": False
    }


def render_markdown(book):
    lines = ["# " + book["overview"]["title"] + " · AI 短视频专业导演交付书", "",
             "核心表达：" + book["overview"]["core_message"],
             "时长：" + str(book["overview"]["duration_s"]) + " 秒",
             "这是导演设计与制作工作单，不是已完成的影片。", "",
             "未完成的导演决策：" + str(book["director_review"]["unresolved"]),
             "剪辑交接就绪：" + ("是（仅表示工作单齐全，仍需人工审片）" if
                         book["director_review"]["editor_handoff_ready"] else
                         "否，仍有 " + str(book["director_review"]["editor_handoff_pending"]) +
                         " 项需要精确时间/音频衔接设计"), ""]
    timeline_by_id = {t["shot_id"]: t for t in book["editor_decision_list"]}
    for shot in book["shots"]:
        lines += ["## " + shot["shot_id"] + " / " + str(shot["start_s"]) + "–" + str(shot["end_s"]) + "秒",
                  "剧情任务：" + shot["story"]["visible_change"],
                  "制作方式：" + shot["production"]["route"],
                  "正式旁白：" + shot["script"]["narration"]]
        for key, title in [
            ("script", "台词、配音与字幕"), ("performance", "动作、走位与逐秒表演"),
            ("camera", "景别与运镜"), ("set_and_lighting", "场景、灯光与美术"),
            ("editing", "剪辑与转场"), ("animation", "动画与视觉特效"),
            ("graphics", "文字图形与字幕"), ("sound", "音乐与环境音效"),
            ("continuity", "连续性"), ("production", "AI 制作提示词与后期工单")
        ]:
            value = shot[key]
            if value is None:
                lines += ["", "### " + title, "尚未设计，需要导演补充"]
            else:
                fence = chr(96) * 3
                lines += ["", "### " + title, fence + "json",
                          json.dumps(value, ensure_ascii=False, indent=2), fence]
        fence = chr(96) * 3
        lines += ["", "### 可交付剪辑工作台时间表（非实际素材）",
                  fence + "json",
                  json.dumps(timeline_by_id[shot["shot_id"]], ensure_ascii=False, indent=2),
                  fence]
        lines.append("")
    if book["director_review"]["timing_review_findings"]:
        lines += ["## 节奏、配音与动画时间点待人工核查"]
        lines += [f"- {x['shot_id']}：{x['code']} —— {x['detail']}"
                  for x in book["director_review"]["timing_review_findings"]]
    if book["director_review"]["findings"]:
        lines += ["## 待完善问题"]
        lines += [f"- {x['shot_id']}：{x['code']} —— {x['detail']}"
                  for x in book["director_review"]["findings"]]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline script-to-director workbook (no AI calls)")
    parser.add_argument("--base", required=True)
    parser.add_argument("--direction", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--markdown")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    try:
        base = json.loads(Path(args.base).read_text(encoding="utf-8"))
        directions = json.loads(Path(args.direction).read_text(encoding="utf-8"))
        book = compile_workbook(base, directions)
        if args.strict and not book["director_review"]["editor_handoff_ready"]:
            raise ValueError("editor handoff incomplete: " +
                             str(book["director_review"]["editor_handoff_pending"]) +
                             " timecoded items, " +
                             str(book["director_review"]["unresolved"]) +
                             " creative blockers; no output written")
        targets = [Path(args.out)] + ([Path(args.markdown)] if args.markdown else [])
        if len(set(str(p.resolve()) for p in targets)) != len(targets):
            raise ValueError("output paths must differ")
        if any(p.exists() for p in targets):
            raise ValueError("existing output cannot be overwritten")
        for path in targets:
            path.parent.mkdir(parents=True, exist_ok=True)
        with targets[0].open("x", encoding="utf-8") as f:
            json.dump(book, f, ensure_ascii=False, indent=2)
            f.write("\n")
        if args.markdown:
            with targets[1].open("x", encoding="utf-8") as f:
                f.write(render_markdown(book))
        print("Director workbook created; pending:", book["director_review"]["unresolved"])
        return 0
    except (KeyError, ValueError, TypeError, OSError) as error:
        print("ERROR:", error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
