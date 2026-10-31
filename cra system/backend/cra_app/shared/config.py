"""Environment-backed application settings.

The database URL is never logged. Public CI and development examples must use
synthetic credentials and data.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CRA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    environment: Literal["synthetic", "test", "development", "production"] = Field(
        default="synthetic", alias="CRA_ENV"
    )
    database_url: SecretStr = Field(alias="CRA_DATABASE_URL")
    database_echo: bool = Field(default=False, alias="CRA_DATABASE_ECHO")
    session_secret: SecretStr | None = Field(
        default=None, alias="CRA_SESSION_SECRET"
    )
    session_cookie_secure: bool | None = Field(
        default=None, alias="CRA_SESSION_COOKIE_SECURE"
    )
    session_max_age_seconds: int = Field(
        default=28800, ge=300, le=86400, alias="CRA_SESSION_MAX_AGE_SECONDS"
    )
    synthetic_actor_id: str = Field(
        default="synthetic-cra", alias="CRA_SYNTHETIC_ACTOR_ID"
    )
    synthetic_tenant_id: str = Field(
        default="synthetic", alias="CRA_SYNTHETIC_TENANT_ID"
    )
    oidc_issuer: str | None = Field(default=None, alias="CRA_OIDC_ISSUER")
    oidc_client_id: str | None = Field(
        default=None, alias="CRA_OIDC_CLIENT_ID"
    )
    oidc_client_secret: SecretStr | None = Field(
        default=None, alias="CRA_OIDC_CLIENT_SECRET"
    )
    oidc_actor_claim: str = Field(default="sub", alias="CRA_OIDC_ACTOR_CLAIM")
    oidc_tenant_claim: str = Field(
        default="tenant_id", alias="CRA_OIDC_TENANT_CLAIM"
    )
    public_base_url: str = Field(
        default="http://localhost:5173", alias="CRA_PUBLIC_BASE_URL"
    )
    model_provider: str = Field(
        default="disabled", alias="CRA_MODEL_PROVIDER"
    )
    ocr_provider: str = Field(default="disabled", alias="CRA_OCR_PROVIDER")
    common_policy_path: str | None = Field(
        default=None, alias="CRA_COMMON_POLICY_PATH"
    )
    private_storage_backend: Literal["local", "s3"] = Field(
        default="local", alias="CRA_STORAGE_BACKEND"
    )
    private_storage_local_path: str = Field(
        default="runtime/private", alias="CRA_PRIVATE_STORAGE_LOCAL_PATH"
    )
    private_storage_endpoint: str | None = Field(
        default=None, alias="CRA_PRIVATE_STORAGE_ENDPOINT"
    )
    private_storage_access_key: str | None = Field(
        default=None, alias="CRA_PRIVATE_STORAGE_ACCESS_KEY"
    )
    private_storage_secret_key: SecretStr | None = Field(
        default=None, alias="CRA_PRIVATE_STORAGE_SECRET_KEY"
    )
    private_storage_bucket: str = Field(
        default="cra-private", alias="CRA_PRIVATE_STORAGE_BUCKET"
    )
    private_storage_region: str = Field(
        default="us-east-1", alias="CRA_PRIVATE_STORAGE_REGION"
    )
    max_upload_bytes: int = Field(
        default=20 * 1024 * 1024,
        ge=1024,
        le=100 * 1024 * 1024,
        alias="CRA_MAX_UPLOAD_BYTES",
    )

    def sqlalchemy_url(self) -> str:
        value = self.database_url.get_secret_value()
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value.removeprefix("postgres://")
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value.removeprefix("postgresql://")
        return value

    def resolved_session_secret(self) -> str:
        if self.session_secret is not None:
            return self.session_secret.get_secret_value()
        if self.environment in {"synthetic", "test"}:
            return "synthetic-only-session-secret-not-for-production"
        raise ValueError("CRA_SESSION_SECRET is required outside synthetic mode")

    def resolved_cookie_secure(self) -> bool:
        if self.session_cookie_secure is not None:
            return self.session_cookie_secure
        return self.environment not in {"synthetic", "test"}

    def oidc_configured(self) -> bool:
        return all(
            (
                self.oidc_issuer,
                self.oidc_client_id,
                self.oidc_client_secret,
            )
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
