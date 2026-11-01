"""Seed synthetic governance scope for the W12 browser acceptance."""
from __future__ import annotations

from cra_app.governance.service import (
    CreateSite,
    CreateStudy,
    GrantMembership,
    GovernanceService,
    ScopeContext,
)
from cra_app.shared.config import get_settings
from cra_app.shared.db import build_engine, build_session_factory


def main() -> None:
    settings = get_settings()
    engine = build_engine(settings.sqlalchemy_url())
    factory = build_session_factory(engine)
    try:
        governance = GovernanceService(factory)
        admin = ScopeContext(
            actor_id="synthetic-admin",
            tenant_id=settings.synthetic_tenant_id,
            authentication_source="trusted-e2e-seed",
            platform_roles=frozenset({"platform_admin"}),
        )
        study = governance.create_study(
            admin,
            CreateStudy(
                expected_revision=0,
                idempotency_key="w12-e2e-study",
                code="W12-E2E",
                title="W12 Synthetic End-to-End Study",
            ),
        )
        for code, name, key in (
            ("E12A", "Synthetic E2E Site A", "w12-e2e-site-a"),
            ("E12B", "Synthetic E2E Site B", "w12-e2e-site-b"),
        ):
            site = governance.create_site(
                admin,
                study.resource_id,
                CreateSite(
                    expected_revision=0,
                    idempotency_key=key,
                    code=code,
                    name=name,
                ),
            )
            governance.grant_membership(
                admin,
                study.resource_id,
                GrantMembership(
                    expected_revision=0,
                    idempotency_key=f"{key}-membership",
                    actor_id=settings.synthetic_actor_id,
                    role="cra",
                    site_id=site.resource_id,
                    can_write=True,
                ),
            )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
