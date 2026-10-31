"""Trusted identity adapters for synthetic development and OIDC deployments."""
from __future__ import annotations

from typing import Literal, Protocol

from authlib.integrations.starlette_client import OAuth
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.requests import Request

from cra_app.shared.config import Settings

SESSION_COOKIE_NAME = "cra_session"


class IdentityError(Exception):
    """Identity cannot be established from the supplied credential."""


class IdentityUnavailable(IdentityError):
    """The selected identity provider is not configured."""


class AuthenticatedIdentity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    actor_id: str = Field(min_length=1, max_length=128)
    tenant_id: str = Field(min_length=1, max_length=128)
    authentication_source: str = Field(min_length=1, max_length=128)
    mode: Literal["synthetic", "oidc"]
    platform_roles: frozenset[Literal["platform_admin"]] = frozenset()


class IdentityProvider(Protocol):
    mode: Literal["synthetic", "oidc"]
    available: bool

    def issue_session(self, identity: AuthenticatedIdentity) -> str: ...

    def resolve(self, token: str | None) -> AuthenticatedIdentity | None: ...


class SignedSessionCodec:
    def __init__(self, secret: str, max_age_seconds: int):
        self._max_age_seconds = max_age_seconds
        self._serializer = URLSafeTimedSerializer(
            secret, salt="cra-session-v1"
        )

    def issue(self, identity: AuthenticatedIdentity) -> str:
        return self._serializer.dumps(identity.model_dump(mode="json"))

    def resolve(self, token: str | None) -> AuthenticatedIdentity | None:
        if not token:
            return None
        try:
            raw = self._serializer.loads(
                token, max_age=self._max_age_seconds
            )
            return AuthenticatedIdentity.model_validate(raw)
        except (BadSignature, SignatureExpired, ValidationError, TypeError):
            return None


class SyntheticIdentityProvider:
    mode: Literal["synthetic"] = "synthetic"

    def __init__(self, settings: Settings):
        self.available = settings.environment in {"synthetic", "test"}
        self._actor_id = settings.synthetic_actor_id
        self._tenant_id = settings.synthetic_tenant_id
        self._codec = SignedSessionCodec(
            settings.resolved_session_secret(),
            settings.session_max_age_seconds,
        )

    def create_identity(
        self,
        actor_id: str | None = None,
        tenant_id: str | None = None,
    ) -> AuthenticatedIdentity:
        if not self.available:
            raise IdentityUnavailable(
                "synthetic identity is disabled in this environment"
            )
        return AuthenticatedIdentity(
            actor_id=actor_id or self._actor_id,
            tenant_id=tenant_id or self._tenant_id,
            authentication_source="synthetic-server-session",
            mode="synthetic",
        )

    def issue_session(self, identity: AuthenticatedIdentity) -> str:
        if identity.mode != self.mode or not self.available:
            raise IdentityError("synthetic provider cannot issue this session")
        return self._codec.issue(identity)

    def resolve(self, token: str | None) -> AuthenticatedIdentity | None:
        identity = self._codec.resolve(token)
        if identity is None or identity.mode != self.mode:
            return None
        return identity


class OidcIdentityProvider:
    mode: Literal["oidc"] = "oidc"

    def __init__(self, settings: Settings):
        self.available = settings.oidc_configured()
        self._settings = settings
        self._codec = SignedSessionCodec(
            settings.resolved_session_secret(),
            settings.session_max_age_seconds,
        )
        self._oauth: OAuth | None = None
        if self.available:
            oauth = OAuth()
            oauth.register(
                name="oidc",
                client_id=settings.oidc_client_id,
                client_secret=(
                    settings.oidc_client_secret.get_secret_value()
                    if settings.oidc_client_secret
                    else None
                ),
                server_metadata_url=(
                    settings.oidc_issuer.rstrip("/")
                    + "/.well-known/openid-configuration"
                ),
                client_kwargs={
                    "scope": "openid profile email",
                    "code_challenge_method": "S256",
                },
            )
            self._oauth = oauth

    def _require_configured(self) -> OAuth:
        if not self.available or self._oauth is None:
            raise IdentityUnavailable("OIDC identity provider is not configured")
        return self._oauth

    async def authorize_redirect(
        self, request: Request, redirect_uri: str
    ):
        oauth = self._require_configured()
        return await oauth.oidc.authorize_redirect(request, redirect_uri)

    async def authorize_access_token(self, request: Request) -> dict:
        oauth = self._require_configured()
        token = await oauth.oidc.authorize_access_token(request)
        if not isinstance(token, dict):
            raise IdentityError("OIDC token response was invalid")
        return token

    async def identity_from_token(
        self, token: dict
    ) -> AuthenticatedIdentity:
        oauth = self._require_configured()
        claims = token.get("userinfo")
        if not isinstance(claims, dict):
            response = await oauth.oidc.get("userinfo", token=token)
            if response.status_code != 200:
                raise IdentityError("OIDC userinfo request failed")
            claims = response.json()
        return self.identity_from_claims(claims)

    def identity_from_claims(
        self, claims: dict
    ) -> AuthenticatedIdentity:
        actor_id = claims.get(self._settings.oidc_actor_claim)
        tenant_id = claims.get(self._settings.oidc_tenant_claim)
        if not isinstance(actor_id, str) or not isinstance(tenant_id, str):
            raise IdentityError(
                "OIDC claims did not contain actor and tenant identifiers"
            )
        raw_roles = claims.get("platform_roles", [])
        roles: set[Literal["platform_admin"]] = set()
        if isinstance(raw_roles, list) and "platform_admin" in raw_roles:
            roles.add("platform_admin")
        return AuthenticatedIdentity(
            actor_id=actor_id,
            tenant_id=tenant_id,
            authentication_source="oidc",
            mode="oidc",
            platform_roles=frozenset(roles),
        )

    def issue_session(self, identity: AuthenticatedIdentity) -> str:
        if identity.mode != self.mode:
            raise IdentityError("OIDC provider cannot issue this session")
        return self._codec.issue(identity)

    def resolve(self, token: str | None) -> AuthenticatedIdentity | None:
        identity = self._codec.resolve(token)
        if identity is None or identity.mode != self.mode:
            return None
        return identity


def build_identity_provider(settings: Settings) -> IdentityProvider:
    if settings.environment in {"synthetic", "test"}:
        return SyntheticIdentityProvider(settings)
    return OidcIdentityProvider(settings)
