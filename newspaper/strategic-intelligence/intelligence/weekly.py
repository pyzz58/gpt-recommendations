"""Durable weekly-run identity and checkpoints on the shared Archive.

This module does not replace the existing source, research, review or edition
controllers. It records which exact existing artifacts have completed each
weekly stage so that another runner can resume without chat state or manual
reconstruction.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import hashlib
from typing import Literal, Self

from pydantic import AwareDatetime, model_validator

from .archive import Archive, ArchiveError, Conflict, canonical
from .contracts import (
    Contract, Digest, Identifier, NonBlank, ObjectKind, ReferenceUse,
    Representation, RightsGrant, VersionReference, VersionSubmission,
)


class WeeklyStage(str, Enum):
    SOURCE = "SOURCE"
    PREPARE = "PREPARE"
    DRAFT = "DRAFT"
    RESEARCH = "RESEARCH"
    REVIEW = "REVIEW"
    REPAIR = "REPAIR"
    EDITION = "EDITION"
    VERIFY = "VERIFY"
    DELIVERY = "DELIVERY"


class WeeklyCheckpointDisposition(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    LIMITED = "LIMITED"
    SKIPPED = "SKIPPED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class WeeklyRunState(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    COMPLETE = "COMPLETE"


_DEFAULT_STAGES = tuple(WeeklyStage)


class WeeklyRunRequest(Contract):
    schema_version: Literal[1] = 1
    weekly_run_id: Identifier
    issue_id: NonBlank
    source_week_start: AwareDatetime
    source_week_end: AwareDatetime
    knowledge_cutoff: AwareDatetime
    source_timezone: NonBlank
    task_version_id: Identifier
    spec_sha256: Digest
    purpose: NonBlank
    planned_stages: tuple[WeeklyStage, ...] = _DEFAULT_STAGES
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if not self.planned_stages:
            raise ValueError("A weekly run needs at least one stage")
        if len(self.planned_stages) != len(set(self.planned_stages)):
            raise ValueError("Weekly stages must be unique")
        if not (
                self.source_week_start < self.source_week_end
                <= self.knowledge_cutoff <= self.created_at):
            raise ValueError(
                "Weekly window, cutoff and creation time are not ordered")
        return self


class WeeklyCheckpointRequest(Contract):
    schema_version: Literal[1] = 1
    weekly_run_id: Identifier
    expected_manifest_version_id: Identifier
    stage: WeeklyStage
    disposition: WeeklyCheckpointDisposition
    artifact_version_ids: tuple[Identifier, ...] = ()
    external_operation_ids: tuple[Identifier, ...] = ()
    note: NonBlank
    next_action: NonBlank | None = None
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("artifact", self.artifact_version_ids),
                ("operation", self.external_operation_ids)):
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate weekly {name}")
        if (self.disposition in {
                WeeklyCheckpointDisposition.SUCCEEDED,
                WeeklyCheckpointDisposition.LIMITED,
        } and not self.artifact_version_ids):
            raise ValueError("A usable weekly checkpoint needs exact artifacts")
        if (self.disposition in {
                WeeklyCheckpointDisposition.BLOCKED,
                WeeklyCheckpointDisposition.FAILED,
                WeeklyCheckpointDisposition.UNKNOWN,
        } and not self.next_action):
            raise ValueError("A stopped weekly checkpoint needs a next action")
        return self


class WeeklyCheckpoint(Contract):
    sequence: int
    checkpoint_id: Identifier
    stage: WeeklyStage
    disposition: WeeklyCheckpointDisposition
    artifact_version_ids: tuple[Identifier, ...]
    external_operation_ids: tuple[Identifier, ...]
    note: NonBlank
    next_action: NonBlank | None
    created_at: AwareDatetime


class WeeklyRunRecord(Contract):
    schema_version: Literal[1] = 1
    request: WeeklyRunRequest
    state: WeeklyRunState
    checkpoints: tuple[WeeklyCheckpoint, ...]
    next_stage: WeeklyStage | None
    updated_at: AwareDatetime


class WeeklyRunError(ArchiveError):
    """Weekly identity/checkpoint failure, never content or delivery approval."""


def _digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _object_id(weekly_run_id: str) -> str:
    return "WEEKLY-RUN-OBJECT-" + _digest([weekly_run_id])[:32]


class WeeklyRunController:
    def __init__(self, archive: Archive, rights: RightsGrant):
        if not isinstance(archive, Archive):
            raise TypeError("WeeklyRunController requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError("WeeklyRunController requires journal rights")
        self.archive = archive
        self.rights = rights

    def _load(self, version_id: str) -> tuple:
        stored = self.archive.get(version_id)
        if stored.submission.kind is not ObjectKind.DOCUMENT:
            raise WeeklyRunError("Weekly run record has the wrong object kind")
        record = WeeklyRunRecord.model_validate_json(
            self.archive.read_body(version_id))
        if (stored.submission.title
                != f"weekly run {record.request.weekly_run_id}"
                or stored.submission.created_at != record.updated_at):
            raise WeeklyRunError("Weekly run record identity mismatch")
        return stored, record

    def latest(self, weekly_run_id: str) -> tuple | None:
        stored = self.archive.latest(_object_id(weekly_run_id))
        if stored is None:
            return None
        _, record = self._load(stored.submission.version_id)
        if record.request.weekly_run_id != weekly_run_id:
            raise WeeklyRunError("Weekly run object identity mismatch")
        return stored, record

    def claim(self, request: WeeklyRunRequest) -> tuple:
        if not isinstance(request, WeeklyRunRequest):
            raise TypeError("claim requires WeeklyRunRequest")
        req = WeeklyRunRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        task = self.archive.get(req.task_version_id)
        if (task.submission.kind is not ObjectKind.TASK
                or task.submission.spec_sha256 != req.spec_sha256):
            raise WeeklyRunError("Weekly run Task/specification mismatch")
        object_id = _object_id(req.weekly_run_id)
        latest = self.archive.latest(object_id)
        if latest is not None:
            _, existing = self._load(latest.submission.version_id)
            if existing.request != req:
                raise WeeklyRunError(
                    "Weekly run identity already exists with different inputs")
            return latest, existing
        record = WeeklyRunRecord(
            request=req, state=WeeklyRunState.CREATED, checkpoints=(),
            next_stage=req.planned_stages[0], updated_at=req.created_at)
        body = canonical(record.model_dump(mode="json")).encode()
        version_id = "WEEKLY-RUN-" + _digest([
            req.weekly_run_id, None, record.model_dump(mode="json")])[:32]
        stored = self.archive.append(
            VersionSubmission(
                schema_version=2, object_id=object_id, version_id=version_id,
                parent_version_id=None, kind=ObjectKind.DOCUMENT,
                title=f"weekly run {req.weekly_run_id}",
                spec_sha256=req.spec_sha256, created_at=req.created_at,
                rights=self.rights, representation=Representation.FULL_BODY,
                references=(VersionReference(
                    target_version_id=req.task_version_id,
                    use=ReferenceUse.BASIS, locator="weekly Task"),)),
            body, expected_current={object_id: None})
        return stored, record

    @staticmethod
    def _checkpoint_id(request: WeeklyCheckpointRequest) -> str:
        return "WEEKLY-CHECKPOINT-" + _digest([
            request.weekly_run_id, request.expected_manifest_version_id,
            request.stage.value, request.disposition.value,
            request.artifact_version_ids, request.external_operation_ids,
            request.note, request.next_action, request.created_at.isoformat(),
        ])[:32]

    def checkpoint(self, request: WeeklyCheckpointRequest) -> tuple:
        if not isinstance(request, WeeklyCheckpointRequest):
            raise TypeError("checkpoint requires WeeklyCheckpointRequest")
        req = WeeklyCheckpointRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        checkpoint_id = self._checkpoint_id(req)
        object_id = _object_id(req.weekly_run_id)
        # A checkpoint ID is stored inside the manifest, not as the manifest's
        # own version ID. Search the run's append history before applying the
        # expected-current check so an exact retry is idempotent.
        for existing in reversed(self.archive.history(object_id)):
            _, record = self._load(existing.submission.version_id)
            if any(item.checkpoint_id == checkpoint_id
                   for item in record.checkpoints):
                return existing, record
        latest = self.archive.latest(object_id)
        if latest is None:
            raise WeeklyRunError("Weekly run has not been claimed")
        if latest.submission.version_id != req.expected_manifest_version_id:
            raise Conflict("Weekly run manifest changed before checkpoint")
        _, current = self._load(latest.submission.version_id)
        if (current.state is WeeklyRunState.COMPLETE
                or current.next_stage is None):
            raise WeeklyRunError("Weekly run is already complete")
        if req.stage is not current.next_stage:
            raise WeeklyRunError(
                f"Expected next weekly stage {current.next_stage.value}, "
                f"found {req.stage.value}")
        if req.created_at < latest.submission.created_at:
            raise WeeklyRunError("Weekly checkpoint predates its manifest")
        for version_id in req.artifact_version_ids:
            self.archive.get(version_id)
        sequence = len(current.checkpoints) + 1
        checkpoint = WeeklyCheckpoint(
            sequence=sequence, checkpoint_id=checkpoint_id,
            stage=req.stage, disposition=req.disposition,
            artifact_version_ids=req.artifact_version_ids,
            external_operation_ids=req.external_operation_ids,
            note=req.note, next_action=req.next_action,
            created_at=req.created_at)
        stopped = req.disposition in {
            WeeklyCheckpointDisposition.BLOCKED,
            WeeklyCheckpointDisposition.FAILED,
            WeeklyCheckpointDisposition.UNKNOWN,
        }
        state = (
            WeeklyRunState.BLOCKED if stopped
            else WeeklyRunState.RUNNING)
        next_stage = req.stage if stopped else None
        if not stopped:
            try:
                index = current.request.planned_stages.index(req.stage)
            except ValueError as exc:
                raise WeeklyRunError("Weekly stage is outside the run plan") from exc
            if index + 1 < len(current.request.planned_stages):
                next_stage = current.request.planned_stages[index + 1]
            else:
                state = WeeklyRunState.COMPLETE
        record = WeeklyRunRecord(
            request=current.request, state=state,
            checkpoints=(*current.checkpoints, checkpoint),
            next_stage=next_stage, updated_at=req.created_at)
        body = canonical(record.model_dump(mode="json")).encode()
        version_id = "WEEKLY-RUN-" + _digest([
            current.request.weekly_run_id, latest.submission.version_id,
            checkpoint_id, record.model_dump(mode="json")])[:32]
        references = [
            VersionReference(
                target_version_id=latest.submission.version_id,
                use=ReferenceUse.BASIS, locator="previous weekly manifest"),
            VersionReference(
                target_version_id=current.request.task_version_id,
                use=ReferenceUse.BASIS, locator="weekly Task"),
        ]
        references.extend(
            VersionReference(
                target_version_id=version_id, use=ReferenceUse.SUPPORT,
                locator=f"weekly artifact {index}")
            for index, version_id in enumerate(req.artifact_version_ids))
        references.extend(
            VersionReference(
                target_version_id=version_id, use=ReferenceUse.SUPPORT,
                locator=f"external operation {index}")
            for index, version_id in enumerate(req.external_operation_ids))
        stored = self.archive.append(
            VersionSubmission(
                schema_version=2, object_id=latest.submission.object_id,
                version_id=version_id,
                parent_version_id=latest.submission.version_id,
                kind=ObjectKind.DOCUMENT,
                title=f"weekly run {current.request.weekly_run_id}",
                spec_sha256=current.request.spec_sha256,
                created_at=req.created_at, rights=self.rights,
                representation=Representation.FULL_BODY,
                references=tuple(references)),
            body, expected_current={
                latest.submission.object_id: latest.submission.version_id})
        return stored, record

    def resume_plan(self, weekly_run_id: str) -> dict:
        latest = self.latest(weekly_run_id)
        if latest is None:
            return {
                "state": "NOT_CLAIMED", "next_stage": None,
                "manifest_version_id": None,
            }
        stored, record = latest
        return {
            "state": record.state.value,
            "next_stage": (
                record.next_stage.value if record.next_stage else None),
            "manifest_version_id": stored.submission.version_id,
            "checkpoints": [
                {
                    "sequence": item.sequence,
                    "stage": item.stage.value,
                    "disposition": item.disposition.value,
                    "artifact_version_ids": item.artifact_version_ids,
                    "next_action": item.next_action,
                }
                for item in record.checkpoints
            ],
        }
