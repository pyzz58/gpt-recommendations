#!/usr/bin/env python3
"""Check derived engineering traceability; no model or network calls."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[1]

def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode("utf-8")).hexdigest()

def version(text):
    match = re.search(r"^版本：(\S+)", text, re.M)
    if not match:
        raise ValueError("Missing document version")
    return match.group(1)

def sources(text):
    result = {}
    visible, in_fence = [], False
    for line in text.splitlines(keepends=True):
        if line.startswith("```"):
            in_fence = not in_fence
            visible.append("\n")
        else:
            visible.append("\n" if in_fence else line)
    clean = "".join(visible)
    headings = list(re.finditer(r"^(#{2,6}) (\d+(?:\.\d+)*)(?:\.|\s)[^\n]*", clean, re.M))
    for index, match in enumerate(headings):
        depth = len(match.group(1))
        end = len(clean)
        for next_match in headings[index + 1:]:
            if len(next_match.group(1)) <= depth:
                end = next_match.start()
                break
        key = "SEC:" + match.group(2)
        if key in result:
            raise ValueError("Duplicate source section: " + key)
        result[key] = clean[match.start():end].strip()
    for match in re.finditer(r"^\| (D-\d{3}|A\d{2}) \|[^\n]+$", clean, re.M):
        key = match.group(1)
        if key in result:
            raise ValueError("Duplicate source identifier: " + key)
        result[key] = match.group(0)
    return result

def anchors(text):
    definitions = {
        "technical_refs": re.findall(r"^## (TR-\d{2}) ", text, re.M),
        "work_packages": re.findall(r"^\| (W\d{2}) \|", text, re.M),
        "acceptance_refs": re.findall(r"^\| (AT-\d{3}) \|", text, re.M),
    }
    for kind, values in definitions.items():
        if len(values) != len(set(values)):
            raise ValueError("Duplicate roadmap identifier: " + kind)
    return {key: set(values) for key, values in definitions.items()}

def combined(refs, source_map):
    return digest("\n".join(ref + "\n" + source_map[ref] for ref in sorted(refs)))

def safe_file(root, value):
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Manifest path escapes project")
    return path

def load_state(root):
    path = root / "traceability" / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    theory_bytes = safe_file(root, manifest["theory_file"]).read_bytes()
    roadmap_bytes = safe_file(root, manifest["roadmap_file"]).read_bytes()
    theory, roadmap = theory_bytes.decode("utf-8"), roadmap_bytes.decode("utf-8")
    return path, manifest, theory_bytes, roadmap_bytes, theory, roadmap

def validate(root, fingerprints=True):
    errors = []
    try:
        _, m, tb, rb, theory, roadmap = load_state(root)
        source_map, declared = sources(theory), anchors(roadmap)
    except (ValueError, KeyError, OSError, UnicodeError) as exc:
        return ["Unreadable traceability input: " + str(exc)]
    if m.get("schema_version") != 1:
        errors.append("Unsupported manifest schema")
    reqs = m.get("requirements", [])
    ids = [r.get("id") for r in reqs]
    if not reqs or any(not re.fullmatch(r"RQ-\d{3}", str(x)) for x in ids):
        errors.append("Requirements must have RQ identifiers")
    if len(ids) != len(set(ids)):
        errors.append("Duplicate requirement")
    covered_sources = set()
    covered = {key: set() for key in declared}
    for r in reqs:
        rid = str(r.get("id"))
        refs = r.get("source_refs", [])
        if not refs or len(refs) != len(set(refs)):
            errors.append(rid + ": empty/duplicate source refs")
        covered_sources.update(refs)
        missing = set(refs) - source_map.keys()
        if missing:
            errors.append(rid + ": missing source refs " + ", ".join(sorted(missing)))
        for kind in declared:
            values = r.get(kind, [])
            if not values:
                errors.append(rid + ": empty " + kind)
            if set(values) - declared[kind]:
                errors.append(rid + ": dead " + kind + " " + ", ".join(sorted(set(values) - declared[kind])))
            covered[kind].update(values)
        if rid not in roadmap:
            errors.append(rid + ": not mentioned in technical document")
        if not r.get("planned_paths"):
            errors.append(rid + ": missing planned implementation path")
        if r.get("implementation_status") not in {"planned", "documentation_ready", "in_progress", "implemented", "verified", "blocked"}:
            errors.append(rid + ": invalid implementation status")
        if fingerprints and not missing and r.get("source_sha256") != combined(refs, source_map):
            errors.append(rid + ": source fingerprint stale")
    for key in source_map:
        if re.fullmatch(r"D-\d{3}|A\d{2}", key) and key not in covered_sources:
            errors.append("Unmapped theory identifier: " + key)
    for kind in declared:
        missing = declared[kind] - covered[kind]
        if missing:
            errors.append("Unmapped " + kind + ": " + ", ".join(sorted(missing)))
    for match in re.finditer(r"^## (TR-\d{2}) [^\n]*\n(.*?)(?=^## TR-|\Z)", roadmap, re.M | re.S):
        body = match.group(2)
        if not re.search(r"^思想依据：.+需求：RQ-", body, re.M):
            errors.append(match.group(1) + ": missing thought/requirement guidance")
    if fingerprints:
        if m.get("theory_sha256") != digest(tb):
            errors.append("Theory content changed; run impact and synchronize")
        if m.get("roadmap_sha256") != digest(rb):
            errors.append("Technical document changed; review and refresh mapping")
        if m.get("theory_version") != version(theory):
            errors.append("Theory version stale")
        if m.get("roadmap_version") != version(roadmap):
            errors.append("Technical version stale")
        current_snapshots = {key: digest(value) for key, value in source_map.items()}
        if m.get("source_snapshots") != current_snapshots:
            errors.append("Source snapshot index stale")
        note = m.get("last_sync", {}).get("note", "")
        if len(note.strip()) < 12:
            errors.append("Missing substantive synchronization note")
    return errors

def impact(root):
    _, m, _, _, theory, _ = load_state(root)
    current = {key: digest(value) for key, value in sources(theory).items()}
    previous = m.get("source_snapshots", {})
    changed = {key for key in current.keys() | previous.keys() if current.get(key) != previous.get(key)}
    affected = [r for r in m["requirements"] if changed.intersection(r["source_refs"])]
    mapped = {key for r in m["requirements"] for key in r["source_refs"]}
    return {
        "changed_sources": sorted(changed),
        "affected": [{"requirement": r["id"], "technical": r["technical_refs"], "work_packages": r["work_packages"], "acceptance": r["acceptance_refs"]} for r in affected],
        "changes_without_direct_mapping": sorted(changed - mapped),
        "instruction": "Review semantics, update affected design/tasks/tests, then refresh. Detection is not automatic design repair.",
    }

def refresh(root, note):
    if len(note.strip()) < 12:
        raise ValueError("Provide a substantive synchronization note")
    problems = validate(root, fingerprints=False)
    if problems:
        raise ValueError("; ".join(problems))
    path, m, tb, rb, theory, roadmap = load_state(root)
    source_map = sources(theory)
    m["theory_version"], m["roadmap_version"] = version(theory), version(roadmap)
    m["theory_sha256"], m["roadmap_sha256"] = digest(tb), digest(rb)
    m["source_snapshots"] = {key: digest(value) for key, value in sorted(source_map.items())}
    for r in m["requirements"]:
        r["source_sha256"] = combined(r["source_refs"], source_map)
    m["last_sync"] = {"at": datetime.now(timezone.utc).isoformat(), "note": note, "meaning": "Operator records semantic review; hashes only detect structural drift."}
    path.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"refreshed": True, "theory_version": m["theory_version"], "roadmap_version": m["roadmap_version"], "requirements": len(m["requirements"])}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "impact", "refresh"], nargs="?", default="check")
    parser.add_argument("--note", default="")
    args = parser.parse_args()
    try:
        if args.command == "impact":
            result = impact(DEFAULT_ROOT)
        elif args.command == "refresh":
            result = refresh(DEFAULT_ROOT, args.note)
        else:
            errors = validate(DEFAULT_ROOT)
            result = {"ok": not errors, "errors": errors, "scope": "Documentation consistency only; application and scientific validation are not implied."}
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 1 if errors else 0
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError, OSError, UnicodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2

if __name__ == "__main__":
    sys.exit(main())

