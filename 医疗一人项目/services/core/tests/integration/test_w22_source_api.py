from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from medical_one_person.config import Settings
from medical_one_person.contracts import DependencyStatus
from medical_one_person.domain.knowledge import SourceRecord, SourceSearchRequest
from medical_one_person.infrastructure.db.models import ExternalSourceSnapshot
from medical_one_person.infrastructure.sources import SourceRouter, load_source_policies
from medical_one_person.infrastructure.sources.pubmed_http import SourceRetrievalRateLimited
from medical_one_person.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def test_source_search_operation_is_exported_in_openapi() -> None:
    schema = json.loads(
        (PROJECT_ROOT / "schemas/openapi.v1.json").read_text(encoding="utf-8")
    )
    operation = schema["paths"]["/api/v1/projects/{project_id}/sources/search"]["post"]

    assert operation["responses"]["200"]
    assert operation["responses"]["400"]
    assert operation["responses"]["429"]
    assert operation["responses"]["502"]


class _FakeSourceAdapter:
    adapter_id = "fake-source.v1"
    policy_ids = frozenset({"biomedical_primary.v1"})

    def __init__(self, mode: str = "ready") -> None:
        self.mode = mode
        self.requests: list[SourceSearchRequest] = []

    def search(self, request: SourceSearchRequest) -> list[SourceRecord]:
        self.requests.append(request)
        if self.mode == "rate_limited":
            raise SourceRetrievalRateLimited("synthetic 429")
        return [
            SourceRecord(
                source_id="offline:1",
                title="Offline source API fixture",
                abstract="Synthetic metadata only.",
                journal="Fixture Journal",
                publication_date=date(2026, 11, 1),
                source_url="https://pubmed.ncbi.nlm.nih.gov/123/",
                source_kind="bibliographic_database",
                peer_reviewed=True,
                preprint=False,
                retracted=False,
                doi="10.0000/fixture",
                pmid="123",
                raw_fulltext_available=False,
                limitations=["Synthetic API transport test."],
            )
        ]


def _router(adapter: _FakeSourceAdapter | None) -> SourceRouter:
    policies = load_source_policies(
        PROJECT_ROOT / "config/source_policies/catalog.yaml"
    )
    return SourceRouter(policies, [adapter] if adapter else [])


def _client(
    session_factory,
    app_database_url: str,
    tmp_path: Path,
    source_router: SourceRouter,
) -> TestClient:
    settings = Settings(
        app_mode="mock",
        environment="development",
        database_url=app_database_url,
        artifact_root=tmp_path / "artifacts",
        knowledge_staging_root=tmp_path / "staging",
        run_root=tmp_path / "runs",
    )
    app = create_app(
        database_checker=lambda: DependencyStatus(
            status="ready",
            detail="integration test",
        ),
        settings_override=settings,
        session_factory_override=session_factory,
        source_router_override=source_router,
    )
    return TestClient(app, base_url="http://127.0.0.1:3000")


def _project(client: TestClient) -> str:
    session = client.post("/api/v1/system/local-session")
    assert session.status_code == 200
    project = client.post(
        "/api/v1/projects",
        headers={"Idempotency-Key": "w22-source-project"},
        json={
            "name": "W22来源API",
            "scope": "只验证项目权限和离线来源适配合同。",
        },
    )
    assert project.status_code == 201
    return project.json()["id"]


def test_project_source_search_uses_injected_adapter_without_network(
    session_factory,
    database: Engine,
    app_database_url: str,
    tmp_path: Path,
) -> None:
    adapter = _FakeSourceAdapter()
    client = _client(session_factory, app_database_url, tmp_path, _router(adapter))
    project_id = _project(client)

    response = client.post(
        f"/api/v1/projects/{project_id}/sources/search",
        json={
            "query": "synthetic feline evidence",
            "policy_id": "biomedical_primary.v1",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["records"][0]["pmid"] == "123"
    assert body["record_count"] == 1
    assert body["adapter_ids"] == ["fake-source.v1"]
    assert len(body["query_sha256"]) == 64
    assert len(body["result_sha256"]) == 64
    assert adapter.requests[0].query == "synthetic feline evidence"

    snapshot = client.get(
        f"/api/v1/projects/{project_id}/sources/snapshots/{body['snapshot_id']}"
    )
    assert snapshot.status_code == 200
    assert snapshot.json()["records"] == body["records"]
    with Session(bind=database) as session:
        row = session.scalar(
            select(ExternalSourceSnapshot).where(
                ExternalSourceSnapshot.id == body["snapshot_id"]
            )
        )
        assert row is not None
        assert row.query == "synthetic feline evidence"
        assert row.record_count == 1


def test_source_search_fails_closed_without_adapter_and_unknown_policy(
    session_factory,
    app_database_url: str,
    tmp_path: Path,
) -> None:
    unavailable = _client(session_factory, app_database_url, tmp_path, _router(None))
    project_id = _project(unavailable)
    response = unavailable.post(
        f"/api/v1/projects/{project_id}/sources/search",
        json={"query": "query", "policy_id": "biomedical_primary.v1"},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "SOURCE_ADAPTER_UNAVAILABLE"

    configured = _client(
        session_factory,
        app_database_url,
        tmp_path,
        _router(_FakeSourceAdapter()),
    )
    assert configured.post("/api/v1/system/local-session").status_code == 200
    unknown = configured.post(
        f"/api/v1/projects/{project_id}/sources/search",
        json={"query": "query", "policy_id": "unknown.v1"},
    )
    assert unknown.status_code == 400


def test_source_api_maps_rate_limit_to_429(
    session_factory,
    app_database_url: str,
    tmp_path: Path,
) -> None:
    client = _client(
        session_factory,
        app_database_url,
        tmp_path,
        _router(_FakeSourceAdapter("rate_limited")),
    )
    project_id = _project(client)

    response = client.post(
        f"/api/v1/projects/{project_id}/sources/search",
        json={"query": "query", "policy_id": "biomedical_primary.v1"},
    )

    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "SOURCE_RATE_LIMITED"
