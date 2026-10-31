from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.sessions import (
    AuthenticatedPrincipal,
    SessionService,
)
from medical_one_person.config import Settings
from medical_one_person.infrastructure.bootstrap import bootstrap_local_owner

SESSION_COOKIE_NAME = "medical_one_session"


class SessionView(BaseModel):
    session_id: UUID
    user_id: UUID
    workspace_id: UUID
    display_name: str
    expires_at: datetime | None


def build_principal_dependency(
    sessions: SessionService,
) -> Callable[[Request], AuthenticatedPrincipal]:
    def current_principal(request: Request) -> AuthenticatedPrincipal:
        token = request.cookies.get(SESSION_COOKIE_NAME, "")
        authorization = request.headers.get("Authorization", "")
        if not token and authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        principal = sessions.authenticate(token)
        if principal is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "NOT_AUTHORIZED",
                    "message": "A valid local session is required",
                    "retryable": False,
                    "details": {},
                },
            )
        return principal

    return current_principal


def build_session_router(
    settings: Settings,
    sessions: SessionService,
    session_factory: sessionmaker[Session],
    current_principal: Callable[[Request], AuthenticatedPrincipal],
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/system", tags=["session"])

    @router.post("/local-session", response_model=SessionView)
    def create_local_session(response: Response) -> SessionView:
        if settings.environment != "development":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "NOT_FOUND",
                    "message": "Local session bootstrap is unavailable",
                    "retryable": False,
                    "details": {},
                },
            )
        identity = bootstrap_local_owner(session_factory)
        issued = sessions.issue(user_id=identity.owner_user_id)
        principal = sessions.authenticate(issued.token)
        if principal is None:
            raise RuntimeError("Issued session could not be authenticated")
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=issued.token,
            max_age=12 * 60 * 60,
            httponly=True,
            secure=False,
            samesite="lax",
            path="/",
        )
        return SessionView(
            session_id=issued.session_id,
            user_id=identity.owner_user_id,
            workspace_id=identity.workspace_id,
            display_name=principal.display_name,
            expires_at=issued.expires_at,
        )

    @router.get("/session", response_model=SessionView)
    def read_session(
        request: Request,
    ) -> SessionView:
        principal = current_principal(request)
        return SessionView(
            session_id=principal.session_id,
            user_id=principal.user_id,
            workspace_id=principal.workspace_id,
            display_name=principal.display_name,
            expires_at=None,
        )

    return router
