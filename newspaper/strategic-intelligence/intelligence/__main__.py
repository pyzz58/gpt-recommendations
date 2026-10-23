"""Offline W13 CLI; no source fetching, model calls, approval or delivery.

uv run --locked python -m intelligence --root /private/archive init
uv run --locked python -m intelligence --root /private/archive put --metadata record.json --body draft.md
uv run --locked python -m intelligence --root /private/archive get VERSION --body-output recovered.md
uv run --locked python -m intelligence schema --contract reference-read
uv run --locked python -m intelligence --root /private/archive read-reference --request request.json --body-output material.bin
uv run --locked --extra workflow python -m intelligence --root /private/archive prepare --request preparation.json --output /private/prepared.json
uv run --locked --extra workflow python -m intelligence --root /private/archive verify-preparation /private/prepared.json

The schema command defaults to VersionSubmission. read-reference checks a
committed owner/reference, exact target kind/body identity and declared purpose;
its stdout contains metadata only. get is local recovery, not a downstream-use
grant. Consumer labels do not authenticate a caller or approve content.
W14 prepares separate canonical/task/material fields, with no model invocation.
created_at/source times come from input; recorded_at is assigned at commit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from pydantic import ValidationError

from .archive import Archive, ArchiveError, BodyUnavailable
from .contracts import ReferenceReadRequest, VersionSubmission


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, help="Explicit private archive directory")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    schema = commands.add_parser("schema")
    schema.add_argument("--contract", choices=("version", "reference-read", "preparation"), default="version")
    put = commands.add_parser("put")
    put.add_argument("--metadata", required=True, type=Path)
    put.add_argument("--body", type=Path)
    get = commands.add_parser("get")
    get.add_argument("version_id")
    get.add_argument("--body-output", type=Path, help="Create a new file; never overwrite")
    read = commands.add_parser("read-reference")
    read.add_argument("--request", required=True, type=Path)
    read.add_argument("--body-output", type=Path, help="Create a new file; never overwrite")
    prepare = commands.add_parser("prepare", help="Offline W14 input bundle; requires the workflow extra")
    prepare.add_argument("--request", required=True, type=Path)
    prepare.add_argument("--output", required=True, type=Path, help="New private file outside the public source directory")
    prepare.add_argument("--spec-root", type=Path, default=Path(__file__).resolve().parents[1])
    verify = commands.add_parser("verify-preparation", help="Recheck current inputs; does not approve content")
    verify.add_argument("bundle", type=Path)
    verify.add_argument("--spec-root", type=Path, default=Path(__file__).resolve().parents[1])
    commands.add_parser("rebuild-index")
    find = commands.add_parser("find")
    find.add_argument("title")
    revoke = commands.add_parser("revoke")
    revoke.add_argument("rights_id")
    revoke.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    if args.command == "schema":
        if args.contract == "preparation":
            from .preparation import PreparationRequest
            contract = PreparationRequest
        else:
            contract = ReferenceReadRequest if args.contract == "reference-read" else VersionSubmission
        print(json.dumps(contract.model_json_schema(), ensure_ascii=False, indent=2))
        return 0
    if args.root is None:
        parser.error("--root is required for archive operations")
    try:
        with Archive(args.root) as archive:
            if args.command == "init":
                result = {"schema_version": archive.schema_version(), "interface": "offline_archive"}
            elif args.command == "put":
                sub = VersionSubmission.model_validate_json(args.metadata.read_bytes())
                result = archive.append(sub, args.body.read_bytes() if args.body else None).model_dump(mode="json")
            elif args.command == "get":
                stored = archive.get(args.version_id)
                if args.body_output:
                    body = archive.read_body(args.version_id)
                    with args.body_output.open("xb") as output:
                        output.write(body)
                result = stored.model_dump(mode="json")
            elif args.command == "read-reference":
                request = ReferenceReadRequest.model_validate_json(args.request.read_bytes())
                material = archive.read_reference(request)
                if args.body_output:
                    if material.body is None:
                        raise BodyUnavailable("INDEX returns metadata only; no body output can be created")
                    with args.body_output.open("xb") as output:
                        output.write(material.body)
                result = material.model_dump(mode="json", exclude={"body"})
            elif args.command in ("prepare", "verify-preparation"):
                from .preparation import PreparedTask, PreparationRequest, prepare_task, verify_prepared_task
                if args.command == "prepare":
                    if args.output.resolve().is_relative_to(Path(__file__).resolve().parents[1]) or args.output.resolve().is_relative_to(args.spec_root.resolve()):
                        raise ValueError("Prepared inputs must remain outside the public source directory")
                    request = PreparationRequest.model_validate_json(args.request.read_bytes())
                    prepared = prepare_task(request, archive, args.spec_root)
                    raw = (prepared.model_dump_json(indent=2)+"\n").encode()
                    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                    with os.fdopen(descriptor, "wb") as output:
                        output.write(raw)
                    output_identity = {"output_sha256": hashlib.sha256(raw).hexdigest(), "output_bytes": len(raw)}
                else:
                    supplied = PreparedTask.model_validate_json(args.bundle.read_bytes())
                    prepared = verify_prepared_task(supplied, archive, args.spec_root)
                    output_identity = {"verification": "CURRENT_INPUTS_RECHECKED"}
                result = {"preparation_id": prepared.request.preparation_id,
                    "spec_sha256": prepared.request.spec_sha256, "input_complete": prepared.input_complete,
                    "handoff": prepared.handoff, "provided_materials": len(prepared.materials),
                    "gaps": [gap.model_dump(mode="json") for gap in prepared.gaps],
                    "executed_nodes": prepared.executed_nodes, "provided_to_model": False, **output_identity}
                print(json.dumps(result, ensure_ascii=False))
                return 0 if prepared.input_complete else 3
            elif args.command == "find":
                result = {"navigation_only": True, "matches": archive.find(args.title)}
            elif args.command == "rebuild-index":
                result = {"navigation_only": True, "indexed_versions": archive.rebuild_index()}
            else:
                revoked = archive.revoke_body_retention(args.rights_id, args.reason)
                result = revoked.model_dump(mode="json")
                print(json.dumps(result, ensure_ascii=False))
                return 3 if revoked.failed_versions else 0
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ArchiveError, ValidationError, OSError, ValueError) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
