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

    environment: Literal["synthetic", "test", "development"] = "synthetic"
    database_url: SecretStr = Field(alias="CRA_DATABASE_URL")
    database_echo: bool = Field(default=False, alias="CRA_DATABASE_ECHO")

    def sqlalchemy_url(self) -> str:
        value = self.database_url.get_secret_value()
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value.removeprefix("postgres://")
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value.removeprefix("postgresql://")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
