#!/usr/bin/env python3
"""F03 source-bound sound, voice, foley and music preflight.

Offline structural review only. No voice cloning, TTS, paid model call,
real audio decode or claim that a mix is artistically finished.
"""
from __future__ import annotations

from copy import deepcopy

VERSION = "director-sound-contract-v1"
MODE = {
    "kind": "source_bound_sound_plan_required",
    "version": 1,
}
MUSIC_MODES = frozenset({"none", "cue"})
RIGHTS_STATES = frozenset({"unknown", "not_selected", "unlicensed", "cleared"})
BRIDGE_TYPES = frozenset({"none", "j_cut", "l_cut", "match_cut", "room_tone_bridge"})
EFFECT_LAYERS = frozenset({"foley", "ambience", "sfx", "silence"})
GENERIC_SOUND = (
    "氛围感", "电影感", "大气", "高级感", "震撼", "感人",
)


class SoundContractError(ValueError):
    """Static codes only; never echo private dialogue or audio paths."""


def _need(ok, code):
    if not ok:
        raise SoundContractError(code)


def _text(value, minimum=1):
    return isinstance(value, str) and len(value.strip()) >= minimum


def _add(items, code, detail, shot_id=None):
    row = {"code": code, "detail": detail}
    if shot_id is not None:
        row["shot_id"] = shot_id
    items.append(row)


def _inside(value, duration):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and 0 <= value <= duration)


