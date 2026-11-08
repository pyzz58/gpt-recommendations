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
from medical_one_person.infrastructure.sources import (
    PubMedXmlAdapter,
    SourceRouter,
    load_source_policies,
)
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
    assert operation["responses"]["409"]
    assert operation["responses"]["429"]
    assert operation["responses"]["502"]


class _FakeSourceAdapter:
    adapter_id = "fake-source.v1"
    policy_ids = frozenset({"biomedical_primary.v1"})
    mode = "mock"

    def __init__(self, behavior: str = "ready") -> None:
        self.behavior = behavior
        self.requests: list[SourceSearchRequest] = []

    def search(self, request: SourceSearchRequest) -> list[SourceRecord]:
        self.requests.append(request)
        if self.behavior == "rate_limited":
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


class _UnmatchedSourceAdapter:
    adapter_id = "unmatched-source.v1"
    policy_ids = frozenset({"other_policy.v1"})
    mode = "mock"

    def __init__(self) -> None:
        self.calls = 0

    def search(self, request: SourceSearchRequest) -> list[SourceRecord]:
        self.calls += 1
        return []


class _LiveSourceAdapter(_FakeSourceAdapter):
    adapter_id = "live-source.v1"
    mode = "live"


def _router(*adapters) -> SourceRouter:
    policies = load_source_policies(
        PROJECT_ROOT / "config/source_policies/catalog.yaml"
    )
    return SourceRouter(policies, list(adapters))


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
    unmatched = _UnmatchedSourceAdapter()
    client = _client(
        session_factory,
        app_database_url,
        tmp_path,
        _router(adapter, unmatched),
    )
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
    assert body["mode"] == "mock"
    assert len(body["query_sha256"]) == 64
    assert len(body["result_sha256"]) == 64
    assert adapter.requests[0].query == "synthetic feline evidence"

    snapshot = client.get(
        f"/api/v1/projects/{project_id}/sources/snapshots/{body['snapshot_id']}"
    )
    assert snapshot.status_code == 200
    assert snapshot.json()["records"] == body["records"]
    assert snapshot.json()["mode"] == "mock"
    assert snapshot.json()["adapter_ids"] == ["fake-source.v1"]
    with Session(bind=database) as session:
        row = session.scalar(
            select(ExternalSourceSnapshot).where(
                ExternalSourceSnapshot.id == body["snapshot_id"]
            )
        )
        assert row is not None
        assert row.query == "synthetic feline evidence"
        assert row.record_count == 1
        assert row.mode == "mock"
        assert row.adapter_ids == ["fake-source.v1"]
    assert unmatched.calls == 0


def test_local_xml_source_snapshot_is_marked_offline(
    session_factory,
    database: Engine,
    app_database_url: str,
    tmp_path: Path,
) -> None:
    adapter = PubMedXmlAdapter(
        b"""
        <PubmedArticleSet><PubmedArticle>
          <MedlineCitation>
            <PMID>24680</PMID>
            <Article>
              <ArticleTitle>Local cached XML fixture</ArticleTitle>
              <Abstract><AbstractText>Synthetic local XML metadata only.</AbstractText></Abstract>
              <Journal><Title>Fixture Journal</Title></Journal>
              <ArticleDate><Year>2026</Year><Month>11</Month><Day>1</Day></ArticleDate>
              <PublicationTypeList>
                <PublicationType>Journal Article</PublicationType>
              </PublicationTypeList>
            </Article>
          </MedlineCitation>
        </PubmedArticle></PubmedArticleSet>
        """
    )
    client = _client(session_factory, app_database_url, tmp_path, _router(adapter))
    project_id = _project(client)

    response = client.post(
        f"/api/v1/projects/{project_id}/sources/search",
        json={"query": "local XML", "policy_id": "biomedical_primary.v1"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mode"] == "mock"
    assert body["adapter_ids"] == ["pubmed.xml.v1"]
    assert body["records"][0]["pmid"] == "24680"
    with Session(bind=database) as session:
        row = session.scalar(
            select(ExternalSourceSnapshot).where(
                ExternalSourceSnapshot.id == body["snapshot_id"]
            )
        )
        assert row is not None
        assert row.mode == "mock"
        assert row.adapter_ids == ["pubmed.xml.v1"]


def test_source_search_fails_closed_without_adapter_and_unknown_policy(
    session_factory,
    app_database_url: str,
    tmp_path: Path,
) -> None:
    unavailable = _client(session_factory, app_database_url, tmp_path, _router())
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


def test_source_search_rejects_mixed_execution_modes_without_snapshot(
    session_factory,
    database: Engine,
    app_database_url: str,
    tmp_path: Path,
) -> None:
    mock_adapter = _FakeSourceAdapter()
    live_adapter = _LiveSourceAdapter()
    client = _client(
        session_factory,
        app_database_url,
        tmp_path,
        _router(mock_adapter, live_adapter),
    )
    project_id = _project(client)

    response = client.post(
        f"/api/v1/projects/{project_id}/sources/search",
        json={"query": "mixed modes", "policy_id": "biomedical_primary.v1"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "SOURCE_EXECUTION_MODE_CONFLICT"
    assert mock_adapter.requests == []
    assert live_adapter.requests == []
    with Session(bind=database) as session:
        assert session.scalar(select(ExternalSourceSnapshot.id)) is None


def test_unmatched_adapter_fails_closed_without_snapshot(
    session_factory,
    database: Engine,
    app_database_url: str,
    tmp_path: Path,
) -> None:
    adapter = _UnmatchedSourceAdapter()
    client = _client(
        session_factory,
        app_database_url,
        tmp_path,
        _router(adapter),
    )
    project_id = _project(client)

    response = client.post(
        f"/api/v1/projects/{project_id}/sources/search",
        json={"query": "unsupported policy", "policy_id": "biomedical_primary.v1"},
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "SOURCE_ADAPTER_UNAVAILABLE"
    assert adapter.calls == 0
    with Session(bind=database) as session:
        assert session.scalar(select(ExternalSourceSnapshot.id)) is None
