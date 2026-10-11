#!/usr/bin/env python3
"""Privacy-preserving offline article -> episode candidates -> storyboard draft.

No LLM, external API, payments or fabricated professional work. An article is
NOT a short-video script: proposals remain "editorial_review_required" until
the author approves what to keep, what to omit and any paraphrase. All extracted
candidate narration is verbatim from the article, with original offsets.

The new episode base feeds the EXISTING showrunner-led team DAG; this module
does NOT fake finished specialist deliverables or a final AI video package.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import re

import agent_team as team
import director

MAX_ARTICLE_CHARS = 250_000
MAX_EPISODES = 120
MAX_NARRATION_CHARS = 185
MAX_SEGMENT_CHARS = 26
MAX_SHOTS = 20
MAX_DURATION = 75
SPEECH_CHARS_PER_SECOND = 4.0

HEADING = re.compile(r"(?m)^\s{0,3}#{2,4}\s+(?:(\d{1,3})[.．、]\s*)?([^\n#]+?)\s*$")
CLAUSE = re.compile(r"[^。！？!?；;]+[。！？!?；;]?")
CLAIM_NUMBER = re.compile(r"\d+(?:[.,]\d+)*(?:\s*[%％]|\s*(?:岁|小时|分钟|例|人|倍|年|度))")
URL = re.compile(r"https?://[^\s<>）)]+")
FACT_CUE = re.compile(r"(?:研究|试验|法律|规定|数据|风险|比例|患病|统计|调查|证据)")
MEDICAL = re.compile(r"(?:医院|急诊|医生|近视|治疗|疫苗|心理|疾病|手术|阴囊|骨骼|抑郁|筛查)")
LEGAL = re.compile(r"(?:刑法|判决|法庭|劳动法|诉讼|公安机关|法条)")
FINANCE = re.compile(r"(?:股票|证券|银行|基金|投资|收益率|贷款)")
FIELDS = ("成本", "说人话", "收益", "证据等级", "来源", "备注")


@dataclass(frozen=True)
class Section:
    key: str
    title: str
    start: int
    end: int
    body: str
    numbered: bool


def _article(source):
    if not isinstance(source, str) or not source.strip():
        raise ValueError("ARTICLE_REQUIRED")
    if len(source) > MAX_ARTICLE_CHARS:
        raise ValueError("ARTICLE_TOO_LARGE")
    if "\0" in source:
        raise ValueError("ARTICLE_CONTAINS_NUL")
    return source


def _headings(source):
    """Only real Markdown headings outside fenced code count as section starts."""
    ranges = []
    fenced = False
    fence_char = None
    fence_count = 0
    offset = 0
    for line in source.splitlines(keepends=True):
        m_fence = re.match(r"^\s{0,3}(`{3,}|~{3,})(?:.*)$", line)
        if m_fence:
            token = m_fence.group(1)
            if not fenced:
                fenced, fence_char, fence_count = True, token[0], len(token)
            elif token[0] == fence_char and len(token) >= fence_count:
                fenced = False
        elif not fenced:
            m = HEADING.match(line.rstrip("\r\n"))
            if m:
                ranges.append((offset, offset + len(line), m.group(1), m.group(2).strip()))
        offset += len(line)
    return ranges


def split_article(source):
    """Return named topic boundaries with offsets into *exact original* source.

    Numbered third/fourth-level themes win over enclosing chapter headings.
    Unnumbered second/third-level headings are supported for ordinary notes.
    A plain text input becomes one episode candidate.
    """
    source = _article(source)
    heads = _headings(source)
    numbered = [x for x in heads if x[2] is not None]
    selected = numbered if numbered else [x for x in heads if x[3]]
    if len(selected) > MAX_EPISODES:
        raise ValueError("TOO_MANY_SECTIONS")
    if not selected:
        return [Section("EP01", "完整短文", 0, len(source), source, False)]
    numbers = [int(h[2]) for h in selected if h[2] is not None]
    if numbers and (len(set(numbers)) != len(numbers) or any(n <= 0 for n in numbers)):
        raise ValueError("DUPLICATE_OR_INVALID_SECTION_NUMBER")
    sections = []
    for i, (header_start, body_start, number, title) in enumerate(selected):
        end = selected[i + 1][0] if i + 1 < len(selected) else len(source)
        if number is not None:
            key = "EP" + str(int(number)).zfill(2)
        else:
            key = "EP" + str(i + 1).zfill(2)
        sections.append(Section(key, title, header_start, end,
                                source[body_start:end], number is not None))
    return sections


def _fields(section):
    """Recognize author-labelled bullet blocks; never mix source and inference."""
    text = section.body
    items = list(re.finditer(r"(?m)^\s*[-*]\s*(成本|说人话|收益|证据等级|来源|备注)\s*[：:]\s*", text))
    extracted = {}
    for i, match in enumerate(items):
        label = match.group(1)
        stop = items[i + 1].start() if i + 1 < len(items) else len(text)
        if label not in extracted:
            block = text[match.end():stop].strip()
            extracted[label] = block
    return extracted


def _risk(section):
    # Topic cue is tentative; risk = none does NOT certify material as harmless.
    content = section.title + " " + section.body[:1000]
    if MEDICAL.search(content):
        return "medical"
    if LEGAL.search(content):
        return "legal"
    if FINANCE.search(content):
        return "financial"
    return "none"


def episode_catalog(source):
    """Only metadata, title, byte-free source character positions, no raw text."""
    original = _article(source)
    result = []
    for s in split_article(original):
        fs = _fields(s)
        passage = fs.get("说人话") or ""
        result.append({
            "episode_id": s.key, "title": s.title,
            "source_start": s.start, "source_end": s.end,
            "candidate_excerpt_present": bool(passage),
            "candidate_excerpt_chars": len(passage),
            "risk_domain_candidate": _risk(s),
            "editorial_decision": "review_required",
            "finished_video": False, "specialists_executed": False,
        })
    return {"kind": "article_episode_catalog", "version": 1,
            "source_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest(),
            "section_count": len(result), "episodes": result,
            "automatic_series_split_is_proposal": True,
            "approved_for_publication": False, "external_calls": 0}


def _source_excerpt(section):
    items = _fields(section)
    if items.get("说人话"):
        # Strip no substantive characters: preserve unmodified utterance body.
        return items["说人话"], "说人话"
    # For ordinary unstructured script, use body, not the heading.
    if not re.search(r"(?m)^\s*[-*]\s*(?:成本|收益|来源|备注)\s*[：:]", section.body):
        return section.body.strip(), "unstructured_body"
    return "", "missing_spoken_summary"


def _chunks(text):
    """Preserve concatenation verbatim, splitting at natural punctuation."""
    candidates = []
    for m in CLAUSE.finditer(text):
        sentence = m.group()
        if not sentence:
            continue
        # Long clauses split on commas when possible; last-resort split at a
        # fixed character boundary with an explicit warning for human revision.
        buffer = ""
        for part in re.findall(r"[^，,]+[，,]?", sentence):
            if len(buffer) + len(part) <= MAX_SEGMENT_CHARS:
                buffer += part
            else:
                if buffer:
                    candidates.append(buffer)
                    buffer = ""
                while len(part) > MAX_SEGMENT_CHARS:
                    candidates.append(part[:MAX_SEGMENT_CHARS])
                    part = part[MAX_SEGMENT_CHARS:]
                buffer = part
        if buffer:
            candidates.append(buffer)
    return candidates


def _candidate_segments(raw):
    # Newline normalization affects matching; keep only paragraphs wholly
    # inside source. No silent whitespace rewrites or translation.
    paragraph = raw.strip()
    if not paragraph:
        return []
    blocks = re.findall(r"\S(?:[^\n]*\S)?", paragraph)
    return [chunk for block in blocks for chunk in _chunks(block)]


def _wording(segment):
    return {"status": "needs_review", "claim_quote": segment,
            "not_externally_verified": True}


def _shot_template(sid, index, start, duration, utterance, claim_id, *, numeric):
    mode = "data_graphic" if numeric else "text_card"
    return {
        "id": sid, "start": start, "duration": duration,
        "purpose": "source_quote_review_required",
        "narration": utterance, "visual_type": mode,
        "claim_ids": [claim_id], "character_ids": [], "scene_id": "LOC01",
        "visual": "待导演具体设计；仅提出原文引文字幕卡或待审数据图形，不是成片画面",
        "action": {"start": "无真人动作", "action": "待动作导演审核",
                   "micro_action": "无", "reaction": "无", "end": "无"},
        "camera": {"shot_size": "postproduction", "angle": "n/a",
                   "lens": "n/a", "movement": "待设计", "composition": "9:16 安全区"},
        "art": {"lighting": "无真实摄影", "palette": "待统一",
                "set_props": "文字或数据图形"},
        "graphics": {"type": mode, "text": "待审核的源文字幕",
                     "animation": "待剪辑指导", "placement": "9:16 safe area"},
        "audio": {"music": "待声音部门设计", "sfx": "无",
                  "voice": "原文候选旁白，未经审核", "pause_before": 0},
        "subtitles": {"text": utterance, "style": "待定",
                      "placement": "中上部安全区域"},
        "transition": "hard_cut" if index else "fade_in",
        "continuity": "待专业部门设计"
    }


def prepare_episode(source, episode_id="EP01"):
    """Produce a NON-APPROVED source-aligned director v0.1 draft + team state.

    The original source remains caller-owned, never written to disk or remote.
    Episode selection is deterministic from numbered Markdown headings; do not
    equate one numbered topic with one optimal finished video.
    """
    source = _article(source)
    sections = split_article(source)
    chosen = next((s for s in sections if s.key == episode_id), None)
    if chosen is None:
        raise ValueError("UNKNOWN_EPISODE_ID")
    raw, strategy = _source_excerpt(chosen)
    chunks = _candidate_segments(raw)
    omissions = []
    chosen_chunks = []
    total_chars = 0
    timeline = 0
    limits = []
    for i, fragment in enumerate(chunks):
        duration = max(3, math.ceil(len(fragment) / SPEECH_CHARS_PER_SECOND))
        if (len(chosen_chunks) == MAX_SHOTS or
                total_chars + len(fragment) > MAX_NARRATION_CHARS or
                timeline + duration > MAX_DURATION):
            omissions.append({
                "text": "".join(chunks[i:]), "reason":
                "preview length/shot limit; author and script editor must review"})
            break
        chosen_chunks.append((fragment, duration))
        total_chars += len(fragment)
        timeline += duration
    warnings = ["AUTHOR_APPROVAL_REQUIRED", "SOURCE_CLAIMS_UNVERIFIED",
                "SHOT_VISUALS_ARE_POST_PLACEHOLDERS_NOT_AI_CREATION"]
    if strategy == "missing_spoken_summary":
        warnings.append("NO_SPOKEN_SUMMARY: MANUAL_SCRIPT_EDIT_REQUIRED")
    if not chosen_chunks:
        warnings.append("NO_NARRATION_SELECTED")
    if timeline < 35:
        warnings.append("UNDER_35_SECONDS: EXPANSION_OR_PACING_REVIEW")
    if len(chunks) > len(chosen_chunks):
        warnings.append("NARRATION_ABRIDGED_WITH_EXPLICIT_OMISSIONS")
    if any(len(c) == MAX_SEGMENT_CHARS for c, _ in chosen_chunks):
        warnings.append("CLAUSE_SPLIT_MAY_REQUIRE_EDITORIAL_REWRITE")

    evidence = _fields(chosen).get("来源", "")
    links = [m.group().rstrip(".,;") for m in URL.finditer(evidence)]
    excerpt_offsets = []
    cursor = chosen.start
    for fragment, duration in chosen_chunks:
        at = source.find(fragment, cursor, chosen.end)
        if at < 0:
            # A normalization/segmentation change is a hard error; never
            # claim provenance to text that cannot be found in original.
            raise ValueError("SOURCE_EXCERPT_NOT_VERBATIM")
        excerpt_offsets.append((at, at + len(fragment)))
        cursor = at + len(fragment)
    claims = []
    shots = []
    position = 0
    for i, ((fragment, duration), (start, end)) in enumerate(
            zip(chosen_chunks, excerpt_offsets), 1):
        cid, sid = "C" + str(i).zfill(2), "S" + str(i).zfill(2)
        claims.append({
            "id": cid, "source_quote": fragment, "video_wording": fragment,
            "status": "needs_review", "evidence_url": "",
            "caution": "未经独立事实核验；来源指向原稿，出处须人工核查"
        })
        shots.append(_shot_template(sid, i-1, position, duration, fragment,
                                    cid, numeric=bool(
                                        CLAIM_NUMBER.search(fragment) or
                                        FACT_CUE.search(fragment))))
        position += duration
    # No statement of factual verification. Source quotation is not sufficient
    # evidence and original article source URLs must be checked independently.
    plan = {
        "schema_version": "0.1", "title": chosen.title,
        "platform": "douyin", "aspect_ratio": "9:16",
        "duration": position, "risk_domain": _risk(chosen),
        "core_message": chosen.title, "audience": "待总导演确定",
        "editorial": {"hook": "待剧本编辑设计；不得悄悄改写原文",
                      "narration_script": "".join(x[0] for x in chosen_chunks),
                      "omissions": omissions +
                      ([{"text": "原文其他资料段落：成本、收益、来源、备注等",
                         "reason": "未纳入候选旁白；保留为上下文及核实材料"}]
                       if strategy == "说人话" else [])},
        "claims": claims,
        "visual_bible": {"style": "专业视觉风格待总导演定义",
                         "palette": "待确定", "lighting": "待确定",
                         "typography": "准确文字必须后期添加",
                         "avoid": "不编造医疗效果、判决和数据"},
        "characters": [],
        "scenes": [{"id": "LOC01", "description":
                    "纯后期图卡占位，待摄影美术与总导演设计"}],
        "shots": shots,
        "production": {"voice": "候选原文旁白，需要人工审批",
                       "music_license_check": True,
                       "asset_license_check": True,
                       "publishing_status": "review_required"},
    }
    errors, issues = director.validate(plan) if shots else (["NO_SHOTS"], [])
    if errors:
        # Fail rather than mislabel a malformed plan as a usable production
        # base. Unknown/empty source still has a catalog record.
        return {"kind": "episode_intake_result",
                "episode_id": episode_id,
                "status": "needs_script_editor",
                "plan": None, "team": None,
                "warnings": warnings + errors,
                "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                "section_source_span": [chosen.start, chosen.end],
                "source_evidence_urls_unverified": links,
                "no_api_calls": True, "private_source_persisted": False}
    state = team.start(plan, source_text=source)
    return {
        "kind": "episode_intake_result", "episode_id": episode_id,
        "status": "editorial_review_required",
        "plan": plan, "team": state,
        "source_sha256": state["source_digest"],
        "section_source_span": [chosen.start, chosen.end],
        "shot_source_spans": [
            {"shot_id": shots[i]["id"], "source_span": list(p)}
            for i, p in enumerate(excerpt_offsets)
        ],
        "source_evidence_urls_unverified": links,
        "warnings": list(dict.fromkeys(warnings + issues)),
        "review": {"narration_approved": False,
                   "omissions_approved": False,
                   "data_claims_verified": False,
                   "visual_directing_complete": False,
                   "ready_for_video_model": False,
                   "paid_model_authorized": False},
        "no_api_calls": True, "private_source_persisted": False,
    }


def prepare_first_department(source, episode_id="EP01"):
    """Offline first-department contract, keeping private prompt in memory.

    A "ready task" is NOT proof that an AI actually did that task.
    """
    result = prepare_episode(source, episode_id)
    if result["team"] is None:
        return result, None
    return result, team.packet(result["team"], "director_brief")
