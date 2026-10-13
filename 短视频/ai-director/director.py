#!/usr/bin/env python3
"""Video Director v0.1: script -> reviewable production JSON -> prompts and HTML preview.
Standard library only. Video asset generation intentionally out of scope.
"""
import argparse
import copy
import html
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

VERSION = "0.1.0"
GENERATION_MODES = {"ai_video", "ai_image", "real_broll", "stock", "data_graphic", "motion_graphic", "medical_animation", "text_card", "digital_human", "screen_record"}
RISK_DOMAINS = {"medical", "financial", "legal", "none"}

SYSTEM_GUIDANCE = """你是严谨的 AI 短视频总导演，不是简单的分句器。输入是用户原始中文文案。只输出一个合法 JSON 对象，不用 Markdown。
目标：制作9:16、**每集绝对不超过90秒**的短视频；总剧本可以很长，应先接收编剧完整剧本与详细说明，由总导演自主按叙事自然断点拆成多集，再为每集设计镜头。每集90秒包括片头、回顾、结束和可选证据尾页；不要强制每句一个镜头。
必须遵守：
1. 忠于核心事实，允许删减重复、次要信息；把被删关键材料写入 omissions。不凭空引入数字或研究来源。
2. 医学/法律/金融内容：绝不把相关性写成因果；明确区分 OR/RR/HR、绝对风险、相对风险；没有外部核验时，所有研究结论的 claims.status 必须为 needs_review，绝不声称已核验。
3. 每个镜头应有叙事目的、时长和旁白。分清 AI 视频、实拍、数据图形、医学动画、字幕卡；不要强迫图表用 AI 真人演。
4. AI_VIDEO 镜头必须给出表演链（start, action, micro_action, reaction, end），以及相机、场景、色彩、灯光、音乐、音效、转场、字幕、构图。
5. 把全片风格统一放在 visual_bible；人物和场景使用一致的 ID；避免不可追溯地改变主人公。
6. 视频模型只负责画面；中文精确字幕和数据数字应由后期叠加，绝不要求模型直接生成准确汉字。
7. 每个镜头引用 claims 中存在的 claim ID；涉及医学/数字的信息必须可追踪到原文与证据待办。
输出字段必须参照以下结构（所有字段均必须存在，列表可为空）：
{
 "schema_version":"0.1", "title":"...", "platform":"douyin", "aspect_ratio":"9:16", "duration":55, "risk_domain":"medical|financial|legal|none",
 "core_message":"...", "audience":"...", "editorial":{"hook":"...","narration_script":"...","omissions":[{"text":"...","reason":"..."}]},
 "claims":[{"id":"C01","source_quote":"原文摘录","video_wording":"可用于视频的审慎表述","status":"needs_review","evidence_url":"","caution":"为什么需要审核"}],
 "visual_bible":{"style":"...","palette":"...","lighting":"...","typography":"...","avoid":"..."},
 "characters":[{"id":"CHAR01","description":"...","wardrobe":"...","identity_anchor":"..."}],
 "scenes":[{"id":"LOC01","description":"..."}],
 "shots":[{"id":"S01","start":0,"duration":4,"purpose":"hook","narration":"...","visual_type":"ai_video","claim_ids":[],"character_ids":[],"scene_id":"LOC01",
 "visual":"...","action":{"start":"...","action":"...","micro_action":"...","reaction":"...","end":"..."},
 "camera":{"shot_size":"...","angle":"...","lens":"...","movement":"...","composition":"..."},
 "art":{"lighting":"...","palette":"...","set_props":"..."},
 "graphics":{"type":"none","text":"","animation":"","placement":""},
 "audio":{"music":"...","sfx":"...","voice":"...","pause_before":0},
 "subtitles":{"text":"...","style":"...","placement":"中上部安全区域"},
 "transition":"hard_cut","continuity":"..."}],
 "production":{"voice":"...","music_license_check":true,"asset_license_check":true,"publishing_status":"review_required"}
}
确保 shots 时间起点依次连续，duration 总和与顶层 duration 一致。镜头通常 3-8 秒，不要靠添加冗长旁白凑时长。对虚构的医疗示意动画标记为示意。
"""

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def write_json(path, data):
    p=Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

