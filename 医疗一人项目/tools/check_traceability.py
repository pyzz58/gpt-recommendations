#!/usr/bin/env python3
"""Check derived engineering traceability; no model or network calls."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_LEVELS = {"mock", "live", "human_expert", "real_outsourcing"}
EVIDENCE_STATES = {"passed", "failed", "blocked", "not_run", "not_applicable"}

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


def _git(root, *args, check=True):
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
    )
    if check and result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError("Git evidence check failed: " + detail)
    return result


def _git_prefix(root):
    result = _git(root, "rev-parse", "--show-prefix")
    return result.stdout.decode("utf-8").strip()


def _tracked_path(root, value):
    result = _git(root, "ls-files", "--", value, check=False)
    if result.returncode != 0:
        return False
    tracked = [
        line
        for line in result.stdout.decode("utf-8").splitlines()
        if line == value or line.startswith(value.rstrip("/") + "/")
    ]
    return bool(tracked)


def _git_file_digest(root, commit, prefix, value):
    full_path = prefix + value
    result = _git(root, "show", f"{commit}:{full_path}", check=False)
    if result.returncode != 0:
        return None
    return digest(result.stdout)


def _load_evidence(root, manifest):
    name = manifest.get("acceptance_evidence_file")
    if not isinstance(name, str) or not name:
        raise ValueError("Manifest must name an acceptance evidence file")
    path = safe_file(root, name)
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported acceptance evidence schema")
    records = data.get("records")
    if not isinstance(records, list):
        raise ValueError("Acceptance evidence records must be a list")
    return data, records


def _tree_fingerprint(root, paths, commit=None):
    args = ["ls-tree", "-r", "--full-tree"]
    if commit:
        args.append(commit)
    args.extend(["--", *paths])
    result = _git(root, *args)
    if commit:
        return digest(result.stdout)
    tracked = result.stdout.decode("utf-8").splitlines()
    entries = []
    prefix = _git_prefix(root)
    for line in tracked:
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        repo_path = parts[1]
        if not repo_path.startswith(prefix):
            continue
        local_path = repo_path[len(prefix):]
        path = safe_file(root, local_path)
        if path.is_file():
            entries.append(local_path + "\0" + digest(path.read_bytes()))
    return digest("\n".join(sorted(entries)))


def _validate_evidence_record(root, record, requirement_ids, requirements, anchors):
    errors = []
    record_id = record.get("id", "<missing>")
    if not isinstance(record_id, str) or not record_id.strip():
        errors.append("Acceptance record has no identifier")
    elif not re.fullmatch(r"ACC-[A-Za-z0-9._-]+", record_id):
        errors.append(record_id + ": invalid acceptance record identifier")
    refs = record.get("requirements", [])
    if not refs or len(refs) != len(set(refs)) or set(refs) - requirement_ids:
        errors.append(record_id + ": invalid requirement references")
    source_commit = record.get("source_commit", "")
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        errors.append(record_id + ": source_commit must be a full SHA")
        return errors
    exists = _git(root, "cat-file", "-e", source_commit + "^{commit}", check=False)
    if exists.returncode != 0:
        errors.append(record_id + ": source_commit does not exist")
        return errors
    ancestor = _git(
        root,
        "merge-base",
        "--is-ancestor",
        source_commit,
        "HEAD",
        check=False,
    )
    if ancestor.returncode != 0:
        errors.append(record_id + ": source_commit is not an ancestor of HEAD")
    result_value = record.get("result")
    if result_value not in EVIDENCE_STATES:
        errors.append(record_id + ": invalid result")
    commands = record.get("commands")
    if not isinstance(commands, list):
        errors.append(record_id + ": commands must be a list")
        commands = []
    if result_value == "passed" and not commands:
        errors.append(record_id + ": passed evidence requires commands")
    for index, command in enumerate(commands):
        prefix = f"{record_id}: command {index + 1}"
        if not isinstance(command, dict):
            errors.append(prefix + " is invalid")
            continue
        for key in ("cwd", "command", "mode", "started_at", "finished_at"):
            if not isinstance(command.get(key), str) or not command[key].strip():
                errors.append(prefix + " missing " + key)
        if not isinstance(command.get("exit_code"), int):
            errors.append(prefix + " missing integer exit_code")
        if not isinstance(command.get("artifacts", []), list):
            errors.append(prefix + " artifacts must be a list")
    levels = record.get("validation_levels")
    if not isinstance(levels, dict) or set(levels) != VALIDATION_LEVELS:
        errors.append(record_id + ": validation levels must be explicit")
    else:
        for name, value in levels.items():
            if not isinstance(value, dict) or value.get("status") not in EVIDENCE_STATES:
                errors.append(record_id + f": invalid {name} validation status")
            elif value.get("status") == "passed" and not value.get("evidence"):
                errors.append(record_id + f": passed {name} needs evidence")
    code_paths = record.get("code_paths")
    if not isinstance(code_paths, list) or not code_paths:
        errors.append(record_id + ": code_paths must be non-empty")
        code_paths = []
    prefix = _git_prefix(root)
    for item in code_paths:
        if not isinstance(item, dict):
            errors.append(record_id + ": invalid code path entry")
            continue
        value = item.get("path", "")
        expected = item.get("sha256", "")
        try:
            path = safe_file(root, value)
        except (ValueError, TypeError):
            errors.append(record_id + ": code path escapes project")
            continue
        if not path.is_file() or not re.fullmatch(r"[0-9a-f]{64}", str(expected)):
            errors.append(record_id + ": invalid code path or hash")
            continue
        committed = _git_file_digest(root, source_commit, prefix, value)
        if committed != expected:
            errors.append(value + ": hash does not match source_commit")
        if digest(path.read_bytes()) != expected:
            errors.append(value + ": implementation changed after tested source")
    source_scope = record.get("source_scope")
    if not isinstance(source_scope, list) or not source_scope:
        errors.append(record_id + ": source_scope must be non-empty")
    else:
        if record.get("source_tree_git_sha256") != _tree_fingerprint(
            root,
            source_scope,
            source_commit,
        ):
            errors.append(record_id + ": source tree differs from source_commit")
        if record.get("source_tree_worktree_sha256") != _tree_fingerprint(
            root,
            source_scope,
        ):
            errors.append(record_id + ": implementation tree changed after acceptance")
    validation_levels = record.get("validation_levels", {})
    if result_value == "passed":
        for requirement_id in refs:
            requirement = requirements.get(requirement_id, {})
            required_levels = requirement.get("required_validation", ["mock"])
            for level in required_levels:
                if validation_levels.get(level, {}).get("status") != "passed":
                    errors.append(
                        requirement_id + f": required {level} validation is not passed"
                    )
            missing_acceptance = set(requirement.get("acceptance_refs", [])) - set(
                record.get("acceptance_refs", [])
            )
            if missing_acceptance:
                errors.append(
                    requirement_id
                    + ": acceptance coverage missing "
                    + ", ".join(sorted(missing_acceptance))
                )
            missing_technical = set(requirement.get("technical_refs", [])) - set(
                record.get("technical_refs", [])
            )
            if missing_technical:
                errors.append(
                    requirement_id
                    + ": technical coverage missing "
                    + ", ".join(sorted(missing_technical))
                )
    if not isinstance(record.get("artifacts"), list):
        errors.append(record_id + ": artifacts must be a list")
    if not isinstance(record.get("uncovered"), list):
        errors.append(record_id + ": uncovered must be a list")
    if result_value == "passed" and any(
        isinstance(command, dict) and command.get("exit_code") != 0
        for command in commands
    ):
        errors.append(record_id + ": passed evidence contains a failed command")
    return errors

def validate(root, fingerprints=True):
    errors = []
    try:
        _, m, tb, rb, theory, roadmap = load_state(root)
        source_map, declared = sources(theory), anchors(roadmap)
    except (ValueError, KeyError, OSError, UnicodeError) as exc:
        return ["Unreadable traceability input: " + str(exc)]
    if m.get("schema_version") != 2:
        errors.append("Unsupported manifest schema")
    reqs = m.get("requirements", [])
    ids = [r.get("id") for r in reqs]
    if not reqs or any(not re.fullmatch(r"RQ-\d{3}", str(x)) for x in ids):
        errors.append("Requirements must have RQ identifiers")
    if len(ids) != len(set(ids)):
        errors.append("Duplicate requirement")
    covered_sources = set()
    covered = {key: set() for key in declared}
    try:
        _evidence_document, evidence_records = _load_evidence(root, m)
    except (ValueError, KeyError, OSError, UnicodeError) as exc:
        evidence_records = []
        errors.append("Unreadable acceptance evidence: " + str(exc))
    evidence_ids = [str(record.get("id")) for record in evidence_records]
    if len(evidence_ids) != len(set(evidence_ids)):
        errors.append("Duplicate acceptance evidence identifier")
    records_by_requirement = {
        rid: [record for record in evidence_records if rid in record.get("requirements", [])]
        for rid in ids
    }
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
        status = r.get("implementation_status")
        if status not in {"planned", "documentation_ready", "in_progress", "implemented", "verified", "blocked"}:
            errors.append(rid + ": invalid implementation status")
        if status in {"implemented", "verified"}:
            paths = r.get("implementation_paths", [])
            if not paths:
                errors.append(rid + ": missing Git implementation paths")
            for value in paths:
                try:
                    safe_file(root, value)
                except ValueError:
                    errors.append(rid + ": implementation path escapes project")
                    continue
                if not _tracked_path(root, value):
                    errors.append(rid + ": implementation path is not tracked by Git: " + value)
        if status == "verified":
            accepted = [
                record
                for record in records_by_requirement.get(rid, [])
                if record.get("result") == "passed"
            ]
            if not accepted:
                errors.append(rid + ": verified requires passed acceptance evidence")
        if fingerprints and not missing and r.get("source_sha256") != combined(refs, source_map):
            errors.append(rid + ": source fingerprint stale")
    for record in evidence_records:
        errors.extend(
            _validate_evidence_record(
                root,
                record,
                set(ids),
                {str(item["id"]): item for item in reqs},
                declared,
            )
        )
    artifact_paths = set()
    for item in m.get("supporting_artifacts", []):
        name = item.get("path", "")
        if name in artifact_paths:
            errors.append("Duplicate supporting artifact: " + name)
        artifact_paths.add(name)
        if not item.get("requirement_ids") or set(item["requirement_ids"]) - set(ids):
            errors.append(name + ": unmapped supporting artifact requirement")
        try:
            path = safe_file(root, name)
            data = path.read_bytes()
            if fingerprints and item.get("sha256") != digest(data):
                errors.append(name + ": supporting artifact fingerprint stale")
            if path.suffix == ".json":
                value = json.loads(data)
                if isinstance(value, dict) and "$defs" in value:
                    def inspect_refs(node):
                        if isinstance(node, dict):
                            target = node.get("$ref", "")
                            if target.startswith("#/$defs/") and target[len("#/$defs/"):] not in value["$defs"]:
                                errors.append(name + ": unresolved schema ref " + target)
                            for child in node.values():
                                inspect_refs(child)
                        elif isinstance(node, list):
                            for child in node:
                                inspect_refs(child)
                    inspect_refs(value)
        except (ValueError, KeyError, OSError, UnicodeError) as exc:
            errors.append(name + ": invalid supporting artifact: " + str(exc))
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
    changed_artifacts = []
    artifact_requirements = set()
    for item in m.get("supporting_artifacts", []):
        path = safe_file(root, item["path"])
        if not path.is_file() or digest(path.read_bytes()) != item.get("sha256"):
            changed_artifacts.append(item["path"])
            artifact_requirements.update(item.get("requirement_ids", []))
    affected = [r for r in m["requirements"] if changed.intersection(r["source_refs"]) or r["id"] in artifact_requirements]
    mapped = {key for r in m["requirements"] for key in r["source_refs"]}
    return {
        "changed_sources": sorted(changed),
        "changed_supporting_artifacts": sorted(changed_artifacts),
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
    for item in m.get("supporting_artifacts", []):
        item["sha256"] = digest(safe_file(root, item["path"]).read_bytes())
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
            result = {
                "ok": not errors,
                "errors": errors,
                "scope": (
                    "Documentation, Git implementation-path and acceptance-record "
                    "structure only; scientific and real-world validity are not implied."
                ),
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 1 if errors else 0
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError, OSError, UnicodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2

if __name__ == "__main__":
    sys.exit(main())


