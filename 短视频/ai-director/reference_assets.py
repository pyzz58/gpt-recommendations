#!/usr/bin/env python3
"""Offline reference-asset catalog: identity/scene/prop shots and preflight.

Planning only. Never downloads, generates, uploads, approves or publishes images.
A file digest proves byte identity, not face/scene consistency or legal ownership.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

ID = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
KINDS = {"character", "scene", "prop"}
STATUSES = {"not_created", "candidate", "approved"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
MAX_IMAGE_BYTES = 20 * 1024 * 1024
VIEWS = {"character": ("front", "three_quarter", "full_body"),
         "scene": ("establishing",),
         "prop": ("detail",)}
RENDER_ROUTES = {"ai_video", "static_post"}


def _empty_view():
    return {"status": "not_created", "path": None, "sha256": None,
            "source": None, "rights_status": "unchecked", "rights_evidence": None,
            "reviewer": None, "human_approved": False}


def _direction_by_id(direction):
    if not isinstance(direction, dict):
        return {}
    shots = direction.get("shots", [])
    if not isinstance(shots, list):
        return {}
    return {s["shot_id"]: s for s in shots if isinstance(s, dict)
            and isinstance(s.get("shot_id"), str)}


def _production_route(shot, directed):
    if not directed:
        return "ai_video" if shot.get("visual_type") == "ai_video" else "post_production"
    from director_v2 import production_route
    return production_route(shot, directed.get("generation", {}))


def scaffold(base, direction=None):
    """A *proposal* catalog from declared character/scene/prop IDs only.

    Scene+character bindings are inferred only for visual-generating routes.
    Props must be explicitly bound to a shot: a continuity inventory also
    includes OFF-SCREEN props and must not be treated as a visible reference.
    """
    assets = {}
    for char in base.get("characters", []):
        ident = char.get("id")
        if isinstance(ident, str) and ID.fullmatch(ident):
            assets[ident] = {"kind": "character",
                             "description": char.get("description", ""),
                             "wardrobe": char.get("wardrobe", ""),
                             "views": {v: _empty_view() for v in VIEWS["character"]}}
    for scene in base.get("scenes", []):
        ident = scene.get("id")
        if isinstance(ident, str) and ID.fullmatch(ident) and ident not in assets:
            assets[ident] = {"kind": "scene",
                             "description": scene.get("description", ""),
                             "views": {"establishing": _empty_view()}}
    for ident, obj in (base.get("continuity_contract") or {}).get("props", {}).items():
        if isinstance(ident, str) and ID.fullmatch(ident) and ident not in assets:
            assets[ident] = {"kind": "prop",
                             "description": obj.get("label", ident) if isinstance(obj, dict) else ident,
                             "views": {"detail": _empty_view()}}
    directions = _direction_by_id(direction)
    requests = {}
    for shot in base.get("shots", []):
        sid = shot.get("id")
        if not isinstance(sid, str):
            continue
        direct = directions.get(sid)
        route = _production_route(shot, direct)
        bindings = []
        if route in RENDER_ROUTES:
            for cid in shot.get("character_ids", []):
                bindings.append({"asset_id": cid, "view": "three_quarter", "role": "identity"})
            if shot.get("scene_id"):
                bindings.append({"asset_id": shot["scene_id"], "view": "establishing", "role": "environment"})
        # Explicit optional bindings can include a prop, another camera angle,
        # or more detail in post. No natural-language guessing.
        for item in (direct or {}).get("generation", {}).get("reference_bindings", []):
            if isinstance(item, dict) and item not in bindings:
                bindings.append(dict(item))
        requests[sid] = bindings
    return {"schema_version": "1.0", "assets": assets,
            "shot_requirements": requests,
            "policy": {"generated_media": False, "identity_consistency_verified": False,
                       "private_media_in_public_repo": False}}


def _safe_image(root, rel):
    """Resolve a private image under an explicit allowed root, no symlinks."""
    if not isinstance(rel, str) or not rel or "\\" in rel:
        return None, "invalid image path"
    posix = PurePosixPath(rel)
    if posix.is_absolute() or ".." in posix.parts or "." in posix.parts or not posix.parts:
        return None, "image path must be a relative child of the asset root"
    if posix.suffix.lower() not in IMAGE_SUFFIXES:
        return None, "unsupported image extension"
    root_path = Path(root).resolve()
    target = root_path.joinpath(*posix.parts)
    if any(part.is_symlink() for part in [root_path, *list(target.parents)[:len(posix.parts)], target]):
        return None, "symlinked image paths are prohibited"
    resolved = target.resolve()
    if not resolved.is_relative_to(root_path):
        return None, "image path escapes the asset root"
    if not resolved.is_file():
        return None, "image file does not exist"
    if resolved.stat().st_size > MAX_IMAGE_BYTES or resolved.stat().st_size == 0:
        return None, "image file size is invalid"
    with resolved.open("rb") as fp:
        prefix = fp.read(16)
    suffix = posix.suffix.lower()
    if not ((suffix == ".png" and prefix.startswith(b"\x89PNG\r\n\x1a\n"))
            or (suffix in {".jpg", ".jpeg"} and prefix.startswith(b"\xff\xd8\xff"))
            or (suffix == ".webp" and prefix[:4] == b"RIFF" and prefix[8:12] == b"WEBP")):
        return None, "image content header does not match extension"
    return resolved, None


def audit(base, direction, manifest, asset_root=None):
    """Return blockers and pending checks, never mark media as generated.

    'ready' is metadata-and-file preflight only; a human must still inspect
    actual faces, camera geometry, license scope and video-model compatibility.
    """
    findings = []
    def add(code, severity, shot_id, asset_id, message):
        findings.append({"code": code, "severity": severity, "shot_id": shot_id,
                         "asset_id": asset_id, "message": message})

    if not isinstance(manifest, dict) or manifest.get("schema_version") != "1.0":
        add("INVALID_CATALOG", "blocker", None, None, "manifest schema_version must be 1.0")
        return _summary(findings, 0, 0)
    policy = manifest.get("policy")
    if not isinstance(policy, dict) or any(policy.get(key) is not False for key in
        ("generated_media", "identity_consistency_verified", "private_media_in_public_repo")):
        add("CATALOG_POLICY_INVALID", "blocker", None, None,
            "catalog must not claim generated media, identity consistency or public private assets")
    assets = manifest.get("assets")
    reqs = manifest.get("shot_requirements")
    if not isinstance(assets, dict) or not isinstance(reqs, dict):
        add("INVALID_CATALOG", "blocker", None, None, "assets and shot_requirements must be objects")
        return _summary(findings, 0, 0)
    src_kinds = {}
    for key, arr, kind in (("characters", base.get("characters", []), "character"),
                           ("scenes", base.get("scenes", []), "scene")):
        if not isinstance(arr, list):
            add("INVALID_BASE", "blocker", None, None, key + " must be a list")
            return _summary(findings, 0, 0)
        for item in arr:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                src_kinds[item["id"]] = kind
    contract = base.get("continuity_contract") or {}
    if not isinstance(contract, dict) or not isinstance(contract.get("props", {}), dict):
        add("INVALID_BASE", "blocker", None, None, "continuity_contract.props must be an object")
        return _summary(findings, 0, 0)
    for asset_id in contract.get("props", {}):
        src_kinds.setdefault(asset_id, "prop")

    for aid, data in assets.items():
        if not isinstance(aid, str) or not ID.fullmatch(aid) or not isinstance(data, dict):
            add("INVALID_ASSET", "blocker", None, aid, "invalid asset identifier or record")
            continue
        if aid not in src_kinds:
            add("ASSET_NOT_DECLARED", "blocker", None, aid, "asset ID not declared by the base plan")
        if data.get("kind") not in KINDS or data.get("kind") != src_kinds.get(aid):
            add("ASSET_KIND_MISMATCH", "blocker", None, aid, "asset kind conflicts with base plan")
        views = data.get("views")
        if not isinstance(views, dict):
            add("INVALID_VIEWS", "blocker", None, aid, "views must be an object")
            continue
        for view, record in views.items():
            if not isinstance(view, str) or not ID.fullmatch(view) or not isinstance(record, dict):
                add("INVALID_VIEW", "blocker", None, aid, "invalid view name or view data")
                continue
            status = record.get("status")
            if status not in STATUSES or not isinstance(record.get("human_approved"), bool):
                add("INVALID_REFERENCE_STATUS", "blocker", None, aid, "invalid status or human_approved flag")
                continue
            if status != "approved":
                if record.get("human_approved"):
                    add("UNAPPROVED_MARKED_APPROVED", "blocker", None, aid,
                        "a missing/candidate reference cannot have human_approved=true")
                continue
            if not (record.get("human_approved") and record.get("rights_status") == "verified"
                    and all(isinstance(record.get(k), str) and record[k].strip()
                            for k in ("path", "sha256", "source", "rights_evidence", "reviewer"))):
                add("APPROVAL_EVIDENCE_MISSING", "blocker", None, aid,
                    "approved image needs human signoff, source, rights evidence, reviewer, path and digest")
                continue
            if not DIGEST.fullmatch(record["sha256"]):
                add("INVALID_DIGEST", "blocker", None, aid, "sha256 must be lowercase 64-digit hex")
                continue
            if asset_root is None:
                add("FILE_NOT_CHECKED", "missing", None, aid,
                    "approved metadata is insufficient without a private asset root")
                continue
            path, error = _safe_image(asset_root, record["path"])
            if error:
                add("UNSAFE_OR_MISSING_IMAGE", "blocker", None, aid, error)
                continue
            hasher = hashlib.sha256()
            with path.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    hasher.update(chunk)
            if hasher.hexdigest() != record["sha256"]:
                add("IMAGE_DIGEST_MISMATCH", "blocker", None, aid,
                    "reference image differs from the manually approved digest")

    base_shots = {shot.get("id"): shot for shot in base.get("shots", []) if isinstance(shot, dict)}
    directions = _direction_by_id(direction)
    for sid in reqs:
        if sid not in base_shots:
            add("UNKNOWN_SHOT", "blocker", sid, None, "shot requirement refers to unknown shot")
    required_total = 0
    ready_count = 0
    for sid, shot in base_shots.items():
        raw = reqs.get(sid)
        if not isinstance(raw, list):
            add("MISSING_SHOT_REQUIREMENTS", "blocker", sid, None,
                "every shot requires an explicit bindings array, even if empty")
            continue
        direct = directions.get(sid)
        try:
            route = _production_route(shot, direct)
        except ValueError as e:
            add("INVALID_PRODUCTION_ROUTE", "blocker", sid, None, str(e))
            continue
        compulsory = set()
        if route in RENDER_ROUTES:
            compulsory |= {(x, "three_quarter") for x in shot.get("character_ids", [])}
            if shot.get("scene_id"):
                compulsory.add((shot["scene_id"], "establishing"))
        for binding in (direct or {}).get("generation", {}).get("reference_bindings", []):
            if isinstance(binding, dict):
                aid, view = binding.get("asset_id"), binding.get("view")
                if isinstance(aid, str) and isinstance(view, str):
                    compulsory.add((aid, view))
        present = set()
        for binding in raw:
            if not isinstance(binding, dict):
                add("INVALID_BINDING", "blocker", sid, None, "binding must be an object")
                continue
            aid, view = binding.get("asset_id"), binding.get("view")
            if not isinstance(aid, str) or not isinstance(view, str):
                add("INVALID_BINDING", "blocker", sid, None, "asset_id and view are required strings")
                continue
            pair = (aid, view)
            if pair in present:
                add("DUPLICATE_BINDING", "blocker", sid, aid, "duplicate shot asset-view binding")
                continue
            present.add(pair)
            required_total += 1
            if aid not in assets or not isinstance(assets[aid], dict):
                add("UNKNOWN_ASSET", "blocker", sid, aid, "referenced asset missing or invalid in catalog")
                continue
            view_map = assets[aid].get("views")
            record = view_map.get(view) if isinstance(view_map, dict) else None
            if not isinstance(record, dict):
                add("MISSING_VIEW", "blocker", sid, aid, "requested view missing from asset catalog: " + view)
                continue
            if record.get("status") != "approved":
                add("REFERENCE_NOT_READY", "missing", sid, aid,
                    "required reference " + view + " is " + str(record.get("status")))
                continue
            # Reuse the global image validation result; a matching metadata
            # status alone does not make any shot ready for generation.
            if any(f["asset_id"] == aid and f["shot_id"] is None
                   and f["severity"] in ("blocker", "missing") for f in findings):
                add("REFERENCE_NOT_VERIFIED", "missing", sid, aid,
                    "reference " + view + " did not pass file/provenance verification")
            else:
                ready_count += 1
        for aid, view in sorted(compulsory - present):
            add("REQUIRED_REFERENCE_UNBOUND", "missing", sid, aid,
                "required visual reference is not bound: " + view)
            required_total += 1
    return _summary(findings, required_total, ready_count)


def _summary(findings, required_total, ready_count):
    blockers = sum(f["severity"] == "blocker" for f in findings)
    missing = sum(f["severity"] == "missing" for f in findings)
    return {"schema_version": "1.0", "status": "preflight_only",
            "required_bindings": required_total, "verified_bindings": ready_count,
            "blockers": blockers, "missing": missing,
            "ready_for_reference_preflight": required_total > 0 and blockers == 0 and missing == 0,
            "human_visual_consistency_verified": False,
            "media_generated": False, "findings": findings}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Reference assets: offline catalog and preflight ONLY")
    sub = parser.add_subparsers(dest="command", required=True)
    for cmd in ("scaffold", "audit"):
        p = sub.add_parser(cmd)
        p.add_argument("--base", required=True)
        p.add_argument("--direction")
        if cmd == "scaffold":
            p.add_argument("--out", required=True)
        else:
            p.add_argument("--manifest", required=True)
            p.add_argument("--asset-root")
    args = parser.parse_args(argv)
    try:
        base = json.loads(Path(args.base).read_text(encoding="utf-8"))
        direction = json.loads(Path(args.direction).read_text(encoding="utf-8")) if args.direction else None
        if args.command == "scaffold":
            manifest = scaffold(base, direction)
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open("x", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
                f.write("\n")
            print("reference catalog created (no image files generated):", out)
            return 0
        catalog = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        report = audit(base, direction, catalog, args.asset_root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2 if report["blockers"] else 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
