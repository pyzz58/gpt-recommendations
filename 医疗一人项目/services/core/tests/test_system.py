from fastapi import FastAPI
from fastapi.testclient import TestClient

from medical_one_person.api.system import build_system_router
from medical_one_person.config import Settings
from medical_one_person.contracts import DependencyStatus
from medical_one_person.main import create_app


def database_ready() -> DependencyStatus:
    return DependencyStatus(status="ready", detail="test database")


def database_unavailable() -> DependencyStatus:
    return DependencyStatus(status="unavailable", detail="test database offline")


def worker_unavailable() -> DependencyStatus:
    return DependencyStatus(status="unavailable", detail="worker heartbeat missing")


def test_health_separates_live_and_mock_readiness() -> None:
    client = TestClient(
        create_app(
            database_checker=database_ready,
            storage_checker_override=database_ready,
            queue_checker_override=database_ready,
            worker_checker_override=database_ready,
        )
    )

    live = client.get("/health/live")
    ready = client.get("/health/ready")

    assert live.status_code == 200
    assert live.json()["status"] == "ok"
    assert live.json()["mode"] == "mock"
    assert ready.status_code == 200
    assert ready.json()["checks"]["database"]["status"] == "ready"
    assert ready.json()["checks"]["artifact_storage"]["status"] == "ready"
    assert ready.json()["checks"]["queue"]["status"] == "ready"
    assert ready.json()["checks"]["worker"]["status"] == "ready"


def test_capabilities_do_not_invent_external_connections() -> None:
    client = TestClient(
        create_app(
            database_checker=database_ready,
            storage_checker_override=database_ready,
            queue_checker_override=database_ready,
            worker_checker_override=database_ready,
        )
    )

    response = client.get("/api/v1/system/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "mock"
    assert body["providers"][0]["mode"] == "mock"
    assert body["external_actions"]["status"] == "ready"
    assert body["dependencies"]["network"]["status"] == "ready"
    assert body["dependencies"]["worker"]["status"] == "ready"
    assert body["dependencies"]["queue"]["status"] == "ready"
    assert body["dependencies"]["artifact_storage"]["status"] == "ready"
    assert "Offline mode" in body["dependencies"]["network"]["detail"]
    assert body["dependencies"]["recovery"]["status"] == "ready"
    assert any("not a complete scientific workflow" in item for item in body["limitations"])


def test_mock_smoke_is_deterministic_and_labeled() -> None:
    client = TestClient(
        create_app(
            database_checker=database_ready,
            storage_checker_override=database_ready,
            queue_checker_override=database_ready,
            worker_checker_override=database_ready,
        )
    )
    request = {"input": "合成测试输入"}

    first = client.post("/api/v1/system/mock-smoke", json=request)
    second = client.post("/api/v1/system/mock-smoke", json=request)

    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["mode"] == "mock"
    assert "不代表真实模型" in first.json()["disclaimer"]


def test_request_id_is_returned_for_correlation() -> None:
    client = TestClient(
        create_app(
            database_checker=database_ready,
            storage_checker_override=database_ready,
            queue_checker_override=database_ready,
            worker_checker_override=database_ready,
        )
    )

    response = client.get("/health/live", headers={"X-Request-ID": "w01-test-request"})

    assert response.headers["X-Request-ID"] == "w01-test-request"


def test_live_mode_is_not_ready_without_a_provider() -> None:
    app = FastAPI()
    app.include_router(
        build_system_router(
            Settings(app_mode="live"),
            database_ready,
            DependencyStatus(status="ready", detail="26 test roles"),
            DependencyStatus(status="ready", detail="skills registry test"),
            DependencyStatus(status="not_checked", detail="source policies test"),
        )
    )
    client = TestClient(app)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"]["mock_provider"]["status"] == "not_configured"


def test_database_failure_does_not_mislabel_mock_provider() -> None:
    client = TestClient(
        create_app(
            database_checker=database_unavailable,
            storage_checker_override=database_ready,
            queue_checker_override=database_ready,
            worker_checker_override=database_ready,
        )
    )

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"]["mock_provider"]["status"] == "ready"
    assert response.json()["checks"]["database"]["status"] == "unavailable"


def test_missing_worker_is_explicit_503_not_ready() -> None:
    client = TestClient(
        create_app(
            database_checker=database_ready,
            storage_checker_override=database_ready,
            queue_checker_override=database_ready,
            worker_checker_override=worker_unavailable,
        )
    )

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"]["worker"] == {
        "status": "unavailable",
        "detail": "worker heartbeat missing",
    }
