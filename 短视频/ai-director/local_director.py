#!/usr/bin/env python3
"""Offline-first Chinese video director orchestrator, v0.3.

Never requires ChatGPT or GitHub at runtime. Creative planning requires a
configured LLM (or user's Codex). Video rendering and reference images do not
happen in this version. Pure Python stdlib.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import sys
import urllib.error
import urllib.request
import zipfile

import director
import director_v2 as v2
from llm_budget import BudgetSession, BudgetError, RetryableLLMError, peak_rates

ROOT = Path(__file__).resolve().parent
SKILLS = ROOT / "skills"
DEFAULT_MODEL = "deepseek-flash"  # override with AI_MODEL if this model ID is unavailable
DEFAULT_URL = "https://api.deepseek.com/v1"

class DirectorError(Exception):
    pass


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)


def create_once(path, data):
    """Create a default without overwriting user-edited files on resume/review."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open('x', encoding='utf-8') as handle:
            if isinstance(data, str):
                handle.write(data)
            else:
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.write('\n')
        return True
    except FileExistsError:
        return False


def series_with_bible(series, bible):
    """Use local user-approved or edited character bible as truth for QA.

    The model-produced series JSON is a draft, not authorization to overwrite
    user-edited character attributes.  Do not reconcile silently; a mismatch
    must fail with an actionable error.
    """
    if not isinstance(bible, dict) or not isinstance(bible.get('characters'), list) or not isinstance(bible.get('visual_bible'), dict):
        raise DirectorError('人物设定文件格式不完整；不会自动覆盖，请人工修复 character_bible.json')
    active = dict(series)
    active['characters'] = bible['characters']
    active['visual_bible'] = bible['visual_bible']
    return check_series(active)


def textfile(path):
    return Path(path).read_text(encoding="utf-8")


def stamp():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def warn_publishing(plan):
    """A link or DOI is not independent evidence of a claim being verified."""
    if plan.get("risk_domain") != "none":
        for claim in plan.get("claims", []):
            claim["status"] = "needs_review"
        production = plan.setdefault("production", {})
        production["publishing_status"] = "review_required"
        req = production.setdefault("review_requirements", [])
        if "Research methods and numeric results must be reviewed against primary sources" not in req:
            req.append("Research methods and numeric results must be reviewed against primary sources")
    return plan


def check_series(series):
    if not isinstance(series, dict):
        raise DirectorError("series.json 必须是 JSON 对象")
    ep = series.get("episodes")
    if not isinstance(ep, list) or not 1 <= len(ep) <= 3:
        raise DirectorError("本版必须规划 1–3 集；不能无限生成造成费用失控")
    required = ("title", "core_message", "narrative_arc", "content_focus", "target_seconds")
    for i, e in enumerate(ep, 1):
        if not isinstance(e, dict) or any(not e.get(k) for k in required):
            raise DirectorError(f"第{i}集缺少必要的标题、主旨、叙事、重点或目标时长")
        if not isinstance(e["target_seconds"], (int, float)) or not 30 <= e["target_seconds"] <= 180:
            raise DirectorError(f"第{i}集目标时长应为30–180秒")
    cast = series.get("characters", [])
    if not isinstance(cast, list):
        raise DirectorError("characters必须为列表（没有出场角色也可以为空）")
    ids = [c.get("id") for c in cast if isinstance(c, dict)]
    if len(ids) != len(cast) or any(not x for x in ids) or len(set(ids)) != len(ids):
        raise DirectorError("人物必须有不重复的角色ID")
    if not isinstance(series.get("visual_bible"), dict):
        raise DirectorError("缺少整个系列的视觉风格 visual_bible")
    return series


def check_episode_against_series(plan, series):
    errors, warnings = director.validate(plan)
    ids = {c["id"] for c in series["characters"]}
    for c in plan.get("characters", []):
        if c.get("id") not in ids:
            errors.append(f"出现系列角色库之外的新人物ID: {c.get('id')}")
    for c in series["characters"]:
        p = next((x for x in plan.get("characters", []) if x.get("id") == c["id"]), None)
        if p:
            for key, label in (("description", "外形描述"), ("wardrobe", "服装"), ("identity_anchor", "人物身份锚点")):
                if p.get(key) != c.get(key):
                    errors.append(f"跨集角色 {c['id']} {label}发生变化；请核对角色设定而非自动变脸")
    # Stories may evolve lighting per shot, but global visual bible is locked.
    for key, value in series.get("visual_bible", {}).items():
        if plan.get("visual_bible", {}).get(key) != value:
            errors.append(f"整片视觉规范 visual_bible.{key} 与系列设定冲突；请明确改版")
    if not ids and any(s.get("character_ids") for s in plan.get("shots", [])):
        errors.append("系列角色库为空，但镜头引用了人物")
    return errors, warnings


