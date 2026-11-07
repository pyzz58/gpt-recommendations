from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def test_shell_config_command_uses_external_file_and_custom_ports(tmp_path) -> None:
    config_file = tmp_path / "outside-repository" / "medical-one.env"
    config_file.parent.mkdir()
    config_file.write_text(
        "\n".join(
            [
                "MEDICAL_ONE_API_PORT=18001",
                "MEDICAL_ONE_WEB_PORT=13001",
                f"MEDICAL_ONE_RUNTIME_DIR={tmp_path}/runtime",
                f"MEDICAL_ONE_ARTIFACT_ROOT={tmp_path}/artifacts",
                "NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:18001",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["MEDICAL_ONE_CONFIG_FILE"] = str(config_file)

    result = subprocess.run(
        [str(PROJECT_ROOT / "scripts/medical-one.sh"), "config"],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    body, end = json.JSONDecoder().raw_decode(result.stdout.lstrip())
    derived = result.stdout.lstrip()[end :].strip().splitlines()
    assert body["config_file"] == str(config_file)
    assert body["next_public_api_base_url"] == "http://127.0.0.1:18001"
    assert body["medical_one_api_port"] == "18001"
    assert body["medical_one_web_port"] == "13001"
    assert "api_url=http://127.0.0.1:18001" in derived
    assert "web_url=http://127.0.0.1:13001" in derived
    assert f"runtime_dir={tmp_path}/runtime" in derived
