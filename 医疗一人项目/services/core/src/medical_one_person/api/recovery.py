from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request

from medical_one_person.application.recovery import RecoveryService
from medical_one_person.application.sessions import AuthenticatedPrincipal
from medical_one_person.domain.recovery import (
    BackupCreateRequest,
    BackupView,
    IndexRebuildView,
    RecoveryWorkspaceView,
    RestoreCheckRequest,
    RestoreCheckView,
    TrashDocumentRequest,
    TrashEntryView,
)


def build_recovery_router(
    service: RecoveryService,
    current_principal: Callable[[Request], AuthenticatedPrincipal],
) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/projects/{project_id}/recovery",
        tags=["recovery"],
    )

    @router.get("", response_model=RecoveryWorkspaceView)
    def workspace(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> RecoveryWorkspaceView:
        return service.workspace(
            project_id=project_id,
            actor_user_id=principal.user_id,
        )

    @router.post(
        "/trash/{document_id}",
        response_model=TrashEntryView,
        status_code=201,
    )
    def trash_document(
        project_id: UUID,
        document_id: UUID,
        request: TrashDocumentRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> TrashEntryView:
        return service.trash_document(
            project_id=project_id,
            document_id=document_id,
            actor_user_id=principal.user_id,
            reason=request.reason,
        )

    @router.post(
        "/trash/{document_id}/restore",
        response_model=TrashEntryView,
    )
    def restore_document(
        project_id: UUID,
        document_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> TrashEntryView:
        return service.restore_document(
            project_id=project_id,
            document_id=document_id,
            actor_user_id=principal.user_id,
        )

    @router.post(
        "/versions/{version_id}/rebuild-index",
        response_model=IndexRebuildView,
    )
    def rebuild_index(
        project_id: UUID,
        version_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> IndexRebuildView:
        return service.rebuild_index(
            project_id=project_id,
            version_id=version_id,
            actor_user_id=principal.user_id,
        )

    @router.post(
        "/backups",
        response_model=BackupView,
        status_code=201,
    )
    def create_backup(
        project_id: UUID,
        request: BackupCreateRequest,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> BackupView:
        return service.create_backup(
            project_id=project_id,
            actor_user_id=principal.user_id,
            passphrase=request.passphrase,
            idempotency_key=idempotency_key,
        )

    @router.post(
        "/backups/{backup_id}/restore-check",
        response_model=RestoreCheckView,
        status_code=201,
    )
    def restore_check(
        project_id: UUID,
        backup_id: UUID,
        request: RestoreCheckRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> RestoreCheckView:
        return service.restore_check(
            project_id=project_id,
            backup_id=backup_id,
            actor_user_id=principal.user_id,
            passphrase=request.passphrase,
        )

    return router