def validate(plan):
    errors=[]
    warnings=[]
    require=["schema_version","title","platform","aspect_ratio","duration","risk_domain","core_message","editorial","claims","visual_bible","characters","scenes","shots","production"]
    for key in require:
        if key not in plan:
            errors.append(f"missing top-level: {key}")
    if errors:
        return errors,warnings
    if plan["aspect_ratio"]!="9:16": errors.append("aspect_ratio must be 9:16 for this MVP")
    if plan["platform"]!="douyin": errors.append("platform must be douyin")
    if plan["risk_domain"] not in RISK_DOMAINS: errors.append("unknown risk_domain")
    # A full pre-adaptation source or writer rehearsal is NOT an episode.
    # Every actual episode must fit 90s, including reserved non-story time.
    production = plan.get("production")
    production_state = (production.get("publishing_status")
                        if isinstance(production, dict) else None)
    if production_state not in {"source_intake_only", "adaptation_review_required"}:
        total = plan.get("duration")
        if isinstance(total, (int, float)) and total > 90:
            errors.append("episode duration exceeds 90 seconds")
    series = plan.get("series_context")
    if series is not None:
        if (not isinstance(series, dict) or
            not isinstance(series.get("episode_total_planned_s"), (int, float)) or
            series["episode_total_planned_s"] > 90):
            errors.append("series episode total exceeds 90 seconds")
    if not isinstance(plan["shots"],list) or not plan["shots"]: errors.append("shots must be non-empty")
    if errors: return errors,warnings
    claim_ids=set()
    for c in plan["claims"]:
        cid=c.get("id")
        if not cid or cid in claim_ids: errors.append("duplicate/empty claim ID")
        claim_ids.add(cid)
        if not c.get("source_quote"): errors.append(f"{cid}: missing source_quote")
        if c.get("status") not in {"needs_review","verified","rejected"}: errors.append(f"{cid}: invalid claim status")
        if c.get("status")=="verified" and not c.get("evidence_url"):
            errors.append(f"{cid}: marked verified without evidence_url")
    character_ids={c.get("id") for c in plan["characters"]}
    scene_ids={s.get("id") for s in plan["scenes"]}
    position=0
    seen=set()
    for shot in plan["shots"]:
        sid=shot.get("id", "?")
        if sid in seen: errors.append(f"duplicate shot: {sid}")
        seen.add(sid)
        d=shot.get("duration")
        st=shot.get("start")
        if not isinstance(d,(int,float)) or d<=0: errors.append(f"{sid}: invalid duration"); continue
        if not isinstance(st,(int,float)) or abs(st-position)>0.01: errors.append(f"{sid}: non-contiguous start, expected {position}")
        position+=d
        mode=shot.get("visual_type")
        if mode not in GENERATION_MODES: errors.append(f"{sid}: unsupported visual_type {mode}")
        for key in ["purpose","narration","visual","action","camera","art","graphics","audio","subtitles","transition","continuity","scene_id","character_ids","claim_ids"]:
            if key not in shot: errors.append(f"{sid}: missing {key}")
        if mode=="ai_video":
            action=shot.get("action") or {}
            for key in ["start","action","micro_action","reaction","end"]:
                if not action.get(key): errors.append(f"{sid}: ai_video missing action.{key}")
        for cid in shot.get("claim_ids",[]):
            if cid not in claim_ids: errors.append(f"{sid}: unknown claim {cid}")
        if shot.get("scene_id") and shot["scene_id"] not in scene_ids:
            errors.append(f"{sid}: unknown scene {shot['scene_id']}")
        for character in shot.get("character_ids",[]):
            if character not in character_ids: errors.append(f"{sid}: unknown character {character}")
        if mode in {"data_graphic","motion_graphic"} and not shot.get("graphics",{}).get("type"):
            warnings.append(f"{sid}: animation type missing")
    if abs(position-plan["duration"])>0.01: errors.append(f"duration mismatch: {position} vs {plan['duration']}")
    if plan["risk_domain"]!="none" and any(c.get("status")!="verified" for c in plan["claims"]):
        warnings.append("PUBLISH BLOCKED: high-stakes claims require human source review")
    if plan["risk_domain"]!="none" and not plan["claims"]:
        warnings.append("PUBLISH BLOCKED: risk-domain production has no claims provenance")
    return errors,warnings

