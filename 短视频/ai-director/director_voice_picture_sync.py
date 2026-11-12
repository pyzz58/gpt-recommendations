#!/usr/bin/env python3
"""QO-D08: source-exact speech, pictured speakers and subtitle cue custody.

Reuses QO-D19's already validated audio/subtitle editor sheet for a reblocked
episode. Explicit director shot IDs and source timecodes identify each video
fragment, so a reaction shot need not hallucinate speaking mouths. Nothing
here watches media, runs ASR, synthesizes voices or certifies lip sync. Native
dialogue remains a media REVIEW candidate, never a guarantee.
"""
from __future__ import annotations

from copy import deepcopy
import math

import agent_team as team

VERSION = "director-dialogue-audio-picture-custody-v1"
FIELDS = ("version", "source_digest", "base_digest", "editor_cue_sheet_digest",
          "audio", "captions", "human_media_review_authenticated",
          "actual_audio_or_frames_inspected")
AUDIO_FIELDS = ("cue_id", "beat_id", "source_kind", "speaker",
                "source_text_exact", "story_from_s", "story_to_s",
                "audio_implementation", "picture_segments",
                "precise_voice_recording_dependency",
                "failure_and_local_repair_instruction")
SEG_FIELDS = ("director_shot_id", "story_from_s", "story_to_s",
              "speaker_picture_status", "lip_target_character_id",
              "other_visible_characters_must_not_mouth_this_dialogue",
              "camera_and_actor_instructions")
SUB_FIELDS = ("subtitle_id", "source_cue_id", "text_exact",
              "story_from_s", "story_to_s", "picture_segments",
              "font_and_safe_area_intention", "requires_actual_render_check")
AUDIO_IMPLEMENTATIONS = frozenset({
    "post_dubbing", "native_dialogue_candidate", "post_voiceover",
})
SCREEN_STATES = frozenset({"on_camera_speaking", "off_camera_audio",
                           "narration_no_visible_speaker"})
EPS = 1e-5


class SpeechPictureError(ValueError):
    """Never expose script/actor data in error strings."""


def _need(flag, code):
    if not flag:
        raise SpeechPictureError(code)


def _shape(x, fields, code):
    _need(type(x) is dict and set(x) == set(fields), code)


def _text(x, code, minlen=16):
    _need(isinstance(x, str) and minlen <= len(x.strip()) <= 2000 and
          "\0" not in x, code)


def _time(a, b):
    return (type(a) in (int, float) and type(b) in (int, float) and
            math.isfinite(a) and math.isfinite(b) and 0 <= a < b)


def _sheet(base, state):
    _need(team.fingerprint(base) == state.get("base_digest"),
          "SYNC_NOT_CURRENT_EPISODE")
    sheet = base.get("director_editor_cue_sheet")
    mode = base.get("screenplay_handoff_mode", {})
    _need(isinstance(sheet, dict) and
          sheet.get("kind") == "qod19_editor_cue_sheet_planning_only" and
          sheet.get("source_screenplay_digest") == state.get("source_digest") and
          isinstance(mode, dict) and
          mode.get("screenplay_sha256") == state.get("source_digest") and
          sheet.get("lip_sync_verified") is False and
          sheet.get("audio_rendered") is False and
          sheet.get("subtitle_media_rendered") is False and
          isinstance(sheet.get("speech_cues"), list) and
          isinstance(sheet.get("subtitle_cues"), list),
          "SYNC_NEEDS_EXACT_DIRECTOR_SPEECH_CUE_SHEET")
    return sheet


def _role(base, segment, speaker, source_kind):
    sid = segment["director_shot_id"]
    shot = next((s for s in base["shots"] if s["id"] == sid), None)
    _need(shot is not None, "SYNC_SHEET_HAS_UNKNOWN_PICTURE_SHOT")
    if source_kind in ("narration", "voiceover"):
        return None
    # QO-D02's merged scene/beat map is the authoritative speaker identity,
    # and may have several picture shots with one shared audio line.
    mapping = shot["source_adaptation"].get("speaker_character_ids", {})
    _need(isinstance(mapping, dict) and
          isinstance(mapping.get(speaker), str) and mapping[speaker],
          "SYNC_DIALOGUE_SPEAKER_NOT_BOUND_TO_CANONICAL_CAST")
    return mapping[speaker]


