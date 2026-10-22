#!/usr/bin/env python3
"""QO-D04: offline, CHANNEL/REVISION scoped video capability evidence.

A director chooses the shot's dramatic necessity FIRST. The technical crew
may choose a candidate provider/channel only within an evidenced API subset.
This registry does NOT implement other companies' APIs; only seedance_adapter
has a separately operator-authorized endpoint. The same model name via a
different channel MUST be treated as a different provider id and reverified.
Unknown capability and unverifiable price/region is NEVER mapped to 'yes'.
"""
from __future__ import annotations

from copy import deepcopy
import math

import agent_team as team

VERSION = "director-evidence-based-provider-routing-v1"
SOURCES_AS_OF = "2026-10-22"
ROUTES = frozenset({"ai_video", "static_post", "edit_composite",
                    "live_action_insert", "post_production"})
POST = ROUTES - {"ai_video"}
SOURCE_LINKS = {
    "veo": "https://ai.google.dev/gemini-api/docs/veo",
    "runway_cloudflare": "https://developers.cloudflare.com/ai/models/runwayml/gen-4.5/",
    "seedance_local": "短视频/ai-director/seedance_adapter.py",
}
# "supported" means ONLY that the named public route documents the narrow
# config, not that the account has paid access, quota, rights or stability.
# "locally_implemented" means even more narrowly: existing adapter guards.
CATALOG = {
    "seedance-2.5-volcengine-existing-adapter": {
        "channel": "volcengine", "model": "doubao-seedance-2-5-260628",
        "status": "locally_implemented_not_live_certified",
        "evidence": SOURCE_LINKS["seedance_local"],
        "durations_integer_s": list(range(4, 16)),
        "ratios": ["9:16"], "resolutions": ["720p"],
        "reference_images_max": 3, "native_audio": True,
        "first_last_frame": False, "multi_shot": False,
        "native_audio_quality_verified": False,
        "endpoint_dispatch_enabled_by_this_module": False,
    },
    "seedance-2.5-byteplus-existing-adapter": {
        "channel": "byteplus", "model": "dreamina-seedance-2-5-260628",
        "status": "locally_implemented_not_live_certified",
        "evidence": SOURCE_LINKS["seedance_local"],
        "durations_integer_s": list(range(4, 16)),
        "ratios": ["9:16"], "resolutions": ["720p"],
        "reference_images_max": 3, "native_audio": True,
        "first_last_frame": False, "multi_shot": False,
        "native_audio_quality_verified": False,
        "endpoint_dispatch_enabled_by_this_module": False,
    },
    "veo-3.1-gemini-api-preview": {
        "channel": "gemini-api", "model": "veo-3.1-generate-preview",
        "status": "official_docs_only_no_local_adapter",
        "evidence": SOURCE_LINKS["veo"],
        "durations_integer_s": [4, 6, 8],
        "ratios": ["9:16", "16:9"],
        "resolutions": ["720p", "1080p", "4k"],
        "reference_images_max": 3, "native_audio": True,
        "first_last_frame": True, "multi_shot": False,
        "native_audio_quality_verified": False,
        "endpoint_dispatch_enabled_by_this_module": False,
    },
    "runway-gen4.5-cloudflare-workers-ai": {
        "channel": "cloudflare-workers-ai", "model": "@cf/runwayml/gen-4.5",
        "status": "channel_public_docs_only_no_local_adapter",
        "evidence": SOURCE_LINKS["runway_cloudflare"],
        "durations_integer_s": list(range(2, 11)),
        "ratios": ["9:16", "16:9", "1:1", "4:3", "3:4", "21:9"],
        "resolutions": ["720p"],
        "reference_images_max": 1, "native_audio": False,
        "first_last_frame": False, "multi_shot": False,
        "native_audio_quality_verified": False,
        "endpoint_dispatch_enabled_by_this_module": False,
    },
}
UNCERTIFIED = frozenset({
    "seedance-2.0-unverified-channel", "kling-3-unverified-channel",
    "runway-direct-api-unverified", "veo-other-channel-unverified",
})
PLAN_FIELDS = (
    "version", "source_digest", "base_digest",
    "director_lock_digest", "shots", "rights_and_budget_verified",
    "actual_provider_media_tested", "human_operator_approval_authenticated",
)
SHOT_FIELDS = (
    "shot_id", "dramatic_necessity", "nonnegotiable_performance_or_fact",
    "preferred_route", "provider_id", "duration_s", "aspect_ratio",
    "resolution", "reference_image_count", "use_first_last_frame",
    "requires_multiple_internal_camera_shots", "audio_route",
    "what_provider_may_not_simplify", "fallback_with_artistic_cost",
    "remaining_unknowns_for_operator",
)
AUDIO_ROUTES = frozenset({
    "silent_video_then_post_voice", "native_dialogue_candidate",
    "post_sound_only", "no_spoken_words",
})


