from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ArtifactMode(StrEnum):
    MOCK = "mock"
    LIVE = "live"


class ArtifactOrigin(StrEnum):
    RAW = "raw"
    DERIVED = "derived"


@dataclass(frozen=True)
class StoredObject:
    object_key: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class ArtifactVersionRecord:
    id: UUID
    project_id: UUID
    artifact_id: UUID
    version: int
    object_key: str
    sha256: str
    size_bytes: int
    mode: ArtifactMode
