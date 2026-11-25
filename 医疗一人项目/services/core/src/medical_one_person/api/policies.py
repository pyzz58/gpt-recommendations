from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.policy_bundles import PolicyBundleService
from medical_one_person.application.sessions import AuthenticatedPrincipal
from medical_one_person.config import Settings
from medical_one_person.domain.policy_bundles import (
    PolicyBundleView,
    PolicyMigrationKind,
    PolicyMigrationView,
    PolicyProjectView,
)


class ActivatePolicyBundleRequest(BaseModel):
    bundle_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_revision: int = Field(ge=1)


class MigrationDryRunRequest(BaseModel):
    target_bundle_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    kind: PolicyMigrationKind
    schema_revision: str | None = Field(default=None, max_length=64)
    backup_ref: str | None = Field(default=None, max_length=300)
    expected_project_revision: int = Field(ge=1)


def build_policy_router(
    session_factory: sessionmaker[Session],
    settings: Settings,
    current_principal: Callable[[Request], AuthenticatedPrincipal],
) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["policy"])
    policies = PolicyBundleService(session_factory, settings=settings)

    @router.get("/projects/{project_id}/policy", response_model=PolicyProjectView)
    def project_policy(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> PolicyProjectView:
        return policies.project_view(
            project_id=project_id,
            actor_user_id=principal.user_id,
        )

    @router.post(
        "/projects/{project_id}/policy/publish",
        response_model=PolicyBundleView,
        status_code=201,
    )
    def publish_policy_bundle(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> PolicyBundleView:
        policies.project_view(
            project_id=project_id,
            actor_user_id=principal.user_id,
        )
        return policies.publish_from_config(
            workspace_id=principal.workspace_id,
            actor_user_id=principal.user_id,
        )

    @router.post(
        "/projects/{project_id}/policy/activate",
        response_model=PolicyProjectView,
    )
    def activate_policy_bundle(
        project_id: UUID,
        request: ActivatePolicyBundleRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> PolicyProjectView:
        return policies.activate_project_bundle(
            project_id=project_id,
            bundle_id=request.bundle_id,
            actor_user_id=principal.user_id,
            expected_revision=request.expected_revision,
        )

    @router.post(
        "/projects/{project_id}/policy/migrations/dry-run",
        response_model=PolicyMigrationView,
        status_code=201,
    )
    def dry_run_policy_migration(
        project_id: UUID,
        request: MigrationDryRunRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> PolicyMigrationView:
        return policies.dry_run_migration(
            project_id=project_id,
            target_bundle_id=request.target_bundle_id,
            kind=request.kind,
            schema_revision=request.schema_revision,
            backup_ref=request.backup_ref,
            expected_project_revision=request.expected_project_revision,
            actor_user_id=principal.user_id,
        )

    @router.post(
        "/projects/{project_id}/policy/migrations/{operation_id}/apply",
        response_model=PolicyMigrationView,
    )
    def apply_policy_migration(
        project_id: UUID,
        operation_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> PolicyMigrationView:
        return policies.apply_migration(
            project_id=project_id,
            operation_id=operation_id,
            actor_user_id=principal.user_id,
        )

    @router.post(
        "/projects/{project_id}/policy/migrations/{operation_id}/rollback",
        response_model=PolicyMigrationView,
    )
    def rollback_policy_migration(
        project_id: UUID,
        operation_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> PolicyMigrationView:
        return policies.rollback_migration(
            project_id=project_id,
            operation_id=operation_id,
            actor_user_id=principal.user_id,
        )

    return router