class ProviderCapabilityError(ValueError):
    """Error codes only; never reveal private prompts or media URLs."""


def _need(yes, code):
    if not yes:
        raise ProviderCapabilityError(code)


def _text(s, code):
    _need(isinstance(s, str) and 16 <= len(s.strip()) <= 2000 and
          "\0" not in s, code)


def catalogue():
    return {
        "kind": "source_and_channel_scoped_video_capability_registry",
        "version": VERSION, "as_of": SOURCES_AS_OF,
        "entries": deepcopy(CATALOG),
        "uncertified_must_not_be_selected": sorted(UNCERTIFIED),
        "price_region_quota_and_model_authentication": "unknown",
        "video_generated": False, "paid_api_dispatch_authorized": False,
    }


def _source(base, state):
    _need(isinstance(base, dict) and isinstance(state, dict) and
          team.fingerprint(base) == state.get("base_digest"),
          "CAPABILITY_NOT_SAME_IMMUTABLE_EPISODE")
    task = state.get("tasks", {}).get("director_lock", {})
    _need(task.get("status") == "completed" and
          isinstance(task.get("deliverable"), dict),
          "CAPABILITY_NEEDS_REAL_DIRECTOR_LOCK")
    return team.fingerprint(task["deliverable"])


def _veo_conditional(entry):
    # Gemini Veo requires 8s for >=1080p, style reference inputs, and frame
    # interpolation as documented for this channel; no quote of cost/region.
    _need(entry["duration_s"] == 8 or (
        entry["resolution"] == "720p" and
        entry["reference_image_count"] == 0 and
        not entry["use_first_last_frame"]),
        "CAPABILITY_VEO_CONDITIONAL_8S_REQUIRED")


def _shot(base_shot, row):
    _need(type(row) is dict and set(row) == set(SHOT_FIELDS),
          "CAPABILITY_SHOT_FIELDS")
    _need(row["shot_id"] == base_shot["id"] and
          type(row["duration_s"]) in (float, int) and
          math.isfinite(row["duration_s"]) and
          row["duration_s"] == base_shot["duration"] and
          row["aspect_ratio"] == "9:16",
          "CAPABILITY_CANNOT_CHANGE_DIRECTOR_SHOT_DURATION_OR_RATIO")
    for field in ("dramatic_necessity",
                  "nonnegotiable_performance_or_fact",
                  "what_provider_may_not_simplify",
                  "fallback_with_artistic_cost",
                  "remaining_unknowns_for_operator"):
        _text(row[field], "CAPABILITY_MISSING_CREATIVE_PRESERVATION")
    route, mid = row["preferred_route"], row["provider_id"]
    _need(isinstance(route, str) and route in ROUTES and
          isinstance(row["audio_route"], str) and row["audio_route"] in AUDIO_ROUTES and
          type(row["use_first_last_frame"]) is bool and
          type(row["requires_multiple_internal_camera_shots"]) is bool and
          type(row["reference_image_count"]) is int and
          0 <= row["reference_image_count"] <= 3,
          "CAPABILITY_ROUTING_FIELDS_INVALID")
    if route in POST:
        _need(mid is None and row["resolution"] is None and
              row["reference_image_count"] == 0 and
              row["use_first_last_frame"] is False and
              row["requires_multiple_internal_camera_shots"] is False and
              row["audio_route"] != "native_dialogue_candidate",
              "CAPABILITY_POST_ROUTE_HAS_FAKE_VIDEO_PROVIDER")
        return "post_production_only_no_video_api"
    _need(route == "ai_video" and mid not in UNCERTIFIED and
          isinstance(mid, str) and mid in CATALOG,
          "CAPABILITY_UNVERIFIED_PROVIDER_OR_CHANNEL")
    spec = CATALOG[mid]
    _need(type(row["duration_s"]) is int and
          row["duration_s"] in spec["durations_integer_s"] and
          row["aspect_ratio"] in spec["ratios"] and
          row["resolution"] in spec["resolutions"] and
          row["reference_image_count"] <= spec["reference_images_max"] and
          (not row["use_first_last_frame"] or spec["first_last_frame"]) and
          (not row["requires_multiple_internal_camera_shots"] or spec["multi_shot"]),
          "CAPABILITY_NOT_SUPPORTED_IN_SELECTED_CHANNEL")
    _need(row["audio_route"] != "post_sound_only" and
          (row["audio_route"] != "native_dialogue_candidate" or
           spec["native_audio"]),
          "CAPABILITY_AUDIO_ROUTE_UNSUPPORTED")
    if mid == "veo-3.1-gemini-api-preview":
        _veo_conditional(row)
    return spec["status"]


