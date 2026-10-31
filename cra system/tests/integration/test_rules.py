"""Real PostgreSQL acceptance for CRA-W04 rule extraction and activation."""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from cra_app.documents.service import (
    CreateDocumentCommand,
    DocumentService,
)
from cra_app.documents.storage import build_private_storage
from cra_app.governance.identity import SyntheticIdentityProvider
from cra_app.governance.service import (
    CreateSite,
    CreateStudy,
    GrantMembership,
    GovernanceService,
    ScopeContext,
)
from cra_app.main import create_app
from cra_app.platform.jobs import ProcrastinateQueue
from cra_app.providers.rule_extraction import AnchoredRuleExtractor
from cra_app.providers.evaluate_rules import evaluate as evaluate_rule_provider
from cra_app.rules.common_policy import load_common_policy_set
from cra_app.rules.contracts import (
    FactValue,
    RuleCondition,
    RuleExtractionResult,
    RuleNode,
    RuleOperand,
    RuleSourceRef,
)
from cra_app.rules.evaluator import evaluate_condition
from cra_app.rules.models import (
    Rule,
    RuleRelation,
    RuleSnapshot,
    RuleVersion,
)
from cra_app.rules.service import (
    ExtractRuleCommand,
    RuleService,
    RuleValidationError,
)
from cra_app.shared.config import Settings
from cra_app.shared.db import build_engine, build_session_factory

pytestmark = pytest.mark.postgres

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
ARTIFACTS = FIXTURES / "documents" / "artifacts"


def _database_url() -> str:
    value = os.environ.get("CRA_TEST_DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError(
            "CRA_TEST_DATABASE_URL is required; W04 never falls back to SQLite"
        )
    return value


@pytest.fixture(scope="session")
def engine():
    db_engine = build_engine(_database_url())
    with db_engine.connect() as connection:
        assert str(connection.scalar(text("SHOW server_version"))).startswith(
            "18."
        )
    yield db_engine
    db_engine.dispose()


@pytest.fixture(scope="session")
def queue():
    adapter = ProcrastinateQueue(_database_url())
    adapter.ensure_schema()
    return adapter


@pytest.fixture
def session_factory(engine, queue):
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE rule_relations, rule_source_refs, "
                "rule_extraction_coverage, version_activations, "
                "rule_versions, rules, rule_snapshots, outbox_events, "
                "business_jobs, parse_coverage, source_anchors, "
                "document_versions, source_documents, idempotency_records, "
                "audit_events, memberships, sites, studies CASCADE"
            )
        )
        connection.execute(
            text(
                "TRUNCATE TABLE procrastinate_events, procrastinate_jobs, "
                "procrastinate_workers, procrastinate_periodic_defers CASCADE"
            )
        )
    return build_session_factory(engine)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        CRA_ENV="test",
        CRA_DATABASE_URL=_database_url(),
        CRA_SESSION_SECRET="synthetic-w04-session-secret",
        CRA_SESSION_COOKIE_SECURE=False,
        CRA_SYNTHETIC_ACTOR_ID="synthetic-cra-a",
        CRA_SYNTHETIC_TENANT_ID="synthetic-tenant",
        CRA_STORAGE_BACKEND="local",
        CRA_PRIVATE_STORAGE_LOCAL_PATH=str(tmp_path / "private"),
        CRA_COMMON_POLICY_PATH=str(
            FIXTURES / "rules" / "common_policy.json"
        ),
    )


