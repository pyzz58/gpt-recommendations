"""PostgreSQL acceptance for CRA-W01.

CRA_TEST_DATABASE_URL must point to a disposable PostgreSQL 18 database.
Running without it fails rather than silently falling back to SQLite or mocks.
"""
from __future__ import annotations

import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import SQLAlchemyError

from cra_app.governance.models import (
    AuditEvent,
    IdempotencyRecord,
    Membership,
    Site,
)
from cra_app.governance.service import (
    AuthorizationDenied,
    CreateSite,
    CreateStudy,
    GrantMembership,
    GovernanceService,
    IdempotencyConflict,
    RevisionConflict,
    ScopeContext,
    UpdateSite,
)
from cra_app.shared.db import build_engine, build_session_factory

pytestmark = pytest.mark.postgres


def _database_url() -> str:
    value = os.environ.get("CRA_TEST_DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError(
            "CRA_TEST_DATABASE_URL is required; this test never falls back to SQLite"
        )
    return value


@pytest.fixture(scope="session")
def engine():
    db_engine = build_engine(_database_url())
    with db_engine.connect() as connection:
        server_version = connection.scalar(text("SHOW server_version"))
        assert str(server_version).split(".")[0] == "18"
        tables = set(inspect(connection).get_table_names())
        assert {
            "studies",
            "sites",
            "memberships",
            "audit_events",
            "idempotency_records",
            "alembic_version",
        } <= tables
    yield db_engine
    db_engine.dispose()


@pytest.fixture
def session_factory(engine):
    with engine.begin() as connection:
        connection.execute(
            text("DROP FUNCTION IF EXISTS cra_test_reject_audit() CASCADE")
        )
        connection.execute(
            text(
                "TRUNCATE TABLE idempotency_records, audit_events, "
                "memberships, sites, studies CASCADE"
            )
        )
    return build_session_factory(engine)


@dataclass(frozen=True)
class SyntheticSetup:
    service: GovernanceService
    admin: ScopeContext
    cra_a: ScopeContext
    cra_b: ScopeContext
    viewer: ScopeContext
    study_id: uuid.UUID
    site_a_id: uuid.UUID
    site_b_id: uuid.UUID


@pytest.fixture
def governance(session_factory) -> SyntheticSetup:
    service = GovernanceService(session_factory)
    admin = ScopeContext(
        actor_id="synthetic-admin",
        tenant_id="synthetic-tenant",
        authentication_source="trusted-test-session",
        platform_roles=frozenset({"platform_admin"}),
    )
    cra_a = ScopeContext(
        actor_id="synthetic-cra-a",
        tenant_id="synthetic-tenant",
        authentication_source="trusted-test-session",
    )
    cra_b = ScopeContext(
        actor_id="synthetic-cra-b",
        tenant_id="synthetic-tenant",
        authentication_source="trusted-test-session",
    )
    viewer = ScopeContext(
        actor_id="synthetic-viewer",
        tenant_id="synthetic-tenant",
        authentication_source="trusted-test-session",
    )

    study_result = service.create_study(
        admin,
        CreateStudy(
            expected_revision=0,
            idempotency_key="fixture-study",
            code="SYNTH-001",
            title="Synthetic two-site study",
        ),
    )
    site_a_result = service.create_site(
        admin,
        study_result.resource_id,
        CreateSite(
            expected_revision=0,
            idempotency_key="fixture-site-a",
            code="A01",
            name="Synthetic Site A",
        ),
    )
    site_b_result = service.create_site(
        admin,
        study_result.resource_id,
        CreateSite(
            expected_revision=0,
            idempotency_key="fixture-site-b",
            code="B01",
            name="Synthetic Site B",
        ),
    )

    grants = (
        (
            "fixture-grant-cra-a",
            cra_a.actor_id,
            site_a_result.resource_id,
            "cra",
            True,
        ),
        (
            "fixture-grant-cra-b",
            cra_b.actor_id,
            site_b_result.resource_id,
            "cra",
            True,
        ),
        (
            "fixture-grant-viewer",
            viewer.actor_id,
            None,
            "viewer",
            False,
        ),
    )
    for key, actor_id, site_id, role, can_write in grants:
        service.grant_membership(
            admin,
            study_result.resource_id,
            GrantMembership(
                expected_revision=0,
                idempotency_key=key,
                actor_id=actor_id,
                role=role,
                site_id=site_id,
                can_write=can_write,
            ),
        )

    return SyntheticSetup(
        service=service,
        admin=admin,
        cra_a=cra_a,
        cra_b=cra_b,
        viewer=viewer,
        study_id=study_result.resource_id,
        site_a_id=site_a_result.resource_id,
        site_b_id=site_b_result.resource_id,
    )