def check_reference_card(plan):
    cards = [s for s in plan.get("shots", []) if s.get("purpose") == "sources"]
    if not cards:
        return  # Without credible studies, don't fabricate a research bibliography.
    card = cards[-1]
    if len(cards) != 1 or plan["shots"][-1] is not card:
        raise DirectorError("研究出处必须仅有一张并且位于片尾")
    if card.get("duration") != 5 or card.get("narration", ""):
        raise DirectorError("研究出处卡固定5秒、无额外旁白")
    ids = card.get("claim_ids", [])
    if not isinstance(ids, list) or len(ids) != len(set(ids)) or not 2 <= len(ids) <= 3:
        raise DirectorError("研究出处卡请选择2-3项不重复的研究")
    if card.get("visual_type") != "text_card":
        raise DirectorError("研究出处卡必须由后期叠加文字，不让视频模型直接画字")
    claims = {c.get("id"): c for c in plan.get("claims", []) if isinstance(c, dict)}
    references = plan.get("references")
    if not isinstance(references, list):
        raise DirectorError("研究卡缺少 references 文献账本（含作者、年份、期刊、研究类型和链接）")
    ref_map = {}
    for ref in references:
        if not isinstance(ref, dict) or not isinstance(ref.get("claim_id"), str) or ref["claim_id"] in ref_map:
            raise DirectorError("references 文献账本有非法或重复 claim_id")
        ref_map[ref["claim_id"]] = ref
    for cid in ids:
        if cid not in claims or cid not in ref_map:
            raise DirectorError(f"片尾引用 {cid} 没有同时出现在 claims 与 references 中")
        claim, ref = claims[cid], ref_map[cid]
        if claim.get("status") == "rejected" or ref.get("status") == "rejected":
            raise DirectorError(f"片尾引用 {cid} 已被拒绝，不可继续展示")
        for field in ("author", "year", "journal", "study_type", "url"):
            if not ref.get(field) or isinstance(ref[field], (list, dict)):
                raise DirectorError(f"片尾引用 {cid} 缺少书目信息 {field}")
        if not isinstance(ref["year"], int) or not 1800 <= ref["year"] <= dt.datetime.now().year:
            raise DirectorError(f"片尾引用 {cid} 年份错误")
        if not isinstance(ref["url"], str) or not ref["url"].startswith("https://"):
            raise DirectorError(f"片尾引用 {cid} 需要 HTTPS 可追踪来源链接")
        if ref.get("status") != "needs_review":
            raise DirectorError(f"片尾引用 {cid} 必须保持 needs_review，直至独立完成来源验证")
        if claim.get("evidence_url") and claim["evidence_url"] != ref["url"]:
            raise DirectorError(f"片尾引用 {cid} 与主张的文献链接不一致")
    # Bibliographic metadata and a DOI link do NOT establish actual evidence.
    # Publishing remains blocked until original methods and figures are checked.