def validate(base, state, plan):
    sheet = _sheet(base, state)
    _shape(plan, FIELDS, "SYNC_PLAN_FIELDS")
    _need(plan["version"] == VERSION and
          plan["base_digest"] == state["base_digest"] and
          plan["source_digest"] == state.get("source_digest") and
          plan["editor_cue_sheet_digest"] == team.fingerprint(sheet) and
          plan["human_media_review_authenticated"] is False and
          plan["actual_audio_or_frames_inspected"] is False,
          "SYNC_OLD_SOURCE_OR_FAKE_REAL_MEDIA_REVIEW")
    cues, subtitles = plan["audio"], plan["captions"]
    _need(isinstance(cues, list) and
          len(cues) == len(sheet["speech_cues"]) and
          isinstance(subtitles, list) and
          len(subtitles) == len(sheet["subtitle_cues"]),
          "SYNC_MISSING_CANONICAL_SPEECH_OR_CAPTIONS")
    for source, row in zip(sheet["speech_cues"], cues):
        _shape(row, AUDIO_FIELDS, "SYNC_AUDIO_ROW_FIELDS")
        _need(all(row[f] == source[f] for f in (
            "cue_id", "beat_id", "source_kind", "speaker")) and
              row["source_text_exact"] == source["text_exact"] and
              _time(row["story_from_s"], row["story_to_s"]) and
              abs(row["story_from_s"] - source["story_from_s"]) <= EPS and
              abs(row["story_to_s"] - source["story_to_s"]) <= EPS and
              row["audio_implementation"] in AUDIO_IMPLEMENTATIONS,
              "SYNC_SOURCE_WORDS_SPEAKER_OR_ABSOLUTE_TIME_DRIFT")
        audio_mode = source["audio_mode"]
        if source["source_kind"] != "dialogue":
            _need(row["audio_implementation"] == "post_voiceover",
                  "SYNC_NARRATOR_HAS_NO_ON_CAMERA_LIP_TARGET")
        else:
            _need(row["audio_implementation"] in (
                "post_dubbing", "native_dialogue_candidate"),
                "SYNC_DIALOGUE_AUDIO_ROUTING_INVALID")
        for key in ("precise_voice_recording_dependency",
                    "failure_and_local_repair_instruction"):
            _text(row[key], "SYNC_DIRECTOR_SOUND_CRAFT_NOT_SPECIFIED")
        segments = row["picture_segments"]
        _need(isinstance(segments, list) and
              len(segments) == len(source["picture_segments"]),
              "SYNC_MISSING_REAL_PICTURE_SEGMENTS")
        any_on_camera = False
        for actual, intended in zip(segments, source["picture_segments"]):
            _shape(actual, SEG_FIELDS, "SYNC_PICTURE_SEGMENT_FIELDS")
            _need(all(actual[k] == intended[k] for k in (
                "director_shot_id", "beat_id") if k in actual and k in intended)
                  and actual["director_shot_id"] == intended["director_shot_id"] and
                  _time(actual["story_from_s"], actual["story_to_s"]) and
                  abs(actual["story_from_s"] - intended["story_from_s"]) <= EPS and
                  abs(actual["story_to_s"] - intended["story_to_s"]) <= EPS and
                  actual["speaker_picture_status"] in SCREEN_STATES and
                  type(actual["other_visible_characters_must_not_mouth_this_dialogue"]) is bool and
                  actual["other_visible_characters_must_not_mouth_this_dialogue"] is True,
                  "SYNC_PICTURE_CUT_OR_OTHER_MOUTH_POLICY_INVALID")
            _text(actual["camera_and_actor_instructions"],
                  "SYNC_ACTOR_AND_EDITOR_CRAFT_MISSING")
            cid = _role(base, actual, row["speaker"], row["source_kind"])
            if cid is None:
                _need(actual["speaker_picture_status"] ==
                      "narration_no_visible_speaker" and
                      actual["lip_target_character_id"] is None,
                      "SYNC_NARRATOR_CANNOT_LIP_SYNC_TO_ACTOR")
            else:
                _need(actual["speaker_picture_status"] !=
                      "narration_no_visible_speaker",
                      "SYNC_DIALOGUE_WRONGLY_IDENTIFIED_AS_NARRATION")
                if actual["speaker_picture_status"] == "on_camera_speaking":
                    shot = next(s for s in base["shots"]
                                if s["id"] == actual["director_shot_id"])
                    _need(cid in shot["character_ids"] and
                          actual["lip_target_character_id"] == cid,
                          "SYNC_MOUTH_TARGET_NOT_IN_ACTUAL_FRAME_CAST")
                    any_on_camera = True
                else:
                    _need(actual["lip_target_character_id"] is None,
                          "SYNC_REACTION_SHOT_SHOULD_NOT_ANIMATE_SPEAKER_MOUTH")
        if (source["source_kind"] == "dialogue" and
                audio_mode == "on_screen"):
            _need(any_on_camera,
                  "SYNC_ONSCREEN_SPEAKER_NEVER_ON_CAMERA")
        if (source["source_kind"] == "dialogue" and
                audio_mode == "off_screen"):
            _need(not any_on_camera,
                  "SYNC_OFFSCREEN_SCRIPT_CUE_REWRITTEN_ON_CAMERA")
    for source, row in zip(sheet["subtitle_cues"], subtitles):
        _shape(row, SUB_FIELDS, "SYNC_CAPTION_FIELDS")
        _need(all(row[k] == source[k] for k in (
            "subtitle_id", "source_cue_id", "text_exact")) and
              _time(row["story_from_s"], row["story_to_s"]) and
              abs(row["story_from_s"]-source["story_from_s"]) <= EPS and
              abs(row["story_to_s"]-source["story_to_s"]) <= EPS and
              row["picture_segments"] == source["picture_segments"] and
              row["requires_actual_render_check"] is True,
              "SYNC_SUBTITLE_TEXT_OR_SHOT_TIMING_DRIFT")
        _text(row["font_and_safe_area_intention"],
              "SYNC_CAPTION_READABILITY_UNSPECIFIED")
    return {
        "kind": "director_screenplay_exact_audio_picture_custody",
        "version": VERSION, "plan_digest": team.fingerprint(plan),
        "source_digest": state["source_digest"],
        "base_digest": state["base_digest"],
        "canonical_audio_cue_count": len(cues),
        "canonical_subtitle_cue_count": len(subtitles),
        "all_audio_subtitle_source_text_and_timing_retained": True,
        "lip_sync_verified_in_real_video": False,
        "asr_transcription_or_human_listening_performed": False,
        "two_people_one_speaker_actual_mouths_verified": False,
        "post_production_audio_and_caption_media_generated": False,
        "no_external_api_or_publication_authority": True,
    }


