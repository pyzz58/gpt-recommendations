#!/usr/bin/env python3
"""QO-D15: director-led, scene-specific cross-department production conference.

The director's approved-for-planning *creative instructions* are intentionally
separate from each department's OWN deliverable. This module validates actual
source/shot/revision scope and injects the task into downstream model-facing
role requests. It does not authenticate approval or judge artistic merit.

No model calls, private disk writes, paid generation, or public manuscripts.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

import agent_team

VERSION = "director-department-command-v1"
DEPARTMENTS = (
    "acting", "camera_art", "sound", "editing_animation",
    "ai_technical", "quality_review", "director_final")
EDGES = (
    ("acting", "camera_art"),
    ("acting", "editing_animation"),
    ("camera_art", "editing_animation"),
    ("sound", "editing_animation"),
    ("editing_animation", "ai_technical"),
    ("ai_technical", "quality_review"),
    ("quality_review", "director_final"))
OWNERSHIP = {
    "acting": "表演/动作：动机、目光、身体反应、站位、手与道具",
    "camera_art": "摄影/美术：景别、视线、空间轴线、光源、构图、色彩",
    "sound": "声音/台词：忠于权威台词、旁白时间码、停顿、音效与混音",
    "editing_animation": "剪辑/动画：叙事切点、转场、J/L-cut、后期动画和精确文字",
    "ai_technical": "AI制作：逐镜生成/静态/合成路线、模型能力、参考资产与失败替代",
    "quality_review": "独立场记QA：跨部门信息、时码、连续性、作品意图阻断点",
    "director_final": "总导演终审：调解部门矛盾、返工与片子观众体验的判断",
}
CONTENT_FIELDS = (
    "specific_assignment", "why_audience_needs_this",
    "concrete_execution", "creative_boundaries",
    "needed_from_upstream", "deliver_to_downstream",
    "failed_result_and_recovery")
SHOT_FIELDS = (
    "dramatic_beat", "desired_viewer_effect", "department_execution",
    "sync_with_other_departments", "observable_acceptance")
MIN_TEXT = 17


class DirectorCommandError(ValueError):
    pass


def _require(cond, code):
    if not cond:
        raise DirectorCommandError(code)


def _text(text, code, minimum=MIN_TEXT):
    _require(isinstance(text, str) and
             minimum <= len(text.strip()) <= 2200 and "\0" not in text, code)


def _exact(obj, fields, code):
    _require(isinstance(obj, dict) and set(obj) == set(fields), code)


def _locked(base, state):
    agent_team._check_state(state)
    _require(agent_team.fingerprint(base) == state["base_digest"],
             "COMMAND_BASE_STALE")
    director = state["tasks"]["director_brief"]
    lock = state["tasks"]["director_lock"]
    _require(director["status"] == "completed" and
             lock["status"] == "completed" and
             isinstance(director["deliverable"], dict) and
             isinstance(lock["deliverable"], dict),
             "COMMAND_DIRECTOR_VISION_NOT_LOCKED")
    obj = lock["deliverable"]
    _require(isinstance(obj.get("global_direction"), dict) and
             isinstance(obj.get("shot_objectives"), dict) and
             set(obj["shot_objectives"]) == set(state["shot_ids"]),
             "COMMAND_INVALID_DIRECTOR_LOCK")
    return director, lock


def _lock_digest(task):
    return agent_team.fingerprint(task["deliverable"])


def _context(base, state):
    director, lock = _locked(base, state)
    return {
        "source_digest": state["source_digest"],
        "base_digest": state["base_digest"],
        "director_brief_revision": director["revision"],
        "director_brief_digest": _lock_digest(director),
        "director_lock_revision": lock["revision"],
        "director_lock_digest": _lock_digest(lock),
    }


def command_request(base, state, *, source_text=None):
    """UNSENT director's real cross-department production meeting.

    Conduct only AFTER the showrunner has completed the normal director lock,
    BEFORE asking acting/camera/sound/editing/AI/QA specialists to work.
    """
    refs = _context(base, state)
    if source_text is not None:
        _require(isinstance(source_text, str) and
                 hashlib.sha256(source_text.encode()).hexdigest() ==
                 state["source_digest"], "COMMAND_WRONG_SOURCE_SCRIPT")
    director, lock = _locked(base, state)
    return {
        "kind": "unsent_director_cross_department_conference",
        "version": VERSION, "dispatch_allowed": False,
        "paid_calls_authorized": False,
        "messages": [{
            "role": "system", "content": (
                "你是影视制作总导演，不是为每个专业岗位写一句总结的产品经理。"
                "你已经独立阅读、剪辑评估并建立导演创作圣经。现在要给每位"
                "部门负责人召开真正详细的制作会。先明确整集想让观众看懂什么、"
                "感受到什么、哪个具体事件/动作产生转变、什么画面与声音最重要。"
                "对动作表演、摄影美术、声音台词、剪辑动画、AI技术、独立QA、"
                "导演最终审片等部门分别下达可执行任务：需要做什么、"
                "为什么对整片重要、具体如何实现、有哪些限制与禁止、"
                "从谁得到什么素材、交给谁什么产物、如何检查成败、"
                "失败如何处理以及哪里需要总导演协调。"
                "每个具体镜头必须有明确独特的审美和叙事用意，不能用"
                "‘电影感强烈/配乐自然/镜头流畅/继续完善’搪塞。"
                "不得把摄影机位交给演员导演、把改写剧本交给声音岗位，"
                "不能伪造可用图片、实测AI视频或批准权限。"
                "各部门应以一套统一人物状态、情绪节奏、物理空间和"
                "声画事实基准相互配合，但保有自己专业的执行自由，"
                "面对技术不可能完成的镜头应提出方案给总导演仲裁。"
                "不能擅自把导演cut提案当成获批准的新版剧本。"
                "生成的是专业计划，不是已制作、已审片、已签字的影片。")},
            {"role": "user", "content": json.dumps({
                "original_script": source_text,
                "base_shots": base["shots"],
                "global_director_bible": lock["deliverable"]["global_direction"],
                "director_initial_vision": director["deliverable"]["creative_brief"],
                "locked_shot_objectives": lock["deliverable"]["shot_objectives"],
                "provenance": refs,
                "roles_and_ownership": OWNERSHIP,
                "required_dept_ids": DEPARTMENTS,
                "required_interfaces": EDGES,
                "output_format": {
                    "version": VERSION, "provenance": "unchanged provenance",
                    "episode_intent": [
                        "specific_audience_journey", "dramatic_or_conceptual_axis",
                        "style_and_visual_motif", "sound_and_silence_logic",
                        "final_aftertaste", "things_not_to_do"],
                    "departments": {
                        dept: {
                            "brief_fields": CONTENT_FIELDS,
                            "per_shot_fields": SHOT_FIELDS,
                            "per_shot_ids": state["shot_ids"],
                            "acceptance_checks": "at least 2 concrete items",
                        } for dept in DEPARTMENTS},
                    "interfaces": [
                        "from", "to", "shared_artifact_or_state",
                        "timing_and_handoff", "conflict_owner"],
                    "review_gaps": "list of unresolved problems, may be []",
                },
                "no_authorization_claims": True,
                "independent_craft_quality_not_proven": True,
            }, ensure_ascii=False, separators=(",", ":"))},
        ],
    }


def validate_command(base, state, command):
    refs = _context(base, state)
    _exact(command, {"version", "provenance", "episode_intent", "departments",
                     "interfaces", "review_gaps"}, "COMMAND_TOPLEVEL_SHAPE")
    _require(command["version"] == VERSION and
             command["provenance"] == refs, "COMMAND_STALE_CREATIVE_VERSION")
    intent = command["episode_intent"]
    _exact(intent, {
        "specific_audience_journey", "dramatic_or_conceptual_axis",
        "style_and_visual_motif", "sound_and_silence_logic",
        "final_aftertaste", "things_not_to_do",
    }, "COMMAND_EPISODE_INTENT_SHAPE")
    for value in intent.values():
        _text(value, "COMMAND_EPISODE_INTENT_TOO_VAGUE")
    depts = command["departments"]
    _require(isinstance(depts, dict) and set(depts) == set(DEPARTMENTS),
             "COMMAND_DEPARTMENT_MISSING_OR_UNKNOWN")
    shot_ids = state["shot_ids"]
    for dept in DEPARTMENTS:
        work = depts[dept]
        _exact(work, {*CONTENT_FIELDS, "per_shot", "acceptance_checks"},
               "COMMAND_DEPT_SHAPE")
        for field in CONTENT_FIELDS:
            _text(work[field], "COMMAND_DEPT_TOO_VAGUE")
        checks = work["acceptance_checks"]
        _require(isinstance(checks, list) and len(checks) >= 2 and
                 len(checks) <= 12 and
                 all(isinstance(c, str) and MIN_TEXT <= len(c.strip()) <= 500
                     for c in checks), "COMMAND_ACCEPTANCE_UNSPECIFIED")
        by_shot = work["per_shot"]
        _require(isinstance(by_shot, dict) and set(by_shot) == set(shot_ids),
                 "COMMAND_SHOT_COVERAGE")
        for sid, instruction in by_shot.items():
            _exact(instruction, SHOT_FIELDS, "COMMAND_SHOT_DIRECTION_SHAPE")
            for field in SHOT_FIELDS:
                _text(instruction[field], "COMMAND_SHOT_DIRECTION_VAGUE")
    edges = command["interfaces"]
    _require(isinstance(edges, list) and len(edges) == len(EDGES),
             "COMMAND_CROSS_DEPARTMENT_COUNT")
    seen = set()
    for e in edges:
        _exact(e, {
            "from", "to", "shared_artifact_or_state",
            "timing_and_handoff", "conflict_owner",
        }, "COMMAND_INTERFACE_SHAPE")
        link = (e["from"], e["to"])
        _require(link in EDGES and link not in seen,
                 "COMMAND_CROSS_DEPARTMENT_INVALID")
        seen.add(link)
        for field in ("shared_artifact_or_state", "timing_and_handoff",
                      "conflict_owner"):
            _text(e[field], "COMMAND_CROSS_DEPARTMENT_VAGUE")
    _require(seen == set(EDGES), "COMMAND_CROSS_DEPARTMENT_MISSING")
    gaps = command["review_gaps"]
    _require(isinstance(gaps, list) and len(gaps) <= 20 and
             all(isinstance(x, str) and len(x.strip()) >= 12 for x in gaps),
             "COMMAND_REVIEW_GAP_SHAPE")
    return {
        "kind": "director_cross_department_command_receipt",
        "command_digest": agent_team.fingerprint(command),
        "source_digest": refs["source_digest"],
        "base_digest": refs["base_digest"],
        "director_lock_digest": refs["director_lock_digest"],
        "department_count": len(DEPARTMENTS),
        "shot_count": len(shot_ids),
        "interfaces_count": len(EDGES),
        "human_author_approval_authenticated": False,
        "director_artistic_quality_verified": False,
        "media_generated": False,
    }


def model_facing_role_context(base, state, task_id, command):
    """Prepare the exact specialized instructions received by a real Agent."""
    _require(task_id in DEPARTMENTS,
             "COMMAND_ONLY_POST_DIRECTOR_LOCK_SPECIALISTS")
    receipt = validate_command(base, state, command)
    work = command["departments"][task_id]
    other = [
        {"from": e["from"], "to": e["to"],
         "shared_artifact_or_state": e["shared_artifact_or_state"],
         "timing_and_handoff": e["timing_and_handoff"],
         "conflict_owner": e["conflict_owner"]}
        for e in command["interfaces"]
        if task_id in (e["from"], e["to"])
    ]
    return {
        "provenance": deepcopy(command["provenance"]),
        "command_digest": receipt["command_digest"],
        "episode_intent": deepcopy(command["episode_intent"]),
        "this_department": task_id,
        "this_department_ownership": OWNERSHIP[task_id],
        "director_mission_and_execution": deepcopy(work),
        "cross_department_handoffs": other,
        "unresolved_director_review_gaps": deepcopy(command["review_gaps"]),
        "must_not_silently_rewrite_story": True,
        "not_a_paid_render_or_user_approval": True,
    }