def compile_prompts(plan):
    if plan.get("director_editorial_montage"):
        raise ValueError("EDITORIAL_MONTAGE_RENDERER_REQUIRED_LEGACY_EDITS_UNSAFE")
    if plan.get("requires_timed_cue_rendering"):
        raise ValueError("TIMED_CUE_RENDERER_REQUIRED_LEGACY_SHOT_TEXT_UNSAFE")
    people={x["id"]:x for x in plan["characters"]}
    places={x["id"]:x for x in plan["scenes"]}
    outputs=[]
    for shot in plan["shots"]:
        if shot["visual_type"]!="ai_video": continue
        anchors="; ".join(f"{cid}: {people[cid]['description']}, {people[cid].get('wardrobe','')}, {people[cid].get('identity_anchor','')}" for cid in shot["character_ids"])
        place=places.get(shot["scene_id"],{}).get("description","")
        a=shot["action"]; c=shot["camera"]; art=shot["art"]
        common=(f"Realistic vertical 9:16 video, {shot['duration']} seconds. "
                f"Shared look: {plan['visual_bible']['style']}; {plan['visual_bible']['palette']}. "
                f"Character continuity: {anchors}. Scene: {place}. "
                f"Opening state: {a['start']}. Primary action: {a['action']}. "
                f"Micro-action: {a['micro_action']}. Reaction: {a['reaction']}. Ending state: {a['end']}. "
                f"Camera: {c['shot_size']}, {c['angle']}, {c['lens']}, {c['movement']}, {c['composition']}. "
                f"Lighting: {art['lighting']}. Color: {art['palette']}. Set and props: {art['set_props']}. "
                "Physically plausible motion and gestures; consistent face and wardrobe. "
                "Do not generate words, numbers, subtitles, logos or watermarks within the footage; overlay later in editing.")
        outputs.append({"shot_id":shot["id"],"duration":shot["duration"],"models":{
            "wan":common+" Single continuous shot; prefer image-to-video with approved character reference frame when available.",
            "seedance":common+" Clearly follow beginning-action-reaction-ending chronology and preserve stable subject continuity."},
            "requires_reference_images":bool(shot["character_ids"]),
            "text_overlay_after_generation":shot["subtitles"]["text"]})
    return outputs

