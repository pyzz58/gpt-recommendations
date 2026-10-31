"""FastAPI application entry point."""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from cra_app.documents.api import router as documents_router
from cra_app.documents.service import (
    DocumentIdempotencyConflict,
    DocumentJobConflict,
    DocumentNotFound,
    DocumentService,
    DocumentValidationError,
)
from cra_app.documents.storage import build_private_storage
from cra_app.governance.api import router as governance_router
from cra_app.governance.identity import IdentityProvider, build_identity_provider
from cra_app.governance.service import (
    AuthorizationDenied,
    GovernanceError,
    GovernanceService,
    IdempotencyConflict,
    InvalidCommand,
    ResourceAlreadyExists,
    ResourceNotFound,
    RevisionConflict,
)
from cra_app.platform.api import router as platform_router
from cra_app.platform.jobs import ProcrastinateQueue
from cra_app.rules.api import router as rules_router
from cra_app.rules.common_policy import load_common_policy_set
from cra_app.rules.service import (
    RuleNotFound,
    RuleService,
    RuleStateConflict,
    RuleValidationError,
)
from cra_app.subjects.api import router as subjects_router
from cra_app.subjects.service import (
    SubjectConflict,
    SubjectNotFound,
    SubjectService,
    SubjectValidationError,
)
from cra_app.shared.api_contract import ErrorDetail, ErrorEnvelope
from cra_app.shared.config import Settings, get_settings
from cra_app.shared.db import (
    build_engine,
    build_session_factory,
)
from cra_app.shared.output_contract import OutputEnvelope

LOGGER = logging.getLogger(__name__)


def _error(
    code: str,
    message: str,
    *,
    retryable: bool = False,
    details: dict | None = None,
) -> dict:
    return ErrorEnvelope(
        error=ErrorDetail(
            code=code,
            message=message,
            retryable=retryable,
            details=details,
        )
    ).model_dump(mode="json")