def _count(
    session_factory,
    model,
    *conditions,
) -> int:
    with session_factory() as session:
        statement = select(func.count()).select_from(model)
        if conditions:
            statement = statement.where(*conditions)
        return int(session.scalar(statement) or 0)


def test_two_site_scopes_are_isolated_for_read_and_write(governance):
    service = governance.service

    site_a = service.get_site(governance.cra_a, governance.study_id, governance.site_a_id)
    site_b = service.get_site(governance.cra_b, governance.study_id, governance.site_b_id)
    assert site_a.code == "A01"
    assert site_b.code == "B01"

    assert [site.code for site in service.list_sites(
        governance.cra_a, governance.study_id
    )] == ["A01"]
    assert [site.code for site in service.list_sites(
        governance.cra_b, governance.study_id
    )] == ["B01"]
    assert [site.code for site in service.list_sites(
        governance.viewer, governance.study_id
    )] == ["A01", "B01"]

    with pytest.raises(AuthorizationDenied):
        service.get_site(
            governance.cra_a, governance.study_id, governance.site_b_id
        )
    with pytest.raises(AuthorizationDenied):
        service.update_site(
            governance.cra_a,
            governance.study_id,
            governance.site_b_id,
            UpdateSite(
                expected_revision=1,
                idempotency_key="forbidden-cross-site-write",
                name="Must not be written",
            ),
        )

    other_tenant = ScopeContext(
        actor_id=governance.cra_a.actor_id,
        tenant_id="other-synthetic-tenant",
        authentication_source="trusted-test-session",
    )
    with pytest.raises(AuthorizationDenied):
        service.get_study(other_tenant, governance.study_id)


def test_database_rejects_membership_with_site_from_another_study(
    governance, session_factory
):
    second_study = governance.service.create_study(
        governance.admin,
        CreateStudy(
            expected_revision=0,
            idempotency_key="fixture-second-study",
            code="SYNTH-002",
            title="Second synthetic study",
        ),
    )
    with pytest.raises(SQLAlchemyError):
        with session_factory() as session:
            with session.begin():
                session.add(
                    Membership(
                        id=uuid.uuid4(),
                        tenant_id=governance.admin.tenant_id,
                        study_id=second_study.resource_id,
                        site_id=governance.site_a_id,
                        actor_id="cross-study-user",
                        role="cra",
                        can_write=True,
                        created_by=governance.admin.actor_id,
                    )
                )


def test_same_key_replays_without_second_audit(governance, session_factory):
    command = UpdateSite(
        expected_revision=1,
        idempotency_key="site-a-idempotent-rename",
        name="Synthetic Site A revised",
    )
    first = governance.service.update_site(
        governance.cra_a, governance.study_id, governance.site_a_id, command
    )
    second = governance.service.update_site(
        governance.cra_a, governance.study_id, governance.site_a_id, command
    )

    assert first.resource_id == second.resource_id
    assert first.revision == second.revision == 2
    assert first.replayed is False
    assert second.replayed is True
    assert _count(
        session_factory,
        AuditEvent,
        AuditEvent.action == "site.update",
        AuditEvent.resource_id == governance.site_a_id,
    ) == 1

    with session_factory() as session:
        audit = session.scalar(
            select(AuditEvent).where(AuditEvent.action == "site.update")
        )
        assert audit is not None
        assert audit.before_state == {
            "code": "A01",
            "name": "Synthetic Site A",
        }
        assert audit.after_state == {
            "code": "A01",
            "name": "Synthetic Site A revised",
        }
        assert audit.revision_before == 1
        assert audit.revision_after == 2

    changed = UpdateSite(
        expected_revision=1,
        idempotency_key=command.idempotency_key,
        name="Different input with reused key",
    )
    with pytest.raises(IdempotencyConflict):
        governance.service.update_site(
            governance.cra_a, governance.study_id, governance.site_a_id, changed
        )


