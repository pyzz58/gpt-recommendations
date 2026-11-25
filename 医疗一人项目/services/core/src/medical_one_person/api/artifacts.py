from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.exports import (
    ArtifactExportService,
    ArtifactExportView,
)
from medical_one_person.application.sessions import AuthenticatedPrincipal
from medical_one_person.domain.artifacts import ArtifactMode
from medical_one_person.domain.exports import ExportFormat
from medical_one_person.infrastructure.artifacts import LocalArtifactStore
from medical_one_person.infrastructure.exports.renderer import OfficeRenderer
from medical_one_person.infrastructure.exports.templates import ExportTemplateRegistry


class CreateArtifactExportRequest(BaseModel):
    analysis_id: UUID
    format: ExportFormat
    template_id: str | None = Field(default=None, max_length=100)
    title: str | None = Field(default=None, min_length=1, max_length=300)


class ArtifactExportRuntimeView(BaseModel):
    status: str
    detail: str
    soffice_path: str | None
    pdftoppm_path: str | None
    versions: dict[str, str]
    templates: list[dict[str, str | int]]


def build_artifact_export_router(
    session_factory: sessionmaker[Session],
    store: LocalArtifactStore,
    renderer: OfficeRenderer,
    templates: ExportTemplateRegistry,
    current_principal: Callable[[Request], AuthenticatedPrincipal],
    *,
    mode: ArtifactMode,
    pdf_font_path: Path | None,
) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/projects/{project_id}/artifact-exports",
        tags=["artifact-exports"],
    )

    @router.get("", response_model=list[ArtifactExportView])
    def list_exports(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> list[ArtifactExportView]:
        service = _service(store, renderer, templates)
        return service.list_exports(
            project_id=project_id,
            actor_user_id=principal.user_id,
        )

    @router.get("/runtime", response_model=ArtifactExportRuntimeView)
    def export_runtime(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> ArtifactExportRuntimeView:
        service = _service(store, renderer, templates)
        runtime = service.runtime_status(
            project_id=project_id,
            actor_user_id=principal.user_id,
        )
        return ArtifactExportRuntimeView(
            status=runtime.status,
            detail=runtime.detail,
            soffice_path=runtime.soffice_path,
            pdftoppm_path=runtime.pdftoppm_path,
            versions=runtime.versions,
            templates=[
                {
                    "template_id": template.template_id,
                    "version": template.version,
                    "name": template.name,
                    "format": template.format.value,
                    "description": template.description,
                }
                for template in templates.templates
            ],
        )

    @router.post("", response_model=ArtifactExportView, status_code=201)
    def create_export(
        project_id: UUID,
        request: CreateArtifactExportRequest,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> ArtifactExportView:
        service = _service(store, renderer, templates)
        return service.create_export(
            project_id=project_id,
            actor_user_id=principal.user_id,
            analysis_id=request.analysis_id,
            export_format=request.format,
            template_id=request.template_id,
            title=request.title,
            idempotency_key=idempotency_key,
        )

    @router.get("/{export_id}/download")
    def download_export(
        project_id: UUID,
        export_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> Response:
        service = _service(store, renderer, templates)
        result = service.read_output(
            project_id=project_id,
            export_id=export_id,
            actor_user_id=principal.user_id,
        )
        return Response(
            result.content,
            media_type=result.media_type,
            headers=_file_headers(result.filename, inline=False),
        )

    @router.get("/{export_id}/preview.pdf")
    def preview_pdf(
        project_id: UUID,
        export_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> Response:
        service = _service(store, renderer, templates)
        content = service.read_preview(
            project_id=project_id,
            export_id=export_id,
            actor_user_id=principal.user_id,
            png=False,
        )
        return Response(
            content,
            media_type="application/pdf",
            headers=_file_headers(f"preview-{export_id}.pdf", inline=True),
        )

    @router.get("/{export_id}/preview.png")
    def preview_png(
        project_id: UUID,
        export_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> Response:
        service = _service(store, renderer, templates)
        content = service.read_preview(
            project_id=project_id,
            export_id=export_id,
            actor_user_id=principal.user_id,
            png=True,
        )
        return Response(
            content,
            media_type="image/png",
            headers=_file_headers(f"preview-{export_id}.png", inline=True),
        )

    def _service(
        export_store: LocalArtifactStore,
        export_renderer: OfficeRenderer,
        export_templates: ExportTemplateRegistry,
    ) -> ArtifactExportService:
        return ArtifactExportService(
            session_factory,
            export_store,
            export_renderer,
            export_templates,
            mode=mode,
            pdf_font_path=pdf_font_path,
        )

    return router


def _file_headers(filename: str, *, inline: bool) -> dict[str, str]:
    safe_ascii = "".join(
        character if 32 <= ord(character) < 127 and character not in {'"', "\\"} else "_"
        for character in filename
    )[:180]
    disposition = "inline" if inline else "attachment"
    return {
        "Content-Disposition": (
            f'{disposition}; filename="{safe_ascii or "artifact"}"; '
            f"filename*=UTF-8''{quote(filename)}"
        ),
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
    }