def llm_json(*, system, user, model, url, key, timeout=160, max_tokens=16384, usage_hook=None, invalid_response_path=None):
    """Single explicit, potentially billable OpenAI-compatible chat request."""
    if not key:
        raise DirectorError("缺少 AI_API_KEY；不用API时请使用 prepare + Codex 模式")
    if not url.startswith("https://") and not url.startswith("http://127.0.0.1:") and not url.startswith("http://localhost:"):
        raise DirectorError("模型地址必须为HTTPS，或明确的本机 localhost 服务")
    endpoint = url.rstrip("/") + "/chat/completions"
    payload = json.dumps({"model": model, "messages": [
        {"role": "system", "content": system + "\n请只返回一个语法正确的JSON对象。字段名和字符串使用双引号，不要尾逗号、注释、Markdown代码围栏或任何解释文字。JSON示例：{\"ok\":true}。"},
        {"role": "user", "content": user}], "temperature": 0.3, "max_tokens": max_tokens,
        "response_format": {"type": "json_object"}}).encode("utf-8")
    request = urllib.request.Request(endpoint, data=payload,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise RetryableLLMError("LLM HTTP 429：请求频率限制，当前调用已计入预算保护；如开启了有限重试，将额外占用一次额度") from exc
        raise DirectorError(f"LLM HTTP {exc.code}，请检查 API Key、模型ID及配额；本次请求可能产生费用，不自动重试") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise DirectorError("无法连接选定模型服务。已有本地成果不丢失；可稍后 --resume") from exc
    try:
        if usage_hook is not None and isinstance(data.get("usage"), dict):
            usage_hook(data["usage"])
        item = data["choices"][0]
        if item.get("finish_reason") == "length":
            raise DirectorError("模型输出被截断，未保存为有效导演方案")
        content = item["message"]["content"]
        if not content:
            raise RetryableLLMError("LLM JSON模式返回空内容；仅在预算足够且显式设置 --max-retries 时重试")
        original_content = content
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            # Diagnostic of a billable model response. Keep the ORIGINAL bytes
            # under the current local job; never print the response or API key.
            # Create-only prevents an automatic retry from destroying evidence.
            if invalid_response_path is not None:
                create_once(invalid_response_path, original_content)
            raise RetryableLLMError(
                f"模型返回非法JSON（第{exc.lineno}行第{exc.colno}列：{exc.msg}；"
                f"响应长度{len(content)}字符）。已保留本地诊断文件（如果设置了诊断路径）；"
                "不会自动额外收费重试") from exc
        if not isinstance(parsed, dict):
            raise RetryableLLMError("模型没有返回JSON对象；仅可进行有预算的有限重试")
        return parsed
    except (KeyError, IndexError, TypeError) as exc:
        raise RetryableLLMError("模型响应结构异常；仅可进行有预算的有限重试") from exc


def create_prepare(input_path, output_dir):
    source = Path(input_path).read_text(encoding="utf-8")
    if not source.strip():
        raise DirectorError("文案为空")
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise DirectorError("目标目录非空；请选择新目录，避免覆盖你之前修改过的导演工作")
    output.mkdir(parents=True, exist_ok=True)
    (output / "source.md").write_text(source, encoding="utf-8")
    (output / "CODEX_TASK.md").write_text(
        "# 交给现有 Codex + DeepSeek 的制作任务\n\n"
        "请先阅读这个目录上方的 AGENTS.md 和 skills/ 中的所有 Markdown。"
        "不要更改全局模型配置，不要调用收费视频/配音接口，不要向GitHub发布。\n\n"
        "请阅读 source.md，按以下阶段生成并保存文件，而不是只在聊天中回答：\n\n"
        "1. series.json（1–3集结构、统一角色和 visual_bible；参考 skills/01-series.md）。\n"
        "2. episodes/ep01/plan.json 等（每集 v0.1 结构、重点数据证据账本、可选5秒研究片尾卡）。\n"
        "3. episodes/ep01/direction_v02.json 等（逐秒动作、运镜、灯光、声音、图表和连续性）。\n"
        "4. 每一步对照 schemas 和原始示例检查，所有来源未经查证一律 needs_review。\n"
        "5. 每完成一集就执行 python3 local_director.py review --job <当前任务目录>，"
        "检查错误并修复；最后给我打开 index.html。\n\n"
        "注意：source.md 是用户原文。不能伪造研究、论文DOI、人物参考图或已生成的视频。"
        "单张研究出处卡5秒、2–3条最相关研究，其余放 description.md。\n",
        encoding="utf-8")
    save(output / "status.json", {"created": stamp(), "mode": "codex_manual", "status": "prepared", "source_sha256": hashlib.sha256(source.encode()).hexdigest()})
    return output


def series_prompt(source):
    system = textfile(SKILLS / "01-series.md")
    user = ("请把下面的中文长文案拆成有故事线的1至3集，不要机械按字数拆。"
            "输出 JSON：{\"series_title\":\"...\",\"characters\":[{\"id\":\"CH_MAIN\",\"description\":\"...\",\"wardrobe\":\"...\",\"identity_anchor\":\"需要制作参考图，尚未创建\"}],"
            "\"visual_bible\":{\"style\":\"...\",\"palette\":\"...\",\"lighting\":\"...\",\"typography\":\"...\",\"avoid\":\"...\"},"
            "\"episodes\":[{\"title\":\"...\",\"core_message\":\"...\",\"narrative_arc\":\"...\",\"content_focus\":\"...\",\"target_seconds\":75}]}. "
            "如果文案不适合多集，可仅1集；研究不足不要伪造来源。\n\n原文：\n"+source)
    return system, user


def episode_prompt(source, series, index):
    spec = series["episodes"][index]
    guidance = director.SYSTEM_GUIDANCE + "\n" + textfile(SKILLS / "02-episode.md")
    guidance += "\n必须沿用系列给定的人物ID、外形、衣服、visual_bible；没有角色不要强行造真人。"
    user = ("完成系列第"+str(index+1)+"集的 v0.1 plan.json。必须完全满足 director.py 的结构。"
            "首尾5秒研究卡仅当有2-3项真实可追溯研究时生成；purpose=sources, text_card, duration=5, narration为空, 使用claim_ids。"
            "所有其余引用留在claims，医疗心理财经类一律 needs_review。"
            "如有片尾来源卡，还必须输出 references 列表，每项按claim_id绑定，包含author/year(整数)/journal/study_type/url/status=needs_review。"
            "只有实际提供的来源才允许引用，找不到原始研究时不生成片尾卡；即便有DOI也不能宣称事实已经核实。"
            "旁白自然可读，时长与全镜头一致。最多3集但这次只写一集。\n"
            "本集要点："+json.dumps(spec, ensure_ascii=False)+"\n"
            "系列已固定人物和风格（必须逐字沿用人物 description）："+json.dumps({"characters":series["characters"],"visual_bible":series["visual_bible"]},ensure_ascii=False)+"\n"
            "原文：\n"+source)
    return guidance,user


def direction_prompt(base, series):
    template = v2.scaffold(base)
    guidance = textfile(SKILLS / "03-direction.md") + "\n" + v2.build_codex_task("plan.json", "direction_v02.json")
    user = ("请基于计划生成可通过 director_v2.validate 的完整专业导演 JSON。"
            "不要留占位符；每镜内部的beats必须覆盖全部秒数。"
            "AI视频镜头详细描述人的动作、摄影运动触发、视线与结束姿势，图形镜头用后期设计。"
            "单张来源卡5秒、无配音、静态图；必须在v0.2的plan里对应。"
            "reference_assets 未实际生成，列表为空，不许虚构存在文件。"
            "global_direction确保全年龄观众理解；qa.human_approved 一律false。"
            "输出基于此schema样板并补完所有字段：\n"+json.dumps(template,ensure_ascii=False)+"\n"
            "已批准的系列规范：\n"+json.dumps(series,ensure_ascii=False)+"\n"
            "本集基础计划：\n"+json.dumps(base,ensure_ascii=False))
    return guidance,user


def run_job(args):
    if not args.approve_model_cost:
        raise DirectorError("为防止意外费用，必须显式添加 --approve-model-cost 才能发起 LLM API 请求")
    key = os.environ.get("AI_API_KEY", "").strip()
    if not key:
        raise DirectorError("AI_API_KEY 未设置。可用 prepare + 现有 Codex，或配置国产模型API")
    job = Path(args.out)
    if job.exists() and any(job.iterdir()) and not args.resume:
        raise DirectorError("已有工作目录。如需在原工作上续跑请用 --resume，避免覆盖成果")
    # Guard the *entire* API lifecycle with explicit CNY cap, model/price lock,
    # request count cap, and a persisted reservation ledger.
    max_cost=getattr(args,'max_cost_cny',None)
    if max_cost is None:
        raise DirectorError("真实API模式还需 --max-cost-cny 金额（人民币）；仅 --approve-model-cost 不够")
    rates=peak_rates(args.model,args.base_url)
    input_rate=getattr(args,'input_cny_per_million',None)
    output_rate=getattr(args,'output_cny_per_million',None)
    if input_rate is None and rates: input_rate=rates[0]
    if output_rate is None and rates: output_rate=rates[1]
    if input_rate is None or output_rate is None:
        raise DirectorError("未知服务商或模型必须明确指定 --input-cny-per-million 和 --output-cny-per-million 单价")
    job.mkdir(parents=True,exist_ok=True)
    budget=BudgetSession(job=job,model=args.model,base_url=args.base_url,cap_cny=max_cost,
        input_cny_m=input_rate,output_cny_m=output_rate,
        max_calls=getattr(args,'max_calls',7),
        max_retries=getattr(args,'max_retries',0),
        max_output_tokens=getattr(args,'max_output_tokens',16384))
    try:
        def guarded(stage, system, user):
            return budget.invoke(stage=stage,system=system,user=user,caller=lambda hook: llm_json(
                system=system,user=user,model=args.model,url=args.base_url,key=key,
                max_tokens=budget.max_output_tokens,usage_hook=hook,
                invalid_response_path=job/"diagnostics"/(stage.replace(".","_")+".invalid-response.txt")))
        def semantic_fix(stage, candidate, system, original_user, check):
            """Repair model-owned new drafts only; each retry is a fresh budgeted call.

            Never silently patch or overwrite existing human-authored project files.
            """
            for iteration in range(budget.max_retries+1):
                errors=check(candidate)
                if not errors:return candidate
                if iteration>=budget.max_retries:
                    raise DirectorError(f'{stage} 结构校验不通过：'+'; '.join(errors[:8]))
                short_errors=json.dumps(errors[:16],ensure_ascii=False)
                repair_user=(original_user+'\n\n上次模型输出以下JSON，但结构校验失败。'
                     '仅修复列出的字段/人物一致性/时间线错误，不要增加新研究事实或虚构URL。'
                     '返回完整有效JSON对象，不能删减经过验证的其他内容。\n'
                     '具体错误：'+short_errors+'\n上一版JSON：\n'+json.dumps(candidate,ensure_ascii=False))
                candidate=guarded(stage+'.repair',system,repair_user)
            raise DirectorError(f'{stage} 自动修复耗尽预算，须人工审核')

        source_path=job/"source.md"
        if source_path.exists():
            source=textfile(source_path)
            if Path(args.input).read_text(encoding="utf-8") != source:
                raise DirectorError("续跑时提供的原文与原项目不同；不能混用")
        else:
            source=Path(args.input).read_text(encoding="utf-8")
            if not source.strip(): raise DirectorError("文案为空")
            source_path.write_text(source, encoding="utf-8")
        if len(source)>45000:
            raise DirectorError("本版单次输入限45000字符，过长请先拆分或交Codex处理")
        series_path=job/"series.json"
        if series_path.exists():
            series=check_series(load(series_path))
        else:
            system,user=series_prompt(source)
            def _check_series_candidate(candidate):
                try:check_series(candidate);return []
                except DirectorError as exc:return [str(exc)]
            first=guarded("series",system,user)
            try:
                series=semantic_fix('series',first,system,user,_check_series_candidate)
            except (DirectorError,BudgetError,RetryableLLMError):
                save(job/'series_invalid.json',first)
                raise
            save(series_path, series)
        create_once(job/"character_bible.json", {"characters":series["characters"],"visual_bible":series["visual_bible"],"reference_images_status":"not_created", "approved":False})
        series = series_with_bible(series, load(job/"character_bible.json"))
        create_once(job/"status.json", {"started":stamp(),"model":args.model,"series_count":len(series["episodes"]),"phase":"planned","cost_approved_by_cli":True,"video_generation":False})
        for index,ep in enumerate(series["episodes"]):
            folder=job/"episodes"/f"ep{index+1:02d}"
            folder.mkdir(parents=True,exist_ok=True)
            base_path=folder/"plan.json"
            if base_path.exists():
                base=load(base_path)
            else:
                system,user=episode_prompt(source,series,index)
                first=warn_publishing(guarded(f"ep{index+1:02d}.plan",system,user))
                def _check_plan_candidate(candidate):
                    warn_publishing(candidate)
                    errs,_=check_episode_against_series(candidate,series)
                    if not errs:
                        try:check_reference_card(candidate)
                        except DirectorError as exc:errs.append(str(exc))
                    return errs
                try:
                    base=semantic_fix(f"ep{index+1:02d}.plan",first,system,user,_check_plan_candidate)
                except (DirectorError,BudgetError,RetryableLLMError):
                    save(folder/"draft_invalid.json",first)
                    raise
                save(base_path,base)
            errors,_=check_episode_against_series(base,series)
            if errors:raise DirectorError("现有基础计划需要修复："+"; ".join(errors[:8]))
            check_reference_card(base)
            direction_path=folder/"direction_v02.json"
            if not direction_path.exists():
                system,user=direction_prompt(base,series)
                first=guarded(f"ep{index+1:02d}.direction",system,user)
                def _check_direction_candidate(candidate):
                    errs,_=v2.validate(base,candidate)
                    return errs
                try:
                    direction=semantic_fix(f"ep{index+1:02d}.direction",first,system,user,_check_direction_candidate)
                except (DirectorError,BudgetError,RetryableLLMError):
                    save(folder/"direction_invalid.json",first)
                    raise
                save(direction_path,direction)
            else:
                direction=load(direction_path)
            errors,_=v2.validate(base,direction)
            if errors:raise DirectorError("方向稿验证失败："+"; ".join(errors[:8]))
            print(f"已生成 ep{index+1:02d}：{len(base['shots'])} 镜、{base['duration']}秒")
        review_job(job)
        return job
    finally:
        budget.close()


def review_job(job):
    job=Path(job)
    series=check_series(load(job/"series.json"))
    if (job/"character_bible.json").exists():
        series=series_with_bible(series, load(job/"character_bible.json"))
    episodes=job/"episodes"
    rows=[]
    if not episodes.exists():
        raise DirectorError("未找到 episodes 文件夹；请先运行Codex创作或者使用 run")
    for i,_ in enumerate(series["episodes"],1):
        folder=episodes/f"ep{i:02d}"
        base=load(folder/"plan.json")
        direction=load(folder/"direction_v02.json")
        errors,warnings=check_episode_against_series(base,series)
        if errors:raise DirectorError(f"第{i}集基础数据错误："+"; ".join(errors[:8]))
        check_reference_card(base)
        errors,warnings_v2=v2.validate(base,direction)
        if errors:raise DirectorError(f"第{i}集导演数据错误："+"; ".join(errors[:8]))
        v2.render_compare(base,direction,folder/"preview.html")
        compiled=v2.compile_package(base,direction)
        save(folder/"prompts.generated.json",compiled)
        create_once(folder/"prompts.json",compiled)
        citations=[f"- {c['id']}：原文：{c.get('source_quote','')}\n  表述：{c.get('video_wording','')}\n  研究URL：{c.get('evidence_url','') or '待补充'}\n  状态：{c.get('status','needs_review')}\n  限制：{c.get('caution','')}" for c in base["claims"]]
        autogenerated = "# "+base["title"]+"\n\n## 研究来源与局限\n\n"+("\n\n".join(citations) if citations else "没有可核实的研究引用；不得凭空加入来源。")+"\n"
        (folder/"description.generated.md").write_text(autogenerated, encoding="utf-8")
        create_once(folder/"description.md",autogenerated)
        rows.append({"label":f"第{i}集：{base['title']}","link":f"episodes/ep{i:02d}/preview.html","seconds":base["duration"],"warnings":warnings+warnings_v2})
    cards=''.join(f'<article><h2>{html.escape(r["label"])}</h2><p>{r["seconds"]}秒</p><a href="{html.escape(r["link"],quote=True)}">查看逐镜头导演预演 →</a></article>' for r in rows)
    page='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI导演本地审片</title><style>body{font-family:system-ui,-apple-system,"PingFang SC",sans-serif;background:#141923;color:#edf0f8;padding:32px;max-width:900px;margin:auto}article{background:#273449;padding:20px;border-radius:12px;margin:14px 0}a{color:#91d2ff}.banner{background:#3b352c;padding:15px;border-radius:9px}</style></head><body><h1>AI 导演 · 本地审片</h1><p class="banner">不依赖GitHub、ChatGPT联网；这仅是分镜与Prompt预演，不是真实MP4。视频、配音、人物参考图片未生成。所有事实/来源仍须人工核对。</p>'''+cards+'</body></html>'
    (job/"index.html").write_text(page,encoding="utf-8")
    save(job/"review_status.generated.json", {"time":stamp(),"episodes":rows,"publishing_allowed":False,"video_generated":False})
    create_once(job/"review_status.json", {"time":stamp(),"episodes":rows,"publishing_allowed":False,"video_generated":False})
    return job/"index.html"


def backup(project, archive):
    project=Path(project).resolve()
    destination=Path(archive).resolve()
    if not project.is_dir():raise DirectorError("备份源目录不存在")
    if destination.is_relative_to(project):raise DirectorError("备份压缩包请存到项目目录之外，避免递归打包")
    destination.parent.mkdir(parents=True,exist_ok=True)
    count=0
    with zipfile.ZipFile(destination,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(project.rglob("*")):
            if not p.is_file():continue
            rel=p.relative_to(project)
            if any(item in {"__pycache__",".git",".venv","node_modules"} for item in rel.parts):continue
            if rel.name in {".env",".env.local",".DS_Store",".api_usage.lock"} or rel.suffix==".pyc":continue
            z.write(p,arcname=str(rel));count+=1
    digest=hashlib.sha256(destination.read_bytes()).hexdigest()
    return count,digest


def main(argv=None):
    parser=argparse.ArgumentParser(description="v0.3: local-first short-video director. No GitHub/ChatGPT needed at runtime.")
    sub=parser.add_subparsers(dest="command",required=True)
    prep=sub.add_parser("prepare",help="prepare job for already configured Codex, no API charges")
    prep.add_argument("--input",required=True);prep.add_argument("--out",required=True)
    run=sub.add_parser("run",help="automatic staged creative calls to compatible LLM API; billable, consent required")
    run.add_argument("--input",required=True);run.add_argument("--out",required=True)
    run.add_argument("--model",default=os.environ.get("AI_MODEL", DEFAULT_MODEL))
    run.add_argument("--base-url",default=os.environ.get("AI_API_BASE_URL", DEFAULT_URL))
    run.add_argument("--approve-model-cost",action="store_true")
    run.add_argument("--max-cost-cny",type=float,help="必须明确的本地估算预留预算上限，人民币；不是供应商账单承诺")
    run.add_argument("--input-cny-per-million",type=float,help="输入token每百万的保守人民币最高单价；DeepSeek官方模型默认高峰单价")
    run.add_argument("--output-cny-per-million",type=float,help="输出token每百万的保守人民币最高单价")
    run.add_argument("--max-calls",type=int,default=7,help="本任务最多发送几次LLM请求，默认7")
    run.add_argument("--max-retries",type=int,default=0,help="只有429和明确空/非法JSON才允许额外尝试0-2次；默认0")
    run.add_argument("--max-output-tokens",type=int,default=16384,help="每次响应最多的输出token")
    run.add_argument("--resume",action="store_true",help="reuse checkpoints; never overwrite finished phase")
    rev=sub.add_parser("review",help="validate and render offline HTML, no LLM call")
    rev.add_argument("--job",required=True)
    z=sub.add_parser("backup",help="export a portable ZIP; omits .env keys")
    z.add_argument("--project",default=str(ROOT));z.add_argument("--out",required=True)
    cs=sub.add_parser("cost-status",help="read local conservative budget ledger, offline")
    cs.add_argument("--job",required=True)
    sub.add_parser("doctor",help="explain local runtime state")
    args=parser.parse_args(argv)
    try:
        if args.command=="prepare":
            result=create_prepare(args.input,args.out)
            print("已准备Codex任务：",result/"CODEX_TASK.md")
            print("接下来让Codex在这个目录读取AGENTS.md及此任务文件；不会自动产生LLM费用。")
        elif args.command=="run":
            result=run_job(args)
            print("导演预演：",result/"index.html")
        elif args.command=="review":
            print("导演预演：",review_job(args.job))
        elif args.command=="backup":
            count,digest=backup(args.project,args.out)
            print(f"已备份 {count} 个文件；SHA256 {digest}")
        elif args.command=="cost-status":
            ledger=load(Path(args.job)/"api_usage.generated.json")
            reserved=sum(float(a['reserved_cny']) for a in ledger.get('attempts',[]))
            print(f"模型: {ledger['model']} / 已发送请求: {len(ledger['attempts'])} 次")
            print(f"本地最坏情况费用预留估算: ¥{reserved:.4f} / 自设上限 ¥{ledger['cap_cny']:.4f}")
            print("这是本地保守估算，不是 DeepSeek 官方结算单；超时/失败也继续占预算。")
        elif args.command=="doctor":
            print("Python:",sys.version.split()[0]," / 本地项目:",ROOT)
            print("ChatGPT/GitHub运行依赖：无；创意阶段需要现有Codex+模型，或兼容的LLM API")
            print("AI_API_KEY:","已提供(不会显示)" if os.environ.get("AI_API_KEY") else "未提供；可用prepare离线准备")
            print("Web预演、校验与备份都能在无网络时运行；LLM云端生成需要模型可连接")
        return 0
    except (DirectorError, BudgetError, RetryableLLMError, ValueError, OSError, json.JSONDecodeError, KeyError) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())