"""Offline W13 CLI; no source fetching, model calls, approval or delivery.

uv run --locked python -m intelligence --root /private/archive init
uv run --locked python -m intelligence --root /private/archive put --metadata record.json --body draft.md
uv run --locked python -m intelligence --root /private/archive get VERSION --body-output recovered.md
uv run --locked python -m intelligence schema --contract reference-read
uv run --locked python -m intelligence --root /private/archive read-reference --request request.json --body-output material.bin
uv run --locked --extra workflow python -m intelligence --root /private/archive prepare --request preparation.json --output /private/prepared.json
uv run --locked --extra workflow python -m intelligence --root /private/archive verify-preparation /private/prepared.json
uv run --locked python -m intelligence --root /private/archive submit-step --record submission.json --rights journal-rights.json
uv run --locked python -m intelligence --root /private/archive decide-step --record decision.json --rights journal-rights.json
uv run --locked python -m intelligence --root /private/archive current-decision W15 M01
uv run --locked python -m intelligence --root /private/archive operation-summary LOGICAL-OP-1

The schema command defaults to VersionSubmission. read-reference checks a
committed owner/reference, exact target kind/body identity and declared purpose;
its stdout contains metadata only. get is local recovery, not a downstream-use
grant. Consumer labels do not authenticate a caller or approve content.
W14 prepares separate canonical/task/material fields, with no model invocation.
created_at/source times come from input; recorded_at is assigned at commit.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from pydantic import ValidationError

from .archive import Archive, ArchiveError, BodyUnavailable, write_private_bytes
from .contracts import MaterialUse, ReferenceReadRequest, RightsBasis, RightsGrant, VersionSubmission


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, help="Explicit private archive directory")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    schema = commands.add_parser("schema")
    schema.add_argument("--contract",
        choices=("version", "reference-read", "preparation", "step-submission",
                 "adoption-decision", "operation-request", "tool-response"),
        default="version")
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
    submit_step = commands.add_parser("submit-step", help="Record a producer submission without an adoption decision")
    submit_step.add_argument("--record", required=True, type=Path)
    submit_step.add_argument("--rights", required=True, type=Path)
    decide_step = commands.add_parser("decide-step", help="Record an authoritative decision after exact checks")
    decide_step.add_argument("--record", required=True, type=Path)
    decide_step.add_argument("--rights", required=True, type=Path)
    current_decision = commands.add_parser("current-decision")
    current_decision.add_argument("work_id")
    current_decision.add_argument("step_id")
    operation_summary = commands.add_parser("operation-summary")
    operation_summary.add_argument("idempotency_key")
    commands.add_parser("rebuild-index")
    find = commands.add_parser("find")
    find.add_argument("title")
    revoke = commands.add_parser("revoke")
    revoke.add_argument("rights_id")
    revoke.add_argument("--reason", required=True)
    revoke_use = commands.add_parser("revoke-use", help="Withdraw selected uses while retaining unrelated history")
    revoke_use.add_argument("rights_id")
    revoke_use.add_argument("--use", action="append", required=True,
        choices=[item.value for item in MaterialUse if item is not MaterialUse.INDEX])
    revoke_use.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    if args.command == "schema":
        if args.contract == "preparation":
            from .preparation import PreparationRequest
            contract = PreparationRequest
        elif args.contract == "step-submission":
            from .adoption import StepSubmission
            contract = StepSubmission
        elif args.contract == "adoption-decision":
            from .adoption import AdoptionDecision
            contract = AdoptionDecision
        elif args.contract == "operation-request":
            from .operations import OperationRequest
            contract = OperationRequest
        elif args.contract == "tool-response":
            from .operations import ToolResponse
            contract = ToolResponse
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
                    write_private_bytes(args.body_output, body)
                result = stored.model_dump(mode="json")
            elif args.command == "read-reference":
                request = ReferenceReadRequest.model_validate_json(args.request.read_bytes())
                material = archive.read_reference(request)
                if args.body_output:
                    if material.body is None:
                        raise BodyUnavailable("INDEX returns metadata only; no body output can be created")
                    write_private_bytes(args.body_output, material.body)
                result = material.model_dump(mode="json", exclude={"body"})
            elif args.command in ("prepare", "verify-preparation"):
                from .preparation import PreparedTask, PreparationRequest, prepare_task, verify_prepared_task
                if args.command == "prepare":
                    if args.output.resolve().is_relative_to(Path(__file__).resolve().parents[1]) or args.output.resolve().is_relative_to(args.spec_root.resolve()):
                        raise ValueError("Prepared inputs must remain outside the public source directory")
                    request = PreparationRequest.model_validate_json(args.request.read_bytes())
                    prepared = prepare_task(request, archive, args.spec_root)
                    raw = (prepared.model_dump_json(indent=2)+"\n").encode()
                    write_private_bytes(args.output, raw)
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
            elif args.command in ("submit-step", "decide-step"):
                from .adoption import AdoptionController, DecisionRequest, StepSubmission
                controller = AdoptionController(archive,
                    RightsGrant.model_validate_json(args.rights.read_bytes()))
                if args.command == "submit-step":
                    submitted = controller.submit(StepSubmission.model_validate_json(args.record.read_bytes()))
                    result = {"submission_id": submitted.submission.version_id,
                              "kind": submitted.submission.kind.value,
                              "adoption": "NOT_DECIDED"}
                else:
                    decided = controller.decide(DecisionRequest.model_validate_json(args.record.read_bytes()))
                    decision = controller.load(decided.submission.version_id)
                    result = {"decision_id": decision.decision_id, "state": decision.state.value,
                              "allowed_scope": decision.allowed_scope,
                              "publication_authorized": False}
                print(json.dumps(result, ensure_ascii=False))
                return 0
            elif args.command == "current-decision":
                from .adoption import AdoptionController
                rights = RightsGrant(rights_id="RIGHTS-CURRENT-QUERY",basis=RightsBasis.OWN_WORK,
                    allowed_uses=frozenset({MaterialUse.INDEX}),evidence="Read-only query selector",
                    checked_by="CLI query",checked_at=datetime.now(timezone.utc))
                decision = AdoptionController(archive,rights).current(args.work_id,args.step_id)
                print(json.dumps(
                    {"state": decision.state.value if decision else "PENDING",
                     "decision": decision.model_dump(mode="json") if decision else None},
                    ensure_ascii=False))
                return 0
            elif args.command == "operation-summary":
                from dataclasses import asdict
                from .operations import OperationJournal
                rights = RightsGrant(rights_id="RIGHTS-OPERATION-QUERY",basis=RightsBasis.OWN_WORK,
                    allowed_uses=frozenset({MaterialUse.INDEX}),evidence="Read-only query selector",
                    checked_by="CLI query",checked_at=datetime.now(timezone.utc))
                summary = OperationJournal(archive,rights).summary(args.idempotency_key)
                print(json.dumps(asdict(summary), ensure_ascii=False, default=str))
                return 0
            elif args.command == "find":
                result = {"navigation_only": True, "matches": archive.find(args.title)}
            elif args.command == "rebuild-index":
                result = {"navigation_only": True, "indexed_versions": archive.rebuild_index()}
            elif args.command == "revoke":
                revoked = archive.revoke_body_retention(args.rights_id, args.reason)
                result = revoked.model_dump(mode="json")
                print(json.dumps(result, ensure_ascii=False))
                return 3 if revoked.failed_versions else 0
            else:
                revoked = archive.revoke_rights(
                    args.rights_id, tuple(MaterialUse(value) for value in args.use), args.reason)
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
