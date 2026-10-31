from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person import __version__
from medical_one_person.agents.config import load_role_configs
from medical_one_person.api.artifacts import build_artifact_export_router
from medical_one_person.api.audits import build_audit_router
from medical_one_person.api.datasets import build_dataset_router
from medical_one_person.api.errors import install_error_handlers
from medical_one_person.api.external import build_external_router
from medical_one_person.api.knowledge import build_knowledge_router
from medical_one_person.api.mail import build_mail_router
from medical_one_person.api.plans import build_plan_router
from medical_one_person.api.policies import build_policy_router
from medical_one_person.api.recovery import build_recovery_router
from medical_one_person.api.session import (
    build_principal_dependency,
    build_session_router,
)
from medical_one_person.api.system import build_system_router
from medical_one_person.api.workflows import build_workflow_router
from medical_one_person.api.workspace import build_workspace_router
from medical_one_person.application.knowledge import KnowledgeIndexService
from medical_one_person.application.knowledge_ingestion import (
    KnowledgeIngestionService,
)
from medical_one_person.application.recovery import RecoveryService
from medical_one_person.application.sessions import SessionService
from medical_one_person.config import Settings, get_settings
from medical_one_person.contracts import DependencyStatus
from medical_one_person.domain.artifacts import ArtifactMode
from medical_one_person.infrastructure.artifacts import LocalArtifactStore
from medical_one_person.infrastructure.db.engine import (
    create_database_engine,
    database_status,
)
from medical_one_person.infrastructure.exports.renderer import OfficeRenderer
from medical_one_person.infrastructure.exports.templates import load_export_templates
from medical_one_person.infrastructure.knowledge.parsers import DocumentParser
from medical_one_person.infrastructure.knowledge.upload import UploadService
from medical_one_person.infrastructure.mail.mock import MailAdapter, MockMailAdapter
from medical_one_person.infrastructure.skills.registry import SkillRegistry
from medical_one_person.infrastructure.sources import load_source_policies
from medical_one_person.infrastructure.workflows import WorkflowRegistry


