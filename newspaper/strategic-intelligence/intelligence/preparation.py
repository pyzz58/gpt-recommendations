"""W14 / T01.L01, R07.F01: offline input preparation, not content adoption.

The initial implementation supplies the complete canonical document. It does
not infer a shorter equivalent, claim model capacity, or claim model reception.
Rules, caller task instructions and material bytes remain separate fields.
Selective extraction, semantic dependency review and W15 decisions are separate.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langsmith import tracing_context
from pydantic import AwareDatetime, Field, model_validator

from .archive import Archive, ArchiveError
from .contracts import (Contract, Digest, Identifier, NonBlank, ObjectKind,
    ReferencedMaterial, ReferenceReadRequest, StoredVersion)

PROJECT = Path(__file__).resolve().parents[1]
_source = importlib.util.spec_from_file_location("si_preparation_sync", PROJECT/"tools/sync_spec.py")
maintenance = importlib.util.module_from_spec(_source)
_source.loader.exec_module(maintenance)

# Exact anchors for §24.6 item 2; never a substitute for the complete source.
GLOBAL_ANCHORS = ("th-0", "th-1", "th-2", "th-6", "th-18", "th-19-2", "th-20", "th-24")


class PreparationError(ValueError):
    """Input identity/completeness failure, not a research quality decision."""


class MaterialNeed(Contract):
    input_id: Identifier
    read: ReferenceReadRequest
    purpose_in_task: NonBlank
    declared_nature: NonBlank
    declared_limits: tuple[NonBlank, ...]
    required: bool = True
    require_body: bool = True


class PreparationRequest(Contract):
    schema_version: int = Field(default=1, ge=1, le=1)
    preparation_id: Identifier
    spec_sha256: Digest
    created_at: AwareDatetime
    work_id: Identifier
    task_version_id: Identifier
    responsibility: NonBlank
    instructions: NonBlank
    materials: tuple[MaterialNeed, ...] = ()

    @model_validator(mode="after")
    def exact_task_dependencies(self):
        if len({need.input_id for need in self.materials}) != len(self.materials):
            raise ValueError("Duplicate material input ID")
        for need in self.materials:
            if need.read.owner_version_id != self.task_version_id:
                raise ValueError("Input reference owner must be this exact task version")
            if need.read.spec_sha256 != self.spec_sha256:
                raise ValueError("Input read request must declare the same specification")
        return self


class CanonicalInput(Contract):
    source: Literal["CANONICAL_SYSTEM_SPEC_V5.md"] = "CANONICAL_SYSTEM_SPEC_V5.md"
    spec_sha256: Digest
    text: str = Field(min_length=1)
    bytes_count: int = Field(ge=1)
    global_anchors: tuple[Identifier, ...]
    technical_anchors: tuple[Identifier, ...]
    method: Literal["PROGRAM_FULL_CANONICAL"] = "PROGRAM_FULL_CANONICAL"

    @model_validator(mode="after")
    def exact_source_bytes(self):
        raw = self.text.encode("utf-8")
        if len(raw) != self.bytes_count or _digest(raw) != self.spec_sha256:
            raise ValueError("Canonical text does not match its declared byte identity")
        return self


class InputGap(Contract):
    input_id: Identifier
    code: NonBlank
    message: NonBlank
    required: bool


class ProvidedMaterial(Contract):
    need: MaterialNeed
    retrieved: ReferencedMaterial


class PreparedTask(Contract):
    model_config = {"ser_json_bytes": "base64", "val_json_bytes": "base64"}

    request: PreparationRequest
    normative: CanonicalInput | None
    task: StoredVersion | None
    materials: tuple[ProvidedMaterial, ...]
    gaps: tuple[InputGap, ...]
    input_complete: bool
    handoff: Literal["W15_INPUT_CHECK", "REPAIR_INPUTS"]
    executed_nodes: tuple[NonBlank, ...]
    prepared_at: AwareDatetime
    generator_sha256: Digest
    task_record_scope: Literal["METADATA_ONLY"] = "METADATA_ONLY"
    provided_to_model: Literal[False] = False
    model_receive_scope: Literal["NOT_ATTEMPTED"] = "NOT_ATTEMPTED"


class _State(TypedDict, total=False):
    request: PreparationRequest
    normative: CanonicalInput | None
    task: StoredVersion | None
    materials: tuple[ProvidedMaterial, ...]
    gaps: tuple[InputGap, ...]
    executed_nodes: tuple[str, ...]
    result: PreparedTask


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _graph(archive: Archive, spec_root: Path):
    def check_current(state: _State):
        req = state["request"]
        try:
            raw = (spec_root/maintenance.SPEC).read_bytes()
            if _digest(raw) != req.spec_sha256:
                raise PreparationError("Task preparation uses a stale specification")
            # Reuse trusted maintenance code; never execute files from spec_root.
            plan = maintenance.assert_work_plan_current(spec_root, [req.work_id])
            card = next(item for item in plan["items"] if item["id"] == req.work_id)
            trace = maintenance.assert_technical_current(spec_root, card["technical_nodes"])
            anchors = tuple(next(n["design_anchor"] for n in trace["nodes"] if n["id"] == node)
                            for node in card["technical_nodes"])
            text = raw.decode("utf-8")
            for anchor in (*GLOBAL_ANCHORS, *anchors):
                if text.count(f'<a id="{anchor}"></a>') != 1:
                    raise PreparationError(f"Missing or ambiguous canonical anchor: {anchor}")
            # No selected excerpt can silently drop a negative or exception.
            normative = CanonicalInput(spec_sha256=req.spec_sha256, text=text,
                bytes_count=len(raw), global_anchors=GLOBAL_ANCHORS, technical_anchors=anchors)
            return {"normative": normative, "gaps": (), "executed_nodes": ("check_current",)}
        except (ValueError, OSError, KeyError, StopIteration) as exc:
            return {"normative": None, "gaps": (InputGap(input_id="SPEC", code="SPEC_INPUT_INVALID",
                message=str(exc) or "Unknown work card", required=True),), "executed_nodes": ("check_current",)}

    def supply_inputs(state: _State):
        req = state["request"]
        gaps, supplied, task = [], [], None
        try:
            task = archive.get(req.task_version_id)
            if task.submission.kind is not ObjectKind.TASK:
                raise PreparationError("Preparation owner is not a Task")
            if task.submission.spec_sha256 != req.spec_sha256:
                raise PreparationError("Task version belongs to a different specification")
            planned = {need.read.reference for need in req.materials}
            if any(ref not in planned for ref in task.submission.references):
                raise PreparationError("A committed task reference has no explicit input disposition")
        except (ArchiveError, ValueError) as exc:
            gaps.append(InputGap(input_id="TASK", code="TASK_INPUT_INVALID", message=str(exc), required=True))
        if not gaps:
            for need in req.materials:
                try:
                    material = archive.read_reference(need.read)
                    if need.require_body and material.body is None:
                        raise PreparationError("Only metadata was provided; this dependency requires body bytes")
                    supplied.append(ProvidedMaterial(need=need, retrieved=material))
                except (ArchiveError, ValueError, OSError) as exc:
                    gaps.append(InputGap(input_id=need.input_id, code=type(exc).__name__,
                        message=str(exc), required=need.required))
        return {"task": task, "materials": tuple(supplied), "gaps": tuple(gaps),
                "executed_nodes": (*state["executed_nodes"], "supply_inputs")}

    def finish(state: _State, complete: bool):
        node = "handoff_inputs" if complete else "repair_inputs"
        return {"result": PreparedTask(request=state["request"], normative=state.get("normative"),
            task=state.get("task"), materials=state.get("materials", ()), gaps=state["gaps"],
            input_complete=complete, handoff="W15_INPUT_CHECK" if complete else "REPAIR_INPUTS",
            executed_nodes=(*state["executed_nodes"], node), prepared_at=datetime.now(timezone.utc),
            generator_sha256=_digest(Path(__file__).read_bytes()))}

    builder = StateGraph(_State)
    builder.add_node("check_current", check_current)
    builder.add_node("supply_inputs", supply_inputs)
    builder.add_node("repair_inputs", lambda state: finish(state, False))
    builder.add_node("handoff_inputs", lambda state: finish(state, True))
    builder.add_edge(START, "check_current")
    builder.add_conditional_edges("check_current", lambda state: "repair" if state["gaps"] else "supply",
                                  {"repair": "repair_inputs", "supply": "supply_inputs"})
    builder.add_conditional_edges("supply_inputs", lambda state: "repair" if any(g.required for g in state["gaps"]) else "handoff",
                                  {"repair": "repair_inputs", "handoff": "handoff_inputs"})
    builder.add_edge("repair_inputs", END)
    builder.add_edge("handoff_inputs", END)
    return builder.compile()


def prepare_task(request: PreparationRequest, archive: Archive, spec_root: Path = PROJECT) -> PreparedTask:
    if not isinstance(request, PreparationRequest):
        raise TypeError("prepare_task requires a PreparationRequest")
    req = PreparationRequest.model_validate_json(request.model_dump_json(warnings=False))
    # W14 is local-only even if the host happens to have tracing configured.
    with tracing_context(enabled=False):
        return _graph(archive, Path(spec_root)).invoke({"request": req})["result"]


def _input_identity(prepared: PreparedTask) -> dict:
    value = json.loads(prepared.model_dump_json(exclude={"prepared_at"}))
    for material in value["materials"]:
        # The retrieval time changes on a real recheck; the actual inputs may not.
        material["retrieved"].pop("recorded_at")
    return value


def verify_prepared_task(prepared: PreparedTask, archive: Archive, spec_root: Path = PROJECT) -> PreparedTask:
    """Re-read current source and exact input bytes before handing to W15.

    This detects edited/omitted rules, spoofed receipts, stale source, changed
    permissions and changed/missing bytes. It does not confer adoption authority.
    """
    if not isinstance(prepared, PreparedTask):
        raise TypeError("verify_prepared_task requires a PreparedTask")
    supplied = PreparedTask.model_validate_json(prepared.model_dump_json(warnings=False))
    fresh = prepare_task(supplied.request, archive, spec_root)
    if _input_identity(supplied) != _input_identity(fresh):
        raise PreparationError("Prepared input differs from the current source or actual material retrieval; regenerate")
    return fresh
