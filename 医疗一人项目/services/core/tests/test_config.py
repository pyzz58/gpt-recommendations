import pytest

from medical_one_person.config import Settings


def test_database_driver_is_postgres_only() -> None:
    with pytest.raises(ValueError, match="PostgreSQL psycopg"):
        Settings(database_url="sqlite:///local.db")


def test_cors_origins_are_trimmed() -> None:
    settings = Settings(cors_origins="http://127.0.0.1:3000, http://localhost:3000")

    assert settings.allowed_origins == [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ]


def test_artifact_limit_must_be_positive() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        Settings(artifact_max_bytes=0)


def test_migration_database_url_uses_separate_postgres_role() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://app@localhost/medical_one",
        migration_database_url="postgresql+psycopg://migrator@localhost/medical_one",
    )

    assert settings.effective_migration_database_url.endswith("@localhost/medical_one")
    assert "migrator" in settings.effective_migration_database_url