def test_concurrent_expected_revision_allows_only_one_writer(
    governance, session_factory
):
    barrier = threading.Barrier(2)

    def update(name: str):
        barrier.wait(timeout=10)
        return governance.service.update_site(
            governance.cra_a,
            governance.study_id,
            governance.site_a_id,
            UpdateSite(
                expected_revision=1,
                idempotency_key=f"concurrent-{name}",
                name=name,
            ),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(update, "Concurrent version A"),
            pool.submit(update, "Concurrent version B"),
        ]

    successes, conflicts = [], []
    for future in futures:
        try:
            successes.append(future.result(timeout=20))
        except RevisionConflict as exc:
            conflicts.append(exc)

    assert len(successes) == 1
    assert len(conflicts) == 1
    assert conflicts[0].current_revision == 2
    assert _count(
        session_factory,
        AuditEvent,
        AuditEvent.action == "site.update",
        AuditEvent.resource_id == governance.site_a_id,
    ) == 1
    assert _count(
        session_factory,
        IdempotencyRecord,
        IdempotencyRecord.command_name == "site.update",
    ) == 1
    with session_factory() as session:
        site = session.get(Site, governance.site_a_id)
        assert site is not None
        assert site.revision == 2
        assert site.name in {
            "Concurrent version A",
            "Concurrent version B",
        }


def test_concurrent_same_key_returns_one_audited_result(
    governance, session_factory
):
    barrier = threading.Barrier(2)
    command = UpdateSite(
        expected_revision=1,
        idempotency_key="concurrent-same-key",
        name="Same-key result",
    )

    def update():
        barrier.wait(timeout=10)
        return governance.service.update_site(
            governance.cra_a,
            governance.study_id,
            governance.site_a_id,
            command,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [pool.submit(update), pool.submit(update)]
        values = [future.result(timeout=20) for future in results]

    assert {value.resource_id for value in values} == {governance.site_a_id}
    assert {value.revision for value in values} == {2}
    assert sorted(value.replayed for value in values) == [False, True]
    assert _count(
        session_factory,
        AuditEvent,
        AuditEvent.action == "site.update",
        AuditEvent.resource_id == governance.site_a_id,
    ) == 1
    assert _count(
        session_factory,
        IdempotencyRecord,
        IdempotencyRecord.idempotency_key == command.idempotency_key,
    ) == 1


def test_audit_failure_rolls_back_business_and_idempotency(
    governance, session_factory, engine
):
    command = UpdateSite(
        expected_revision=1,
        idempotency_key="rollback-then-retry",
        name="Committed after rollback",
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE FUNCTION cra_test_reject_audit() RETURNS trigger AS $$
                BEGIN
                  IF NEW.action = 'site.update' THEN
                    RAISE EXCEPTION 'synthetic forced audit failure';
                  END IF;
                  RETURN NEW;
                END;
                $$ LANGUAGE plpgsql
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TRIGGER cra_test_reject_audit
                BEFORE INSERT ON audit_events
                FOR EACH ROW EXECUTE FUNCTION cra_test_reject_audit()
                """
            )
        )

    with pytest.raises(SQLAlchemyError):
        governance.service.update_site(
            governance.cra_a, governance.study_id, governance.site_a_id, command
        )

    with session_factory() as session:
        site = session.get(Site, governance.site_a_id)
        assert site is not None
        assert site.revision == 1
        assert site.name == "Synthetic Site A"
    assert _count(
        session_factory,
        AuditEvent,
        AuditEvent.action == "site.update",
    ) == 0
    assert _count(
        session_factory,
        IdempotencyRecord,
        IdempotencyRecord.idempotency_key == command.idempotency_key,
    ) == 0

    with engine.begin() as connection:
        connection.execute(
            text("DROP TRIGGER cra_test_reject_audit ON audit_events")
        )
        connection.execute(text("DROP FUNCTION cra_test_reject_audit()"))

    result = governance.service.update_site(
        governance.cra_a, governance.study_id, governance.site_a_id, command
    )
    assert result.revision == 2
    assert result.replayed is False
    assert _count(
        session_factory,
        AuditEvent,
        AuditEvent.action == "site.update",
    ) == 1
    assert _count(
        session_factory,
        IdempotencyRecord,
        IdempotencyRecord.idempotency_key == command.idempotency_key,
    ) == 1
