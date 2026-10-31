from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from medical_one_person.domain.recovery import NetworkMode


class Settings(BaseSettings):
    """Validated process settings with mock-safe defaults."""

    model_config = SettingsConfigDict(
        env_prefix="MEDICAL_ONE_",
        env_file=(".env", "../../.env"),
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

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def effective_migration_database_url(self) -> str:
        return self.migration_database_url or self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
