"""Offline W13 CLI; no source fetching, model calls, approval or delivery.

uv run --locked python -m intelligence --root /private/archive init
uv run --locked python -m intelligence --root /private/archive put --metadata record.json --body draft.md
uv run --locked python -m intelligence --root /private/archive get VERSION --body-output recovered.md
uv run --locked python -m intelligence schema --contract reference-read
uv run --locked python -m intelligence --root /private/archive read-reference --request request.json --body-output material.bin

The schema command defaults to VersionSubmission. read-reference checks a
committed owner/reference, exact target kind/body identity and declared purpose;
its stdout contains metadata only. get is local recovery, not a downstream-use
grant. Consumer labels do not authenticate a caller or approve content.
created_at/source times come from input; recorded_at is assigned at commit.
"""
from __future__ import annotations

import argparse
import json
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
    schema.add_argument("--contract", choices=("version", "reference-read"), default="version")
    put = commands.add_parser("put")
    put.add_argument("--metadata", required=True, type=Path)
    put.add_argument("--body", type=Path)
    get = commands.add_parser("get")
    get.add_argument("version_id")
    get.add_argument("--body-output", type=Path, help="Create a new file; never overwrite")
    read = commands.add_parser("read-reference")
    read.add_argument("--request", required=True, type=Path)
    read.add_argument("--body-output", type=Path, help="Create a new file; never overwrite")
    commands.add_parser("rebuild-index")
    find = commands.add_parser("find")
    find.add_argument("title")
    revoke = commands.add_parser("revoke")
    revoke.add_argument("rights_id")
    revoke.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    if args.command == "schema":
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
