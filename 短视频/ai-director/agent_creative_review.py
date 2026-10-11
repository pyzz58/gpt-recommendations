"""Offline, advisory evidence checks for specialist creative submissions.

No model invocation, no authority to modify original sources, and no automatic
human approval. Designed to work with both draft and fully-authored handoffs.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

OWNERS = {
    "acting": ("staging", "performance", "beats", "continuity", "shootability"),
    "camera_art": ("camera", "art"),
    "sound": ("sound", "speech"),
    "editing_animation": ("editing", "animation", "graphics"),
    "ai_technical": ("generation",),
}
VAGUE = {"自然", "流畅", "电影感", "专业", "合理", "生动", "优质",
         "自然过渡", "平滑衔接", "cinematic", "professional", "smooth"}


def _has_evidence(value: Any) -> bool:
    """Nested structure with meaningful, non-generic creative specifics."""
    if isinstance(value, dict):
        return any(_has_evidence(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_evidence(v) for v in value)
    if isinstance(value, str):
        s = value.strip()
        return len(s) >= 8 and s.lower() not in VAGUE
    return False


def _make(code: str, task: str, shot: str | None, detail: str,
          severity: str = "review") -> dict:
    return {"code": code, "task_id": task, "shot_id": shot,
            "severity": severity, "detail": detail}


def review_deliverable(task_id: str, payload: dict,
                       expected_shot_ids: list[str] | None = None, *,
                       shot_context: dict | None = None,
                       terminal_shot_id: str | None = None) -> list[dict]:
    """Advisory findings; checks evidence, not taste or rendered-media quality.

    Can assess a scoped revision. Does not mutate payload. Structural ownership
    and shot coverage remain the responsibility of agent_team._validate_payload.
    """
    issues = []
    if task_id not in OWNERS:
        return issues
    shots = payload.get("shots") if isinstance(payload, dict) else None
    if not isinstance(shots, dict):
        return [_make("CREATIVE_NO_SHOTS", task_id, None,
                      "岗位交付缺少 shots 映射", "blocker")]
    if expected_shot_ids is not None:
        missing = set(expected_shot_ids) - set(shots)
        for sid in sorted(missing):
            issues.append(_make("CREATIVE_SHOT_MISSING", task_id, sid,
                                "该镜头没有专业交付", "blocker"))
    for sid, item in shots.items():
        if not isinstance(item, dict):
            issues.append(_make("CREATIVE_SHOT_INVALID", task_id, sid,
                                "镜头交付不是对象", "blocker"))
            continue
        for field in OWNERS[task_id]:
            section = item.get(field)
            if field == "shootability" and section is None:
                # Only AI-video scenes featuring people need this structure.
                # Without a source plan, stay conservative for draft audits.
                source = shot_context.get(sid) if isinstance(shot_context, dict) else None
                if isinstance(source, dict) and not (
                        source.get("visual_type") == "ai_video"
                        and source.get("character_ids")):
                    continue
                issues.append(_make("SHOOTABILITY_UNDESIGNED", task_id, sid,
                                    "动作可拍性暂未设计，需要制作前补齐"))
                continue
            if not _has_evidence(section):
                issues.append(_make("CREATIVE_EMPTY_SECTION", task_id, sid,
                                    f"{field} 缺乏可复核的具体创作证据"))
        if task_id == "acting":
            beats = item.get("beats", [])
            if isinstance(beats, list) and beats:
                if not all(isinstance(b, dict) and
                           isinstance(b.get("visible_change"), str) and
                           b["visible_change"].strip() for b in beats):
                    issues.append(_make("ACTING_NO_VISIBLE_CHANGE", task_id, sid,
                                        "动作节拍需要可观察的 visible_change"))
        if task_id == "sound":
            speech = item.get("speech")
            if isinstance(speech, dict) and not any(
                    key in speech for key in ("voiceover", "dialogue", "subtitle_cues")):
                issues.append(_make("SOUND_NO_SPEECH_PLAN", task_id, sid,
                                    "未区分旁白、对白或字幕时码"))
        if task_id == "editing_animation":
            edit = item.get("editing")
            if (isinstance(edit, dict) and sid != terminal_shot_id
                    and "narrative_bridge" not in edit):
                issues.append(_make("EDIT_NO_NARRATIVE_BRIDGE", task_id, sid,
                                    "此镜到下一镜缺少剪辑叙事桥"))
        if task_id == "ai_technical":
            gen = item.get("generation")
            if isinstance(gen, dict) and "route" not in gen:
                issues.append(_make("GEN_NO_ROUTE", task_id, sid,
                                    "制作工单尚未指定 AI视频/静态/后期等 route"))
    return issues


def review_team(state: dict, base: dict | None = None) -> dict:
    """Read-only aggregate creative inspection for versioned team ledgers.

    Supplying the authoritative base avoids flagging static/graphic shots as
    missing human action; the final shot never has an outgoing cut.
    """
    if not isinstance(state, dict) or not isinstance(state.get("tasks"), dict):
        raise ValueError("invalid team state")
    findings = []
    base_shots = None
    if base is not None:
        if not isinstance(base, dict) or not isinstance(base.get("shots"), list):
            raise ValueError("base must contain a list of shots")
        base_shots = {shot["id"]: shot for shot in base["shots"]}
        if set(base_shots) != set(state.get("shot_ids", [])):
            raise ValueError("source shot IDs do not match the team ledger")
    last_shot = state.get("shot_ids", [])[-1] if state.get("shot_ids") else None
    for task_id in OWNERS:
        entry = state["tasks"].get(task_id, {})
        if entry.get("status") != "completed":
            findings.append(_make("TEAM_DEPARTMENT_NOT_READY", task_id, None,
                                  "部门尚未完成或返工后失效", "blocker"))
            continue
        findings.extend(review_deliverable(
            task_id, entry.get("deliverable"),
            state.get("shot_ids"), shot_context=base_shots,
            terminal_shot_id=last_shot))
    counts = dict(Counter(x["severity"] for x in findings))
    return {"creative_review_version": "0.1",
            "status": ("blocked" if counts.get("blocker", 0)
                       else "needs_human_creative_review" if findings
                       else "structured_evidence_present"),
            "counts": counts, "findings": findings,
            "human_approved": False, "actual_media_tested": False,
            "paid_api_authorized": False,
            "note": "启发式证据检查；即使无问题也不证明艺术质量、真实可拍性或真人批准。"}


def review_packet(state: dict, task_id: str) -> dict:
    """Preview checker requirements without requesting or running an LLM."""
    if task_id not in OWNERS:
        return {"task_id": task_id, "checks": [], "requires_human_review": True}
    return {"task_id": task_id,
            "checks": [f"provide concrete {field}" for field in OWNERS[task_id]],
            "requires_human_review": True, "llm_calls": 0}
