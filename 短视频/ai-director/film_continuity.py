#!/usr/bin/env python3
"""Source-bound continuity cards and explicit transitions, inspired by CineCrew FilmDSL.

No source/media/API calls. No code copied from CineCrew. Static audit evidence
only: the checker cannot prove a real face, costume, prop or room matches video.

Known entities are derived from the AUTHORITATIVE plan, not from model prose.
No new character / prop / location may be smuggled through a role answer.
A deliberately undeclared asset is an unresolved blocker, not fake evidence.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import re

import agent_team as team

VERSION="film-continuity-track-v1"
ID_PATTERN=re.compile(r"^[A-Za-z][A-Za-z0-9_-]{1,63}$")
FIELDS=("position","appearance","condition","holder")
ALLOWED_TYPES=("character","prop")
BREAK_KINDS=frozenset(("none","time_jump","offscreen_transition","scene_change"))


class ContinuityError(ValueError):
    """Error codes must not contain original scripts or model output."""


def _check(ok, code):
    if not ok:
        raise ContinuityError(code)


def _id(value):
    return type(value) is str and ID_PATTERN.fullmatch(value) is not None


def _ids(entries, code):
    _check(isinstance(entries,list),code)
    out={}
    for entry in entries:
        _check(isinstance(entry,dict) and _id(entry.get("id")) and
               entry["id"] not in out,code)
        out[entry["id"]]=entry
    return out


def inventory(base, *, source_digest=None):
    """Extract only IDs actually declared in immutable source plan."""
    _check(isinstance(base,dict) and isinstance(base.get("shots"),list) and
           bool(base["shots"]),"CONTINUITY_INVALID_PLAN")
    shots=_ids(base["shots"],"CONTINUITY_BAD_SHOT_IDS")
    characters=_ids(base.get("characters",[]),"CONTINUITY_BAD_CHARACTER_IDS")
    props=_ids(base.get("props",[]),"CONTINUITY_BAD_PROP_IDS")
    scenes=_ids(base.get("scenes",[]),"CONTINUITY_BAD_SCENE_IDS")
    _check(not (set(characters)&set(props) or set(characters)&set(scenes) or
                set(props)&set(scenes)),"CONTINUITY_ID_COLLISION")
    entries={
        "characters":{k:{"kind":"character", "id":k,
                           "reference_asset_id":None,
                           "reference_status":"missing",
                           "identity_verified_in_media":False}
                       for k in characters},
        "props":{k:{"kind":"prop","id":k,
                     "reference_asset_id":None,
                     "reference_status":"missing",
                     "identity_verified_in_media":False}
                 for k in props},
        "scenes":{k:{"kind":"scene","id":k,
                      "reference_asset_id":None,
                      "reference_status":"missing",
                      "geometry_verified_in_media":False}
                  for k in scenes},
    }
    gaps=[]
    ids=set(characters)|set(props)
    for shot in base["shots"]:
        sid=shot["id"]
        referenced=shot.get("character_ids",[])
        objects=shot.get("prop_ids",[])
        _check(isinstance(referenced,list) and isinstance(objects,list) and
               all(_id(x) for x in referenced+objects) and
               len(set(referenced))==len(referenced) and
               len(set(objects))==len(objects),
               "CONTINUITY_BAD_SHOT_ENTITY_REFS")
        for item in referenced:
            _check(item in characters,"CONTINUITY_UNKNOWN_SHOT_CHARACTER")
        for item in objects:
            _check(item in props,"CONTINUITY_UNKNOWN_SHOT_PROP")
        if shot.get("scene_id") is not None:
            _check(shot["scene_id"] in scenes,
                   "CONTINUITY_UNKNOWN_SHOT_SCENE")
        if shot.get("visual_type")=="ai_video" and not referenced:
            gaps.append({"code":"CONTINUITY_CAST_NOT_DECLARED",
                         "task_id":"acting","shot_ids":[sid],
                         "severity":"review",
                         "detail":"画面是否有人物尚未确认；若有人须在权威计划建立稳定角色ID"})
        if shot.get("visual_type")=="ai_video" and not objects:
            gaps.append({"code":"CONTINUITY_PROPS_NOT_DECLARED",
                         "task_id":"acting","shot_ids":[sid],
                         "severity":"review",
                         "detail":"检查镜头是否有可交互道具，不能假定零道具"})
    if not scenes:
        gaps.append({"code":"CONTINUITY_SCENE_REGISTRY_EMPTY",
                     "task_id":"camera_art","shot_ids":list(shots),
                     "severity":"review",
                     "detail":"权威计划没有场景ID，不能宣称空间布局已验证"})
    return {
        "version":VERSION,"source_plan_digest":team.fingerprint(base),
        "source_digest":source_digest,"entities":entries,
        "unverified_asset_count":sum(map(len,entries.values())),
        "declaration_gaps":gaps,
        "status":"unverified_planning_inventory",
        "reference_media_verified":False,"human_approved":False,
        "paid_api_authorized":False,
    }


def _state(data):
    _check(type(data) is dict and set(data)==set(FIELDS) and
           all(isinstance(data[k],str) and data[k].strip() for k in FIELDS),
           "CONTINUITY_ENTITY_STATE_INVALID")
    return data


def _issue(code, task, shots, message, severity="blocker"):
    return {"code":code,"task_id":task,"shot_ids":shots,
            "detail":message,"severity":severity}


def inspect_tracks(base, tracks_by_shot, *, source_digest=None):
    """Validate proposed per-clip start/end snapshots and cause-bounded events.

    Comparing strings can prove only DECLARED internal consistency; not
    semantic plausibility or what a real video looks like. No autocorrection.
    """
    inv=inventory(base,source_digest=source_digest)
    _check(isinstance(tracks_by_shot,dict) and
           set(tracks_by_shot)=={s["id"] for s in base["shots"]},
           "CONTINUITY_SHOT_TRACK_COVERAGE")
    issues=deepcopy(inv["declaration_gaps"])
    registry=inv["entities"]
    known={**registry["characters"],**registry["props"]}
    previous={}
    verified_events=0
    for shot in base["shots"]:
        sid=shot["id"]
        requested=shot.get("character_ids",[])+shot.get("prop_ids",[])
        payload=tracks_by_shot[sid]
        _check(type(shot.get("duration")) in (int,float) and
               0 < shot["duration"] <= 86400,
               "CONTINUITY_SHOT_DURATION_INVALID")
        _check(isinstance(payload,dict) and
               set(payload)=={"entity_tracks","scene_id"} and
               payload["scene_id"]==shot.get("scene_id") and
               isinstance(payload["entity_tracks"],list),
               "CONTINUITY_SHOT_TRACK_STRUCTURE")
        seen=set()
        for item in payload["entity_tracks"]:
            _check(type(item) is dict and set(item)=={
                "entity_id","start_state","end_state","events",
                "cut_break","cut_reason"},
                "CONTINUITY_ENTITY_TRACK_SHAPE")
            eid=item["entity_id"]
            _check(eid in known and eid in requested and eid not in seen,
                   "CONTINUITY_UNKNOWN_DUPLICATE_OR_UNDECLARED_ENTITY")
            seen.add(eid)
            start=_state(item["start_state"])
            end=_state(item["end_state"])
            events=item["events"]
            _check(isinstance(events,list),"CONTINUITY_EVENTS_REQUIRED")
            kind=item["cut_break"]
            _check(type(kind) is str and kind in BREAK_KINDS and
                   type(item["cut_reason"]) is str,
                   "CONTINUITY_BREAK_KIND_INVALID")
            if kind=="none":
                _check(not item["cut_reason"].strip(),
                       "CONTINUITY_UNEXPECTED_CUT_REASON")
            else:
                _check(len(item["cut_reason"].strip())>=12,
                       "CONTINUITY_CUT_REASON_REQUIRED")
            changes={k for k in FIELDS if start[k]!=end[k]}
            events_seen=set()
            prior_values=deepcopy(start)
            for e in events:
                _check(type(e) is dict and set(e)=={
                    "field","from","to","time_s","cause"},
                    "CONTINUITY_EVENT_SHAPE")
                field=e["field"]
                t=e["time_s"]
                _check(field in FIELDS and field not in events_seen and
                       type(t) in (int,float) and t>=0 and
                       t<=shot.get("duration",0) and
                       type(e["cause"]) is str and
                       len(e["cause"].strip())>=12 and
                       type(e["from"]) is str and type(e["to"]) is str and
                       e["from"]!=e["to"] and
                       e["from"]==prior_values[field] and
                       e["to"]==end[field],
                       "CONTINUITY_EVENT_NOT_CAUSALLY_BOUND")
                events_seen.add(field)
                prior_values[field]=e["to"]
                verified_events+=1
            _check(changes==events_seen,
                   "CONTINUITY_UNEXPLAINED_IN_SHOT_STATE_CHANGE")
            if eid in previous and previous[eid]["end"]!=start:
                if kind=="none":
                    issues.append(_issue("CONTINUITY_TELEPORT_OR_COSTUME_DRIFT",
                                         "acting",
                                         [previous[eid]["shot"],sid],
                                         "相同资产上一镜结束状态与本镜开始状态不同，且没有过渡说明"))
                else:
                    issues.append(_issue("CONTINUITY_OFFSCREEN_CHANGE_REVIEW",
                                         "acting",
                                         [previous[eid]["shot"],sid],
                                         "已声明画外/时间跳转，但需要总导演确认对应事件是否成立",
                                         severity="review"))
            elif kind!="none":
                issues.append(_issue("CONTINUITY_REDUNDANT_BREAK_REVIEW",
                                     "acting",[sid],
                                     "没有发现资产状态差异，画外转换声明需要人审",
                                     severity="review"))
            previous[eid]={"shot":sid,"end":deepcopy(end)}
        _check(seen==set(requested),"CONTINUITY_DECLARED_ENTITY_MISSING_TRACK")
    return {
        "kind":VERSION,"status":"blocked" if any(
            i["severity"]=="blocker" for i in issues) else "needs_human_review",
        "source_plan_digest":inv["source_plan_digest"],
        "source_digest":source_digest,
        "asset_inventory":inv,
        "shot_count":len(base["shots"]),
        "tracked_entity_events":verified_events,
        "issues":issues,
        "semantic_plausibility_verified":False,
        "media_identity_verified":False,
        "production_ready":False,
        "human_approved":False,
        "paid_api_authorized":False,
    }
