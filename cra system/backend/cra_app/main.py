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

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        yield
        if own_engine is not None:
            own_engine.dispose()

    application = FastAPI(
        title="CRA System API",
        version="0.2.0",
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
    application.state.governance_service = GovernanceService(session_factory)

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
