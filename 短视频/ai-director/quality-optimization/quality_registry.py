#!/usr/bin/env python3
"""Quality issue registry: strict evidence closure and synchronized readable board.

Only offline public metadata. No source text, model calls or private media.
The legacy AUD-xxx technical registry remains independently authoritative.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "QUALITY_ISSUES.json"
BOARD = ROOT / "QUALITY_ISSUES.md"
STAGES = {"now_screenwriter", "now_director", "future_dept"}
STATUSES = {"confirmed_open", "partially_addressed", "audit_pending",
            "in_progress", "blocked_external", "complete"}
PRIORITIES = {"P0", "P1", "P2", "P3"}
FIELDS = {
    "id", "stage", "department", "priority", "status", "title",
    "observed_in", "problem", "root_cause", "solution", "acceptance",
    "ai_video_constraint", "depends_on", "legacy_links", "owner", "opened_on",
    "evidence", "history",
}
EVIDENCE = {"implementation_pr", "commit_sha", "automated_test",
            "independent_review", "media_validation", "closure_note", "closed_on"}
GH = re.compile(r"https://github\.com/pyzz58/gpt-recommendations/(issues|pull)/\d+")
SHA = re.compile(r"[0-9a-f]{40}")
IDENT = re.compile(r"QO-(W|D|F)\d{2}")
BASELINE_IDS = frozenset(
    [f"QO-W{i:02d}" for i in range(1, 12)] +
    [f"QO-D{i:02d}" for i in range(1, 16)] +
    [f"QO-F{i:02d}" for i in range(1, 11)])


class QualityLedgerError(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise QualityLedgerError(code)


def valid_date(value):
    try:
        return isinstance(value, str) and date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def validate(data):
    require(isinstance(data, dict) and
            data.get("registry_version") == "2.0-quality" and
            data.get("canonical_registry") is True and
            data.get("world_class_is_target_not_status") is True and
            data.get("api_calls_authorized") is False and
            data.get("user_source_publishing_authorized") is False and
            data.get("future_departments_registered") is True and
            data.get("phase_focus") == ["now_screenwriter", "now_director"],
            "QUALITY_ROOT_POLICY_CHANGED")
    items = data.get("items")
    require(isinstance(items, list) and len(items) >= 25, "QUALITY_MISSING_REGISTER")
    require(isinstance(data.get("reference_sources"), list) and
            len(data["reference_sources"]) >= 4 and
            all(isinstance(x, dict) and isinstance(x.get("topic"), str) and
                x["topic"] and isinstance(x.get("url"), str) and
                x["url"].startswith("https://") for x in data["reference_sources"]),
            "QUALITY_MISSING_PROFESSIONAL_SOURCES")
    ids = set()
    for item in items:
        require(isinstance(item, dict) and set(item) == FIELDS, "QUALITY_FIELDS")
        ident = item["id"]
        require(isinstance(ident, str) and IDENT.fullmatch(ident) and
                ident not in ids, "QUALITY_DUPLICATE_OR_INVALID_ID")
        ids.add(ident)
        require(item["priority"] in PRIORITIES and item["stage"] in STAGES and
                item["status"] in STATUSES and
                isinstance(item["department"], str) and
                item["department"] == item["owner"] and valid_date(item["opened_on"]),
                "QUALITY_STATUS_OR_OWNER")
        if ident.startswith("QO-W"):
            require(item["stage"] == "now_screenwriter" and
                    item["department"] == "screenwriter", "QUALITY_WRITER_OWNERSHIP")
        if ident.startswith("QO-D"):
            require(item["stage"] == "now_director" and
                    item["department"] == "director", "QUALITY_DIRECTOR_OWNERSHIP")
        if ident.startswith("QO-F"):
            require(item["stage"] == "future_dept", "QUALITY_FUTURE_STAGE")
        if item["stage"] == "future_dept" and item["status"] != "audit_pending":
            require(item["evidence"].get("independent_review"),
                    "QUALITY_FUTURE_NEEDS_PROFESSIONAL_AUDIT")
        for field in ("title", "observed_in", "problem", "root_cause",
                      "solution", "acceptance", "ai_video_constraint"):
            val = item[field]
            require(isinstance(val, str) and len(val.strip()) >=
                    (5 if field == "title" else 12), "QUALITY_UNACTIONABLE_ISSUE")
        deps, links = item["depends_on"], item["legacy_links"]
        require(isinstance(deps, list) and len(set(deps)) == len(deps) and
                all(isinstance(x, str) and IDENT.fullmatch(x) and x != ident
                    for x in deps), "QUALITY_DEPENDENCY_INVALID")
        require(isinstance(links, list) and len(set(links)) == len(links) and
                all(isinstance(x, str) and GH.fullmatch(x) for x in links),
                "QUALITY_LINK_INVALID")
        proof = item["evidence"]
        require(isinstance(proof, dict) and set(proof) == EVIDENCE and
                all(isinstance(x, str) for x in proof.values()),
                "QUALITY_EVIDENCE_SHAPE")
        history = item["history"]
        require(isinstance(history, list) and len(history) >= 1 and
                all(isinstance(e, dict) and set(e) == {
                    "date", "status", "note", "evidence_ref"
                } and valid_date(e["date"]) and e["status"] in STATUSES and
                isinstance(e["note"], str) and len(e["note"]) >= 20 and
                isinstance(e["evidence_ref"], str) and
                (not e["evidence_ref"] or GH.fullmatch(e["evidence_ref"]))
                for e in history) and
                history[-1]["status"] == item["status"],
                "QUALITY_STATUS_HISTORY_INVALID")
        if item["status"] == "complete":
            require(GH.fullmatch(history[-1]["evidence_ref"]) is not None,
                    "QUALITY_COMPLETION_EVENT_MISSING")
            require(GH.fullmatch(proof["implementation_pr"]) is not None and
                    SHA.fullmatch(proof["commit_sha"]) is not None and
                    len(proof["automated_test"]) >= 15 and
                    len(proof["independent_review"]) >= 15 and
                    len(proof["closure_note"]) >= 30 and
                    valid_date(proof["closed_on"]),
                    "QUALITY_FALSE_DONE_WITHOUT_EVIDENCE")
            if item["department"] in {"director", "acting", "cinematography_art",
                                      "sound_voice", "editing_animation",
                                      "ai_technical", "media_qc",
                                      "postdelivery", "api_privacy_cost",
                                      "continuity_qa", "product_workflow"}:
                require(len(proof["media_validation"]) >= 15,
                        "QUALITY_MEDIA_DEPARTMENT_NEEDS_REAL_MEDIA")
        else:
            require(proof["closed_on"] == "" and proof["closure_note"] == "",
                    "QUALITY_OPEN_CANNOT_HAVE_CLOSURE")
    require(BASELINE_IDS <= ids, "QUALITY_EXISTING_ID_REMOVED")
    for item in items:
        require(set(item["depends_on"]) <= ids, "QUALITY_UNKNOWN_DEPENDENCY")
    by_id = {item["id"]: item for item in items}
    for item in items:
        if item["status"] == "complete":
            require(all(by_id[parent]["status"] == "complete"
                        for parent in item["depends_on"]),
                    "QUALITY_DEPENDENCY_NOT_CLOSED")
    graph = {item["id"]: item["depends_on"] for item in items}
    visiting, visited = set(), set()

    def visit(node):
        if node in visited:
            return
        require(node not in visiting, "QUALITY_CYCLIC_DEPENDENCY")
        visiting.add(node)
        for parent in graph[node]:
            visit(parent)
        visiting.remove(node)
        visited.add(node)
    for node in graph:
        visit(node)
    return {
        "total": len(items), "stages": dict(Counter(x["stage"] for x in items)),
        "statuses": dict(Counter(x["status"] for x in items)),
        "complete": sum(x["status"] == "complete" for x in items),
        "real_media_or_world_class_proven": False, "new_paid_requests": 0,
    }


def render(data):
    summary = validate(data)
    lines = [
        "# AI 视频导演｜质量优化问题清单", "",
        "> 本文件根据 QUALITY_ISSUES.json 自动生成。勿直接修改状态。",
        "> QO 管理专业创作及 AI 视频质量；现有 AUD-xxx 技术安全问题仍需独立跟踪。",
        "",
        "## 总览", "",
        f"- 登记 {summary['total']} 项；编剧 {summary['stages'].get('now_screenwriter',0)} 项，总导演 {summary['stages'].get('now_director',0)} 项，其它部门 {summary['stages'].get('future_dept',0)} 项。",
        f"- 全部验收完成 {summary['complete']} 项；没有真实独立验证不能自称达到一流水准。",
        "- 现阶段只修编剧及总导演；其它部门保持后续审计状态。",
        "",
        "| 编号 | 岗位 | 优先级 | 状态 | 问题 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in data["items"]:
        lines.append(f"| {item['id']} | {item['department']} | {item['priority']} | {item['status']} | {item['title']} |")
    lines.extend(["", "## 每个问题的根因、解法、验收与证据", ""])
    for item in data["items"]:
        proof = item["evidence"]
        lines.extend([
            f"### {item['id']} · {item['title']}", "",
            f"- 状态：{item['status']}；优先级：{item['priority']}；阶段：{item['stage']}；负责人：{item['owner']}",
            f"- 发现位置：{item['observed_in']}",
            f"- 问题：{item['problem']}",
            f"- 根因：{item['root_cause']}",
            f"- 方案：{item['solution']}",
            f"- 完成验收：{item['acceptance']}",
            f"- AI 视频适配：{item['ai_video_constraint']}",
            f"- 依赖：{', '.join(item['depends_on']) if item['depends_on'] else '无'}",
            f"- 历史问题：{', '.join(item['legacy_links']) if item['legacy_links'] else '无'}",
            f"- 修复证据：PR {proof['implementation_pr'] or '未提供'}；回归 {proof['automated_test'] or '未完成'}；独立审核 {proof['independent_review'] or '未完成'}；真实媒体 {proof['media_validation'] or '未完成或不适用'}",
            f"- 状态历史：{' → '.join(h['date'] + ':' + h['status'] for h in item['history'])}",
            "",
        ])
    lines.extend([
        "## 修复一项就更新一项", "",
        "复现缺陷 → 有针对性的解决方案 → 合成反例和回归测试 →",
        "独立专业评审 → 所需的真实媒体/授权人工验收 →",
        "补充证据 → 将对应 JSON 状态改为 complete → 重新生成本文件并通过 CI。",
        "",
        "代码绿色仅证明结构与回归；不能代表剧本/导演艺术质量、一流等级或真实成片已验证。",
        "不公开用户稿件、不自动发付费请求，不绕过旧 AUD 安全门禁。",
        "",
    ])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-board", action="store_true")
    parser.add_argument("--render-board", action="store_true")
    args = parser.parse_args(argv)
    data = json.loads(SOURCE.read_text("utf-8"))
    summary = validate(data)
    if args.render_board:
        BOARD.write_text(render(data), "utf-8")
    if args.check_board:
        require(BOARD.exists() and BOARD.read_text("utf-8") == render(data),
                "QUALITY_BOARD_OUT_OF_SYNC")
    print(json.dumps(summary, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
