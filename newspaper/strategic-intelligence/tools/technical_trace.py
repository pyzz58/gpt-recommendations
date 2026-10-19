"""Deterministic theory/design traceability; never rewrites or approves design prose."""
from __future__ import annotations

import hashlib
import json
import re

SPEC = "CANONICAL_SYSTEM_SPEC_V5.md"
JSON_OUTPUT = "technical_trace.json"
TEXT_OUTPUT = "TECHNICAL_TRACE.md"
IDS = {*(f"T{i:02d}" for i in range(1, 14)), *(f"R{i:02d}" for i in range(1, 9))}
HEX = re.compile(r"[0-9a-f]{64}\Z")


def sha(value):
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def fenced_block(text, name):
    begin, end = f"<!-- BEGIN {name} -->", f"<!-- END {name} -->"
    if text.count(begin) != 1 or text.count(end) != 1:
        raise ValueError(f"Missing or duplicate canonical block: {name}")
    a, b = text.index(begin) + len(begin), text.index(end)
    if a >= b:
        raise ValueError(f"Invalid canonical block order: {name}")
    body = text[a:b].strip()
    if not body.startswith("```json\n") or not body.endswith("\n```"):
        raise ValueError(f"{name} must be a fenced JSON object")
    return json.loads(body[8:-4])


def units(text):
    # Keep the actual issue-governance policy; suggestions/history are not rules.
    start, end = "<!-- BEGIN ISSUE_LEDGER -->", "<!-- END ISSUE_LEDGER -->"
    if text.count(start) != 1 or text.count(end) != 1 or text.index(start) >= text.index(end):
        raise ValueError("Invalid issue ledger while resolving technical sources")
    a, b = text.index(start), text.index(end) + len(end)
    ledger = text[a:b]
    policy_anchor = '<a id="th-23-2-1"></a>\n'
    if ledger.count(policy_anchor) != 1:
        raise ValueError("Missing/duplicate issue governance policy anchor")
    policy_start = ledger.index(policy_anchor)
    policy_heading = re.search(r"^#### [^\n]+$", ledger[policy_start:], re.M)
    if not policy_heading:
        raise ValueError("Missing issue governance policy heading")
    following = re.search(r"^#### [^\n]+$", ledger[policy_start + policy_heading.end():], re.M)
    if not following:
        raise ValueError("Missing boundary after issue governance policy")
    policy_end = policy_start + policy_heading.end() + following.start()
    policy = re.sub(r'<a id="[^"]+"></a>\n$', '', ledger[policy_start:policy_end])
    clean = text[:a] + policy + "<!-- ISSUE_RECORDS: non-normative records excluded -->\n" + text[b:]
    headings = list(re.finditer(r"^(#{2,4}) (\d+(?:\.\d+)*)(?:\.)? ([^\n]+)$", clean, re.M))
    located = []
    for h in headings:
        prefix = clean[max(0, h.start() - 180):h.start()]
        anchor = re.search(r'<a id="((?:th|tech)-[a-z0-9-]+)"></a>\n$', prefix)
        located.append((h, anchor[1] if anchor else None, h.start() - len(anchor[0]) if anchor else h.start()))
    result = {}
    for i, (h, anchor, boundary) in enumerate(located):
        if not anchor:
            continue
        if anchor in result or clean.count(f'<a id="{anchor}"></a>') != 1:
            raise ValueError(f"Duplicate technical/theory anchor: {anchor}")
        stop = len(clean)
        for next_h, _, next_boundary in located[i + 1:]:
            if len(next_h[1]) <= len(h[1]):
                stop = next_boundary
                break
        body = clean[h.start():stop].rstrip() + "\n"
        result[anchor] = {"anchor": anchor, "section": h[2], "title": h[3],
                          "text": body, "sha256": sha(body)}
    return result, [(h[2], len(h[1])) for h in headings]


