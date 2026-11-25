import json
from pathlib import Path

from fastapi.testclient import TestClient

from medical_one_person.contracts import DependencyStatus
from medical_one_person.main import create_app


def test_all_mock_provider_scenarios_return_marked_responses() -> None:
    fixture_path = Path(__file__).resolve().parents[3] / "fixtures" / "fake-provider-scenarios.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    client = TestClient(
        create_app(
            database_checker=lambda: DependencyStatus(status="ready", detail="test database")
        )
    )

    for scenario in fixture["scenarios"]:
        response = client.post(
            "/api/v1/system/mock-smoke",
            json={"input": scenario["input"]},
        )
        body = response.json()

        assert response.status_code == 200
        assert body["mode"] == scenario["expected_marker"]
        assert scenario["expected_disclaimer_contains"] in body["disclaimer"]
