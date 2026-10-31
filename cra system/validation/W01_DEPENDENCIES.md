# CRA-W01 dependency and environment lock

Date: 2026-10-31. This record applies to CRA-W01 only. The research commit in
`architecture/reuse-catalog.json` is not an installed package version.

| Component | Locked version | Declared licence | Package Python requirement | Role |
| --- | --- | --- | --- | --- |
| SQLAlchemy | 2.0.55 | MIT | >=3.7 | ORM, transactions and row locking |
| Alembic | 1.20.1 | MIT | >=3.10 | Versioned PostgreSQL DDL |
| psycopg | 3.3.6 | LGPL-3.0-only | >=3.10 | PostgreSQL driver |
| Pydantic | 2.14.2 | MIT | >=3.10 | Command and trusted-scope validation |
| pydantic-settings | 2.16.2 | MIT | >=3.11 | Environment configuration |
| pytest | 9.2.0 (development) | MIT | >=3.10 | PostgreSQL acceptance tests |

Installed versions come from `uv.lock`; `uv sync --frozen --group dev` resolves
from that lock. The project and CI run CPython 3.13.15. The CI/development
PostgreSQL image is `postgres:18.6-bookworm` pinned to manifest
`sha256:5c4783a8cc3f0074912164f94dfa1be4e043438f0f707cf968d7af9a0d31a2c8`;
local acceptance used PostgreSQL 18.6. Package metadata confirms each declared
Python floor permits 3.13.15. Compatibility is also exercised by migration and
real-PostgreSQL tests rather than inferred from version ranges alone.

Official package metadata used for this check:

- https://pypi.org/project/SQLAlchemy/2.0.55/
- https://pypi.org/project/alembic/1.20.1/
- https://pypi.org/project/psycopg/3.3.6/
- https://pypi.org/project/pydantic/2.14.2/
- https://pypi.org/project/pydantic-settings/2.16.2/
- https://pypi.org/project/pytest/9.2.0/

This is an engineering dependency check, not a clinical validation or a claim
that OIDC, OCR, reporting or other later modules are installed.
