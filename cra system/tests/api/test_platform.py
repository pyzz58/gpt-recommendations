"""FastAPI, identity, scope and capability acceptance for CRA-W02."""
from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker

from cra_app.governance.identity import (
    OidcIdentityProvider,
    SyntheticIdentityProvider,
)
from cra_app.governance.service import (
    CreateSite,
    CreateStudy,
    GrantMembership,
    GovernanceService,
    ScopeContext,
)
from cra_app.main import create_app
from cra_app.shared.config import Settings
from cra_app.shared.db import build_engine, build_session_factory
from cra_app.shared.output_contract import (
    Claim,
    OutputEnvelope,
    OutputScope,
    UnknownItem,
)

pytestmark = pytest.mark.postgres


def _database_url() -> str:
    value = os.environ.get("CRA_TEST_DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError(
            "CRA_TEST_DATABASE_URL is required; W02 API tests require PostgreSQL"
        )
    return value


@pytest.fixture(scope="session")
def engine():
    db_engine = build_engine(_database_url())
    with db_engine.connect() as connection:
        assert str(connection.scalar(text("SHOW server_version"))).startswith(
            "18."
        )
        tables = set(inspect(connection).get_table_names())
        assert {"studies", "sites", "memberships", "alembic_version"} <= tables
    yield db_engine
    db_engine.dispose()


@pytest.fixture
def session_factory(engine) -> sessionmaker:
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE idempotency_records, audit_events, "
                "memberships, sites, studies CASCADE"
            )
        )
    return build_session_factory(engine)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        CRA_ENV="test",
        CRA_DATABASE_URL=_database_url(),
        CRA_SESSION_SECRET="synthetic-test-session-secret",
        CRA_SESSION_COOKIE_SECURE=False,
        CRA_SYNTHETIC_ACTOR_ID="synthetic-cra-a",
        CRA_SYNTHETIC_TENANT_ID="synthetic-tenant",
        CRA_MODEL_PROVIDER="disabled",
        CRA_OCR_PROVIDER="disabled",
    )


@pytest.fixture
def governed_workspace(session_factory):
    service = GovernanceService(session_factory)
    admin = ScopeContext(
        actor_id="synthetic-admin",
        tenant_id="synthetic-tenant",
        authentication_source="trusted-test-session",
        platform_roles=frozenset({"platform_admin"}),
    )
    study = service.create_study(
        admin,
        CreateStudy(
            expected_revision=0,
            idempotency_key="w02-study",
            code="W02-SYN",
            title="W02合成项目",
        ),
    )
    site_a = service.create_site(
        admin,
        study.resource_id,
        CreateSite(
            expected_revision=0,
            idempotency_key="w02-site-a",
            code="A01",
            name="合成中心A",
        ),
    )
    site_b = service.create_site(
        admin,
        study.resource_id,
        CreateSite(
            expected_revision=0,
            idempotency_key="w02-site-b",
            code="B01",
            name="合成中心B",
        ),
    )
    service.grant_membership(
        admin,
        study.resource_id,
        GrantMembership(
            expected_revision=0,
            idempotency_key="w02-grant-a",
            actor_id="synthetic-cra-a",
            role="cra",
            site_id=site_a.resource_id,
            can_write=True,
        ),
    )
    service.grant_membership(
        admin,
        study.resource_id,
        GrantMembership(
            expected_revision=0,
            idempotency_key="w02-grant-b",
            actor_id="synthetic-cra-b",
            role="cra",
            site_id=site_b.resource_id,
            can_write=True,
        ),
    )
    return study.resource_id, site_a.resource_id, site_b.resource_id


def _client(settings: Settings, session_factory, provider):
    application = create_app(
        settings=settings,
        session_factory=session_factory,
        identity_provider=provider,
    )
    return TestClient(application)


def test_health_capabilities_and_openapi(
    settings, session_factory
):
    provider = SyntheticIdentityProvider(settings)
    with _client(settings, session_factory, provider) as client:
        live = client.get("/health/live")
        assert live.status_code == 200
        assert live.json() == {"status": "ok", "service": "cra-system"}

        ready = client.get("/health/ready")
        assert ready.status_code == 200
        assert ready.json()["dependencies"]["postgresql"]["status"] == "ready"

        capabilities = client.get("/capabilities")
        assert capabilities.status_code == 200
        body = capabilities.json()
        assert body["automatic_completion_allowed"] is False
        assert body["providers"]["model"]["status"] == "not_configured"
        assert body["providers"]["ocr"]["status"] == "not_configured"
        module_status = {
            module["module_id"]: module["status"]
            for module in body["modules"]
        }
        assert module_status["M01"] == "implemented"
        assert module_status["M03"] == "implemented"
        assert module_status["M04"] == "implemented"
    assert module_status["M05"] == "limited"
    assert module_status["M06"] == "implemented"
        assert module_status["M08"] == "not_implemented"

        openapi = client.get("/api/v1/openapi.json")
        assert openapi.status_code == 200
        schema = openapi.json()
        assert "/api/v1/me/scopes" in schema["paths"]
        assert "OutputEnvelope" in schema["components"]["schemas"]
        assert "tenant_id" in schema["components"]["schemas"]["OutputScope"][
            "properties"
        ]