def create_app(
    database_checker: Callable[[], DependencyStatus] | None = None,
    *,
    settings_override: Settings | None = None,
    session_factory_override: sessionmaker[Session] | None = None,
    mail_adapter_override: MailAdapter | None = None,
) -> FastAPI:
    settings = settings_override or get_settings()
    roles = load_role_configs(settings.agent_config_path)
    skills = SkillRegistry.from_catalog(settings.skill_config_path)
    skills.validate_against_roles(roles)
    source_policies = load_source_policies(settings.source_policy_path)
    workflows = WorkflowRegistry.from_catalog(
        settings.workflow_catalog_path,
        roles,
    )
    export_templates = load_export_templates(settings.export_template_path)
    theory_hash = hashlib.sha256(settings.theory_path.read_bytes()).hexdigest()
    if session_factory_override is None:
        engine = create_database_engine(settings.database_url)
        session_factory: sessionmaker[Session] = sessionmaker(
            bind=engine,
            expire_on_commit=False,
        )
        checker = database_checker or (lambda: database_status(engine))
    else:
        engine = None
        session_factory = session_factory_override
        if database_checker is None:
            raise ValueError("database_checker is required with an injected session factory")
        checker = database_checker

    sessions = SessionService(session_factory)
    current_principal = build_principal_dependency(sessions)
    store = LocalArtifactStore(
        settings.artifact_root,
        max_bytes=settings.artifact_max_bytes,
    )
    uploads = UploadService(
        session_factory,
        store,
        settings.knowledge_staging_root,
        max_file_bytes=settings.knowledge_max_file_bytes,
        max_batch_bytes=settings.knowledge_max_batch_bytes,
        chunk_size=settings.knowledge_upload_chunk_size,
    )
    ingestion = KnowledgeIngestionService(session_factory, store, DocumentParser())
    indexer = KnowledgeIndexService(session_factory)
    recovery = RecoveryService(
        session_factory,
        store,
        indexer,
        backup_root=settings.backup_root,
        restore_root=settings.restore_root,
    )
    office_renderer = OfficeRenderer(
        soffice_path=settings.office_soffice_path,
        pdftoppm_path=settings.office_pdftoppm_path,
        timeout_seconds=settings.office_conversion_timeout_seconds,
        max_pages=settings.office_max_preview_pages,
    )
    mail_adapter = mail_adapter_override or MockMailAdapter()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if engine is not None:
            engine.dispose()

    app = FastAPI(
        title="医疗一人项目 API",
        version=__version__,
        description=(
            "W15 local research workbench. Immutable datasets and analyses, versioned "
            "plans, project knowledge, validated Office/PDF exports and an explicitly "
            "authorized mock mailbox use real PostgreSQL state; unavailable capabilities "
            "are reported explicitly."
        ),
        lifespan=lifespan,
    )
    app.state.agent_roles = roles
    app.state.skills = skills
    app.state.source_policies = source_policies
    app.state.workflows = workflows
    app.state.export_templates = export_templates
    app.state.office_renderer = office_renderer
    app.state.mail_adapter = mail_adapter
    app.state.recovery = recovery
    app.state.theory_hash = theory_hash

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    install_error_handlers(app)

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        origin = request.headers.get("Origin")
        if (
            request.method in {"POST", "PUT", "DELETE"}
            and request.url.path.startswith("/api/")
            and origin
            and origin not in settings.allowed_origins
        ):
            return JSONResponse(
                status_code=403,
                content={
                    "code": "NOT_AUTHORIZED",
                    "message": "Request origin is not allowed",
                    "request_id": request_id,
                    "retryable": False,
                    "details": {},
                },
                headers={"X-Request-ID": request_id},
            )
        try:
            response = await call_next(request)
        except Exception:
            return JSONResponse(
                status_code=500,
                content={
                    "code": "INTERNAL_ERROR",
                    "message": "Unexpected server error",
                    "request_id": request_id,
                    "retryable": False,
                    "details": {},
                },
                headers={"X-Request-ID": request_id},
            )
        response.headers["X-Request-ID"] = request_id
        return response

    app.include_router(
        build_system_router(
            settings,
            checker,
            DependencyStatus(
                status="ready",
                detail=f"{len(roles)} role contracts loaded; mock provider only",
            ),
            DependencyStatus(
                status="ready",
                detail=(
                    f"registry loaded: "
                    f"{sum(item.state.value == 'ready' for item in skills.list())} ready, "
                    f"{sum(item.state.value != 'ready' for item in skills.list())} unavailable"
                ),
            ),
            DependencyStatus(
                status="not_checked",
                detail=(
                    f"{len(source_policies)} professional source policies loaded; "
                    "live scholarly adapters are not connected"
                ),
            ),
        )
    )
    app.include_router(
        build_session_router(
            settings,
            sessions,
            session_factory,
            current_principal,
        )
    )
    app.include_router(
        build_workspace_router(
            session_factory,
            roles,
            current_principal,
        )
    )
    app.include_router(
        build_knowledge_router(
            session_factory,
            store,
            uploads,
            ingestion,
            indexer,
            current_principal,
        )
    )
    app.include_router(
        build_plan_router(
            session_factory,
            roles,
            workflows,
            theory_hash,
            current_principal,
        )
    )
    app.include_router(
        build_policy_router(
            session_factory,
            settings,
            current_principal,
        )
    )
    app.include_router(
        build_workflow_router(
            session_factory,
            workflows,
            roles,
            current_principal,
        )
    )
    app.include_router(
        build_dataset_router(
            session_factory,
            store,
            roles,
            current_principal,
        )
    )
    app.include_router(
        build_artifact_export_router(
            session_factory,
            store,
            office_renderer,
            export_templates,
            current_principal,
            mode=(
                ArtifactMode.MOCK
                if settings.app_mode == "mock"
                else ArtifactMode.LIVE
            ),
            pdf_font_path=settings.office_pdf_font_path,
        )
    )
    app.include_router(
        build_mail_router(
            session_factory,
            store,
            mail_adapter,
            current_principal,
        )
    )
    app.include_router(
        build_external_router(
            session_factory,
            current_principal,
        )
    )
    app.include_router(
        build_audit_router(
            session_factory,
            roles,
            settings.audit_fixture_path,
            current_principal,
        )
    )
    app.include_router(
        build_recovery_router(
            recovery,
            current_principal,
        )
    )
    return app


app = create_app()