def build_role_context(base, state, plan, task_id):
    proof = validate(base, state, plan)
    _need(task_id in ("sound", "editing_animation", "ai_technical",
                      "director_final"),
          "SYNC_ROLE_NOT_RESPONSIBLE")
    return {
        "kind": "one_director_source_exact_sound_picture_instruction",
        "source_digest": proof["source_digest"],
        "cue_sheet_digest": plan["editor_cue_sheet_digest"],
        "plan_digest": proof["plan_digest"],
        "profession": task_id,
        "spoken_words_and_origin": deepcopy(plan["audio"]),
        "subtitles_and_picture_cut_custody": deepcopy(plan["captions"]),
        "provider_must_not_change_script_or_double_voice": True,
        "real_audio_asr_lip_sync_subtitle_manual_qc_still_required": True,
        "model_or_media_dispatch_authorized": False,
    }


def audit_real_media_review_record(base, state, plan, record):
    """Assess an operator-entered listening/viewing record, NOT media bytes.

    The model cannot independently verify that someone viewed the file. A
    trusted private runtime must hash/probe actual media, then bind a review
    from a real operator. No autopass from generated/self-filled reviews.
    """
    proof = validate(base, state, plan)
    fields = ("version", "plan_digest", "reviewed_media_sha256",
              "reviewer", "watched_and_listened_entire_episode",
              "audio_events", "subtitle_events")
    _shape(record, fields, "SYNC_MEDIA_REVIEW_RECORD_SHAPE")
    _need(record["version"] == VERSION and
          record["plan_digest"] == proof["plan_digest"] and
          isinstance(record["reviewed_media_sha256"], str) and
          len(record["reviewed_media_sha256"]) == 64 and
          all(c in "0123456789abcdef" for c in record["reviewed_media_sha256"]) and
          isinstance(record["reviewer"], str) and
          len(record["reviewer"].strip()) >= 2 and
          record["watched_and_listened_entire_episode"] is True,
          "SYNC_MEDIA_REVIEW_CANNOT_CLAIM_REAL_FILE_AUTHENTICATION")
    aud = record["audio_events"]
    subs = record["subtitle_events"]
    _need(isinstance(aud, list) and
          len(aud) == proof["canonical_audio_cue_count"] and
          isinstance(subs, list) and
          len(subs) == proof["canonical_subtitle_cue_count"],
          "SYNC_MEDIA_REVIEW_MISSING_PER_CUE_EVIDENCE")
    failures = []
    for source, obs in zip(plan["audio"], aud):
        _shape(obs, ("cue_id", "heard_exact_text",
                     "voice_speaker_matches", "mouth_target_matches",
                     "other_visible_mouths_not_speaking",
                     "time_alignment_matches", "notes"),
               "SYNC_MEDIA_AUDIO_OBSERVATION")
        _need(obs["cue_id"] == source["cue_id"] and
              all(type(obs[k]) is bool for k in (
                  "voice_speaker_matches", "mouth_target_matches",
                  "other_visible_mouths_not_speaking",
                  "time_alignment_matches")) and
              isinstance(obs["notes"], str),
              "SYNC_MEDIA_AUDIO_OBSERVATION_VALUES")
        if obs["heard_exact_text"] != source["source_text_exact"] or not all(
            obs[k] for k in (
                "voice_speaker_matches", "mouth_target_matches",
                "other_visible_mouths_not_speaking",
                "time_alignment_matches")):
            failures.append({"cue_id": source["cue_id"],
                             "repair_owner": "sound_or_picture_editor"})
    for source, obs in zip(plan["captions"], subs):
        _shape(obs, ("subtitle_id", "rendered_exact_text",
                     "time_alignment_matches", "readable_and_safe",
                     "notes"), "SYNC_MEDIA_CAPTION_OBSERVATION")
        _need(obs["subtitle_id"] == source["subtitle_id"] and
              type(obs["time_alignment_matches"]) is bool and
              type(obs["readable_and_safe"]) is bool and
              isinstance(obs["notes"], str),
              "SYNC_MEDIA_CAPTION_OBSERVATION_VALUES")
        if (obs["rendered_exact_text"] != source["text_exact"] or
                not obs["time_alignment_matches"] or
                not obs["readable_and_safe"]):
            failures.append({"subtitle_id": source["subtitle_id"],
                             "repair_owner": "editing_animation"})
    return {
        "kind": "operator_declared_media_alignment_review_not_authenticated",
        "version": VERSION,
        "plan_digest": proof["plan_digest"],
        "review_record_digest": team.fingerprint(record),
        "reported_lip_text_and_subtitle_failures": failures,
        "reported_unresolved_issue_count": len(failures),
        "actual_media_hash_recomputed_here": False,
        "human_reviewer_identity_authenticated_here": False,
        "independent_asr_or_frame_lip_sync_verified_here": False,
        "can_publish_or_autoapprove": False,
    }