def render_preview(plan, output):
    if plan.get("director_editorial_montage"):
        raise ValueError("EDITORIAL_MONTAGE_PREVIEW_REQUIRED_LEGACY_EDITS_UNSAFE")
    if plan.get("requires_timed_cue_rendering"):
        raise ValueError("TIMED_CUE_PREVIEW_REQUIRED_LEGACY_SHOT_TEXT_UNSAFE")
    esc=lambda x: html.escape(str(x))
    cards=[]
    for sh in plan["shots"]:
        cid=", ".join(sh["claim_ids"]) or "—"
        cards.append(f'''<article class="shot"><div class="screen"><div class="kicker">{esc(sh['id'])} · {esc(sh['visual_type'])}</div><div class="visual">{esc(sh['visual'])}</div><div class="subtitle">{esc(sh['subtitles']['text'])}</div></div><section><h3>{esc(sh['id'])} · {esc(sh['start'])}–{esc(sh['start']+sh['duration'])}s</h3><p><b>旁白：</b>{esc(sh['narration'])}</p><p><b>动作：</b>{esc(sh['action'].get('action',''))}</p><p><b>摄影：</b>{esc(sh['camera'].get('movement',''))} · {esc(sh['camera'].get('shot_size',''))}</p><p><b>色彩/灯光：</b>{esc(sh['art']['palette'])} · {esc(sh['art']['lighting'])}</p><p><b>音乐/音效：</b>{esc(sh['audio']['music'])} · {esc(sh['audio']['sfx'])}</p><p class="muted">证据标记：{esc(cid)}</p></section></article>''')
    warning=" <strong>本预演是文字分镜，不是实际视频。</strong> 凡医学、金融、法律数据在发布前均需核验。"
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(plan['title'])} · 导演预演</title><style>body{{font-family:-apple-system,BlinkMacSystemFont,'Noto Sans SC',sans-serif;background:#11141b;color:#edf0f7;padding:24px;max-width:1250px;margin:auto}}header{{border-bottom:1px solid #343943;margin-bottom:18px}}.muted{{color:#a8b1c0}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px}}.shot{{border:1px solid #333c4a;border-radius:13px;overflow:hidden;background:#1c212c}}.screen{{width:70%;aspect-ratio:9/16;margin:18px auto;background:linear-gradient(150deg,#333e53,#151a24);display:flex;flex-direction:column;justify-content:space-between;padding:16px;box-sizing:border-box;border-radius:8px}}.kicker{{font-size:12px;opacity:.8}}.visual{{text-align:center;font-size:16px;line-height:1.6}}.subtitle{{text-align:center;font-weight:750;background:#0009;border-radius:6px;padding:8px}}section{{padding:14px}}section p{{font-size:14px;line-height:1.6}}h1{{margin-bottom:4px}}.warning{{background:#303329;padding:12px;border-radius:9px;margin:12px 0}}</style><header><h1>{esc(plan['title'])}</h1><p class="muted">{esc(plan['core_message'])} · {esc(plan['duration'])} 秒 · 9:16 · {len(plan['shots'])} 镜头</p></header><div class="warning">{warning}</div><div class="grid">{''.join(cards)}</div></html>'''
    p=Path(output);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(page,encoding="utf-8")

def request_plan(script, model, base_url, api_key):
    if not api_key: raise ValueError("missing AI_API_KEY; use 'prepare' for Codex manual mode")
    if not base_url.startswith("https://"):
        raise ValueError("AI_API_BASE_URL must be https://")
    url=base_url.rstrip("/")+"/chat/completions"
    body=json.dumps({"model":model,"messages":[{"role":"system","content":SYSTEM_GUIDANCE},{"role":"user","content":"原始文案如下：\n"+script}],"temperature":0.25,"max_tokens":16384,"response_format":{"type":"json_object"}}).encode()
    req=urllib.request.Request(url,data=body,headers={"Content-Type":"application/json","Authorization":"Bearer "+api_key},method="POST")
    with urllib.request.urlopen(req,timeout=120) as response:
        data=json.load(response)
    answer=data["choices"][0]["message"]["content"]
    if answer.startswith("```"):
        answer=re.sub(r"^```(?:json)?\s*|\s*```$","",answer)
    return json.loads(answer)

def main(argv=None):
    p=argparse.ArgumentParser(description="AI Short Video Director MVP")
    sub=p.add_subparsers(dest="command",required=True)
    prep=sub.add_parser("prepare",help="generate offline Codex work packet")
    prep.add_argument("--input",required=True);prep.add_argument("--out",required=True)
    gen=sub.add_parser("generate",help="call OpenAI-compatible chat API to create structured plan")
    gen.add_argument("--input",required=True);gen.add_argument("--out",required=True)
    gen.add_argument("--model",default=os.environ.get("AI_MODEL","deepseek-flash"))
    gen.add_argument("--base-url",default=os.environ.get("AI_API_BASE_URL","https://api.deepseek.com/v1"))
    val=sub.add_parser("validate");val.add_argument("--plan",required=True)
    compile_=sub.add_parser("compile");compile_.add_argument("--plan",required=True);compile_.add_argument("--out",required=True)
    preview=sub.add_parser("preview");preview.add_argument("--plan",required=True);preview.add_argument("--out",required=True)
    args=p.parse_args(argv)
    try:
        if args.command=="prepare":
            source=Path(args.input).read_text(encoding="utf-8")
            dest=Path(args.out);dest.mkdir(parents=True,exist_ok=True)
            (dest/"source.md").write_text(source,encoding="utf-8")
            (dest/"codex_task.md").write_text("# Codex 任务：按照下列导演规则生成 plan.json\n\n"+SYSTEM_GUIDANCE+"\n\n请分析下面原文，输出到 plan.json，不要假装事实核验完成；使用 `python3 director.py validate --plan ...` 检查。\n\n## 原文\n\n"+source,encoding="utf-8")
            print(f"Codex work packet: {dest/'codex_task.md'}")
        else:
            if args.command=="generate":
                source=Path(args.input).read_text(encoding="utf-8")
                plan=request_plan(source,args.model,args.base_url,os.environ.get("AI_API_KEY",""))
                errors,warnings=validate(plan)
                if errors:
                    raise ValueError("AI result failed validation; nothing saved: "+"; ".join(errors))
                write_json(args.out,plan)
                for w in warnings: print("WARNING:",w)
                print("Created:",args.out)
            else:
                plan=read_json(args.plan)
                errors,warnings=validate(plan)
                for w in warnings: print("WARNING:",w)
                if errors:
                    for e in errors: print("ERROR:",e,file=sys.stderr)
                    return 2
                if args.command=="validate": print(f"Valid plan: {len(plan['shots'])} shots, {plan['duration']}s")
                elif args.command=="compile": write_json(args.out,{"schema_version":"0.1","shot_prompts":compile_prompts(plan)});print("Created:",args.out)
                elif args.command=="preview": render_preview(plan,args.out);print("Created:",args.out)
    except (ValueError,KeyError,json.JSONDecodeError,FileNotFoundError,urllib.error.URLError) as err:
        print(f"ERROR: {err}",file=sys.stderr);return 2
    return 0

if __name__=="__main__":
    raise SystemExit(main())