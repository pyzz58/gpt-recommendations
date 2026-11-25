from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class PolicyBundleState(StrEnum):
    PUBLISHED = "published"
    RETIRED = "retired"


class PolicyImpactStatus(StrEnum):
    RECORDED = "recorded"
    APPLIED = "applied"


class PolicyMigrationKind(StrEnum):
    CONFIG = "config"
    DATABASE = "database"


class PolicyMigrationState(StrEnum):
    DRY_RUN_PASSED = "dry_run_passed"
    DRY_RUN_FAILED = "dry_run_failed"
    APPLYING = "applying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class PolicyBundleView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    workspace_id: str
    version_label: str
    content_sha256: str
    theory_version: str
    theory_sha256: str
    component_sha256: dict[str, str]
    state: PolicyBundleState
    created_at: datetime


class PolicyImpactView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    project_id: str
    from_bundle_id: str | None
    to_bundle_id: str
    changed_components: list[str]
    affected_requirements: list[str]
    affected_task_ids: list[str]
    status: PolicyImpactStatus
    created_at: datetime


class PolicyMigrationView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    project_id: str
    kind: PolicyMigrationKind
    from_bundle_id: str | None
    to_bundle_id: str
    expected_project_revision: int
    schema_revision: str | None
    state: PolicyMigrationState
    report: dict[str, Any]
    backup_ref: str | None
    error_code: str | None
    created_at: datetime
    finished_at: datetime | None


class PolicyProjectView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    project_revision: int
    active_bundle: PolicyBundleView | None
    project_bundle: PolicyBundleView | None
    impacts: list[PolicyImpactView]
    migrations: list[PolicyMigrationView]
    limitations: list[str]