def nonempty(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing annotation: {field}")
    return value


def refs(value, catalog, field, prefix="th-"):
    if not isinstance(value, list) or not value or len(set(value)) != len(value):
        raise ValueError(f"Empty or duplicate theory references: {field}")
    for ref in value:
        if not isinstance(ref, str) or ref not in catalog or not ref.startswith(prefix):
            raise ValueError(f"Missing/invalid theory reference: {field}: {ref}")
    return value


def build(text, spec_sha256):
    config = fenced_block(text, "TECHNICAL_BINDINGS")
    if config.get("schema_version") != 1:
        raise ValueError("Unsupported technical binding schema")
    catalog, headings = units(text)
    global_refs = refs(config.get("global_refs"), catalog, "global_refs")
    roots = refs(config.get("theory_roots"), catalog, "theory_roots")
    shared_refs = refs(config.get("shared_design_refs"), catalog, "shared_design_refs", "tech-shared-")
    actual_roots = {number for number, level in headings if level == 2}
    classified = {catalog[r]["section"] for r in roots} | set(config.get("technical_sections", []))
    if actual_roots != classified:
        raise ValueError("Unclassified/missing root sections: " + repr(sorted(actual_roots ^ classified)))
    nodes = config.get("nodes")
    if not isinstance(nodes, list) or {n.get("id") for n in nodes} != IDS or len(nodes) != len(IDS):
        raise ValueError("Missing or duplicate T01—T13 / R01—R08 binding")
    by_id = {n["id"]: n for n in nodes}
    declared = re.findall(r"^#{2,4} \d+(?:\.\d+)*\.? ([TR]\d{2})｜", text, re.M)
    if set(declared) != IDS or len(declared) != len(IDS):
        raise ValueError("Unbound/duplicate module or route design heading")
    logic_ids = set()
    for n in nodes:
        anchor = n.get("design_anchor")
        if anchor not in catalog or anchor != "tech-" + n["id"].lower():
            raise ValueError(f"Missing/mismatched design anchor: {n['id']}")
        if n["id"] not in catalog[anchor]["title"]:
            raise ValueError(f"Design anchor points to another node: {n['id']}")
        for field in ("owner", "phase", "implementation", "intent", "validation"):
            nonempty(n.get(field), n["id"] + "." + field)
        refs(n.get("theory_refs"), catalog, n["id"])
        deps = n.get("design_dependencies")
        if not isinstance(deps, list) or len(set(deps)) != len(deps) or any(d not in IDS or d == n["id"] for d in deps):
            raise ValueError(f"Invalid design dependencies: {n['id']}")
        logic = n.get("logic")
        if not isinstance(logic, list) or not logic:
            raise ValueError(f"Missing logic annotation: {n['id']}")
        for step in logic:
            sid = step.get("id", "")
            if not re.fullmatch(re.escape(n["id"]) + r"\.(?:L|F)\d{2}", sid) or sid in logic_ids:
                raise ValueError(f"Invalid/duplicate logic ID: {sid}")
            logic_ids.add(sid)
            if step.get("executor") not in IDS:
                raise ValueError(f"Invalid logic executor: {sid}")
            for field in ("action", "input", "condition", "output", "limit"):
                nonempty(step.get(field), sid + "." + field)
            refs(step.get("theory_refs"), catalog, sid)
            for field in ("success_to", "failure_to"):
                dest = step.get(field)
                if not isinstance(dest, list) or not dest or any(d not in IDS for d in dest):
                    raise ValueError(f"Missing/invalid branch target: {sid}.{field}")
    used = set(global_refs)
    for n in nodes:
        used.update(n["theory_refs"])
        for step in n["logic"]:
            used.update(step["theory_refs"])
    if not set(roots) <= used:
        raise ValueError("Unbound theory root(s): " + repr(sorted(set(roots) - used)))

    computed, visiting = {}, set()
    shared_hashes = {ref: catalog[ref]["sha256"] for ref in sorted(shared_refs)}

    def compute(node_id):
        if node_id in computed:
            return computed[node_id]
        if node_id in visiting:
            raise ValueError("Cyclic design-dependency graph; runtime return loops belong in branch annotations")
        visiting.add(node_id)
        n = by_id[node_id]
        metadata = {k: v for k, v in n.items() if k != "reviewed_binding"}
        design_hash = sha({"definition": catalog[n["design_anchor"]]["text"], "annotations": metadata})
        source_ids = set(global_refs) | set(n["theory_refs"])
        for step in n["logic"]:
            source_ids.update(step["theory_refs"])
        source_hashes = {ref: catalog[ref]["sha256"] for ref in sorted(source_ids)}
        deps = {d: compute(d)["basis_sha256"] for d in sorted(n["design_dependencies"])}
        candidate = {"design_sha256": design_hash, "sources": source_hashes,
                     "shared_context": shared_hashes, "dependencies": deps}
        reviewed = n.get("reviewed_binding")
        if not isinstance(reviewed, dict) or not HEX.fullmatch(reviewed.get("design_sha256", "")):
            raise ValueError(f"Missing/invalid reviewed binding: {node_id}")
        for field in ("sources", "shared_context", "dependencies"):
            values = reviewed.get(field)
            if not isinstance(values, dict) or any(not isinstance(k, str) or not isinstance(v, str) or not HEX.fullmatch(v) for k, v in values.items()):
                raise ValueError(f"Invalid reviewed {field}: {node_id}")
        changed_sources = sorted(k for k in set(source_hashes) | set(reviewed["sources"])
                                 if source_hashes.get(k) != reviewed["sources"].get(k))
        changed_deps = sorted(k for k in set(deps) | set(reviewed["dependencies"])
                              if deps.get(k) != reviewed["dependencies"].get(k))
        changed_shared = sorted(k for k in set(shared_hashes) | set(reviewed["shared_context"])
                                if shared_hashes.get(k) != reviewed["shared_context"].get(k))
        unreviewed_deps = sorted(d for d in n["design_dependencies"]
                                 if computed[d]["binding_status"] != "CURRENT_BINDING")
        record = {**metadata, "current_binding": candidate,
                  "basis_sha256": sha(candidate),
                  "binding_status": "CURRENT_BINDING" if candidate == reviewed and not unreviewed_deps else "REVIEW_REQUIRED",
                  "changed_theory_refs": changed_sources,
                  "design_changed": design_hash != reviewed["design_sha256"],
                  "changed_dependencies": changed_deps, "unreviewed_dependencies": unreviewed_deps}
        record["changed_shared_context"] = changed_shared
        visiting.remove(node_id)
        computed[node_id] = record
        return record

    for node_id in sorted(IDS):
        compute(node_id)
    reverse = {}
    for ref in sorted(used):
        direct = sorted(nid for nid, n in computed.items() if ref in n["current_binding"]["sources"])
        affected = set(direct)
        while True:
            extra = {nid for nid, n in computed.items() if set(n["design_dependencies"]) & affected}
            if extra <= affected:
                break
            affected |= extra
        reverse[ref] = {"section": catalog[ref]["section"], "title": catalog[ref]["title"],
                        "sha256": catalog[ref]["sha256"], "direct_nodes": direct,
                        "potentially_affected_nodes": sorted(affected)}
    return {"schema_version": 1, "spec_sha256": spec_sha256,
            "meaning": "Binding freshness only; never content approval, implementation verification or execution permission.",
            "review_required": sorted(nid for nid, n in computed.items() if n["binding_status"] != "CURRENT_BINDING"),
            "global_refs": global_refs, "nodes": [computed[nid] for nid in sorted(IDS)],
            "theory_to_technical": reverse,
            "shared_design_sources": {r: {k: catalog[r][k] for k in ("section", "title", "sha256")}
                                      for r in sorted(shared_refs)}}


def report(trace):
    lines = ["# 技术关联与变更检查", "",
             "本文件从最高说明唯一原文机械生成，请勿手工修改。理论、模块/路线正文与逻辑标注都只在最高说明维护。",
             "", "**CURRENT_BINDING仅表示本次关联版本一致；不证明方案正确、程序已实现、内容已审或获准运行。**",
             "理论或设计/依赖改变会变为REVIEW_REQUIRED；重新生成只刷新事实，不自动改写技术正文或批准新基线。",
             "", f"当前规范SHA-256：`{trace['spec_sha256']}`。",
             "", "需复核节点：" + ("、".join(trace["review_required"]) or "无；仅限关联新鲜度检查。"), "",
             "| 节点 | 设计原文 | 关联状态 | 责任/阶段 | 实现范围 |", "|---|---|---|---|---|"]

    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ")

    for n in trace["nodes"]:
        lines.append(f"| [{n['id']}](#{n['id'].lower()}) | [原文]({SPEC}#{n['design_anchor']}) | {n['binding_status']} | {cell(n['owner'])}；{cell(n['phase'])} | {cell(n['implementation'])} |")
    for n in trace["nodes"]:
        lines.extend(["", f"## {n['id']}", "", f"设计目的：{n['intent']}", "",
                      f"责任：{n['owner']}；阶段：{n['phase']}；实现：{n['implementation']}。", "",
                      "理论出处：" + "、".join(f"[§{trace['theory_to_technical'][r]['section']}]({SPEC}#{r})" for r in n["theory_refs"])
                      + "。另继承全局约束，完整哈希及依赖见technical_trace.json。", "",
                      "设计影响依赖：" + ("、".join(n["design_dependencies"]) or "无") + "；这些不是任务启动前必须全部PASS的状态条件。", "",
                      f"关联状态：{n['binding_status']}；理论变化：{','.join(n['changed_theory_refs']) or '无'}；设计变化：{n['design_changed']}；共用设计变化：{','.join(n['changed_shared_context']) or '无'}；上游变化：{','.join(n['changed_dependencies']) or '无'}。", "",
                      "| 逻辑编号/动作 | 输入与启用条件 | 输出 | 成功去向/失败去向 | 理论与限制 |",
                      "|---|---|---|---|---|"])
        for step in n["logic"]:
            refs_text = "、".join(f"[§{trace['theory_to_technical'][r]['section']}]({SPEC}#{r})" for r in step["theory_refs"])
            lines.append("| " + " | ".join([cell(step['id'] + ' / ' + step['executor'] + ' ' + step['action']),
                cell(step['input'] + '；条件：' + step['condition']), cell(step['output']),
                cell('成功：' + '/'.join(step['success_to']) + '；失败：' + '/'.join(step['failure_to'])),
                refs_text + '；' + cell(step['limit'])]) + " |")
        lines.extend(["", "验收：" + n["validation"]])
    lines.extend(["", "## 共用设计来源", "",
                  "以下共用架构、接口、阶段及维护边界由所有节点继承；变更会列出具体共用来源并要求复核。", "",
                  "| 稳定设计ID / 当前节号 | 当前标题 |", "|---|---|"])
    for ref, item in trace["shared_design_sources"].items():
        lines.append(f"| [{ref} / §{item['section']}]({SPEC}#{ref}) | {cell(item['title'])} |")
    lines.extend(["", "## 理论到技术的反向索引", "",
                  "包含全局约束的保守影响范围，不宣称自然语言依赖已经穷尽。问题台账中的未采纳方案及历史记录不升级为规范。", "",
                  "| 稳定理论ID/当前节号 | 直接绑定 | 设计依赖传播范围 |", "|---|---|---|"])
    for ref, item in trace["theory_to_technical"].items():
        lines.append(f"| [{ref} / §{item['section']}]({SPEC}#{ref}) | {','.join(item['direct_nodes'])} | {','.join(item['potentially_affected_nodes'])} |")
    return "\n".join(lines) + "\n"


def project(text, spec_sha256):
    trace = build(text, spec_sha256)
    return {JSON_OUTPUT: (json.dumps(trace, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8"),
            TEXT_OUTPUT: report(trace).encode("utf-8")}


def pending_errors(trace, node_ids=None):
    nodes = {n["id"]: n for n in trace["nodes"]}
    wanted = sorted(nodes) if node_ids is None else list(node_ids)
    if not wanted:
        return ["No technical node selected"]
    errors = []
    for node_id in wanted:
        if node_id not in nodes:
            errors.append(f"Unknown technical node: {node_id}")
        elif nodes[node_id]["binding_status"] != "CURRENT_BINDING":
            errors.append(f"Technical binding requires review before adoption: {node_id}")
    return errors
