from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TrashState(StrEnum):
    TRASHED = "trashed"
    RESTORED = "restored"
    PURGED = "purged"


class NetworkMode(StrEnum):
    OFFLINE = "offline"
    ALLOWLISTED = "allowlisted"


class TrashDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reason: str = Field(min_length=3, max_length=5_000)


class TrashEntryView(BaseModel):
    id: UUID
    document_id: UUID
    title: str
    reference_count: int
    blocked_reason: str | None
    reason: str
    state: TrashState
    purge_after: datetime
    deleted_at: datetime
    restored_at: datetime | None


class IndexRebuildView(BaseModel):
    version_id: UUID
    chunks: int
    state: str
    index_version: str
    rebuilt: bool


class BackupCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    passphrase: str = Field(min_length=12, max_length=1_024)


class BackupView(BaseModel):
    id: UUID
    project_id: UUID
    format: str
    file_name: str
    state: Literal["completed", "failed"]
    backup_sha256: str | None
    plaintext_sha256: str | None
    encrypted_size_bytes: int
    manifest: dict[str, Any]
    error_code: str | None
    created_at: datetime


class RestoreCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    passphrase: str = Field(min_length=12, max_length=1_024)


class RestoreCheckView(BaseModel):
    id: UUID
    backup_id: UUID
    state: Literal["verified", "failed"]
    object_count: int
    table_counts: dict[str, int]
    detail: dict[str, Any]
    created_at: datetime


class RecoveryWorkspaceView(BaseModel):
    trash: list[TrashEntryView]
    backups: list[BackupView]
    restore_checks: list[RestoreCheckView]
    limitations: list[str]
