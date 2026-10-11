#!/usr/bin/env python3
"""Provider-neutral reference-input preview. No API, image reads, or uploads.

This is a proposed *reference requirement manifest*, not a ready-to-send
Wan/Seedance API payload. Credentials, paths and image bytes are never included.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import director_v2
import reference_assets


def make_packet(base, directions, catalog):
    """Generate an immutable-to-input, fail-closed dry-run job specification.

    Even if catalog image records claim "approved", actual binary transport,
    provider compatibility, visual similarity and payment authorization remain
    outside this tool. No private path, source, rights evidence or image bytes
    are copied into the public-facing packet.
    """
    errors, _ = director_v2.validate(base, directions, catalog, None)
    if errors:
        raise ValueError("invalid director or asset catalog: " + "; ".join(errors[:10]))
    audit = reference_assets.audit(base, directions, catalog, None)
    shot_map = {d["shot_id"]: d for d in directions["shots"]}
    shot_requirements = catalog["shot_requirements"]
    records = []
    for shot in base["shots"]:
        sid = shot["id"]
        directed = shot_map[sid]
        route = director_v2.production_route(shot, directed["generation"])
        images = []
        for item in shot_requirements[sid]:
            aid, view = item["asset_id"], item["view"]
            entry = catalog["assets"].get(aid, {})
            rec = entry.get("views", {}).get(view, {})
            images.append({
                "asset_id": aid, "view": view, "role": item["role"],
                "asset_kind": entry.get("kind"),
                "catalog_status": rec.get("status"),
                "media_bytes_included": False,
                "reference_uploaded_to_provider": False,
                "provider_binding_verified": False,
            })
        records.append({
            "shot_id": sid,
            "execution_route": route,
            "reference_requirements": images,
            "human_shot_approval_recorded": directed["qa"]["human_approved"] is True,
            "runtime_input_ready": False,
            "upload_authorized": False,
            "paid_execution_authorized": False,
        })
    return {
        "schema_version": "1.0",
        "kind": "offline_reference_input_preview",
        "model_provider": "not_selected",
        "actual_provider_request": False,
        "private_paths_included": False,
        "media_bytes_included": False,
        "images_uploaded": False,
        "user_payment_authorized": False,
        "reference_preflight": {
            "blockers": audit["blockers"],
            "missing": audit["missing"],
            "files_verified": False,
            "identity_consistency_verified": False,
        },
        "jobs": records,
        "runtime_execution_allowed": False,
        "note": "This is a reference requirement preview only; not an API payload, legal license verification, actual upload, or visual identity guarantee.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline provider-neutral reference packet preview")
    parser.add_argument("--base", required=True)
    parser.add_argument("--direction", required=True)
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        files = [Path(args.base), Path(args.direction), Path(args.catalog)]
        base, direction, catalog = [
            json.loads(path.read_text(encoding="utf-8")) for path in files
        ]
        packet = make_packet(base, direction, catalog)
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        # Never overwrite a user-reviewed or manually edited packet.
        with output.open("x", encoding="utf-8") as fp:
            json.dump(packet, fp, ensure_ascii=False, indent=2)
            fp.write("\n")
        print("Reference input preview created (no assets uploaded):", output)
        return 0
    except (OSError, ValueError, TypeError, KeyError) as err:
        print("ERROR:", err, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