def test_login_scope_authorization_refresh_and_spoof_rejection(
    settings, session_factory, governed_workspace
):
    provider = SyntheticIdentityProvider(settings)
    with _client(settings, session_factory, provider) as client:
        unauthenticated = client.get("/api/v1/me/scopes")
        assert unauthenticated.status_code == 401
        assert (
            unauthenticated.json()["error"]["code"]
            == "authentication_required"
        )

        login = client.post("/api/v1/auth/synthetic/session")
        assert login.status_code == 200
        assert login.json()["identity"]["actor_id"] == "synthetic-cra-a"
        assert "HttpOnly" in login.headers["set-cookie"]
        assert "SameSite=lax" in login.headers["set-cookie"]

        first = client.get(
            "/api/v1/me/scopes",
            headers={
                "X-CRA-Actor": "synthetic-cra-b",
                "X-CRA-Tenant": "another-tenant",
            },
        )
        assert first.status_code == 200
        assert first.json()["actor_id"] == "synthetic-cra-a"
        studies = first.json()["studies"]
        assert len(studies) == 1
        assert [site["code"] for site in studies[0]["sites"]] == ["A01"]

        refreshed = client.get("/api/v1/me/scopes")
        assert refreshed.status_code == 200
        assert refreshed.json() == first.json()

        logout = client.post("/api/v1/auth/logout")
        assert logout.status_code == 204
        assert client.get("/api/v1/me/scopes").status_code == 401


def test_second_site_identity_only_receives_its_own_site(
    settings, session_factory, governed_workspace
):
    provider = SyntheticIdentityProvider(settings)
    identity = provider.create_identity(actor_id="synthetic-cra-b")
    with _client(settings, session_factory, provider) as client:
        client.cookies.set(
            "cra_session",
            provider.issue_session(identity),
        )
        response = client.get("/api/v1/me/scopes")
        assert response.status_code == 200
        assert [
            site["code"]
            for site in response.json()["studies"][0]["sites"]
        ] == ["B01"]


def test_production_rejects_synthetic_identity_and_client_headers(
    session_factory,
):
    production_settings = Settings(
        CRA_ENV="production",
        CRA_DATABASE_URL=_database_url(),
        CRA_SESSION_SECRET="production-test-session-secret",
        CRA_SESSION_COOKIE_SECURE=True,
        CRA_SYNTHETIC_ACTOR_ID="must-not-be-used",
    )
    provider = OidcIdentityProvider(production_settings)
    assert provider.available is False
    with _client(
        production_settings, session_factory, provider
    ) as client:
        synthetic = client.post("/api/v1/auth/synthetic/session")
        assert synthetic.status_code == 403
        assert synthetic.json()["error"]["code"] == "synthetic_auth_disabled"

        scope = client.get(
            "/api/v1/me/scopes",
            headers={"X-CRA-Actor": "spoofed", "X-CRA-Tenant": "spoofed"},
        )
        assert scope.status_code == 401

        oidc = client.get("/api/v1/auth/oidc/login")
        assert oidc.status_code == 503
        assert oidc.json()["error"]["code"] == "oidc_not_configured"


def test_oidc_claim_mapping_requires_explicit_tenant(
    settings,
):
    settings = settings.model_copy(
        update={
            "oidc_issuer": "https://identity.example.invalid",
            "oidc_client_id": "cra-client",
            "oidc_client_secret": settings.session_secret,
        }
    )
    provider = OidcIdentityProvider(settings)
    identity = provider.identity_from_claims(
        {
            "sub": "oidc-user",
            "tenant_id": "oidc-tenant",
            "platform_roles": ["platform_admin"],
        }
    )
    assert identity.actor_id == "oidc-user"
    assert identity.tenant_id == "oidc-tenant"
    assert identity.platform_roles == frozenset({"platform_admin"})


def test_output_envelope_keeps_claim_kinds_separate():
    envelope = OutputEnvelope(
        output_id=uuid.uuid4(),
        purpose="visit_window",
        scope=OutputScope(
            tenant_id="synthetic-tenant",
            study_id=uuid.uuid4(),
            site_id=uuid.uuid4(),
            subject_id="SYN-001",
        ),
        claims=[
            Claim(
                claim_id="fact-1",
                kind="fact",
                label="synthetic fact",
                value="2026-10-31",
                verification_status="unverified",
            ),
            Claim(
                claim_id="candidate-1",
                kind="auto_candidate",
                label="synthetic window",
                value={"days": 3},
                verification_status="needs_review",
            ),
        ],
        unknowns=[
            UnknownItem(
                code="activation_date_unknown",
                reason="synthetic source does not state an activation date",
                affected_scope="study-version",
            )
        ],
        status="limited",
        generated_at=datetime.now(UTC),
        actor_id="synthetic-cra-a",
    )
    rendered = envelope.model_dump(mode="json")
    assert [claim["kind"] for claim in rendered["claims"]] == [
        "fact",
        "auto_candidate",
    ]
    assert "clinical_safe" not in rendered

    with pytest.raises(ValueError):
        OutputEnvelope(
            output_id=uuid.uuid4(),
            purpose="lab_comparison",
            scope=OutputScope(
                tenant_id="synthetic-tenant", study_id=uuid.uuid4()
            ),
            claims=[
                Claim(
                    claim_id="bad-candidate",
                    kind="auto_candidate",
                    label="automatic extraction",
                    value=1.2,
                    verification_status="cra_confirmed",
                )
            ],
            status="limited",
            generated_at=datetime.now(UTC),
            actor_id="synthetic-cra-a",
        )
