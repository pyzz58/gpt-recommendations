"""Editor-facing timecoded production decision list; zero API calls/dependencies.

The user supplies a script; AI direction remains authored in v0.2 JSON. This
module assembles only explicitly authored directives onto one absolute timeline.
It does NOT invent cuts, dialogue, voiceover pauses or visual animations.
"""
from __future__ import annotations
import re

AUDIO_BRIDGE_TYPES = {"none", "j_cut", "l_cut"}
AUDIO_TRACKS = {"none", "voiceover", "dialogue", "ambience", "music", "sfx"}
HAN = re.compile(r"[\u3400-\u9fff]")


def assemble(base, direction):
    """Return (shot tracks, QA findings). All times in seconds.

    This is a neutral edit decision list, not an exported FCP/Resolve OTIO file,
    source footage, rendered video or a frame-accurate subtitle transcript.
    """
    directions = {x["shot_id"]: x for x in direction["shots"]}
    tracks, findings = [], []

    def issue(sid, code, level, detail):
        findings.append({"shot_id": sid, "code": code,
                         "severity": level, "detail": detail})

    all_shots = base["shots"]
    for shot_index, shot in enumerate(all_shots):
        sid = shot["id"]
        d = directions[sid]
        shot_start = shot["start"]
        duration = shot["duration"]

        def timed(value, label, required=False):
            if not isinstance(value, dict):
                if required:
                    issue(sid, "EVENT_NOT_OBJECT", "blocker", label)
                return None
            a, b = value.get("from_s"), value.get("to_s")
            valid = (all(isinstance(x, (int, float)) and not isinstance(x, bool)
                         for x in (a, b)) and 0 <= a < b <= duration)
            if not valid:
                if required or "from_s" in value or "to_s" in value:
                    issue(sid, "EVENT_TIME_INVALID", "blocker",
                          label + " must be inside shot 0–" + str(duration))
                return None
            return {"from_s": a, "to_s": b,
                    "absolute_in_s": round(shot_start + a, 3),
                    "absolute_out_s": round(shot_start + b, 3)}

        beat_tracks = []
        for index, beat in enumerate(d["beats"]):
            info = timed(beat, "beat[" + str(index) + "]", required=True)
            if info:
                info.update({"picture_action": beat["visible_change"],
                             "acting": beat["performance"], "camera": beat["camera"],
                             "sound": beat["sound"]})
                beat_tracks.append(info)

        voiceover = shot.get("narration", "")
        # A narration string is NOT a precise speech timeline. Keep delivery
        # unassigned until a director explicitly supplies optional cue windows.
        speech = d.get("speech") if isinstance(d.get("speech"), dict) else {}
        voice = speech.get("voiceover") if isinstance(speech.get("voiceover"), dict) else {}
        vo_cues = voice.get("cues")
        timed_voice = []
        if vo_cues is not None:
            if not isinstance(vo_cues, list):
                issue(sid, "VOICEOVER_CUES_INVALID", "blocker", "speech.voiceover.cues must be an array")
            else:
                last_out = 0
                texts = []
                for i, cue in enumerate(vo_cues):
                    info = timed(cue, "voiceover.cues[" + str(i) + "]", required=True)
                    if not info:
                        continue
                    text = cue.get("text", "")
                    if not isinstance(text, str) or not text.strip():
                        issue(sid, "VOICEOVER_CUE_EMPTY", "blocker", "voiceover cue text missing")
                        continue
                    if info["from_s"] < last_out - 0.001:
                        issue(sid, "VOICEOVER_CUE_OVERLAP", "blocker", "voiceover cues overlap")
                    last_out = info["to_s"]
                    texts.append(text)
                    info["text"] = text
                    timed_voice.append(info)
                if "".join("".join(text.split()) for text in texts) != "".join(voiceover.split()):
                    issue(sid, "VOICEOVER_CUE_DRIFT", "blocker",
                          "timecoded voiceover text does not reproduce original narration")
        if voiceover and not timed_voice:
            issue(sid, "VOICEOVER_CUE_PENDING", "review",
                  "VO words have no exact timecodes; delivery/timing notes are not audio alignment")
        chinese_count = len(HAN.findall(voiceover))
        if duration and chinese_count / duration > 3.5:
            issue(sid, "VOICEOVER_PACE_REVIEW", "review",
                  f"{chinese_count} Chinese characters in {duration:g}s "
                  f"({chinese_count/duration:.1f} characters/s); audition narration before lock")

        dialogues = []
        raw_dialogue = speech.get("dialogue", [])
        if not isinstance(raw_dialogue, list):
            issue(sid, "DIALOGUE_LIST_INVALID", "blocker", "speech.dialogue must be an array")
            raw_dialogue = []
        for i, line in enumerate(raw_dialogue):
            info = timed(line, "dialogue[" + str(i) + "]", required=True)
            if info:
                info.update({"speaker_id": line.get("speaker_id"), "text": line.get("text"),
                             "delivery": line.get("delivery")})
                dialogues.append(info)
        if voiceover and dialogues:
            issue(sid, "VO_DIALOGUE_MIX_REVIEW", "review",
                  "VO and sync dialogue share a shot; explicitly mix/duck/mute rather than guessing")

        fx_events = []
        sound = d.get("sound", {})
        effects = sound.get("effects", []) if isinstance(sound, dict) else []
        if not isinstance(effects, list):
            issue(sid, "SFX_LIST_INVALID", "blocker",
                  "sound.effects must be an array")
            effects = []
        for i, fx in enumerate(effects):
            t = fx.get("time_s") if isinstance(fx, dict) else None
            if not isinstance(t, (int, float)) or isinstance(t, bool) or not 0 <= t <= duration:
                issue(sid, "SFX_CUE_OUT_OF_RANGE", "blocker",
                      "sound.effects[" + str(i) + "] time_s outside shot")
                continue
            fx_events.append({"at_s": t, "absolute_at_s": round(shot_start + t, 3),
                              "cue": fx.get("cue", "")})

        anim = d.get("animation") if isinstance(d.get("animation"), dict) else {}
        animation_events = []
        elements = anim.get("elements", [])
        if not isinstance(elements, list):
            issue(sid, "ANIMATION_ELEMENTS_INVALID", "blocker",
                  "animation.elements must be a list")
            elements = []
        for i, item in enumerate(elements):
            if not isinstance(item, dict):
                issue(sid, "ANIMATION_ELEMENT_INVALID", "blocker",
                      "animation element must be an object")
                continue
            timing = timed(item, "animation.elements[" + str(i) + "]")
            if timing is None:
                issue(sid, "ANIMATION_KEYFRAMES_NEED_TIMECODES", "review",
                      "animation element has descriptive timing only; cannot produce timecoded keyframes")
                timing = {"from_s": None, "to_s": None,
                          "absolute_in_s": None, "absolute_out_s": None}
            timing.update({"layer": item.get("layer"), "action": item.get("action"),
                           "director_timing_note": item.get("timing")})
            animation_events.append(timing)

        if shot.get("graphics", {}).get("type") not in (None, "none", "None") and \
                anim.get("mode") == "none":
            issue(sid, "MOTION_GRAPHIC_DESIGN_REVIEW", "review",
                  "base shot requires graphics; animation.mode=none must be justified")
        edit = d.get("editing") if isinstance(d.get("editing"), dict) else {}
        audio_bridge = edit.get("audio_bridge")
        bridge_track = None
        if audio_bridge is None:
            issue(sid, "AUDIO_BRIDGE_DECISION_PENDING", "review",
                  "director must explicitly choose no bridge or J-cut/L-cut for handoff")
        elif not isinstance(audio_bridge, dict):
            issue(sid, "AUDIO_BRIDGE_INVALID", "blocker",
                  "editing.audio_bridge must be an object")
        else:
            bridge_type = audio_bridge.get("type")
            bridge_duration = audio_bridge.get("duration_s")
            track = audio_bridge.get("track")
            next_shot = all_shots[shot_index + 1] if shot_index + 1 < len(all_shots) else None
            valid_duration = (isinstance(bridge_duration, (int, float))
                              and not isinstance(bridge_duration, bool))
            valid = (isinstance(bridge_type, str)
                     and isinstance(track, str)
                     and bridge_type in AUDIO_BRIDGE_TYPES and track in AUDIO_TRACKS
                     and valid_duration and bridge_duration >= 0)
            if not valid:
                issue(sid, "AUDIO_BRIDGE_INVALID", "blocker",
                      "bridge needs type, track and numeric duration_s")
            elif bridge_type == "none":
                if bridge_duration != 0 or track != "none":
                    issue(sid, "AUDIO_BRIDGE_NONE_CONFLICT", "blocker",
                          "type=none requires duration_s=0 and track=none")
                else:
                    bridge_track = {"type": "none", "duration_s": 0, "track": "none",
                                    "reason": audio_bridge.get("reason", "")}
            elif (not next_shot or track == "none" or bridge_duration <= 0
                  or bridge_duration > min(duration, next_shot["duration"])):
                issue(sid, "AUDIO_BRIDGE_TIME_INVALID", "blocker",
                      "J/L cut must have adjacent shot and positive duration within both shots")
            elif not isinstance(audio_bridge.get("reason"), str) or not audio_bridge["reason"].strip():
                issue(sid, "AUDIO_BRIDGE_REASON_MISSING", "blocker",
                      "J/L cut must explain dramatic reason for cross-shot audio")
            else:
                cut = shot_start + duration
                bridge_track = {"type": bridge_type, "duration_s": bridge_duration,
                                "track": track, "reason": audio_bridge["reason"],
                                "next_shot_id": next_shot["id"],
                                "absolute_in_s": round(cut - bridge_duration, 3)
                                                  if bridge_type == "j_cut" else cut,
                                "absolute_out_s": cut if bridge_type == "j_cut"
                                    else round(cut + bridge_duration, 3)}
        tracks.append({
            "shot_id": sid, "absolute_in_s": shot_start,
            "absolute_out_s": shot_start + duration,
            "picture_beats": beat_tracks,
            "voiceover": {"text": voiceover, "timed_cues": timed_voice,
                          "cue_status": "timecoded" if timed_voice else
                                        ("none" if not voiceover else "timing_unassigned")},
            "sync_dialogue": dialogues,
            "sound_effect_cues": fx_events,
            "animation_layers": animation_events,
            "edit": {"incoming_transition": edit.get("incoming_transition"),
                     "outgoing_transition": edit.get("outgoing_transition", shot.get("transition")),
                     "cut_reason": edit.get("cut_reason"),
                     "assembly_instructions": edit.get("assembly_instructions"),
                     "audio_bridge": bridge_track},
            "source_media_exists": False, "frame_accurate": False,
        })
    return tracks, findings
