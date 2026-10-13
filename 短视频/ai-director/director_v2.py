#!/usr/bin/env python3
"""AI Director v0.2: offline professional shot contracts & model-aware prompt compiler.

Requires a v0.1 plan and a Codex-authored v0.2 direction file. This program is
intentionally deterministic: it does NOT pretend to perform creative LLM work or
verify external evidence, and it cannot generate/publish video.
"""
from __future__ import annotations

import argparse
import copy
import html
import json
import math
from pathlib import Path
import re
import sys

from director import validate as validate_v1
import reference_assets as refassets
import production_gate

VERSION = "0.2.0"
FORBIDDEN_UNSUPPORTED_MODES = {"paid_video_generation", "publish", "auto_upload"}
REQUIRED_SHOT_FIELDS = ("objective", "staging", "performance", "beats", "camera", "art", "sound", "continuity", "graphics", "generation", "qa")
REQUIRED_BEAT_FIELDS = ("from_s", "to_s", "visible_change", "performance", "camera", "sound")

# An ai_video base shot may be produced using still images, editing or real
# inserts. These are planning routes only: this module cannot render footage.
PRODUCTION_ROUTES = {"ai_video", "static_post", "edit_composite", "live_action_insert", "post_production"}
METHOD_ALIASES = {
    "ai_video": "ai_video", "ai视频": "ai_video", "ai视频生成": "ai_video", "ai生成视频": "ai_video",
    "static_post": "static_post", "static_image_post": "static_post", "still_post": "static_post",
    "静态图+后期": "static_post", "静态图后期": "static_post",
    "静态关键帧+后期灯光": "static_post", "静态关键帧+后期": "static_post",
    "静态图+后期灯光": "static_post",
    "edit_composite": "edit_composite", "editing_composite": "edit_composite",
    "剪辑合成": "edit_composite", "后期剪辑合成": "edit_composite", "剪辑+合成": "edit_composite",
    "live_action_insert": "live_action_insert", "live_action": "live_action_insert",
    "practical_insert": "live_action_insert", "实拍插入": "live_action_insert", "实拍": "live_action_insert",
    "post_production": "post_production", "后期制作": "post_production",
}

def production_route(shot, generation):
    """Resolve an explicit non-video production method without changing base.

    Supports a known production_method overriding old direction.route=ai_video
    for conceptually ai_video shots. Unknown methods and conflicting explicit
    routes fail closed. Route choices are plans, not rendered/verified assets.
    """
    route = generation.get("route")
    if route in FORBIDDEN_UNSUPPORTED_MODES:
        raise ValueError("disallowed execution route")
    if route not in PRODUCTION_ROUTES:
        raise ValueError("unsupported execution route: " + str(route))
    method = generation.get("production_method")
    if method is not None:
        if not isinstance(method, str) or not method.strip():
            raise ValueError("production_method must be a nonempty string")
        mapped = METHOD_ALIASES.get(method.strip().lower().replace(" ", ""))
        if mapped is None:
            raise ValueError("unrecognized production_method; choose a documented canonical route")
        if mapped != route:
            if route == "ai_video" and shot.get("visual_type") == "ai_video":
                route = mapped
            else:
                raise ValueError("production_method contradicts generation.route")
    if shot.get("visual_type") != "ai_video" and route == "ai_video":
        raise ValueError("generation route contradicts base visual_type")
    return route



