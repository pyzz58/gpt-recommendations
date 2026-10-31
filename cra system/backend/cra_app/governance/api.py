"""Identity and authorized workspace HTTP endpoints."""
from __future__ import annotations

import secrets
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict

from cra_app.governance.identity import (
    SESSION_COOKIE_NAME,
    AuthenticatedIdentity,
    IdentityError,
    IdentityUnavailable,
    OidcIdentityProvider,
    SyntheticIdentityProvider,
)
from cra_app.governance.service import GovernanceService, ScopeContext
from cra_app.shared.config import Settings

router = APIRouter(prefix="/api/v1", tags=["governance"])
CSRF_COOKIE_NAME = "cra_csrf"


class IdentityView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor_id: str
    mode: Literal["synthetic", "oidc"]
    authentication_source: str


class SessionView(BaseModel):
    authenticated: Literal[True] = True
    identity: IdentityView


class ScopeSite(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    revision: int


class ScopeStudy(BaseModel):
    id: uuid.UUID
    code: str
    title: str
    revision: int
    roles: list[str]
    sites: list[ScopeSite]


class ScopeResponse(BaseModel):
    actor_id: str
    authentication_mode: Literal["synthetic", "oidc"]
    studies: list[ScopeStudy]


def require_identity(request: Request) -> AuthenticatedIdentity:
    provider = request.app.state.identity_provider
    identity = provider.resolve(request.cookies.get(SESSION_COOKIE_NAME))
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "authentication_required",
                "message": "A valid CRA session is required",
            },
        )
    return identity


def scope_from_identity(identity: AuthenticatedIdentity) -> ScopeContext:
    return ScopeContext(
        actor_id=identity.actor_id,
        tenant_id=identity.tenant_id,
        authentication_source=identity.authentication_source,
        platform_roles=identity.platform_roles,
    )


def _session_view(identity: AuthenticatedIdentity) -> SessionView:
    return SessionView(
        identity=IdentityView(
            actor_id=identity.actor_id,
            mode=identity.mode,
            authentication_source=identity.authentication_source,
        )
    )


def _set_session_cookie(
    response: Response, token: str, settings: Settings
) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        secure=settings.resolved_cookie_secure(),
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=secrets.token_urlsafe(32),
        max_age=settings.session_max_age_seconds,
        httponly=False,
        secure=settings.resolved_cookie_secure(),
        samesite="lax",
        path="/",
    )


def require_csrf(
    request: Request,
    csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    if (
        not cookie_token
        or not csrf_token
        or not secrets.compare_digest(cookie_token, csrf_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "csrf_validation_failed",
                "message": "A matching CSRF token is required",
            },
        )


@router.post(
    "/auth/synthetic/session",
    response_model=SessionView,
    responses={403: {"description": "Synthetic identity is disabled"}},
)
def create_synthetic_session(
    request: Request,
) -> Response:
    provider = request.app.state.identity_provider
    if not isinstance(provider, SyntheticIdentityProvider):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "synthetic_auth_disabled",
                "message": "Synthetic identity is not available in this environment",
            },
        )
    try:
        identity = provider.create_identity()
        body = _session_view(identity)
        result = JSONResponse(body.model_dump(mode="json"))
        _set_session_cookie(
            result, provider.issue_session(identity), request.app.state.settings
        )
        return result
    except IdentityUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "synthetic_auth_disabled", "message": str(exc)},
        ) from exc


@router.get("/auth/oidc/login", include_in_schema=True)
async def oidc_login(request: Request):
    provider = request.app.state.identity_provider
    if not isinstance(provider, OidcIdentityProvider) or not provider.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "oidc_not_configured",
                "message": "OIDC identity has not been configured",
                "retryable": False,
            },
        )
    settings: Settings = request.app.state.settings
    redirect_uri = (
        settings.public_base_url.rstrip("/") + "/api/v1/auth/oidc/callback"
    )
    try:
        return await provider.authorize_redirect(request, redirect_uri)
    except IdentityUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "oidc_not_configured", "message": str(exc)},
        ) from exc


@router.get("/auth/oidc/callback", include_in_schema=False)
async def oidc_callback(request: Request):
    provider = request.app.state.identity_provider
    if not isinstance(provider, OidcIdentityProvider) or not provider.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "oidc_not_configured",
                "message": "OIDC identity has not been configured",
            },
        )
    try:
        token = await provider.authorize_access_token(request)
        identity = await provider.identity_from_token(token)
    except IdentityError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "oidc_authentication_failed",
                "message": "OIDC authentication could not be completed",
            },
        ) from exc
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    _set_session_cookie(
        response, provider.issue_session(identity), request.app.state.settings
    )
    return response


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def logout(request: Request) -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path="/",
        secure=request.app.state.settings.resolved_cookie_secure(),
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(
        CSRF_COOKIE_NAME,
        path="/",
        secure=request.app.state.settings.resolved_cookie_secure(),
        httponly=False,
        samesite="lax",
    )
    return response


@router.get(
    "/me/scopes",
    response_model=ScopeResponse,
    responses={401: {"description": "Authentication required"}},
)
def get_my_scopes(
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> ScopeResponse:
    service: GovernanceService = request.app.state.governance_service
    scope = scope_from_identity(identity)
    workspaces = service.list_authorized_workspaces(scope)
    return ScopeResponse(
        actor_id=identity.actor_id,
        authentication_mode=identity.mode,
        studies=[
            ScopeStudy(
                id=study.id,
                code=study.code,
                title=study.title,
                revision=study.revision,
                roles=list(study.roles),
                sites=[
                    ScopeSite(
                        id=site.id,
                        code=site.code,
                        name=site.name,
                        revision=site.revision,
                    )
                    for site in study.sites
                ],
            )
            for study in workspaces
        ],
    )
