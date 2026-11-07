from __future__ import annotations

from pathlib import Path

from medical_one_person.config import Settings, get_settings
from medical_one_person.config_file import (
    load_config_values,
    resolve_config_path,
    safe_summary,
)


def test_external_config_is_one_source_for_python_paths_and_ports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_file = tmp_path / "external" / "medical-one.env"
    config_file.parent.mkdir()
    config_file.write_text(
        "\n".join(
            [
                "MEDICAL_ONE_APP_MODE=mock",
                "MEDICAL_ONE_DATABASE_URL=postgresql+psycopg://app@db.example/medical",
                f"MEDICAL_ONE_ARTIFACT_ROOT={tmp_path}/artifacts",
                f"MEDICAL_ONE_RUN_ROOT={tmp_path}/runs",
                "MEDICAL_ONE_API_PORT=18000",
                "MEDICAL_ONE_WEB_PORT=13000",
                "NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:18000",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MEDICAL_ONE_CONFIG_FILE", str(config_file))
    monkeypatch.delenv("MEDICAL_ONE_APP_MODE", raising=False)
    monkeypatch.delenv("MEDICAL_ONE_DATABASE_URL", raising=False)
    monkeypatch.delenv("MEDICAL_ONE_ARTIFACT_ROOT", raising=False)
    monkeypatch.delenv("MEDICAL_ONE_RUN_ROOT", raising=False)

    resolved = resolve_config_path()
    _, values = load_config_values()
    settings = Settings(
        database_url=values["MEDICAL_ONE_DATABASE_URL"],
        artifact_root=Path(values["MEDICAL_ONE_ARTIFACT_ROOT"]),
        run_root=Path(values["MEDICAL_ONE_RUN_ROOT"]),
    )

    assert resolved == config_file
    assert settings.database_url == "postgresql+psycopg://app@db.example/medical"
    assert settings.artifact_root == tmp_path / "artifacts"
    assert settings.run_root == tmp_path / "runs"
    assert values["MEDICAL_ONE_API_PORT"] == "18000"
    assert values["MEDICAL_ONE_WEB_PORT"] == "13000"
    assert values["NEXT_PUBLIC_API_BASE_URL"] == "http://127.0.0.1:18000"
    get_settings.cache_clear()
    effective = get_settings()
    assert effective.database_url == "postgresql+psycopg://app@db.example/medical"
    assert effective.artifact_root == tmp_path / "artifacts"
    get_settings.cache_clear()


def test_parent_environment_overrides_file_values(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_file = tmp_path / "medical-one.env"
    config_file.write_text("MEDICAL_ONE_APP_MODE=mock\n", encoding="utf-8")
    monkeypatch.setenv("MEDICAL_ONE_APP_MODE", "live")

    _, values = load_config_values(config_file)

    assert values["MEDICAL_ONE_APP_MODE"] == "mock"
    assert Settings().app_mode == "live"


def test_unknown_config_key_fails_closed_and_summary_redacts_secrets(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "medical-one.env"
    config_file.write_text(
        "MEDICAL_ONE_MODEL_PROVIDER_API_KEY=secret-value\n"
        "UNSUPPORTED_KEY=not-allowed\n",
        encoding="utf-8",
    )

    try:
        load_config_values(config_file)
    except ValueError as exc:
        assert "Unsupported configuration key" in str(exc)
    else:
        raise AssertionError("unknown configuration keys must fail closed")

    config_file.write_text(
        "MEDICAL_ONE_MODEL_PROVIDER_API_KEY=secret-value\n",
        encoding="utf-8",
    )
    summary = safe_summary(config_file)
    assert summary["medical_one_model_provider_api_key"] == "[redacted]"

    config_file.write_text(
        "MEDICAL_ONE_DATABASE_URL=postgresql+psycopg://app:secret@db/medical\n",
        encoding="utf-8",
    )
    summary = safe_summary(config_file)
    assert summary["medical_one_database_url"] == "[redacted]"