@pytest.fixture
def services(session_factory, settings, queue):
    governance = GovernanceService(session_factory)
    admin = ScopeContext(
        actor_id="synthetic-admin",
        tenant_id="synthetic-tenant",
        authentication_source="trusted-test",
        platform_roles=frozenset({"platform_admin"}),
    )
    study = governance.create_study(
        admin,
        CreateStudy(
            expected_revision=0,
            idempotency_key="w04-study",
            code="W04-SYN",
            title="W04 Synthetic Rules",
        ),
    )
    site_a = governance.create_site(
        admin,
        study.resource_id,
        CreateSite(
            expected_revision=0,
            idempotency_key="w04-site-a",
            code="A01",
            name="Synthetic Rules Site A",
        ),
    )
    site_b = governance.create_site(
        admin,
        study.resource_id,
        CreateSite(
            expected_revision=0,
            idempotency_key="w04-site-b",
            code="B01",
            name="Synthetic Rules Site B",
        ),
    )
    for actor, site in (
        ("synthetic-cra-a", site_a.resource_id),
        ("synthetic-cra-b", site_b.resource_id),
    ):
        governance.grant_membership(
            admin,
            study.resource_id,
            GrantMembership(
                expected_revision=0,
                idempotency_key=f"w04-grant-{actor}",
                actor_id=actor,
                role="cra",
                site_id=site,
                can_write=True,
            ),
        )
    documents = DocumentService(
        session_factory,
        storage=build_private_storage(settings),
        queue=queue,
        governance=governance,
    )
    rules = RuleService(
        session_factory,
        governance=governance,
        common_policy_set=load_common_policy_set(settings.common_policy_path),
    )
    return {
        "governance": governance,
        "admin": admin,
        "study": study.resource_id,
        "site_a": site_a.resource_id,
        "site_b": site_b.resource_id,
        "documents": documents,
        "rules": rules,
    }


@pytest.fixture
def api(settings, session_factory, services):
    application = create_app(
        settings=settings,
        session_factory=session_factory,
        identity_provider=SyntheticIdentityProvider(settings),
        document_service=services["documents"],
        rule_service=services["rules"],
    )
    with TestClient(application) as client:
        assert client.post("/api/v1/auth/synthetic/session").status_code == 200
        yield client


def _upload_rule_document(
    api: TestClient,
    services: dict,
    *,
    filename: str,
    version_label: str,
    idempotency_key: str,
) -> dict:
    content = (ARTIFACTS / filename).read_bytes()
    response = api.post(
        f"/api/v1/studies/{services['study']}/documents",
        files={"file": (filename, content, "application/octet-stream")},
        data={
            "title": f"synthetic {filename}",
            "document_type": "protocol",
            "purpose": "rule",
            "version_label": version_label,
            "expected_revision": "0",
            "site_id": str(services["site_a"]),
        },
        headers={
            "Idempotency-Key": idempotency_key,
            "X-CSRF-Token": api.cookies.get("cra_csrf"),
        },
    )
    assert response.status_code == 202, response.text
    result = response.json()
    processed = services["documents"].process_job(uuid.UUID(result["job_id"]))
    assert processed.status == "completed"
    return result