def validate(base, state, plan):
    """Only a preflight: no API, model access, lip sync or artistic verdict."""
    lock = _source(base, state)
    _need(type(plan) is dict and set(plan) == set(PLAN_FIELDS) and
          plan["version"] == VERSION and
          plan["source_digest"] == state.get("source_digest") and
          plan["base_digest"] == state["base_digest"] and
          plan["director_lock_digest"] == lock and
          plan["rights_and_budget_verified"] is False and
          plan["actual_provider_media_tested"] is False and
          plan["human_operator_approval_authenticated"] is False,
          "CAPABILITY_STALE_OR_FALSE_RELEASE_ASSERTION")
    rows = plan["shots"]
    _need(isinstance(rows, list) and
          len(rows) == len(state["shot_ids"]) == len(base["shots"]),
          "CAPABILITY_MISSING_PHYSICAL_DIRECTOR_SHOT")
    decisions = []
    for shot, row in zip(base["shots"], rows):
        decisions.append({
            "shot_id": shot["id"],
            "technical_readiness": _shot(shot, row),
            "selected_provider_id": row["provider_id"],
            "route": row["preferred_route"],
        })
    return {
        "kind": "review_required_director_first_provider_preflight",
        "version": VERSION,
        "capability_registry_as_of": SOURCES_AS_OF,
        "plan_digest": team.fingerprint(plan),
        "locked_director_revision_digest": lock,
        "planned_shots": decisions,
        "can_call_other_vendor_api_here": False,
        "can_dispatch_seedance_adapter_from_this_module": False,
        "pricing_access_rights_and_region_certified": False,
        "real_media_and_lip_sync_verified": False,
        "director_intent_changed_for_provider": False,
        "paid_api_or_publication_authorized": False,
    }


def crew_context(base, state, plan, task_id):
    proof = validate(base, state, plan)
    _need(task_id in ("ai_technical", "director_final"),
          "CAPABILITY_CONTEXT_WRONG_PROFESSION")
    return {
        "kind": "source_locked_director_to_ai_specialist_video_constraints",
        "version": VERSION,
        "plan_digest": proof["plan_digest"],
        "task_id": task_id,
        "real_director_shot_choices": deepcopy(plan["shots"]),
        "prohibited": (
            "Do not secretly shorten, lengthen, re-time, rewrite screenplay, "
            "remove a visible dramatic decision, or fabricate vendor support"),
        "provider_capability_is_not_generation_permission": True,
        "need_real_provider_account_and_version_check_before_dispatch": True,
    }


def validate_technical_delivery(base, state, plan, output):
    """Check actual technician's routes; no silent video-provider substitution."""
    validate(base, state, plan)
    _need(isinstance(output, dict) and isinstance(output.get("shots"), dict),
          "CAPABILITY_NO_REAL_TECHNICAL_DELIVERY")
    planned = {p["shot_id"]: p for p in plan["shots"]}
    _need(set(output["shots"]) <= set(planned),
          "CAPABILITY_TECHNICAL_UNKNOWN_SHOT")
    for sid, row in output["shots"].items():
        gen = row.get("generation") if isinstance(row, dict) else None
        _need(isinstance(gen, dict) and
              gen.get("route") == planned[sid]["preferred_route"],
              "CAPABILITY_TECHNICAL_IGNORED_DIRECTOR_ROUTE")
    return {
        "kind": "director_tech_delivery_route_alignment_only",
        "plan_digest": team.fingerprint(plan),
        "verified_scoped_shots": sorted(output["shots"]),
        "provider_api_dispatch_supported": False,
        "technical_video_and_artistic_quality_verified": False,
    }
