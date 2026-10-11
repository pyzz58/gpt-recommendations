#!/usr/bin/env python3
"""Offline end-to-end production *instruction* export for AI video + post.

Generates actual reviewable, per-shot prompt candidate documents from the
existing qualified v0.2 directing work. It does NOT call a model, generate
media, verify source claims, obtain commercial licences, or authorize upload.
The two entry paths are deliberately distinct:
- existing vetted-in-repository v0.2 reference examples (no live crew claimed);
- a snapshot-locked, complete 10-stage source-bound crew handoff.

Do not put user source/deliverables in a public repository or GitHub Actions.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import agent_team as team
import director_v2
import director_workbook
import editorial_review_lock as locks
import creative_production_handoff as first_vision

SCHEMA = "operator-video-production-bundle-v1"
TARGETS = ("wan", "seedance")
MAX_SHOTS = 120


class ProductionDeliveryError(ValueError):
    """Private-material-safe error codes (never echo document contents)."""


def _hash(value):
    return team.fingerprint(value)


def _require(ok, code):
    if not ok:
        raise ProductionDeliveryError(code)


def _make_bundle(base, direction, *, provenance, crew_workbook=None,
                 locked_digest=None, source_digest=None):
    _require(isinstance(base, dict) and isinstance(direction, dict),
             "DELIVERY_INPUT_INVALID")
    _require(isinstance(base.get("shots"), list) and
             1 <= len(base["shots"]) <= MAX_SHOTS, "DELIVERY_INVALID_SHOT_COUNT")
    # The v0.2 composer rejects inconsistent timestamps, missing professional
    # camera/acting/graphics fields, unsupported production routes and more.
    try:
        errors, _ = director_v2.validate(base, direction)
        if errors:
            raise ProductionDeliveryError("DELIVERY_UNQUALIFIED_DIRECTION")
        package = director_v2.compile_package(base, direction)
        book = crew_workbook or director_workbook.compile_workbook(base, direction)
    except (KeyError, TypeError, ValueError) as err:
        if isinstance(err, ProductionDeliveryError):
            raise
        raise ProductionDeliveryError("DELIVERY_DIRECTION_COMPILE_FAILED") from None

    by_id = {item["shot_id"]: item for item in package["shots"]}
    workbook_ids = [x["shot_id"] for x in book["shots"]]
    expected = [s["id"] for s in base["shots"]]
    _require(workbook_ids == expected and set(by_id) == set(expected),
             "DELIVERY_SHOT_ORDER_OR_COVERAGE")
    graphic_claims = {c["id"]: c for c in base.get("claims", [])}
    deliverables = []
    for shot, row in zip(base["shots"], book["shots"]):
        sid = shot["id"]
        job = by_id[sid]
        is_video = job["execution_route"] == "ai_video"
        prompts = deepcopy(job["prompts"]) if is_video else {}
        if is_video:
            _require(set(prompts) == set(TARGETS) and all(
                isinstance(prompts[target], str) and prompts[target].strip()
                for target in TARGETS), "DELIVERY_AI_PROMPT_MISSING")
        else:
            _require(not job["prompts"], "DELIVERY_NONVIDEO_AI_PROMPT_CONFLICT")
        claim_ids = shot.get("claim_ids", [])
        _require(all(cid in graphic_claims for cid in claim_ids),
                 "DELIVERY_UNKNOWN_CLAIM")
        requirements = deepcopy(job["reference_roles"])
        deliverables.append({
            "shot_id": sid,
            "timeline": {"start_s": shot["start"],
                         "end_s": shot["start"] + shot["duration"],
                         "duration_s": shot["duration"],
                         "out_transition": shot["transition"]},
            "production_route": job["execution_route"],
            "target_type": "video_generation_candidate" if is_video else "postproduction_only",
            "shot_objective": deepcopy(row["story"]),
            "film_script": {"voiceover": shot["narration"],
                            "subtitles": deepcopy(shot["subtitles"])},
            "action_beats": deepcopy(row["performance"]["timed_beats"]),
            "camera": deepcopy(row["camera"]),
            "lighting_and_set": deepcopy(row["set_and_lighting"]),
            "character_and_prop_continuity": deepcopy(row["continuity"]),
            "ai_video_prompt_candidates": prompts,
            "required_reference_roles": requirements,
            "reference_files_confirmed": False,
            "postproduction_work_order": deepcopy(job["postproduction_job"]),
            "sound_and_voice_direction": deepcopy(row["sound"]),
            "editing_and_animation": {
                "editing": deepcopy(row["editing"]),
                "animation": deepcopy(row["animation"]),
                "graphics": deepcopy(row["graphics"])},
            "claim_review": [{
                "id": cid, "text_from_source": graphic_claims[cid]["source_quote"],
                "review_state": graphic_claims[cid]["status"],
                "external_fact_check_completed": False,
            } for cid in claim_ids],
            "human_checklist": [
                "核对原文事实、数字口径与删减批准",
                "核对人物、服装、道具、参考资产和相邻镜头连续性",
                "核对 AI 视频模型当前是否支持该提示词与镜头长度",
                "核对配音、音效、文字图表、剪辑与版权后期方案",
            ],
            "operator_actions_allowed": ["read", "review", "copy_prompt_manually"],
            "model_generation_authorized": False,
            "video_generated": False,
        })
    _require(len(deliverables) == len(base["shots"]), "DELIVERY_SHOT_COUNT_DRIFT")
    _require(package.get("not_generated_video") is True and
             package.get("publishing_allowed") is False,
             "DELIVERY_UPSTREAM_RELEASE_INCONSISTENT")
    design_ready = bool(book["director_review"]["production_blueprint_ready"])
    source_reviews_open = any(c.get("status") != "verified"
                              for c in base.get("claims", []))
    result = {
        "schema_version": SCHEMA, "kind": "ai_director_operator_work_orders",
        "provenance": provenance,
        "source_plan_digest": _hash(base),
        "direction_digest": _hash(direction),
        "locked_plan_digest": locked_digest,
        "source_digest": source_digest,
        "project": {
            "title": base["title"], "core_message": base["core_message"],
            "duration_s": base["duration"], "aspect_ratio": base["aspect_ratio"],
            "total_shots": len(deliverables), "supported_prompt_targets": list(TARGETS)},
        "production_counts": deepcopy(package["production_summary"]),
        "shooting_order": [x["shot_id"] for x in deliverables],
        "shots": deliverables,
        "editor_timeline": deepcopy(book["editor_decision_list"]),
        "cross_shot_bridges": deepcopy(book["narrative_bridges"]),
        "full_workbook_review": {
            "director_blueprint_complete": design_ready,
            "editor_handoff_ready": bool(book["director_review"]["editor_handoff_ready"]),
            "creative_findings": len(book["director_review"]["findings"]),
            "independent_crew_completed": provenance == "locked_ten_role_crew",
            "team_delivery_gate": (
                deepcopy(book.get("team_delivery_gate"))
                if provenance == "locked_ten_role_crew" else None),
            "media_generated": False,
        },
        "blocking_conditions": [
            "NO_AUTHORIZED_PROVIDER_DISPATCH",
            "REFERENCE_ASSETS_NOT_VERIFIED",
            "REAL_VIDEO_TEST_NOT_COMPLETED",
            "HUMAN_EDITORIAL_AND_RIGHTS_REVIEW_REQUIRED",
        ] + (["CLAIMS_STILL_REQUIRE_INDEPENDENT_VERIFICATION"]
             if source_reviews_open else []) +
            (["DIRECTOR_BLUEPRINT_HAS_UNFINISHED_REVIEW"]
             if not design_ready else []),
        "source_facts_verified": False,
        "human_approved": False,
        "external_model_calls": 0,
        "actual_video_generated": False,
        "publishing_allowed": False,
        "ready_to_call_video_model": False,
        "status": "offline_operator_review_workbook_not_model_ready",
    }
    return result


def build_reference_delivery(base, direction):
    """Export the repository's existing professional v0.2 demo/reference.

    No claim that roles were executed: a provided direction may have been
    manually designed earlier, and its output still needs human review.
    """
    return _make_bundle(base, direction,
                        provenance="existing_v02_reference_not_agent_run")


def build_locked_crew_delivery(snapshot, episode_source, final_team_state):
    """From accepted structural planning snapshot AND full role DAG only.

    No proof of authenticated human signoff. This is merely the same plan
    and source that all ten offline roles inspected, with QA findings.
    """
    if not isinstance(snapshot, dict) or not isinstance(final_team_state, dict):
        raise ProductionDeliveryError("DELIVERY_LOCK_OR_TEAM_INVALID")
    try:
        lock = locks.stage_locked_team(snapshot, episode_source)
    except (KeyError, TypeError, ValueError):
        raise ProductionDeliveryError("DELIVERY_UNTRUSTED_LOCK") from None
    base = snapshot["plan"]
    _require(final_team_state.get("base_digest") == lock["plan_digest"],
             "DELIVERY_TEAM_WRONG_PLAN_VERSION")
    _require(final_team_state.get("source_digest") == lock["source_digest"],
             "DELIVERY_TEAM_WRONG_SOURCE_VERSION")
    try:
        team._check_state(final_team_state)
        _require(all(x["status"] == "completed"
                     for x in final_team_state["tasks"].values()),
                 "DELIVERY_CREW_HAS_OPEN_TASKS")
        _require(team.source_matches(final_team_state, episode_source),
                 "DELIVERY_SOURCE_DOES_NOT_MATCH")
        # Also validate final *merged* camera/scene/light source consistency.
        # Older reviewed shot revisions cannot bypass source-locked QA.
        first_vision.camera_requirements_for_role(
            base, final_team_state["tasks"]["camera_art"]["deliverable"])
        book = team.compile_team_workbook(base, final_team_state, strict=False)
        direction = team.assemble_direction(base, final_team_state)
    except (KeyError, TypeError, ValueError) as err:
        if isinstance(err, ProductionDeliveryError):
            raise
        raise ProductionDeliveryError("DELIVERY_CREW_QA_OR_COMPILE_BLOCKED") from None
    bundle = _make_bundle(
        base, direction, provenance="locked_ten_role_crew", crew_workbook=book,
        locked_digest=lock["plan_digest"], source_digest=lock["source_digest"])
    # Preserve the original real director/editor creative intent in the
    # exported operator pack, with the original source/plan hashes. The old
    # assembler had dropped it when v0.1 transitioned to a new ten-role DAG.
    editorial = first_vision.validate_locked_handoff(snapshot, episode_source)
    initial_gaps = first_vision.inspect_preproduction(base, editorial)
    designed = editorial["creative_concept"]["shot_designs"]
    for job, vision in zip(bundle["shots"], designed):
        _require(job["shot_id"] == vision["shot_id"],
                 "DELIVERY_ORIGINAL_VISION_SHOT_ORDER_DRIFT")
        job["first_director_editor_vision"] = {
            key: deepcopy(vision[key]) for key in (
                "visual_intention", "camera_intention", "light_intention",
                "transition_intention", "reason", "observable_action")}
        job["first_vision_is_unapproved_planning_proposal"] = True
    bundle["creative_intent_provenance"] = {
        "first_director_editor_intent_digest": snapshot["creative_handoff_digest"],
        "original_plan_digest": snapshot["plan_digest"],
        "source_digest": snapshot["source_digest"],
        "initial_preproduction_gaps": initial_gaps,
        "initial_gaps_not_proof_of_current_department_failures": True,
        "actual_physical_references_verified": False,
        "human_approved": False,
        "real_video_feasibility_proven": False,
    }
    return bundle


def render_operator_markdown(bundle):
    """Read-only production work orders, prompt copy/paste, and editing cues."""
    if not isinstance(bundle, dict) or bundle.get("schema_version") != SCHEMA:
        raise ProductionDeliveryError("DELIVERY_INVALID_BUNDLE")
    project = bundle["project"]
    lines = [
        "# " + project["title"] + "｜AI 视频制作工作单（仅供人工审阅）", "",
        "**本文件不是已生成的视频，也不构成付费模型调用授权。**",
        "导演版本：" + bundle["source_plan_digest"],
        "制作来源：" + bundle["provenance"],
        "画幅：" + project["aspect_ratio"] + " ｜ 时长：" +
        str(project["duration_s"]) + " 秒 ｜ 镜头：" +
        str(project["total_shots"]), "",
        "## 制作前必须解决的问题", "",
    ]
    lines += ["- " + x for x in bundle["blocking_conditions"]]
    lines += ["", "## 逐镜生产工单", ""]
    for shot in bundle["shots"]:
        t = shot["timeline"]
        lines += [
            "### " + shot["shot_id"] + "｜" + str(t["start_s"]) + "–" +
            str(t["end_s"]) + " 秒",
            "生产路线：" + shot["production_route"],
            "画面目标：" + shot["shot_objective"]["visible_change"],
            "旁白：" + shot["film_script"]["voiceover"],
            "参考资产：" + json.dumps(shot["required_reference_roles"], ensure_ascii=False),
            "参考素材已提供：否，必须人工核验",
            "",
        ]
        vision = shot.get("first_director_editor_vision")
        if vision:
            lines += [
                "**第一轮导演与剧本编辑的原始创意依据（仅提案、未验收）：**",
                "原始视觉意图：" + vision["visual_intention"],
                "摄影原始构想：" + vision["camera_intention"],
                "灯光原始构想：" + vision["light_intention"],
                "相邻镜接力意图：" + vision["transition_intention"], "",
            ]
        if shot["ai_video_prompt_candidates"]:
            for model, prompt in shot["ai_video_prompt_candidates"].items():
                lines += [
                    "**" + model + " 视频生成候选提示词（未实机验证）**", "",
                    "```text", prompt, "```", "",
                ]
        else:
            lines += ["**非 AI 视频生成镜头：只需后期制作，禁止强行生成真人视频。**", ""]
        for name, key in (
                ("表演动作节拍", "action_beats"),
                ("摄影及运镜", "camera"),
                ("布光与场景", "lighting_and_set"),
                ("声音与配音", "sound_and_voice_direction"),
                ("剪辑与动画", "editing_and_animation"),
                ("后期制作步骤", "postproduction_work_order"),
                ("事实标记", "claim_review")):
            lines += [name + "：", "```json",
                      json.dumps(shot[key], ensure_ascii=False, indent=2), "```", ""]
        lines += ["镜头验收待办："] + ["- " + x for x in shot["human_checklist"]] + [""]
    lines += ["## 全片剪辑时间线", "```json",
              json.dumps(bundle["editor_timeline"], ensure_ascii=False, indent=2),
              "```", "", "## 镜间接力",
              "```json", json.dumps(bundle["cross_shot_bridges"], ensure_ascii=False, indent=2),
              "```", "",
              "状态：" + bundle["status"],
              "人工批准：否；外部模型调用：0；视频生成：否；可以发布：否。", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Export v0.2 AI operator work orders offline (no models)")
    parser.add_argument("--base", required=True, help="Existing local plan JSON")
    parser.add_argument("--direction", required=True, help="Existing v0.2 directing JSON")
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args(argv)
    try:
        output = [Path(args.out_json), Path(args.out_md)]
        if (output[0].resolve() == output[1].resolve() or
                any(x.exists() for x in output)):
            raise ProductionDeliveryError("DELIVERY_OUTPUT_EXISTS_OR_COLLIDES")
        base = json.loads(Path(args.base).read_text(encoding="utf-8"))
        direction = json.loads(Path(args.direction).read_text(encoding="utf-8"))
        bundle = build_reference_delivery(base, direction)
        markdown = render_operator_markdown(bundle)
        # No result text printed to logs, especially not private prompts.
        for target in output:
            target.parent.mkdir(parents=True, exist_ok=True)
        with output[0].open("x", encoding="utf-8") as fp:
            json.dump(bundle, fp, ensure_ascii=False, indent=2, allow_nan=False)
            fp.write("\n")
        with output[1].open("x", encoding="utf-8") as fp:
            fp.write(markdown)
        print("OFFLINE director work orders exported:",
              len(bundle["shots"]), "shots;",
              "external_calls=0; no_publication=true")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("ERROR:", str(exc) if isinstance(exc, ProductionDeliveryError)
              else "DELIVERY_INVALID_INPUT", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