def _extract(api: TestClient, version_id: str, key: str) -> dict:
    response = api.post(
        f"/api/v1/document-versions/{version_id}/rule-candidates",
        json={"expected_revision": 0, "idempotency_key": key},
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert response.status_code == 202, response.text
    return response.json()


def _rules(api: TestClient, services: dict) -> list[dict]:
    response = api.get(
        f"/api/v1/studies/{services['study']}/rules",
        params={"site_id": str(services["site_a"])},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _confirm_current(
    api: TestClient,
    item: dict,
    *,
    key: str,
    operations: list[dict],
):
    assert item["current_version"] is not None
    response = api.post(
        f"/api/v1/rules/{item['id']}/confirmation",
        json={
            "expected_revision": item["revision"],
            "idempotency_key": key,
            "base_version_id": item["current_version"]["id"],
            "reason": "Synthetic CRA confirmation",
            "operations": operations,
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_provider_evaluation_and_three_value_ast():
    summary = evaluate_rule_provider(FIXTURES / "manifest.json")
    assert summary["passed"] is True
    assert summary["evaluation_group"] == "evaluation"
    assert summary["rules_extracted"] == 2
    assert all(summary["corruption_checks"].values())

    condition = RuleCondition(
        op="all",
        children=[
            RuleCondition(
                op="ge",
                left=RuleOperand(kind="fact_ref", fact_key="value"),
                right=RuleOperand(kind="literal", value="10.5", unit="mg"),
            ),
            RuleCondition(
                op="not",
                child=RuleCondition(
                    op="eq",
                    left=RuleOperand(kind="fact_ref", fact_key="flagged"),
                    right=RuleOperand(kind="literal", value=True),
                ),
            ),
        ],
    )
    assert (
        evaluate_condition(
            condition,
            {
                "value": FactValue(value="11", unit="mg"),
                "flagged": FactValue(value=False),
            },
        ).result
        == "true"
    )
    assert (
        evaluate_condition(
            condition,
            {
                "value": FactValue(value="11", unit="mg"),
            },
        ).result
        == "unknown"
    )
    assert (
        evaluate_condition(
            condition,
            {
                "value": FactValue(value="11", unit="kg"),
                "flagged": FactValue(value=False),
            },
        ).result
        == "unknown"
    )


def test_extract_confirm_add_remove_and_preserve_history(
    api, services, session_factory
):
    uploaded = _upload_rule_document(
        api,
        services,
        filename="synthetic_rule_matrix_v1.docx",
        version_label="v1",
        idempotency_key="rule-v1-upload",
    )
    extracted = _extract(
        api, uploaded["document_version_id"], "rule-v1-extract"
    )
    assert extracted["candidate_count"] == 2
    assert extracted["confirmed_count"] == 0
    assert extracted["status"] == "needs_review"

    again = _extract(
        api, uploaded["document_version_id"], "rule-v1-extract"
    )
    assert again["replayed"] is True
    assert again["snapshot_id"] == extracted["snapshot_id"]

    rules = _rules(api, services)
    screen = next(item for item in rules if item["rule_key"] == "R-SCREEN-01")
    screen_detail = api.get(
        f"/api/v1/rule-versions/{screen['current_version']['id']}"
    ).json()
    source_ref = screen_detail["tree"]["source_refs"][0]
    added_child = {
        "node_key": "R-SCREEN-01-USER",
        "summary": "Check the signed consent source record",
        "children": [],
        "source_refs": [source_ref],
    }
    first_confirmation = _confirm_current(
        api,
        screen,
        key="confirm-screen-add",
        operations=[{"op": "add_child", "child": added_child}],
    )
    assert first_confirmation["replayed"] is False

    rules = _rules(api, services)
    screen = next(item for item in rules if item["rule_key"] == "R-SCREEN-01")
    second_confirmation = _confirm_current(
        api,
        screen,
        key="confirm-screen-remove",
        operations=[
            {
                "op": "remove_child",
                "child_key": "R-SCREEN-01-USER",
            }
        ],
    )
    assert second_confirmation["revision"] == screen["revision"] + 1
    current_detail = api.get(
        f"/api/v1/rule-versions/{second_confirmation['rule_version_id']}"
    )
    assert current_detail.status_code == 200
    assert all(
        child["node_key"] != "R-SCREEN-01-USER"
        for child in current_detail.json()["tree"]["children"]
    )
    history = api.get(f"/api/v1/rules/{screen['id']}/versions")
    assert history.status_code == 200
    assert [item["version_no"] for item in history.json()] == [3, 2, 1]
    assert any(item["state"] == "candidate" for item in history.json())
    with session_factory() as session:
        versions = list(
            session.scalars(
                select(RuleVersion)
                .join(Rule, Rule.id == RuleVersion.rule_id)
                .where(Rule.rule_key == "R-SCREEN-01")
                .order_by(RuleVersion.version_no)
            )
        )
        assert len(versions) == 3
        assert any(
            child["node_key"] == "R-SCREEN-01-USER"
            for child in versions[-2].tree["children"]
        )
        assert session.scalar(
            select(func.count())
            .select_from(RuleRelation)
            .where(RuleRelation.rule_key == "R-SCREEN-01")
        ) >= 3
        last_version_id = versions[-1].id
    with pytest.raises(SQLAlchemyError):
        with session_factory() as session:
            with session.begin():
                session.execute(
                    text(
                        "UPDATE rule_versions SET tree = :tree WHERE id = :id"
                    ),
                    {
                        "tree": '{"tampered": true}',
                        "id": str(last_version_id),
                    },
                )


def test_version_activation_boundaries_history_and_new_version_carryover(
    api, services, session_factory
):
    v1 = _upload_rule_document(
        api,
        services,
        filename="synthetic_rule_matrix_v1.docx",
        version_label="v1",
        idempotency_key="activation-v1-upload",
    )
    _extract(api, v1["document_version_id"], "activation-v1-extract")
    for item in _rules(api, services):
        _confirm_current(
            api,
            item,
            key=f"activation-confirm-v1-{item['rule_key']}",
            operations=[
                {
                    "op": "edit_fields",
                    "summary": item["current_version"]["summary"],
                }
            ],
        )

    v1_activation = api.post(
        "/api/v1/version-activations",
        json={
            "expected_revision": 0,
            "idempotency_key": "activate-v1",
            "document_version_id": v1["document_version_id"],
            "starts_on": "2020-01-01",
            "ends_before": "2021-01-01",
            "reason": "Synthetic user-managed start date",
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert v1_activation.status_code == 200, v1_activation.text

    previous = api.post(
        "/api/v1/rules/applicable",
        json={
            "study_id": str(services["study"]),
            "site_id": str(services["site_a"]),
            "event_date": "2020-12-31",
            "jurisdiction": "synthetic",
            "facts": {
                "screening_active": {"value": True},
                "consent_given": {"value": False},
                "emergency_treatment": {"value": False},
                "study_phase": {"value": "screening"},
            },
        },
    )
    assert previous.status_code == 200, previous.text
    previous_body = previous.json()
    assert {
        item["rule_key"] for item in previous_body["rules"]
    } == {"R-SCREEN-01", "R-VISIT-01"}
    previous_screen = next(
        item
        for item in previous_body["rules"]
        if item["rule_key"] == "R-SCREEN-01"
    )
    assert previous_screen["evaluation"]["status"] == "applicable"
    assert "B" in previous_screen["evaluation"]["selected_branch_keys"]
    assert "screening" not in previous_screen["tree"]["required_facts"]
    assert previous_body["envelope"]["status"] == "limited"
    assert previous_body["common_policy_configured"] is True

    version_add = api.post(
        f"/api/v1/documents/{v1['document_id']}/versions",
        files={
            "file": (
                "synthetic_rule_matrix_v2.docx",
                (ARTIFACTS / "synthetic_rule_matrix_v2.docx").read_bytes(),
                "application/octet-stream",
            )
        },
        data={
            "version_label": "v2",
            "expected_revision": "1",
            "user_starts_on": "2021-01-01",
        },
        headers={
            "Idempotency-Key": "activation-v2-upload",
            "X-CSRF-Token": api.cookies.get("cra_csrf"),
        },
    )
    assert version_add.status_code == 202, version_add.text
    v2 = version_add.json()
    assert services["documents"].process_job(
        uuid.UUID(v2["job_id"])
    ).status == "completed"
    extracted_v2 = _extract(
        api, v2["document_version_id"], "activation-v2-extract"
    )
    assert extracted_v2["candidate_count"] == 1
    assert extracted_v2["confirmed_count"] == 1
    rules_after_v2 = _rules(api, services)
    screen_v2 = next(
        item for item in rules_after_v2 if item["rule_key"] == "R-SCREEN-01"
    )
    screen_detail = api.get(
        f"/api/v1/rule-versions/{screen_v2['current_version']['id']}"
    ).json()
    assert any(
        relation["relation_type"] == "exception"
        for relation in screen_detail["relations"]
    )
    visit_v2 = next(
        item for item in rules_after_v2 if item["rule_key"] == "R-VISIT-01"
    )
    visit_detail = api.get(
        f"/api/v1/rule-versions/{visit_v2['current_version']['id']}"
    ).json()
    assert any(
        relation["relation_type"] == "unchanged"
        and "not treated as withdrawn" in relation["reason"]
        for relation in visit_detail["relations"]
    )
    _confirm_current(
        api,
        screen_v2,
        key="activation-confirm-screen-v2",
        operations=[
            {
                "op": "edit_fields",
                "follow_up": "Use the v2 synthetic consent wording",
            }
        ],
    )

    v2_activation = api.post(
        "/api/v1/version-activations",
        json={
            "expected_revision": 0,
            "idempotency_key": "activate-v2",
            "document_version_id": v2["document_version_id"],
            "starts_on": "2021-01-01",
            "reason": "Synthetic next version start date",
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert v2_activation.status_code == 200, v2_activation.text
    assert v2_activation.json()["conflicts"] == []

    current = api.post(
        "/api/v1/rules/applicable",
        json={
            "study_id": str(services["study"]),
            "site_id": str(services["site_a"]),
            "event_date": "2021-01-01",
            "jurisdiction": "synthetic",
            "facts": {
                "screening_active": {"value": True},
                "consent_given": {"value": False},
                "emergency_treatment": {"value": False},
                "study_phase": {"value": "screening"},
            },
        },
    )
    assert current.status_code == 200, current.text
    current_body = current.json()
    screen_current = next(
        item
        for item in current_body["rules"]
        if item["rule_key"] == "R-SCREEN-01"
    )
    assert "B" in screen_current["evaluation"]["selected_branch_keys"]
    assert any(
        unknown["code"] == "common_policy_unknown"
        for unknown in current_body["envelope"]["unknowns"]
    )
    assert current_body["envelope"]["status"] == "limited"

    preview = api.post(
        f"/api/v1/version-activations/{v2_activation.json()['activation_id']}"
        "/preview-change",
        json={
            "starts_on": "2020-06-01",
            "ends_before": "2022-01-01",
            "reason": "Synthetic correction preview",
        },
    )
    assert preview.status_code == 200
    assert preview.json()["retroactive_reassessment"] is False
    assert preview.json()["affected_rule_ids"]

    with session_factory() as session:
        assert session.scalar(
            select(func.count()).select_from(RuleSnapshot)
        ) == 2


def test_duplicate_text_is_direct_and_never_reconfirmed(api, services):
    text_content = (
        ARTIFACTS / "synthetic_rule_text.txt"
    ).read_bytes()
    first = api.post(
        f"/api/v1/studies/{services['study']}/documents",
        files={"file": ("rule.txt", text_content, "text/plain")},
        data={
            "title": "Synthetic direct rule email",
            "document_type": "text",
            "purpose": "rule",
            "version_label": "email-1",
            "expected_revision": "0",
            "site_id": str(services["site_a"]),
        },
        headers={
            "Idempotency-Key": "direct-text-upload",
            "X-CSRF-Token": api.cookies.get("cra_csrf"),
        },
    )
    assert first.status_code == 202
    first_body = first.json()
    assert services["documents"].process_job(
        uuid.UUID(first_body["job_id"])
    ).status == "completed"
    extracted = _extract(
        api, first_body["document_version_id"], "direct-text-extract"
    )
    assert extracted["confirmed_count"] == 1
    assert extracted["candidate_count"] == 0
    assert extracted["status"] == "ready"

    duplicate = api.post(
        f"/api/v1/documents/{first_body['document_id']}/versions",
        files={"file": ("rule-copy.txt", text_content, "text/plain")},
        data={"version_label": "email-2", "expected_revision": "1"},
        headers={
            "Idempotency-Key": "direct-text-duplicate",
            "X-CSRF-Token": api.cookies.get("cra_csrf"),
        },
    )
    assert duplicate.status_code == 202
    duplicate_body = duplicate.json()
    services["documents"].process_job(uuid.UUID(duplicate_body["job_id"]))
    conflicting_key = api.post(
        f"/api/v1/document-versions/{duplicate_body['document_version_id']}"
        "/rule-candidates",
        json={
            "expected_revision": 0,
            "idempotency_key": "direct-text-extract",
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert conflicting_key.status_code == 409
    assert conflicting_key.json()["error"]["code"] == "idempotency_conflict"
    replayed = _extract(
        api,
        duplicate_body["document_version_id"],
        "direct-text-duplicate-extract",
    )
    assert replayed["replayed"] is True
    assert replayed["duplicate_source"] is True
    assert replayed["snapshot_id"] == extracted["snapshot_id"]


class _StaticProvider:
    def __init__(self, result: RuleExtractionResult):
        self.result = result

    def extract_rules(self, *, anchors):
        return self.result


def test_fake_anchor_and_numeric_invention_are_rejected(
    api, services, session_factory, settings
):
    uploaded = _upload_rule_document(
        api,
        services,
        filename="synthetic_rule_evaluation.docx",
        version_label="bad-provider-v1",
        idempotency_key="bad-provider-upload",
    )
    anchors = services["documents"].anchors(
        ScopeContext(
            actor_id="synthetic-cra-a",
            tenant_id="synthetic-tenant",
            authentication_source="trusted-test",
        ),
        uuid.UUID(uploaded["document_version_id"]),
    )
    parsed = [
        services["rules"]._anchor_from_model(anchor) for anchor in anchors
    ]
    good = AnchoredRuleExtractor().extract_rules(anchors=parsed)
    fake = good.model_copy(deep=True)
    fake.rules[0].source_refs = [
        RuleSourceRef(
            anchor_key="fake-anchor",
            quote="A fabricated but plausible requirement",
            locator="fake",
        )
    ]
    bad_anchor_service = RuleService(
        session_factory,
        governance=services["governance"],
        provider=_StaticProvider(fake),
    )
    scope = ScopeContext(
        actor_id="synthetic-cra-a",
        tenant_id="synthetic-tenant",
        authentication_source="trusted-test",
    )
    with pytest.raises(RuleValidationError, match="unknown anchor"):
        bad_anchor_service.extract_candidates(
            scope,
            uuid.UUID(uploaded["document_version_id"]),
            ExtractRuleCommand(idempotency_key="fake-anchor"),
        )

    invented = good.model_copy(deep=True)
    invented.rules[0].summary += " Threshold 999 mg."
    numeric_service = RuleService(
        session_factory,
        governance=services["governance"],
        provider=_StaticProvider(invented),
    )
    with pytest.raises(RuleValidationError, match="numbers absent"):
        numeric_service.extract_candidates(
            scope,
            uuid.UUID(uploaded["document_version_id"]),
            ExtractRuleCommand(idempotency_key="invented-number"),
        )
    with session_factory() as session:
        assert session.scalar(
            select(func.count()).select_from(RuleSnapshot)
        ) == 0
        assert session.scalar(
            select(func.count()).select_from(RuleVersion)
        ) == 0


def test_cross_site_rule_extraction_is_denied(api, services, settings):
    uploaded = _upload_rule_document(
        api,
        services,
        filename="synthetic_rule_matrix_v1.docx",
        version_label="cross-site-v1",
        idempotency_key="cross-site-upload",
    )
    provider = SyntheticIdentityProvider(settings)
    identity = provider.create_identity(actor_id="synthetic-cra-b")
    application = create_app(
        settings=settings,
        session_factory=services["rules"].session_factory,
        identity_provider=provider,
        document_service=services["documents"],
        rule_service=services["rules"],
    )
    with TestClient(application) as other:
        other.cookies.set("cra_session", provider.issue_session(identity))
        other.cookies.set("cra_csrf", "synthetic-cross-site-csrf")
        denied = other.post(
            f"/api/v1/document-versions/{uploaded['document_version_id']}"
            "/rule-candidates",
            json={"expected_revision": 0, "idempotency_key": "forbidden"},
            headers={"X-CSRF-Token": "synthetic-cross-site-csrf"},
        )
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "authorization_denied"
