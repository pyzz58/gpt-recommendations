from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def load_deployment_checker():
    path = PROJECT_ROOT / "tools" / "check_deployment.py"
    spec = importlib.util.spec_from_file_location("check_deployment", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_w23_static_deployment_package_is_consistent() -> None:
    checker = load_deployment_checker()

    assert checker.validate(PROJECT_ROOT) == []


def test_w23_static_check_rejects_wrong_database_health_user(tmp_path) -> None:
    checker = load_deployment_checker()
    for relative in checker.REQUIRED_RUNTIME_FILES:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PROJECT_ROOT / relative, target)
    compose_path = tmp_path / "deploy" / "compose.yaml"
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    compose["services"]["postgres"]["healthcheck"]["test"] = [
        "CMD-SHELL",
        "pg_isready -U medical_one -d medical_one",
    ]
    compose_path.write_text(yaml.safe_dump(compose), encoding="utf-8")

    errors = checker.validate(tmp_path)

    assert any("removed generic medical_one role" in error for error in errors)
