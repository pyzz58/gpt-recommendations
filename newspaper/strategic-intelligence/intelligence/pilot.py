"""One controlled, private draft run using the existing Archive and W18 gate.

This is a thin content execution entry point, not another workflow engine or an
official Article/Review/Edition adoption path. All prose comes from actual HTTP
responses. Operator admissions, rights and finite budgets must already exist.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
from typing import Self

from pydantic import AwareDatetime, Field, model_validator

from .archive import (Archive, ArchiveError, Conflict, MissingVersion, canonical,
                      require_private_output_path, write_private_bytes)
from .contracts import (Contract, Digest, Identifier, MaterialUse, NonBlank, ObjectKind,
                        ReferenceReadRequest, ReferenceUse, Representation, RightsGrant,
                        UseContext, VersionReference, VersionSubmission)
from .gating import AdmissionMode, PreCallGate, ReservationEstimate
from .http_adapter import HttpAdapterConfig, HttpsAdapter
from .operations import ObservationKind, OperationKind, OperationRequest, OperationStatus
from .preparation import maintenance
from .presentation import _body_markup

STAGES = ("SELECTION", "ADVISER", "TEACHER", "CONDITIONS", "REVIEW")


class PilotRequest(Contract):
    pilot_id: Identifier
    task_version_id: Identifier
    spec_sha256: Digest
    title: NonBlank
    source_version_ids: tuple[Identifier, ...]
    writer: HttpAdapterConfig
    reviewer: HttpAdapterConfig
    writer_admission_id: Identifier
    reviewer_admission_id: Identifier
    stage_estimates: tuple[ReservationEstimate, ...]
    output_rights: RightsGrant
    created_at: AwareDatetime
    translation_requested: bool = False
    max_material_bytes: int = Field(default=400_000, ge=1024, le=4_000_000)

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if (not self.source_version_ids
                or len(self.source_version_ids) != len(set(self.source_version_ids))):
            raise ValueError("Pilot needs unique, exact source versions")
        if self.task_version_id in self.source_version_ids:
            raise ValueError("Task instructions must remain separate from source materials")
        if self.writer.kind != "CHAT" or self.reviewer.kind != "CHAT":
            raise ValueError("Pilot writer and reviewer must be CHAT adapters")
        if (self.writer.tool_id == self.reviewer.tool_id
                or self.writer_admission_id == self.reviewer_admission_id):
            raise ValueError("Review requires a separate tool role and admission")
        if len(self.stage_estimates) != len(STAGES):
            raise ValueError("Pilot needs a finite reservation for each of its five calls")
        return self


class FetchRequest(Contract):
    admission_id: Identifier
    configuration: HttpAdapterConfig
    operation: OperationRequest
    estimate: ReservationEstimate
    material: VersionSubmission


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def stage_id(pilot_id: str, stage: str) -> str:
    return "PILOT-OP-" + digest([pilot_id, stage])[:32]


def _get(archive, version_id):
    try:
        return archive.get(version_id)
    except MissingVersion:
        return None


def _append_exact(archive, metadata, body, context=None):
    old = _get(archive, metadata.version_id)
    if old is None:
        try:
            return archive.append(metadata, body, storage_context=context)
        except Conflict:
            old = archive.get(metadata.version_id)
    if (old.submission != metadata or archive.read_body(metadata.version_id) != body):
        raise Conflict("Pilot identity already binds different bytes or metadata")
    return old


class _Capture:
    """Persist exact response before the journal confirms success.

    If capture fails, W17 retains UNKNOWN; a restart never blindly repeats the
    accepted call. A missing receipt still requires real reconciliation.
    """
    def __init__(self, adapter, archive, metadata, context):
        self.adapter, self.archive = adapter, archive
        self.metadata, self.context = metadata, context

    def descriptor(self):
        return self.adapter.descriptor()

    def invoke(self, operation, payload):
        returned = self.adapter.invoke(operation, payload)
        if returned.status is OperationStatus.SUCCEEDED and returned.response_body is not None:
            _append_exact(self.archive, self.metadata.model_copy(update={
                'created_at': returned.ended_at}), returned.response_body, self.context)
        return returned


def fetch_material(archive: Archive, rights: RightsGrant, item: FetchRequest, *, adapter=None):
    """Execute one already admitted exact URL; retain bytes with explicit rights."""
    item = FetchRequest.model_validate_json(item.model_dump_json())
    cfg, op = item.configuration, item.operation
    if maintenance.assert_current()["spec_sha256"] != op.spec_sha256:
        raise ValueError("Fetch operation uses a stale canonical specification")
    if (cfg.kind != "FETCH" or op.kind is not OperationKind.DOWNLOAD
            or cfg.sha256 != op.configuration_sha256
            or item.material.spec_sha256 != op.spec_sha256
            or item.material.representation is not Representation.FULL_BODY
            or item.material.source_locator != cfg.endpoint
            or not any(r.target_version_id == op.operation_id for r in item.material.references)):
        raise ValueError("Fetch metadata must bind the exact source, operation and configuration")
    gate = PreCallGate(archive, rights)
    admission = gate.load_admission(item.admission_id)
    context = UseContext(at=datetime.now(timezone.utc), provider=op.provider_id,
                         territory=admission.territory)
    payload = canonical({"url": cfg.endpoint}).encode()
    result = gate.execute(item.admission_id, op,
        _Capture(adapter or HttpsAdapter(cfg), archive, item.material, context), payload, item.estimate)
    receipt = gate.journal.receipt(op.operation_id)
    if receipt.status is not OperationStatus.SUCCEEDED:
        raise ArchiveError("Source acquisition did not produce a confirmed successful result")
    return archive.get(item.material.version_id)


class PilotRunner:
    def __init__(self, archive: Archive, rights: RightsGrant, *, adapter_factory=HttpsAdapter):
        self.archive, self.rights = archive, rights
        self.gate = PreCallGate(archive, rights)
        self.adapter_factory = adapter_factory

    def run(self, request: PilotRequest, output: str | Path,
            spec_root: str | Path = maintenance.ROOT) -> dict:
        req = PilotRequest.model_validate_json(request.model_dump_json())
        target = require_private_output_path(output)
        if target.exists():
            raise FileExistsError("Pilot output already exists; choose a new private path")
        root = Path(spec_root)
        contract = maintenance.assert_current(root)
        if contract["spec_sha256"] != req.spec_sha256:
            raise ValueError("Pilot uses a stale canonical specification")
        text = (root / maintenance.SPEC).read_text(encoding="utf-8")
        policy = maintenance.trace.fenced_block(text, "PILOT_RUNTIME")
        if tuple(policy["stages"]) != STAGES or policy.get("publication_authorized") is not False:
            raise ValueError("Canonical pilot policy is incomplete or widens publication")
        task = self.archive.get(req.task_version_id)
        if (task.submission.kind is not ObjectKind.TASK
                or task.submission.spec_sha256 != req.spec_sha256
                or self.archive.latest(task.submission.object_id).submission.version_id != req.task_version_id):
            raise ValueError("Pilot requires the exact current Task and specification")
        # Validate every local prerequisite before the first billable call.
        adapters = {"writer": self.adapter_factory(req.writer),
                    "reviewer": self.adapter_factory(req.reviewer)}
        for adapter in adapters.values():
            adapter.preflight()
        admissions = {}
        for role, aid in (("writer", req.writer_admission_id), ("reviewer", req.reviewer_admission_id)):
            admission = self.gate.load_admission(aid)
            if (admission.mode is not AdmissionMode.CONTROLLED_TRIAL
                    or admission.task_version_id != req.task_version_id
                    or admission.spec_sha256 != req.spec_sha256):
                raise ValueError("Pilot needs explicit CONTROLLED_TRIAL admissions for this Task")
            admissions[role] = admission
        budgets = [self.gate.load_budget(a.budget_id) for a in admissions.values()]
        if len({b.run_id for b in budgets}) != 1:
            raise ValueError("Pilot admissions must bind the same run identity")
        for index, stage in enumerate(STAGES):
            role = "reviewer" if stage == "REVIEW" else "writer"
            aid = admissions[role]
            opid = stage_id(req.pilot_id, stage)
            if req.stage_estimates[index].operation_id != opid:
                raise ValueError("Stage estimate does not bind its deterministic operation ID")
            context = UseContext(at=datetime.now(timezone.utc), provider=aid.provider_id,
                                 territory=aid.territory)
            cfg = req.reviewer if role == 'reviewer' else req.writer
            kind = OperationKind.TRANSLATE if stage == 'SELECTION' and req.translation_requested else OperationKind.MODEL
            self.gate._validate_scope(aid, OperationRequest(
                operation_id=opid, idempotency_key=opid, run_id=budgets[0].run_id,
                task_version_id=req.task_version_id, step_id='PILOT-'+stage,
                spec_sha256=req.spec_sha256, kind=kind, tool_id=cfg.tool_id,
                tool_version=HttpsAdapter.VERSION, provider_id=cfg.provider_id,
                configuration_sha256=cfg.sha256, request_sha256='0'*64,
                material_use=MaterialUse.TRANSLATE if kind is OperationKind.TRANSLATE else MaterialUse.MODEL_PROCESS,
                created_at=req.created_at), adapters[role].descriptor(), datetime.now(timezone.utc))
            for vid in (req.task_version_id, *req.source_version_ids):
                stored = self.archive.get(vid)
                if self.archive.latest(stored.submission.object_id).submission.version_id != vid:
                    raise ValueError("A pilot source is superseded; create a new pilot basis")
                self.archive.check_version_use(vid, MaterialUse.MODEL_PROCESS, context)
                if vid != req.task_version_id and stage == 'SELECTION' and req.translation_requested:
                    self.archive.check_version_use(vid, MaterialUse.TRANSLATE, context)
        manifest_id = "PILOT-RUN-" + digest(req.pilot_id)[:32]
        now = req.created_at  # Declared request time; acquisition times come from actual receipts/DB.
        manifest = VersionSubmission(object_id=manifest_id, version_id=manifest_id,
            kind=ObjectKind.PILOT_DRAFT, title=req.title, spec_sha256=req.spec_sha256,
            created_at=now, rights=req.output_rights, representation=Representation.FULL_BODY,
            references=tuple(VersionReference(target_version_id=v, use=ReferenceUse.SOURCE,
                locator="exact pilot source") for v in req.source_version_ids))
        _append_exact(self.archive, manifest, canonical(req.model_dump(mode="json")).encode())
        for aid in admissions.values():
            self.archive.check_version_use(manifest_id, MaterialUse.MODEL_PROCESS,
                UseContext(at=datetime.now(timezone.utc), provider=aid.provider_id, territory=aid.territory))
        outputs, output_ids, model_observations = {}, [], []
        for index, stage in enumerate(STAGES):
            role = "reviewer" if stage == "REVIEW" else "writer"
            cfg = req.reviewer if role == "reviewer" else req.writer
            admission = admissions[role]
            aid = req.reviewer_admission_id if role == "reviewer" else req.writer_admission_id
            inputs = (req.task_version_id, *req.source_version_ids, *output_ids)
            if hashlib.sha256((root / maintenance.SPEC).read_bytes()).hexdigest() != req.spec_sha256:
                raise ValueError("Canonical specification changed during the pilot")
            for vid in req.source_version_ids:
                source = self.archive.get(vid)
                if self.archive.latest(source.submission.object_id).submission.version_id != vid:
                    raise ValueError("Source changed during the pilot; create a new basis")
            context = UseContext(at=datetime.now(timezone.utc), provider=cfg.provider_id,
                                 territory=admission.territory)
            opid = stage_id(req.pilot_id, stage)
            input_id = "PILOT-INPUT-" + digest([req.pilot_id, stage])[:32]
            envelope = VersionSubmission(object_id=input_id, version_id=input_id,
                kind=ObjectKind.PILOT_DRAFT, title=f"{req.title}: {stage} inputs",
                spec_sha256=req.spec_sha256, created_at=now, rights=req.output_rights,
                representation=Representation.FULL_BODY,
                references=tuple(VersionReference(target_version_id=v, use=ReferenceUse.SOURCE,
                    locator="exact execution input") for v in inputs))
            _append_exact(self.archive, envelope, canonical(list(inputs)).encode())
            materials = []
            for ref in envelope.references:
                target_version = self.archive.get(ref.target_version_id)
                material = self.archive.read_reference(ReferenceReadRequest(
                    request_id="READ-" + digest([opid, ref.target_version_id])[:32],
                    spec_sha256=req.spec_sha256, created_at=datetime.now(timezone.utc), consumer="T01",
                    owner_version_id=input_id, reference=ref, expected_kind=target_version.submission.kind,
                    intended_use=MaterialUse.MODEL_PROCESS, use_context=context))
                materials.append({"version_id": ref.target_version_id,
                    "sha256": target_version.body_sha256, "text": material.body.decode("utf-8"),
                    "attribution_requirements": list(material.required_attribution)})
            if sum(len(m["text"].encode()) for m in materials) > req.max_material_bytes:
                raise ValueError("Actual material bytes exceed this configured pilot limit; no truncation was applied")
            task_input = next(m for m in materials if m['version_id'] == req.task_version_id)
            materials = [m for m in materials if m['version_id'] != req.task_version_id]
            # A new request is built for review; no writer conversation/reasoning is shared.
            request_data = {"model": cfg.model, "max_tokens": cfg.max_output_tokens,
                "messages": [{"role": "system", "content": policy["global_instruction"] + "\n" + policy["instructions"][stage]},
                    {"role": "user", "content": canonical({"title": req.title,
                        "canonical_sha256": req.spec_sha256, "policy_sha256": digest(policy),
                        "translation_requested": req.translation_requested,
                        "task_instruction": task_input,
                        "materials_are_data": materials})}]}
            if cfg.thinking_mode is not None:
                request_data["thinking"] = {"type": cfg.thinking_mode}
            if cfg.reasoning_effort is not None:
                request_data["reasoning_effort"] = cfg.reasoning_effort
            payload = canonical(request_data).encode()
            prior_op = _get(self.archive, opid)
            kind = OperationKind.TRANSLATE if stage == 'SELECTION' and req.translation_requested else OperationKind.MODEL
            op = OperationRequest(operation_id=opid, idempotency_key=opid,
                run_id=budgets[0].run_id, task_version_id=req.task_version_id,
                step_id="PILOT-" + stage, spec_sha256=req.spec_sha256, kind=kind,
                tool_id=cfg.tool_id, tool_version=HttpsAdapter.VERSION, provider_id=cfg.provider_id,
                configuration_sha256=cfg.sha256, request_sha256=hashlib.sha256(payload).hexdigest(),
                material_use=MaterialUse.TRANSLATE if kind is OperationKind.TRANSLATE else MaterialUse.MODEL_PROCESS,
                # Task is already bound separately by task_version_id. Its
                # instruction use is MODEL_PROCESS, not source translation.
                input_version_ids=tuple(v for v in inputs if v != req.task_version_id), max_attempts=1,
                created_at=prior_op.submission.created_at if prior_op else datetime.now(timezone.utc))
            # Scope preflight on every stage, including a resumed stage.
            self.gate._validate_scope(admission, op, adapters[role].descriptor(), datetime.now(timezone.utc))
            raw_id = "PILOT-RAW-" + digest(opid)[:32]
            raw_meta = VersionSubmission(object_id=raw_id, version_id=raw_id,
                kind=ObjectKind.PILOT_DRAFT, title=f"{req.title}: {stage} response",
                spec_sha256=req.spec_sha256, created_at=now, rights=req.output_rights,
                representation=Representation.FULL_BODY,
                references=(VersionReference(target_version_id=opid, use=ReferenceUse.SOURCE,
                    locator="exact HTTP response for operation"),))
            receipt = self.gate.journal.receipt(opid)
            if receipt is None:
                self.gate.execute(aid, op,
                    _Capture(adapters[role], self.archive, raw_meta, context),
                    payload, req.stage_estimates[index])
                receipt = self.gate.journal.receipt(opid)
            persisted_op = OperationRequest.model_validate_json(self.archive.read_body(opid))
            if persisted_op.request_sha256 != op.request_sha256:
                raise Conflict("Existing pilot operation binds another actual input")
            if receipt.status is not OperationStatus.SUCCEEDED:
                raise ArchiveError("Pilot stage is failed/UNKNOWN; reconcile before any retry")
            raw = self.archive.read_body(raw_id)
            if hashlib.sha256(raw).hexdigest() != receipt.result_sha256:
                raise ArchiveError("Stored provider bytes do not match the successful receipt")
            try:
                response = json.loads(raw)
                choice = response["choices"][0]
                content = choice["message"]["content"]
                observed_model = response["model"]
            except (ValueError, KeyError, TypeError, IndexError):
                raise ValueError("Provider response does not contain a valid completion") from None
            if (choice.get("finish_reason") != "stop"
                    or not isinstance(content, str) or not content.strip()):
                raise ValueError("Model output is empty or incomplete; draft was not completed")
            if not isinstance(observed_model, str) or not observed_model.strip():
                raise ValueError("Provider response does not identify the served model")
            model_observations.append({
                "stage": stage,
                "requested_model": cfg.model,
                "observed_model": observed_model,
                "system_fingerprint": response.get("system_fingerprint"),
            })
            oid = "PILOT-TEXT-" + digest(opid)[:32]
            output_meta = VersionSubmission(object_id=oid, version_id=oid,
                kind=ObjectKind.PILOT_DRAFT, title=f"{req.title}: {stage}",
                spec_sha256=req.spec_sha256, created_at=receipt.ended_at, rights=req.output_rights,
                representation=Representation.FULL_BODY,
                references=(VersionReference(target_version_id=raw_id, use=ReferenceUse.SOURCE,
                    locator="actual generated content"), VersionReference(target_version_id=input_id,
                    use=ReferenceUse.BASIS, locator="actual supplied inputs")))
            _append_exact(self.archive, output_meta, content.encode(), context)
            outputs[stage], output_ids = content, [*output_ids, oid]
        # All reads/rights are rechecked on restart; output text is escaped by W32's existing renderer.
        if hashlib.sha256((root / maintenance.SPEC).read_bytes()).hexdigest() != req.spec_sha256:
            raise ValueError('Canonical specification changed before draft output')
        for vid in req.source_version_ids:
            source = self.archive.get(vid)
            if self.archive.latest(source.submission.object_id).submission.version_id != vid:
                raise ValueError('Source changed before draft output')
            for aid in admissions.values():
                self.archive.check_version_use(vid, MaterialUse.MODEL_PROCESS,
                    UseContext(at=datetime.now(timezone.utc), provider=aid.provider_id, territory=aid.territory))
        pieces = [f"<!doctype html><html lang='zh'><meta charset='utf-8'><title>{html.escape(req.title)}</title>",
            "<style>body{max-width:900px;margin:3em auto;padding:1em;line-height:1.9;font-family:serif}p{white-space:pre-wrap}</style>",
            f"<h1>{html.escape(req.title)}</h1><p>研究试刊 · 待最终审阅 · 未获出版或自动交付授权</p>"]
        for stage in STAGES:
            pieces.append("<h2>" + html.escape(policy["labels"][stage]) + "</h2>" + str(_body_markup(outputs[stage])))
        pieces.append("<h2>模型身份</h2><ul>" + "".join(
            "<li>" + html.escape(
                f"{item['stage']}: requested={item['requested_model']}; "
                f"served={item['observed_model']}; fingerprint={item['system_fingerprint']}")
            + "</li>" for item in model_observations) + "</ul>")
        pieces.append("<h2>来源版本</h2><ul>" + "".join("<li>" + html.escape(v) + "</li>" for v in req.source_version_ids) + "</ul></html>")
        body = "\n".join(pieces).encode()
        write_private_bytes(target, body)
        return {"pilot_id": req.pilot_id, "state": "DRAFT_AWAITING_REVIEW",
            "publication_authorized": False, "formal_acceptance": False,
            "output": str(target), "output_sha256": hashlib.sha256(body).hexdigest(),
            "output_version_ids": output_ids,
            "model_observations": model_observations,
            "operation_ids": [stage_id(req.pilot_id, s) for s in STAGES]}