def inspect_delivery(base, payload):
    report = {"version": VERSION, "mode": deepcopy(MODE),
              "blockers": [], "reviews": []}
    mode = base.get("sound_contract_mode")
    if mode is None:
        report["not_required"] = True
        return report
    if mode != MODE:
        _add(report["blockers"], "SOUND_CONTRACT_MODE_INVALID",
             "sound_contract_mode must be the reviewed source-bound mode")
        return report
    shots = payload.get("shots")
    if not isinstance(shots, dict):
        _add(report["blockers"], "SOUND_SHOTS_INVALID",
             "sound payload must contain a shots object")
        return report
    sources = {shot.get("id"): shot for shot in base.get("shots", [])
               if isinstance(shot, dict)}
    character_ids = {c.get("id") for c in base.get("characters", [])
                     if isinstance(c, dict)}
    source_dialogue = base.get("dialogue") if isinstance(base.get("dialogue"), list) else None
    for sid, source in sources.items():
        authored = shots.get(sid)
        if authored is None:
            continue
        sound = authored.get("sound") if isinstance(authored, dict) else None
        speech = authored.get("speech") if isinstance(authored, dict) else None
        if not isinstance(sound, dict) or not isinstance(speech, dict):
            _add(report["blockers"], "SOUND_AND_SPEECH_SECTIONS_REQUIRED",
                 "sound and speech must both be authored objects", shot_id=sid)
            continue
        duration = source.get("duration")
        mix = sound.get("mix")
        if not isinstance(mix, dict):
            _add(report["blockers"], "SOUND_MIX_MISSING",
                 "sound.mix is required for the strict sound contract", shot_id=sid)
        else:
            for field, code in (
                ("dialogue_priority", "SOUND_DIALOGUE_PRIORITY_MISSING"),
                ("music_level", "SOUND_MUSIC_LEVEL_MISSING"),
                ("ambience_level", "SOUND_AMBIENCE_LEVEL_MISSING"),
                ("dynamic_range_note", "SOUND_DYNAMIC_RANGE_MISSING"),
                ("silence_intent", "SOUND_SILENCE_INTENT_MISSING"),
            ):
                if not _text(mix.get(field)):
                    _add(report["blockers"], code,
                         "sound.mix needs concrete " + field, shot_id=sid)
        music = sound.get("music_plan")
        if not isinstance(music, dict):
            _add(report["blockers"], "SOUND_MUSIC_PLAN_MISSING",
                 "sound.music_plan is required", shot_id=sid)
        else:
            if music.get("mode") not in MUSIC_MODES:
                _add(report["blockers"], "SOUND_MUSIC_MODE_INVALID",
                     "music mode must be none or cue", shot_id=sid)
            for field in ("cue_id", "purpose", "instrumentation", "mix_level"):
                if not _text(music.get(field)):
                    _add(report["blockers"], "SOUND_MUSIC_FIELD_MISSING",
                         "music_plan needs concrete " + field, shot_id=sid)
            rights = music.get("rights_status")
            if rights not in RIGHTS_STATES:
                _add(report["blockers"], "SOUND_MUSIC_RIGHTS_INVALID",
                     "music rights_status must be unknown/not_selected/unlicensed/cleared",
                     shot_id=sid)
            if rights == "cleared" and not _text(music.get("license_ref")):
                _add(report["blockers"], "SOUND_MUSIC_LICENSE_EVIDENCE_MISSING",
                     "cleared music needs a concrete license reference", shot_id=sid)
            start, end = music.get("start_s"), music.get("end_s")
            if music.get("mode") == "none":
                if start != 0 or end != 0:
                    _add(report["blockers"], "SOUND_MUSIC_NONE_INTERVAL_INVALID",
                         "no-music plan must use start_s=end_s=0", shot_id=sid)
            elif (not _inside(start, duration) or not _inside(end, duration)
                  or not isinstance(start, (int, float)) or not isinstance(end, (int, float))
                  or end <= start):
                _add(report["blockers"], "SOUND_MUSIC_INTERVAL_INVALID",
                     "music cue must sit inside the shot and end after it starts",
                     shot_id=sid)
            for field in ("purpose", "instrumentation"):
                value = music.get(field)
                if _text(value) and any(signal in value for signal in GENERIC_SOUND):
                    _add(report["reviews"], "SOUND_MUSIC_GENERIC_LANGUAGE",
                         "review generic music language in " + field, shot_id=sid)
        effects = sound.get("effects")
        if not isinstance(effects, list) or not effects:
            _add(report["blockers"], "SOUND_EFFECTS_MISSING",
                 "strict sound needs explicit effects/foley/silence events", shot_id=sid)
        else:
            for effect in effects:
                if not isinstance(effect, dict):
                    _add(report["blockers"], "SOUND_EFFECT_INVALID",
                         "every effect must be an object", shot_id=sid)
                    continue
                if not _inside(effect.get("time_s"), duration):
                    _add(report["blockers"], "SOUND_EFFECT_TIME_INVALID",
                         "effect time must sit inside the shot", shot_id=sid)
                for field in ("cue", "source", "mix_note"):
                    if not _text(effect.get(field)):
                        _add(report["blockers"], "SOUND_EFFECT_FIELD_MISSING",
                             "effect needs concrete " + field, shot_id=sid)
                if effect.get("layer") not in EFFECT_LAYERS:
                    _add(report["blockers"], "SOUND_EFFECT_LAYER_INVALID",
                         "effect layer must be foley/ambience/sfx/silence",
                         shot_id=sid)
        bridge = sound.get("sound_bridge")
        if not isinstance(bridge, dict):
            _add(report["blockers"], "SOUND_BRIDGE_MISSING",
                 "every shot needs an explicit sound bridge decision", shot_id=sid)
        else:
            kind = bridge.get("type")
            if kind not in BRIDGE_TYPES:
                _add(report["blockers"], "SOUND_BRIDGE_TYPE_INVALID",
                     "sound bridge type is not recognized", shot_id=sid)
            if not _text(bridge.get("reason")):
                _add(report["blockers"], "SOUND_BRIDGE_REASON_MISSING",
                     "sound bridge needs a reason", shot_id=sid)
            bridge_duration = bridge.get("duration_s")
            if kind == "none":
                if bridge_duration != 0 or bridge.get("track") not in (None, "", "none"):
                    _add(report["blockers"], "SOUND_BRIDGE_NONE_INVALID",
                         "none bridge needs duration 0 and no track", shot_id=sid)
            elif (not _inside(bridge_duration, duration)
                  or not isinstance(bridge_duration, (int, float))
                  or bridge_duration <= 0):
                _add(report["blockers"], "SOUND_BRIDGE_TIME_INVALID",
                     "non-none bridge duration must sit inside the shot", shot_id=sid)
            if kind != "none" and not _text(bridge.get("track")):
                _add(report["blockers"], "SOUND_BRIDGE_TRACK_MISSING",
                     "non-none bridge needs an audio track", shot_id=sid)
        voice = speech.get("voiceover")
        if not isinstance(voice, dict):
            _add(report["blockers"], "SOUND_VOICEOVER_MISSING",
                 "speech.voiceover is required", shot_id=sid)
        else:
            if voice.get("text") != source.get("narration", ""):
                _add(report["blockers"], "SOUND_VOICEOVER_SOURCE_DRIFT",
                     "voiceover text must exactly match base narration", shot_id=sid)
            for field in ("delivery", "timing"):
                if not _text(voice.get(field)):
                    _add(report["blockers"], "SOUND_VOICEOVER_FIELD_MISSING",
                         "voiceover needs concrete " + field, shot_id=sid)
            cues = voice.get("cues")
            if not isinstance(cues, list):
                _add(report["blockers"], "SOUND_VOICEOVER_CUES_INVALID",
                     "voiceover cues must be a list", shot_id=sid)
            else:
                for cue in cues:
                    if (not isinstance(cue, dict)
                            or not _inside(cue.get("from_s"), duration)
                            or not _inside(cue.get("to_s"), duration)
                            or not isinstance(cue.get("from_s"), (int, float))
                            or not isinstance(cue.get("to_s"), (int, float))
                            or cue["to_s"] <= cue["from_s"]
                            or not _text(cue.get("text"))):
                        _add(report["blockers"], "SOUND_VOICEOVER_CUE_INVALID",
                             "voiceover cue needs an in-shot interval and exact text",
                             shot_id=sid)
        dialogue = speech.get("dialogue")
        if not isinstance(dialogue, list):
            _add(report["blockers"], "SOUND_DIALOGUE_INVALID",
                 "speech.dialogue must be a list", shot_id=sid)
            dialogue = []
        seen_spans = {}
        for line in dialogue:
            if not isinstance(line, dict):
                _add(report["blockers"], "SOUND_DIALOGUE_INVALID",
                     "every dialogue line must be an object", shot_id=sid)
                continue
            speaker = line.get("speaker_id")
            if speaker not in character_ids:
                _add(report["blockers"], "SOUND_DIALOGUE_SPEAKER_UNKNOWN",
                     "dialogue speaker must be a declared character", shot_id=sid)
            if not _text(line.get("text")) or not _text(line.get("delivery")):
                _add(report["blockers"], "SOUND_DIALOGUE_FIELD_MISSING",
                     "dialogue needs exact text and delivery", shot_id=sid)
            if not _text(line.get("clarity_note")):
                _add(report["blockers"], "SOUND_DIALOGUE_CLARITY_MISSING",
                     "dialogue needs a clarity/mix note", shot_id=sid)
            kind = line.get("kind")
            lip = line.get("lip_sync")
            if kind == "onscreen_dialogue":
                if lip not in ("required", "native"):
                    _add(report["blockers"], "SOUND_DIALOGUE_LIPSYNC_REQUIRED",
                         "onscreen dialogue needs required/native lip sync", shot_id=sid)
            elif kind == "offscreen_dialogue":
                if lip not in ("none", "not_applicable"):
                    _add(report["blockers"], "SOUND_OFFSCREEN_LIPSYNC_FORBIDDEN",
                         "offscreen dialogue must not drive visible lip sync", shot_id=sid)
            else:
                _add(report["blockers"], "SOUND_DIALOGUE_KIND_INVALID",
                     "dialogue kind must be onscreen_dialogue or offscreen_dialogue",
                     shot_id=sid)
            start, end = line.get("from_s"), line.get("to_s")
            if (not _inside(start, duration) or not _inside(end, duration)
                    or not isinstance(start, (int, float)) or not isinstance(end, (int, float))
                    or end <= start):
                _add(report["blockers"], "SOUND_DIALOGUE_TIME_INVALID",
                     "dialogue interval must sit inside the shot", shot_id=sid)
                continue
            for old_start, old_end in seen_spans.get(speaker, []):
                if start < old_end and old_start < end:
                    _add(report["blockers"], "SOUND_DIALOGUE_OVERLAP",
                         "one speaker has overlapping dialogue lines", shot_id=sid)
                    break
            seen_spans.setdefault(speaker, []).append((start, end))
            if source_dialogue is not None:
                exact = any(
                    isinstance(item, dict)
                    and item.get("speaker") == speaker
                    and item.get("line") == line.get("text")
                    for item in source_dialogue
                )
                if not exact:
                    _add(report["blockers"], "SOUND_DIALOGUE_SOURCE_DRIFT",
                         "dialogue is not in the reviewed source ledger", shot_id=sid)
            elif dialogue:
                _add(report["reviews"], "SOUND_DIALOGUE_SOURCE_NOT_LEDGERED",
                     "dialogue exists but the base has no source dialogue ledger",
                     shot_id=sid)
        subtitles = speech.get("subtitle_cues")
        if not isinstance(subtitles, list):
            _add(report["blockers"], "SOUND_SUBTITLE_CUES_INVALID",
                 "subtitle_cues must be a list", shot_id=sid)
        else:
            spoken_texts = {line.get("text") for line in dialogue if isinstance(line, dict)}
            if isinstance(voice, dict) and _text(voice.get("text")):
                spoken_texts.add(voice["text"])
            for cue in subtitles:
                if (not isinstance(cue, dict)
                        or not _text(cue.get("text"))
                        or cue.get("text") not in spoken_texts
                        or not _inside(cue.get("from_s"), duration)
                        or not _inside(cue.get("to_s"), duration)
                        or not isinstance(cue.get("from_s"), (int, float))
                        or not isinstance(cue.get("to_s"), (int, float))
                        or cue["to_s"] <= cue["from_s"]):
                    _add(report["blockers"], "SOUND_SUBTITLE_CUE_INVALID",
                         "subtitle must match spoken text and sit inside the shot",
                         shot_id=sid)
        policy = speech.get("lip_sync_policy")
        if not _text(policy):
            _add(report["blockers"], "SOUND_LIPSYNC_POLICY_MISSING",
                 "speech needs an explicit lip-sync policy", shot_id=sid)
        else:
            onscreen = any(line.get("kind") == "onscreen_dialogue"
                           for line in dialogue if isinstance(line, dict))
            lowered = policy.lower()
            if onscreen and not any(word in lowered for word in ("lip", "口型", "required")):
                _add(report["blockers"], "SOUND_ONSCREEN_POLICY_MISSING",
                     "onscreen dialogue policy must explicitly require lip sync",
                     shot_id=sid)
            if not onscreen and not any(word in lowered for word in
                                        ("no lip", "none", "不驱动", "不要求")):
                _add(report["blockers"], "SOUND_OFFSCREEN_POLICY_AMBIGUOUS",
                     "no onscreen dialogue must state that lip sync is not driven",
                     shot_id=sid)
    return report
