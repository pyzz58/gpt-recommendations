"""Traceability for the CRA engineering baseline; no clinical data processing."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from execution_plan import render_execution_views, validate_execution

VIEW_PATHS = ("theory/REQUIREMENTS.md", "traceability/INDEX.md", "plan/WORK_PLAN.md", "architecture/QUALITY.md")


def fingerprint(value: dict) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_json(root: Path, relative: str):
    return json.loads((root / relative).read_text(encoding="utf-8"))


def render_views(root: Path) -> dict[str, str]:
    requirements = read_json(root, "theory/requirements.json")["requirements"]
    modules = read_json(root, "traceability/modules.json")["modules"]
    tasks = read_json(root, "plan/tasks.json")["tasks"]
    scenarios = read_json(root, "traceability/scenarios.json")["scenarios"]
    module_map = {m["id"]: m for m in modules}
    parts = ["# 固定编号理论清单", "", "开发规范源为requirements.json；本页由tools/render_views.py生成。修订理论时保留编号、提高revision并同步技术复核。", ""]
    for r in requirements:
        parts += [
            f'<a id="{r["id"].lower()}"></a>',
            f'## {r["id"]} {r["title"]}', "",
            f'- 修订：{r["revision"]}；状态：{r["status"]}；来源类型：{r["origin"]}',
            f'- 对应模块：{"、".join(r["modules"])}',
            f'- 来源位置：{r["source_heading"]}', "", r["statement"], "",
            "验收：" + "；".join(r["acceptance"]), "",
        ]
    requirement_view = "\n".join(parts).rstrip() + "\n"
    parts = [
        "# 理论—技术—开发—验收对照", "",
        "每条理论可对应多个模块。模块文件是具体技术入口，任务和场景编号可在相应工作计划及质量页找到。此表只表示设计覆盖，不表示功能已经实现。", "",
        "| 理论 | 对应技术模块 | 开发任务 | 验收场景 |",
        "| --- | --- | --- | --- |",
    ]
    for r in requirements:
        links = "、".join(f'[{mid}](../{module_map[mid]["design_path"]})' for mid in r["modules"])
        task_ids = [t["id"] for t in tasks if r["id"] in t["requirement_ids"]]
        scenario_ids = [s["id"] for s in scenarios if r["id"] in s["requirement_ids"]]
        parts.append(f'| [{r["id"]} {r["title"]}](../theory/REQUIREMENTS.md#{r["id"].lower()}) | {links} | {"、".join(task_ids)} | {"、".join(scenario_ids)} |')
    index_view = "\n".join(parts) + "\n"
    parts = [
        "# 第一版开发工作计划", "",
        "状态以实际代码和证据为准：planned=待实现，prepared=基线已备待云端验证，verified=所列工作包验收已完成。W00通过不等于整个系统完成。", "",
        "执行顺序按依赖逐项推进；不承诺未经测量的工期。W14是用户已允许分期的照片识别V1B，W15需获准部署环境。", "",
        "| 工作包 | 内容 | 前置 | 模块 | 状态 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for t in tasks:
        parts.append(f'| {t["id"]} | {t["title"]} | {"、".join(t["depends_on"]) or "无"} | {"、".join(t["module_ids"])} | {t["status"]} |')
    parts.append("")
    for t in tasks:
        parts += [f'## {t["id"]} {t["title"]}', "", "验收：" + t["acceptance"], "", "对应理论：" + "、".join(t["requirement_ids"]), ""]
        for evidence in t.get("evidence", []):
            parts += ["实际证据：" + evidence, ""]
    plan_view = "\n".join(parts).rstrip() + "\n"
    parts = [
        "# 质量验收与场景", "",
        "以下为端到端验收计划。状态planned表示尚未完成该完整场景，即使已有小范围核心单元测试也不能称整个场景通过。", "",
        "发布前同时记录关键遗漏、误配、误报、错误关闭及查找、录入、复核、报告和返工总时间。阈值按具体用途和风险设定，不用一个平均准确率替代。", "",
        "工程检查、合成案例和获授权真实试用分开；缺模型/资料/部署授权时不能宣称完整临床试用就绪。", "",
        "| 场景 | 对应理论 | 期望结果 | 状态 |",
        "| --- | --- | --- | --- |",
    ]
    for s in scenarios:
        parts.append(f'| {s["id"]} {s["title"]} | {"、".join(s["requirement_ids"])} | {s["expected"]} | {s["status"]} |')
    views = dict(zip(VIEW_PATHS, [requirement_view, index_view, plan_view, "\n".join(parts) + "\n"]))
    views.update(render_execution_views(tasks, module_map))
    return views


def safe_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("path outside project: " + relative)
    return path


def unique_map(items: list[dict], label: str, errors: list[str]) -> dict:
    result = {}
    for item in items:
        key = item["id"]
        if key in result:
            errors.append(f"duplicate {label}: {key}")
        result[key] = item
    return result


def revision_errors(current: dict, previous: dict) -> list[str]:
    errors = []
    for rid in previous.keys() - current.keys():
        errors.append(f"{rid}: IDs cannot be removed; retain a retired record with its reason")
    for rid in current.keys() & previous.keys():
        if current[rid] != previous[rid] and current[rid]["revision"] <= previous[rid]["revision"]:
            errors.append(f"{rid}: changed theory must increase revision")
    return errors


def git_text(root: Path, ref: str, relative: str) -> str | None:
    process = subprocess.run(
        ["git", "show", f"{ref}:cra system/{relative}"],
        cwd=root, text=True, encoding="utf-8", capture_output=True, check=False,
    )
    return process.stdout if process.returncode == 0 else None


def validate(root: Path, base_ref: str | None = None, check_views: bool = True) -> list[str]:
    errors: list[str] = []
    requirements = read_json(root, "theory/requirements.json")["requirements"]
    modules = read_json(root, "traceability/modules.json")["modules"]
    tasks = read_json(root, "plan/tasks.json")["tasks"]
    scenarios = read_json(root, "traceability/scenarios.json")["scenarios"]
    bindings = read_json(root, "traceability/bindings.json")["bindings"]
    records = [(path, json.loads(path.read_text(encoding="utf-8"))) for path in sorted((root / "changes").glob("CR-*.json"))]
    rmap = unique_map(requirements, "requirement", errors)
    mmap = unique_map(modules, "module", errors)
    tmap = unique_map(tasks, "task", errors)
    smap = unique_map(scenarios, "scenario", errors)
    errors.extend(validate_execution(root, tasks, mmap, rmap, smap))
    expected = {(r["id"], mid) for r in requirements for mid in r["modules"]}
    seen = set()
    for b in bindings:
        key = (b["requirement_id"], b["module_id"])
        if key in seen:
            errors.append(f"duplicate binding: {key}")
        seen.add(key)
        r = rmap.get(key[0])
        if not r or key[1] not in mmap or key not in expected:
            errors.append(f"unknown binding: {key}")
        elif b["reviewed_revision"] != r["revision"] or b["reviewed_digest"] != fingerprint(r):
            errors.append(f"{key[0]} -> {key[1]}: stale technical review")
    for rid, mid in sorted(expected - seen):
        errors.append(f"{rid} -> {mid}: missing technical binding")
    for r in requirements:
        rid = r["id"]
        if not re.fullmatch(r"CRA-R\d{3}", rid) or not r["modules"] or r["revision"] < 1:
            errors.append(f"invalid requirement: {rid}")
        if not r.get("statement") or not r.get("acceptance") or not r.get("source_heading"):
            errors.append(f"{rid}: missing meaning, acceptance or source")
        if r["status"] not in ("active", "retired") or (r["status"] == "retired" and not r.get("retirement_reason")):
            errors.append(f"{rid}: invalid retirement/status")
        if not any(rid in t["requirement_ids"] for t in tasks):
            errors.append(f"{rid}: no development task")
        if not any(rid in s["requirement_ids"] for s in scenarios):
            errors.append(f"{rid}: no acceptance scenario")
        for mid in r["modules"]:
            matched = [
                record for _, record in records
                if record.get("requirement_fingerprints", {}).get(rid) == fingerprint(r)
                and mid in record.get("module_reviews", {})
            ]
            if not matched:
                errors.append(f"{rid} -> {mid}: no matching change record")
            for record in matched:
                review = record["module_reviews"][mid]
                if review.get("decision") not in ("updated", "no_technical_change") or len(review.get("reason", "")) < 10:
                    errors.append(f"{record['id']} {mid}: missing impact decision/reason")
                for relative in review.get("paths", []):
                    if not safe_path(root, relative).is_file():
                        errors.append(f"{record['id']} {mid}: missing review path {relative}")
    for m in modules:
        mid = m["id"]
        path = safe_path(root, m["design_path"])
        if not path.is_file():
            errors.append(f"{mid}: missing design path {m['design_path']}")
        if set(m["requirement_ids"]) != {r["id"] for r in requirements if mid in r["modules"]}:
            errors.append(f"{mid}: reverse theory mapping mismatch")
        if set(m["task_ids"]) != {t["id"] for t in tasks if mid in t["module_ids"]}:
            errors.append(f"{mid}: reverse task mapping mismatch")
        for sid in m["scenarios"]:
            if sid not in smap:
                errors.append(f"{mid}: unknown scenario {sid}")
    for collection, known, dependency_key in [(modules, mmap, "depends_on"), (tasks, tmap, "depends_on")]:
        visiting, done = set(), set()
        def visit(key):
            if key in visiting:
                errors.append("dependency cycle: " + key)
                return
            if key in done:
                return
            visiting.add(key)
            for dep in known[key][dependency_key]:
                if dep not in known:
                    errors.append(f"{key}: unknown dependency {dep}")
                else:
                    visit(dep)
            visiting.remove(key)
            done.add(key)
        for item in collection:
            visit(item["id"])
    for t in tasks:
        for rid in t["requirement_ids"]:
            if rid not in rmap:
                errors.append(f"{t['id']}: unknown requirement {rid}")
        for mid in t["module_ids"]:
            if mid not in mmap:
                errors.append(f"{t['id']}: unknown module {mid}")
        if t["status"] not in ("planned", "prepared", "in_progress", "blocked", "verified"):
            errors.append(f"{t['id']}: invalid task status")
        if t["status"] == "verified" and not t.get("evidence"):
            errors.append(f"{t['id']}: verified task needs actual evidence")
    for s in scenarios:
        for rid in s["requirement_ids"]:
            if rid not in rmap:
                errors.append(f"{s['id']}: unknown requirement {rid}")
        if s["status"] == "verified" and not s.get("evidence_paths"):
            errors.append(f"{s['id']}: verified scenario needs evidence")
    if check_views:
        for relative, expected_text in render_views(root).items():
            path = root / relative
            if not path.is_file() or path.read_text(encoding="utf-8") != expected_text:
                errors.append(f"{relative}: generated view is stale; run tools/render_views.py --write")
    if base_ref and base_ref != "0" * 40:
        if not re.fullmatch(r"[0-9a-f]{40}", base_ref):
            errors.append("base ref must be an exact lowercase 40-character commit SHA")
            return errors
        commit = subprocess.run(["git", "cat-file", "-e", base_ref + "^{commit}"], cwd=root, capture_output=True)
        if commit.returncode:
            errors.append("base commit unavailable; fetch complete history")
            return errors
        old_text = git_text(root, base_ref, "theory/requirements.json")
        if old_text is not None:
            previous = {r["id"]: r for r in json.loads(old_text)["requirements"]}
            errors.extend(revision_errors(rmap, previous))
            for path, record in records:
                old = git_text(root, base_ref, path.relative_to(root).as_posix())
                if old is not None and json.loads(old) != record:
                    errors.append(f"{record['id']}: change records are immutable; add a new CR")
            changed = [r for r in requirements if previous.get(r["id"]) != r]
            for r in changed:
                for mid in r["modules"]:
                    matched = [record for path, record in records
                               if git_text(root, base_ref, path.relative_to(root).as_posix()) is None
                               and record.get("requirement_fingerprints", {}).get(r["id"]) == fingerprint(r)
                               and mid in record.get("module_reviews", {})]
                    if not matched:
                        errors.append(f"{r['id']} -> {mid}: new change record required")
                    for record in matched:
                        review = record["module_reviews"][mid]
                        if review["decision"] == "updated":
                            acceptable = [
                                p for p in review.get("paths", [])
                                if p.startswith("architecture/") or p.startswith(mmap[mid]["planned_code_path"])
                            ]
                            if not any(git_text(root, base_ref, p) != (root / p).read_text(encoding="utf-8") for p in acceptable):
                                errors.append(f"{r['id']} -> {mid}: claimed updated but no technical file changed")
            old_baseline = git_text(root, base_ref, "theory/BASELINE.md")
            if old_baseline is not None and old_baseline != (root / "theory/BASELINE.md").read_text(encoding="utf-8") and not changed:
                if not any(record.get("documentation_only_reason") and git_text(root, base_ref, path.relative_to(root).as_posix()) is None for path, record in records):
                    errors.append("theory/BASELINE.md changed without theory items or a documentation-only change reason")
    return errors
