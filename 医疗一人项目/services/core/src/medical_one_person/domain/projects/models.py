from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ProjectStage(StrEnum):
    DRAFT = "draft"
    SCREENING = "screening"
    AWAITING_SELECTION = "awaiting_selection"
    PLANNED = "planned"
    ACTIVE = "active"
    WAITING_EXTERNAL = "waiting_external"
    PAUSED = "paused"
    STOPPED = "stopped"
    ARCHIVED = "archived"


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    SCREENING = "screening"
    AWAITING_SELECTION = "awaiting_selection"
    PLANNED = "planned"
    ACTIVE = "active"
    WAITING_EXTERNAL = "waiting_external"
    PAUSED = "paused"
    STOPPED = "stopped"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class ProjectSnapshot:
    id: UUID
    workspace_id: UUID
    name: str
    scope: str
    stage: ProjectStage
    status: ProjectStatus
    revision: int
    created_at: datetime
    updated_at: datetime
    policy_bundle_id: str | None = None