def create_app(
    *,
    settings: Settings | None = None,
    session_factory=None,
    identity_provider: IdentityProvider | None = None,
    document_service: DocumentService | None = None,
    rule_service: RuleService | None = None,
    subject_service: SubjectService | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    own_engine = None
    if session_factory is None:
        own_engine = build_engine(
            resolved_settings.sqlalchemy_url(),
            echo=resolved_settings.database_echo,
        )
        session_factory = build_session_factory(own_engine)
    resolved_provider = identity_provider or build_identity_provider(
        resolved_settings
    )
    if document_service is None:
        document_service = DocumentService(
            session_factory,
            storage=build_private_storage(resolved_settings),
            queue=ProcrastinateQueue(resolved_settings.sqlalchemy_url()),
            max_upload_bytes=resolved_settings.max_upload_bytes,
        )
    if rule_service is None:
        rule_service = RuleService(
            session_factory,
            common_policy_set=load_common_policy_set(
                resolved_settings.common_policy_path
            ),
        )
    governance_service = GovernanceService(session_factory)
    if subject_service is None:
        subject_service = SubjectService(
            session_factory,
            governance=governance_service,
            rules=rule_service,
        )

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        yield
        if own_engine is not None:
            own_engine.dispose()

    application = FastAPI(
        title="CRA System API",
        version="0.4.0",
        description=(
            "Synthetic-first CRA monitoring workbench API. Service health and "
            "implemented capabilities are reported separately from clinical use."
        ),
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.session_factory = session_factory
    application.state.identity_provider = resolved_provider
    application.state.governance_service = governance_service
    application.state.document_service = document_service
    application.state.rule_service = rule_service
    application.state.subject_service = subject_service

    application.add_middleware(
        SessionMiddleware,
        secret_key=resolved_settings.resolved_session_secret(),
        same_site="lax",
        https_only=resolved_settings.resolved_cookie_secure(),
        max_age=resolved_settings.session_max_age_seconds,
    )

    @application.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api/"):
            if "cache-control" not in response.headers:
                response.headers["Cache-Control"] = "no-store"
        return response

    @application.exception_handler(AuthorizationDenied)
    async def authorization_error(
        request: Request, exc: AuthorizationDenied
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=_error("authorization_denied", str(exc)),
        )

    @application.exception_handler(ResourceNotFound)
    async def not_found_error(
        request: Request, exc: ResourceNotFound
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_error("resource_not_found", str(exc)),
        )

    @application.exception_handler(RevisionConflict)
    async def revision_error(
        request: Request, exc: RevisionConflict
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error(
                "revision_conflict",
                str(exc),
                details={"current_revision": exc.current_revision},
            ),
        )

    @application.exception_handler(IdempotencyConflict)
    async def idempotency_error(
        request: Request, exc: IdempotencyConflict
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error("idempotency_conflict", str(exc)),
        )

    @application.exception_handler(InvalidCommand)
    async def invalid_command_error(
        request: Request, exc: InvalidCommand
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error("invalid_command", str(exc)),
        )

    @application.exception_handler(ResourceAlreadyExists)
    async def resource_exists_error(
        request: Request, exc: ResourceAlreadyExists
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error("resource_already_exists", str(exc)),
        )

    @application.exception_handler(GovernanceError)
    async def governance_error(
        request: Request, exc: GovernanceError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error("governance_error", str(exc)),
        )

    @application.exception_handler(DocumentValidationError)
    async def document_validation_error(
        request: Request, exc: DocumentValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error("document_validation_failed", str(exc)),
        )

    @application.exception_handler(DocumentNotFound)
    async def document_not_found_error(
        request: Request, exc: DocumentNotFound
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_error("document_not_found", str(exc)),
        )

    @application.exception_handler(DocumentIdempotencyConflict)
    async def document_idempotency_error(
        request: Request, exc: DocumentIdempotencyConflict
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error("document_idempotency_conflict", str(exc)),
        )

    @application.exception_handler(DocumentJobConflict)
    async def document_job_error(
        request: Request, exc: DocumentJobConflict
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error("document_job_conflict", str(exc)),
        )

    @application.exception_handler(RuleNotFound)
    async def rule_not_found_error(
        request: Request, exc: RuleNotFound
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_error("rule_not_found", str(exc)),
        )

    @application.exception_handler(RuleValidationError)
    async def rule_validation_error(
        request: Request, exc: RuleValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error("rule_validation_failed", str(exc)),
        )

    @application.exception_handler(RuleStateConflict)
    async def rule_state_conflict_error(
        request: Request, exc: RuleStateConflict
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error("rule_state_conflict", str(exc)),
        )

    @application.exception_handler(SubjectNotFound)
    async def subject_not_found_error(
        request: Request, exc: SubjectNotFound
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_error("subject_not_found", str(exc)),
        )

    @application.exception_handler(SubjectValidationError)
    async def subject_validation_error(
        request: Request, exc: SubjectValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error("subject_validation_failed", str(exc)),
        )

    @application.exception_handler(SubjectConflict)
    async def subject_conflict_error(
        request: Request, exc: SubjectConflict
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error("subject_conflict", str(exc)),
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error(
                "request_validation_failed",
                "The request did not match the API contract",
                details={
                    "fields": [
                        {
                            "location": list(item["loc"]),
                            "message": item["msg"],
                            "type": item["type"],
                        }
                        for item in exc.errors()
                    ]
                },
            ),
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_error(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict):
            code = str(detail.get("code", "http_error"))
            message = str(detail.get("message", "Request failed"))
            retryable = bool(detail.get("retryable", False))
        else:
            code = "http_error"
            message = str(detail)
            retryable = False
        return JSONResponse(
            status_code=exc.status_code,
            content=_error(code, message, retryable=retryable),
            headers=exc.headers,
        )

    @application.exception_handler(Exception)
    async def unexpected_error(
        request: Request, exc: Exception
    ) -> JSONResponse:
        LOGGER.exception(
            "Unhandled API error request_id=%s",
            getattr(request.state, "request_id", "unknown"),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error(
                "internal_error", "The request could not be completed"
            ),
        )

    application.include_router(platform_router)
    application.include_router(governance_router)
    application.include_router(documents_router)
    application.include_router(rules_router)
    application.include_router(subjects_router)

    def custom_openapi():
        if application.openapi_schema:
            return application.openapi_schema
        schema = get_openapi(
            title=application.title,
            version=application.version,
            description=application.description,
            routes=application.routes,
        )
        components = schema.setdefault("components", {}).setdefault(
            "schemas", {}
        )
        output_schema = OutputEnvelope.model_json_schema(
            ref_template="#/components/schemas/{model}"
        )
        definitions = output_schema.pop("$defs", {})
        components.update(definitions)
        components["OutputEnvelope"] = output_schema
        application.openapi_schema = schema
        return schema

    application.openapi = custom_openapi
    return application


app = create_app()
