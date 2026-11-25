from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.errors import NotFoundError
from medical_one_person.infrastructure.db.models import Session as DatabaseSession
from medical_one_person.infrastructure.db.models import User


@dataclass(frozen=True)
class IssuedSession:
    session_id: UUID
    token: str
    expires_at: datetime


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    session_id: UUID
    user_id: UUID
    workspace_id: UUID
    display_name: str


class SessionService:
    """Issue opaque session tokens while storing only their SHA-256 digests."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def issue(self, *, user_id: UUID, ttl: timedelta = timedelta(hours=12)) -> IssuedSession:
        token = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        expires_at = now + ttl
        session_id = uuid4()
        with self._session_factory.begin() as session:
            user = session.get(User, user_id)
            if user is None:
                raise NotFoundError("User not found")
            session.add(
                DatabaseSession(
                    id=session_id,
                    workspace_id=user.workspace_id,
                    user_id=user.id,
                    session_hash=_session_hash(token),
                    created_at=now,
                    expires_at=expires_at,
                )
            )
        return IssuedSession(session_id=session_id, token=token, expires_at=expires_at)

    def authenticate(self, token: str) -> AuthenticatedPrincipal | None:
        if not token:
            return None
        now = datetime.now(UTC)
        with self._session_factory() as session:
            row = session.execute(
                select(DatabaseSession, User)
                .join(User, User.id == DatabaseSession.user_id)
                .where(
                    DatabaseSession.session_hash == _session_hash(token),
                    DatabaseSession.expires_at > now,
                    DatabaseSession.revoked_at.is_(None),
                )
            ).one_or_none()
            if row is None:
                return None
            database_session, user = row
            return AuthenticatedPrincipal(
                session_id=database_session.id,
                user_id=user.id,
                workspace_id=user.workspace_id,
                display_name=user.display_name,
            )

    def revoke(self, session_id: UUID) -> None:
        with self._session_factory.begin() as session:
            database_session = session.get(DatabaseSession, session_id)
            if database_session is not None and database_session.revoked_at is None:
                database_session.revoked_at = datetime.now(UTC)


def _session_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