def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def scaffold(base):
    """Create clearly unapproved work slots; never fabricate 'professional' direction."""
    return {
        "schema_version": "0.2", "title": base["title"],
        "global_direction": {
            "audience_emotion_arc": "待导演设计：逐段情绪曲线",
            "visual_grammar": "待导演设计：贯穿全片的摄影、美术、图形统一规则",
            "audio_grammar": "待导演设计：配音、BGM、音效与留白的统一规则",
            "graphic_safety": "所有准确数字与中文字由后期叠加；注明比较组、研究类型与来源；避免平台UI遮挡",
            "reference_strategy": "待确认：人物/场景/道具参考图只记录角色与要求，不伪造存在的素材文件",
            "generation_budget": "不允许自动调用付费 API；先审查再生成"
        },
        "shots": [{
            "shot_id": shot["id"], "review_status": "needs_directing",
            "objective": {"emotion": "待填", "observable_turn": "待填", "visual_focus": "待填"},
            "staging": {"blocking": "待填", "gaze": "待填", "props": [], "spatial_constraints": ["待填"]},
            "performance": {"motivation": "待填", "facial_microaction": "待填", "body_microaction": "待填", "ending_pose": "待填"},
            "beats": [{"from_s": 0, "to_s": shot["duration"], "visible_change": "待导演拆解", "performance": "待填", "camera": "待填", "sound": "待填"}],
            "camera": {"start_frame": "待填", "movement": "待填", "move_trigger_s": 0, "end_frame": "待填", "lens_feel": "待填", "reason": "待填"},
            "art": {"environment": "待填", "light_source": "待填", "color_path": "待填", "texture": "待填"},
            "sound": {"ambient": "待填", "music": "待填", "effects": [], "voiceover_note": "待填"},
            "continuity": {"start_state": "待填", "end_state": "待填", "locked_entities": [], "reference_assets": []},
            "graphics": {"treatment": "待填", "claims_used": list(shot.get("claim_ids", [])), "labels": [], "motion": "待填", "context_note": "待填"},
            "generation": {"route": "ai_video" if shot["visual_type"] == "ai_video" else "post_production", "clip_type": "single_continuous_take" if shot["visual_type"] == "ai_video" else "not_a_video_model_job", "negative_constraints": [], "reference_roles": [], "reference_bindings": [], "limits": "不在画面内部生成准确汉字、数字或字幕"},
            "editing": {"incoming_transition": "待导演设计", "outgoing_transition": shot["transition"],
                        "cut_reason": "待导演设计", "rhythm": "待导演设计",
                        "assembly_instructions": "待导演设计",
                        "audio_bridge": None,
                        "narrative_bridge": None},
            "animation": {"mode": "待导演设计", "timing": "待导演设计",
                          "elements": [], "render_in_post": False, "style": "待导演设计"},
            "speech": {"voiceover": {"text": shot["narration"],
                                    "delivery": "待导演设计", "timing": "待导演设计",
                                    "cues": []},
                       "dialogue": [], "subtitle_cues": [],
                       "subtitle_direction": "待导演设计",
                       "lip_sync_policy": "待导演设计"},
            "shootability": ({"mode": "待导演选择", "action_units": [],
                              "fallback": None}
                             if shot["visual_type"] == "ai_video" and shot.get("character_ids")
                             else None),
            "qa": {"acceptance_tests": ["待导演明确可观察结果"], "issues": [], "human_approved": False}
        } for shot in base["shots"]]
    }


