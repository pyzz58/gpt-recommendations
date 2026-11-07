from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from medical_one_person.config_file import load_config_values
from medical_one_person.domain.recovery import NetworkMode


class Settings(BaseSettings):
    """Validated process settings with mock-safe defaults."""

    model_config = SettingsConfigDict(
        env_prefix="MEDICAL_ONE_",
        extra="ignore",
    )

    app_mode: Literal["mock", "live"] = "mock"
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://medical_one_app@127.0.0.1:5432/medical_one"
    migration_database_url: str | None = None
    cors_origins: str = "http://127.0.0.1:3000,http://localhost:3000"
    artifact_root: Path = Path.home() / ".medical-one-person" / "artifacts"
    knowledge_staging_root: Path = Path.home() / ".medical-one-person" / "knowledge-staging"
    run_root: Path = Path.home() / ".medical-one-person" / "runs"
    backup_root: Path = Path.home() / ".medical-one-person" / "backups"
    restore_root: Path = Path.home() / ".medical-one-person" / "restore-checks"
    network_mode: NetworkMode = NetworkMode.OFFLINE
    artifact_max_bytes: int = 100 * 1024 * 1024
    knowledge_max_file_bytes: int = 100 * 1024 * 1024
    knowledge_max_batch_bytes: int = 500 * 1024 * 1024
    knowledge_upload_chunk_size: int = 8 * 1024 * 1024
    office_soffice_path: str | None = None
    office_pdftoppm_path: str | None = None
    office_conversion_timeout_seconds: int = 120
    office_max_preview_pages: int = 40
    office_pdf_font_path: Path | None = None
    agent_config_path: Path = (
        Path(__file__).resolve().parents[4] / "config" / "agents" / "roles.yaml"
    )
    skill_config_path: Path = (
        Path(__file__).resolve().parents[4] / "config" / "skills" / "catalog.yaml"
    )
    source_policy_path: Path = (
        Path(__file__).resolve().parents[4] / "config" / "source_policies" / "catalog.yaml"
    )
    workflow_catalog_path: Path = (
        Path(__file__).resolve().parents[4] / "config" / "workflows" / "catalog.yaml"
    )
    export_template_path: Path = (
        Path(__file__).resolve().parents[4] / "config" / "templates" / "catalog.yaml"
    )
    audit_fixture_path: Path = (
        Path(__file__).resolve().parents[4] / "fixtures" / "w17-audit-cases.json"
    )
    theory_path: Path = Path(__file__).resolve().parents[4] / "最高思想.md"
    model_provider: Literal["mock", "openai_compatible"] = "mock"
    model_provider_base_url: str | None = None
    model_provider_api_key: str | None = None
    model_provider_model: str | None = None
    model_provider_timeout_seconds: float = 60.0
    model_provider_live_enabled: bool = False
    model_provider_max_context_tokens: int = 32_000
    model_provider_max_output_tokens: int = 4_096
    model_provider_max_cost_per_call: float | None = None
    model_provider_input_cost_per_million: float | None = None
    model_provider_output_cost_per_million: float | None = None
    model_provider_currency: str | None = None
    mail_adapter: Literal["mock", "smtp"] = "mock"
    mail_smtp_host: str | None = None
    mail_smtp_port: int = 587
    mail_smtp_username: str | None = None
    mail_smtp_password: str | None = None
    mail_smtp_security: Literal["starttls", "ssl"] = "starttls"
    mail_smtp_from_address: str | None = None
    mail_smtp_from_name: str = "医疗一人项目"
    mail_smtp_timeout_seconds: float = 30.0
    mail_smtp_live_enabled: bool = False
    mail_smtp_allowed_recipients: str = ""

    @field_validator("database_url")
    @classmethod
    def validate_postgres_url(cls, value: str) -> str:
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("database_url must use the PostgreSQL psycopg driver")
        return value

    @field_validator("migration_database_url")
    @classmethod
    def validate_migration_url(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("postgresql+psycopg://"):
            raise ValueError("migration_database_url must use the PostgreSQL psycopg driver")
        return value

    @field_validator("artifact_max_bytes")
    @classmethod
    def validate_artifact_limit(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("artifact_max_bytes must be positive")
        return value

    @field_validator(
        "knowledge_max_file_bytes",
        "knowledge_max_batch_bytes",
        "knowledge_upload_chunk_size",
    )
    @classmethod
    def validate_knowledge_limits(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Knowledge upload limits must be positive")
        return value

    @field_validator("office_conversion_timeout_seconds", "office_max_preview_pages")
    @classmethod
    def validate_office_limits(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Office export limits must be positive")
        return value

    @field_validator("model_provider_timeout_seconds")
    @classmethod
    def validate_provider_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("model_provider_timeout_seconds must be positive")
        return value

    @field_validator(
        "model_provider_max_context_tokens",
        "model_provider_max_output_tokens",
    )
    @classmethod
    def validate_provider_token_limits(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Provider token limits must be positive")
        return value

    @field_validator("mail_smtp_timeout_seconds")
    @classmethod
    def validate_smtp_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("mail_smtp_timeout_seconds must be positive")
        return value

    @field_validator(
        "model_provider_input_cost_per_million",
        "model_provider_output_cost_per_million",
        "model_provider_max_cost_per_call",
    )
    @classmethod
    def validate_provider_rates(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("Provider rates cannot be negative")
        return value

    @field_validator("mail_smtp_port")
    @classmethod
    def validate_smtp_port(cls, value: int) -> int:
        if not 1 <= value <= 65_535:
            raise ValueError("mail_smtp_port must be between 1 and 65535")
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def effective_migration_database_url(self) -> str:
        return self.migration_database_url or self.database_url


@lru_cache
def get_settings() -> Settings:
    _, values = load_config_values()
    configured: dict[str, Any] = {}
    for field_name in Settings.model_fields:
        env_name = "MEDICAL_ONE_" + field_name.upper()
        if env_name in os.environ:
            continue
        if env_name in values:
            configured[field_name] = values[env_name]
    return Settings(**configured)
