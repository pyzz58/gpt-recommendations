"""Idempotently create the public synthetic workbench data."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from cra_app.governance.service import (  # noqa: E402
    CreateSite,
    CreateStudy,
    GovernanceService,
    GrantMembership,
    ScopeContext,
)
from cra_app.shared.config import get_settings  # noqa: E402
from cra_app.shared.db import build_engine, build_session_factory  # noqa: E402


def main() -> int:
    settings = get_settings()
    if settings.environment != "synthetic":
        print("Refusing to seed synthetic records outside CRA_ENV=synthetic", file=sys.stderr)
        return 2

    engine = build_engine(settings.sqlalchemy_url())
    try:
        service = GovernanceService(build_session_factory(engine))
        admin = ScopeContext(
            actor_id="synthetic-platform-admin",
            tenant_id=settings.synthetic_tenant_id,
            authentication_source="synthetic-seed-command",
            platform_roles=frozenset({"platform_admin"}),
        )
        study = service.create_study(
            admin,
            CreateStudy(
                expected_revision=0,
                idempotency_key="synthetic-v1-study",
                code="SYNTH-001",
                title="合成监查演示项目",
            ),
        )
        sites = []
        for code, name in (
            ("S01", "合成中心一"),
            ("S02", "合成中心二"),
        ):
            sites.append(
                service.create_site(
                    admin,
                    study.resource_id,
                    CreateSite(
                        expected_revision=0,
                        idempotency_key=f"synthetic-v1-site-{code.lower()}",
                        code=code,
                        name=name,
                    ),
                )
            )
        service.grant_membership(
            admin,
            study.resource_id,
            GrantMembership(
                expected_revision=0,
                idempotency_key="synthetic-v1-default-cra",
                actor_id=settings.synthetic_actor_id,
                role="cra",
                site_id=None,
                can_write=True,
            ),
        )
        print(
            json.dumps(
                {
                    "tenant_id": settings.synthetic_tenant_id,
                    "actor_id": settings.synthetic_actor_id,
                    "study_id": str(study.resource_id),
                    "site_ids": [str(site.resource_id) for site in sites],
                },
                ensure_ascii=False,
            )
        )
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