def _has_unfinished_placeholder(value):
    """Detect drafting markers, not ordinary Chinese words such as 等待/期待."""
    if isinstance(value, dict):
        return any(_has_unfinished_placeholder(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_unfinished_placeholder(v) for v in value)
    return isinstance(value, str) and any(
        marker in value for marker in ("待填", "待导演", "待设计", "待确认", "TODO", "TBD")
    )


def validate(base, directions, assets=None, asset_root=None):
    errors, warnings = validate_v1(base)
    if not isinstance(directions, dict):
        return errors + ["v0.2 direction must be an object"], warnings
    if directions.get("schema_version") != "0.2": errors.append("direction schema_version must be 0.2")
    global_dir = directions.get("global_direction")
    for key in ("audience_emotion_arc", "visual_grammar", "audio_grammar", "graphic_safety", "reference_strategy", "generation_budget"):
        if not isinstance(global_dir, dict) or not str(global_dir.get(key, "")).strip():
            errors.append(f"missing global_direction.{key}")
    if _has_unfinished_placeholder(global_dir): errors.append("global direction contains unfinished placeholder")
    raw_shots = directions.get("shots")
    if not isinstance(raw_shots, list) or len(raw_shots) != len(base.get("shots", [])):
        return errors+["direction shots do not match base plan length"], warnings
    expected = {x["id"]: x for x in base["shots"]}
    seen = set()
    accepted = []
    for ix, direction in enumerate(raw_shots):
        if not isinstance(direction, dict):
            errors.append(f"direction[{ix}] must be object"); continue
        sid = direction.get("shot_id", "?")
        prefix=f"{sid}"
        if sid in seen: errors.append(f"{prefix}: duplicate shot_id")
        seen.add(sid)
        if sid not in expected:
            errors.append(f"{prefix}: not found in base plan"); continue
        shot = expected[sid]
        for key in REQUIRED_SHOT_FIELDS:
            if key not in direction or not isinstance(direction[key], dict if key not in ("beats",) else list):
                errors.append(f"{prefix}: missing/invalid {key}")
        if any(k not in direction for k in REQUIRED_SHOT_FIELDS): continue
        for name, subkeys in {
            "objective": ["emotion", "observable_turn", "visual_focus"],
            "staging": ["blocking", "gaze", "spatial_constraints"],
            "performance": ["motivation", "facial_microaction", "body_microaction", "ending_pose"],
            "camera": ["start_frame", "movement", "move_trigger_s", "end_frame", "lens_feel", "reason"],
            "art": ["environment", "light_source", "color_path", "texture"],
            "sound": ["ambient", "music", "effects", "voiceover_note"],
            "continuity": ["start_state", "end_state", "locked_entities", "reference_assets"],
            "graphics": ["treatment", "claims_used", "labels", "motion", "context_note"],
            "generation": ["route", "clip_type", "negative_constraints", "reference_roles", "limits"],
            "qa": ["acceptance_tests", "issues", "human_approved"]
        }.items():
            obj=direction[name]
            for key in subkeys:
                if key not in obj: errors.append(f"{prefix}: missing {name}.{key}")
            if any(key not in obj for key in subkeys): continue
            for key in subkeys:
                if key not in ("move_trigger_s", "human_approved", "effects", "locked_entities", "reference_assets", "claims_used", "labels", "negative_constraints", "reference_roles", "acceptance_tests", "issues", "spatial_constraints"):
                    value=obj[key]
                    if not isinstance(value, str) or not value.strip():
                        errors.append(f"{prefix}: empty {name}.{key}")
                    elif _has_unfinished_placeholder(value):
                        errors.append(f"{prefix}: placeholder in {name}.{key}")
        beats=direction["beats"]
        if not isinstance(beats, list) or not beats:
            errors.append(f"{prefix}: beats must not be empty")
        else:
            t=0.0
            for j,b in enumerate(beats):
                if not isinstance(b,dict) or any(k not in b for k in REQUIRED_BEAT_FIELDS):
                    errors.append(f"{prefix}: beat {j} missing required fields");continue
                a, end=b.get("from_s"), b.get("to_s")
                if not all(isinstance(x,(float,int)) and not isinstance(x,bool) for x in (a,end)):
                    errors.append(f"{prefix}: beat {j} invalid time"); continue
                if abs(a-t)>0.011: errors.append(f"{prefix}: beat {j} gap/overlap; expected {t}")
                if end<=a: errors.append(f"{prefix}: beat {j} non-positive duration")
                if end-a<0.30: warnings.append(f"{prefix}: beat {j} may be too short to read")
                for k in ("visible_change", "performance", "camera", "sound"):
                    if not isinstance(b.get(k),str) or not b[k].strip() or _has_unfinished_placeholder(b[k]):
                        errors.append(f"{prefix}: beat {j} missing concrete {k}")
                t=end
            if abs(t-shot["duration"])>0.011: errors.append(f"{prefix}: beat timeline {t} != {shot['duration']}")
        move_time=direction["camera"].get("move_trigger_s",0)
        if not isinstance(move_time,(int,float)) or move_time<0 or move_time>shot["duration"]:
            errors.append(f"{prefix}: camera move trigger outside shot")
        try:
            route = production_route(shot, direction["generation"])
        except ValueError as exc:
            errors.append(f"{prefix}: {exc}")
            route = None
        if route == "ai_video" and not direction["continuity"].get("locked_entities"):
            errors.append(f"{prefix}: ai_video missing locked identity/prop constraints")
        if direction["graphics"].get("claims_used") != shot.get("claim_ids",[]):
            errors.append(f"{prefix}: graphics.claims_used must match base claims without adding new assertions")
        if direction["qa"].get("human_approved") is True:
            warnings.append(f"{prefix}: claims of human approval cannot be verified by this tool")
        if direction.get("review_status") != "reviewed":
            warnings.append(f"{prefix}: directing not yet marked reviewed")
        accepted.append(sid)
    # source_credit_policy_v03: compact, auditable bibliography end-card.
    # A bibliography credit is optional, but if provided must remain readable
    # and must not displace the end of a short-form video.
    credits = [(index, shot) for index, shot in enumerate(base["shots"])
               if shot.get("purpose") == "sources"]
    if credits:
        if len(credits) != 1:
            errors.append("source credits must use exactly one end-card")
        for index, card in credits:
            if index != len(base["shots"]) - 1:
                errors.append(f"{card['id']}: source credits must be final shot")
            if card.get("duration") != 5:
                errors.append(f"{card['id']}: source credit card must be 5 seconds")
            if card.get("visual_type") != "text_card":
                errors.append(f"{card['id']}: source card must be post-production text_card")
            ids = card.get("claim_ids", [])
            if not isinstance(ids, list) or not 2 <= len(set(ids)) <= 3:
                errors.append(f"{card['id']}: show 2-3 primary research references")
            if str(card.get("narration", "")).strip():
                errors.append(f"{card['id']}: 5-second reference card must not have voiceover")
    if set(accepted)!=set(expected): errors.append("missing/extra directed shot IDs")
    if accepted != list(expected): warnings.append("shot order differs from base; compiler will follow base order")
    if base.get("risk_domain") != "none" and any(x.get("status")!="verified" for x in base.get("claims",[])):
        warnings.append("PUBLISH BLOCKED: expert video prompting does not verify medical data")
    if assets is not None:
        report = refassets.audit(base, directions, assets, asset_root)
        if report["blockers"]:
            errors.append(f"reference catalog has {report['blockers']} invalid/unsafe entries")
        if not report["ready_for_reference_preflight"]:
            warnings.append(f"reference assets missing/unverified: {report['missing']} pending; no generation approval")
        # Even ready file hashes do not verify facial identity across shots.
        warnings.append("Reference hashes do not establish visual identity consistency or publishing approval")
    return errors, list(dict.fromkeys(warnings))


def beat_lines(direction):
    return "\n".join(
        f"{b['from_s']:g}–{b['to_s']:g}s: Visible {b['visible_change']}; performer {b['performance']}; camera {b['camera']}; sound {b['sound']}"
        for b in direction["beats"]
    )


def visual_prompt_contract(base, shot, direction):
    """Select authored visual instructions, never private reference metadata.

    Typed lens/axis/layout and the source cast define the requested design.
    Free-form notes remain useful but cannot silently override those fields.
    Only simple numeric lens conflicts are machine-detectable; other semantic
    conflicts still require a director's review.
    """
    lens = direction['camera']
    focal = lens.get('focal_length_mm')
    if focal is not None:
        if type(focal) not in (int, float) or not math.isfinite(focal) or not 14 <= focal <= 135:
            raise ValueError('DIRECTOR_FOCAL_LENGTH_INVALID')
        prose_lengths = re.findall(r'(\d+(?:\.\d+)?)\s*(?:mm|毫米)', lens['lens_feel'], re.I)
        if any(abs(float(x) - focal) > .01 for x in prose_lengths):
            raise ValueError('DIRECTOR_FOCAL_LENGTH_CONFLICT')
    ids = set(shot.get('character_ids', []))
    cast = [{k: actor[k] for k in ('id', 'description', 'wardrobe') if k in actor}
            for actor in base.get('characters', []) if actor['id'] in ids]
    contract = {
        'visible_cast': cast,
        'camera_spec': {k: lens[k] for k in ('shot_size', 'focal_length_mm', 'screen_axis') if k in lens},
        'spatial_constraints': direction['staging']['spatial_constraints'],
        'props': direction['staging'].get('props', []),
        'performance': {k: direction['performance'][k] for k in
                        ('motivation', 'facial_microaction', 'body_microaction', 'ending_pose')},
        'lighting_and_geometry': {k: direction['art'][k] for k in
                                 ('lighting_state', 'practical_sources', 'lighting_change_reason',
                                  'scene_geometry') if k in direction['art']},
    }
    return ('\nAuthored visual specification (cast, numeric lens, axis and layout are authoritative; '
            'do not replace them with conflicting decorative prose. Character IDs refer to these '
            'descriptions, not proof of supplied reference images): '
            + json.dumps(contract, ensure_ascii=False, allow_nan=False, sort_keys=True))


def compile_package(base, directions, assets=None, asset_root=None):
    if base.get("requires_timed_cue_rendering"):
        raise ValueError("TIMED_CUE_RENDERER_REQUIRED_LEGACY_SHOT_TEXT_UNSAFE")
    errors,warnings=validate(base,directions,assets,asset_root)
    if errors: raise ValueError("cannot compile invalid director plan:\n"+"\n".join(errors))
    shots={x["shot_id"]:x for x in directions["shots"]}
    asset_report = refassets.audit(base, directions, assets, asset_root) if assets is not None else None
    shot_bindings = assets.get("shot_requirements", {}) if assets is not None else {}
    jobs=[]
    for shot in base["shots"]:
        d=shots[shot["id"]]
        route = production_route(shot, d["generation"])
        shared={"shot_id":shot["id"],"duration":shot["duration"],"visual_type":shot["visual_type"],
                "execution_route":route, "human_review_required":True,
                "direction":d, "reference_roles":d["generation"]["reference_roles"],
                "reference_bindings":shot_bindings.get(shot["id"], []),
                "reference_preflight_ready":bool(asset_report and
                    asset_report["ready_for_reference_preflight"] and
                    all(f["shot_id"] != shot["id"] for f in asset_report["findings"])),
                "reference_media_supplied":False}
        if route != "ai_video":
            shared["postproduction_job"]={
                "production_route":route, "visual":shot["visual"], "graphics":d["graphics"],
                "sound":d["sound"], "editorial_claims":shot["claim_ids"],
                "overlay_text":shot["subtitles"]["text"],
                "voiceover":shot["narration"], "voiceover_source":"base.narration",
                "voiceover_note":d["sound"]["voiceover_note"],
                "beats":d["beats"], "fallback":d["generation"].get("fallback"),
                "cost_note":d["generation"].get("cost_note"),
                "reference_roles":d["generation"]["reference_roles"],
                "asset_status":"not_verified", "requires_operator_review":True}
            shared["prompts"]={}
        else:
            lens=d["camera"]
            # Visual-only prompts; exact numerals, Chinese titles and subtitles remain post-production assets.
            shot_direction=(
                f"Narrative task: {d['objective']['observable_turn']}. Audience feeling: {d['objective']['emotion']}.\n"
                f"Framing and space: {lens['start_frame']}. Lens feel: {lens['lens_feel']}. "
                f"Blocking: {d['staging']['blocking']}. Gaze direction: {d['staging']['gaze']}.\n"
                f"What actually happens:\n{beat_lines(d)}\n"
                f"Camera path: {lens['movement']}; trigger at {lens['move_trigger_s']:g}s, finish {lens['end_frame']}. "
                f"Reason for movement: {lens['reason']}.\n"
                f"Lighting: {d['art']['light_source']}. Palette evolution: {d['art']['color_path']}. "
                f"Environment: {d['art']['environment']}. Texture: {d['art']['texture']}.\n"
                f"Locked identities/objects: {'; '.join(d['continuity']['locked_entities'])}. "
                f"Beginning continuity: {d['continuity']['start_state']}. Final state: {d['continuity']['end_state']}.\n"
                f"Do not include: {'; '.join(d['generation']['negative_constraints'])}. "
                "Do not render any title, text, numbers, subtitles, logo or watermark in the generated footage. "
                "Voiceover, sound effects, music and exact charts are handled in post-production."
            )
            shot_direction += visual_prompt_contract(base, shot, d)
            shared["prompts"]={
                "wan":(f"Create ONE coherent {shot['duration']:g}s vertical 9:16 visual clip; preserve shot identity and physical realism.\n"+shot_direction+
                       "\nPrefer a vetted reference image for consistent face and wardrobe when available; do not assert nonexistent references were supplied."),
                "seedance":(f"Single continuous {shot['duration']:g}s shot, portrait 9:16. One clear evolving visual intention; keep subject and prop continuity stable.\n"+shot_direction+
                            "\nDo not force multiple cuts into one generation. Preserve observed end frame for continuation planning.")}
            shared["postproduction_job"]={"voiceover":shot["narration"],"voiceover_source":"base.narration","voiceover_note":d["sound"]["voiceover_note"],"ambience":d["sound"]["ambient"],"music":d["sound"]["music"],"effects":d["sound"]["effects"],"overlay_text":shot["subtitles"]["text"]}
        jobs.append(shared)
        # Preserve the complete authored speech contract on both production
        # routes. A voiceover string alone loses dialogue, timing and lip sync.
        shared["postproduction_job"]["speech"] = json.loads(json.dumps(d.get("speech")))
    route_counts = {route:sum(j["execution_route"] == route for j in jobs)
                    for route in sorted(PRODUCTION_ROUTES)
                    if any(j["execution_route"] == route for j in jobs)}
    package = {"schema_version":"0.2", "title":base["title"], "aspect_ratio":"9:16", "shots":jobs,
            "production_summary":{"routes":route_counts,
                                  "ai_video_jobs":route_counts.get("ai_video",0),
                                  "non_video_jobs":len(jobs)-route_counts.get("ai_video",0),
                                  "media_created":False},
            "reference_asset_preflight":asset_report if asset_report is not None else
                {"status":"not_assessed","ready_for_reference_preflight":False,
                 "human_visual_consistency_verified":False, "media_generated":False},
            "warnings":warnings, "not_generated_video":True, "publishing_allowed":False,
            "prompt_usage":"Prompts are candidates for operator review and actual-model testing; platform capabilities, version and limits must be checked before generation."}
    package["generation_gate"] = production_gate.evaluate(package)
    return package


def render_compare(base, directions, output):
    esc=lambda s:html.escape(str(s),quote=True)
    shot_dirs={d["shot_id"]:d for d in directions["shots"]}
    cards=[]
    for s in base["shots"]:
        d=shot_dirs[s["id"]]
        beats="".join("<tr><th>"+esc(f"{b['from_s']:g}–{b['to_s']:g}s")+"</th><td>"+esc(b['visible_change'])+"</td><td>"+esc(b['performance'])+"</td><td>"+esc(b['camera'])+"</td><td>"+esc(b['sound'])+"</td></tr>" for b in d["beats"])
        cards.append(f'''<article><h2>{esc(s['id'])} · {esc(s['duration'])}s · {esc(s['purpose'])}</h2><div class="pair"><div class="old"><b>旧版概略</b><p>{esc(s['visual'])}</p><p>摄影：{esc(s['camera']['movement'])} · {esc(s['camera']['shot_size'])}</p></div><div class="new"><b>专业导演意图</b><p>{esc(d['objective']['observable_turn'])}</p><p><b>构图</b>：{esc(d['camera']['start_frame'])}</p><p><b>运镜</b>：{esc(d['camera']['movement'])}</p><p><b>质感</b>：{esc(d['art']['texture'])}</p><p><b>建议制作路线</b>：{esc(production_route(s, d['generation']))}</p></div></div><table><thead><tr><th>时间</th><th>画面变化</th><th>表演</th><th>摄影</th><th>声音</th></tr></thead><tbody>{beats}</tbody></table><p class="dim">画面审查：{esc('、'.join(d['qa']['acceptance_tests']))}</p></article>''')
    page=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(base['title'])} v0.2 专业导演审片</title><style>body{{max-width:1350px;padding:26px;margin:auto;background:#101723;color:#eef3fa;font-family:system-ui,"PingFang SC",sans-serif}}article{{background:#1c2635;border:1px solid #334256;border-radius:14px;margin:18px 0;padding:20px}}h1{{margin-bottom:4px}}.notice{{padding:12px 15px;background:#323128;border-radius:8px}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}.old,.new{{border-radius:9px;padding:13px;background:#273244}}.old{{opacity:.72}}p{{line-height:1.55}}table{{width:100%;border-collapse:collapse;margin-top:15px;font-size:13px}}td,th{{border-bottom:1px solid #475365;padding:10px;text-align:left;vertical-align:top}}.dim{{color:#bcc7d7;font-size:13px}}@media(max-width:720px){{.pair{{grid-template-columns:1fr}}table{{display:block;overflow-x:auto}}}}</style></head><body><h1>{esc(base['title'])} · 专业导演 v0.2</h1><p>{esc(base['duration'])} 秒 / {len(base['shots'])} 镜头 / 9:16</p><div class="notice">这是用于比较的文字导演计划，不是真正的视频；医学数字未获事实核验，不能直接发布。模型生成也无法保证逐秒精确执行。</div>{''.join(cards)}</body></html>'''
    path=Path(output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(page,encoding="utf-8")


def build_codex_task(base_path, direction_path):
    return f'''# AI 短视频导演 v0.2：专业导演深度增强任务

使用当前 Codex 会话已有的 DeepSeek，**不要更改模型或全局配置，不调用付费 API**。

1. 先读取本项目的 AGENTS.md、director_v2.py、参考文件 {base_path}。
2. 读取导演蓝图 {direction_path}，按原结构完成专业创意修改，绝不丢失已有经过人工修改的内容。
3. 对每个镜头定义清晰的戏剧任务（观众应看到什么变化）。优先确定人物/物体空间关系、环境物理、动作终点，再制定有动机的摄影移动。
4. 每个镜头拆解为按相对时间连续的 beats，每个 beat 必须有可见变化、表演、摄影和声音线索，全部时长与 v0.1 相同。不要为堆字数而追加不可能完成的动作。
5. 设计角色/衣服/道具/场景的固定状态与镜头的起止状态；如果没有真实参考资产，明确标注待制作，**不能杜撰已存在的参考图**。涉及出镜道具时在 generation.reference_bindings 用稳定资产ID及所需视角明确绑定；只做规划不生成图片。
6. 对数据图形镜头优先设计图表/字幕/旁白，而不是让生视频模型画中文数字；保留研究类型、对照组、口径的来源提示。
7. 将全片摄影、美术、声画风格写入 global_direction，单镜头补具体而非空泛的视觉形容词。
8. 风险领域的内容如果没有权威来源验证，绝不可写 verified，不得改变研究类型或把 OR 写成 RR。必要时降低表述强度并保留待核验标记。
9. 当镜头需依赖模型能力、参考图片或多段衔接时，在 qa.issues 中写出具体限制。human_approved 一律 false；review_status 可标记 reviewed，意为机器导演稿通过结构审查，绝非用户签字批准。
9c. 对所有含真人动作的 AI 视频镜头，请明确设计 shootability：mode 选择 single_take / split_stitch / static_edit / post_composite / practical_insert；action_units 为每个 beats 至少填写一个动作或有意保持不动的单元，逐项写 id、beat_index、actor_id、hand(left/right/both/none)、prop_id(只允许已在 continuity_contract.props 声明的稳定ID，没道具写 null)、from_s/to_s、action、visible_result。单位时间必须处于所属 beat 内；同一人物同一只手不得在重叠时间执行两种动作；两只手可并行。连续三项精细道具操作集中在约2秒内或某项不足0.55秒，只能视为试制风险，需要改写节奏、拆段或注明 fallback，不能虚构模型一定能做到。没有真人动作或走静态图后期等路线的镜头可使用 shootability=null。具体规则见 SHOOTABILITY.md。\n9b. **除片尾外，每个镜头 editing.narrative_bridge 必须额外填写 beat_link{{outgoing_beat_index,incoming_beat_index,cut_on_visible_event}}，将真正的出画/入画动作锚定到当前镜头末节拍与下一镜首节拍。并给下一镜写四份真实导演方案：cut_intention（viewer_question/answer_or_reframe/why_cut_here/information_change/cut_type），emotion_pacing（emotion_before/emotion_after/audience_effect/tempo_change/tempo_reason/hold_before_s/settle_after_s），visual_handoff（outgoing_frame_anchor/incoming_frame_anchor/axis_or_gaze_rule/motion_or_prop_link/relation），style_handoff（strategy/palette_target/lighting_logic/composition_rule/texture_rule/typography_rule/implementation）。不要复制相同套话，每一对镜头都要解释独有的故事推进；AI 视频与图表/静态/实拍镜头切换时，具体写明统一色彩与排版的后期做法；无特定风格变化可明确 preserve，但要有理由。详情见 NARRATIVE_HANDOFF.md。\n9a. 每镜必须设计 editing（incoming_transition、outgoing_transition、cut_reason、rhythm、assembly_instructions、audio_bridge）、animation（mode、timing、elements、render_in_post、style）、speech（voiceover{{text,delivery,timing,cues[]}}、dialogue[]、subtitle_cues[]、subtitle_direction、lip_sync_policy）。若无跨镜声音连接，audio_bridge={{type:none,duration_s:0,track:none,reason:不用}}；否则必须选 J/L cut、时长、轨道和动机。voiceover.cues 与 subtitle_cues 各自填明确 from_s/to_s/text，注意字幕与旁白内容并不一定相同，分别保持原稿一致。动画 elements 填数字 from_s/to_s，不可以用文字“适当添加”。精确安排对白/旁白、剪辑、动态图层，不能只堆画面提示词；voiceover.text 必须和基础分镜旁白逐字一致，修改需要先修订基础稿。 每句dialogue明确填写speaker_id、text、delivery、from_s、to_s、kind；kind为onscreen_dialogue（出镜口型）或offscreen_dialogue（画外对白），不得把画外对白当成旁白或驱动听者嘴部。
10. 运行 `python3 director_v2.py validate --base {base_path} --direction {direction_path}` 通过后再运行 compile 与 preview；原目录已有内容不覆盖，输出命名带 `_v02`。
11. 报告每个镜头的改进点、依然不可能保证的限制和医学事实阻断。结束时停止，不付费生成视频。
'''


def main(argv=None):
    parser=argparse.ArgumentParser(description="Professional director layer v0.2; offline only")
    subs=parser.add_subparsers(dest="command",required=True)
    for name in ("scaffold","validate","compile","preview","task"):
        sp=subs.add_parser(name)
        sp.add_argument("--base",required=True,help="v0.1 plan.json")
        if name=="scaffold":sp.add_argument("--out",required=True)
        elif name=="task":
            sp.add_argument("--direction",required=True)
            sp.add_argument("--out",required=True)
        else:
            sp.add_argument("--direction",required=True)
            if name in ("validate", "compile"):
                sp.add_argument("--assets", help="optional offline reference catalog")
                sp.add_argument("--asset-root", help="private local image root for hash verification")
            if name!="validate":sp.add_argument("--out",required=True)
    args=parser.parse_args(argv)
    try:
        base=read_json(args.base)
        errors,_=validate_v1(base)
        if errors:raise ValueError("invalid base v0.1 plan: "+"; ".join(errors))
        if args.command=="scaffold":
            write_json(args.out,scaffold(base));print("Draft direction scaffold:",args.out)
        elif args.command=="task":
            target=Path(args.out);target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(build_codex_task(args.base,args.direction),encoding="utf-8")
            print("Codex task:",args.out)
        else:
            directions=read_json(args.direction)
            assets=read_json(args.assets) if getattr(args,"assets",None) else None
            if getattr(args,"asset_root",None) and assets is None:
                raise ValueError("--asset-root needs --assets")
            errors,warnings=validate(base,directions,assets,getattr(args,"asset_root",None))
            for w in warnings:print("WARNING:",w)
            if errors:raise ValueError("; ".join(errors))
            if args.command=="validate":print(f"Professional direction OK: {len(base['shots'])} shots; does NOT approve publication")
            elif args.command=="compile":write_json(args.out,compile_package(base,directions,assets,getattr(args,"asset_root",None)));print("Compiled:",args.out)
            elif args.command=="preview":render_compare(base,directions,args.out);print("Preview:",args.out)
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as ex:
        print("ERROR:",ex,file=sys.stderr);return 2
    return 0

if __name__=="__main__":
    raise SystemExit(main())
