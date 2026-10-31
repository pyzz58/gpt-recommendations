# CRA-W01 completion record

Status: verified. Date: 2026-10-31.

Revalidated after W05 added the subject/checkpoint migration. Current evidence:
run `41185363902`, tested commit
`f97fb13fe4557f9aa5fecef838ce596c8571f0a8`, digest
`03b83983234d59ee9974f1e78b1545b0a69ce439f167368d4be7c29a808ef150`.

Revalidated after W06 added the issue/monitoring migration and shared API/UI
entrypoints. Current evidence: run `41187245522`, tested commit
`713440c1c32aaa738093f23a6fb92e6c68520421`, digest
`81fbdbc98039f4d1a5e2fcd813d13c6593bc64f3972e6fc68b291267c08f36b8`.

Revalidated after W02 added the authorized workspace-list query to the shared
governance service. Current evidence: GitHub Actions run `41178355227`, tested
commit `2db8475906b57a1689ca0f6fcc19b02880c67c4f`, current subject digest
`03ba12806def27bcfcce82a406ebbc72cf0f06cfc5af27cd593c8c62edef462a`.
The earlier W01 evidence remains in `plan/tasks.json` under
`completion_history`; the execution details below record that earlier run.

Revalidated again after W03 changed the shared Python dependency lock and
synthetic storage configuration. Current evidence: run `41181003025`, tested
commit `b6ccecb60ae7894bf9ca589509ef0d6aa12d1cdb`, digest
`c9e4a400a314628a818104c2ca8c79fac86ec500d7c8504f8d50d99e3e78aea5`.

Revalidated after W04 expanded the migration entrypoint and shared runtime
configuration. Current evidence: run `41183652961`, tested commit
`f2bac7dcf527e7e54e6a5af27cb2663af862cccf`, digest
`a414762fe3ff30fe2512ac1ddff2ea69867cf4d1000efe20ae1a78cc2ff99ec9`.

This record covers only the shared data, authorization, revision, idempotency
and audit foundation. It is engineering and synthetic validation, not clinical
use validation.

## Delivered code and migration

- `backend/cra_app/governance/models.py`: study, site, membership, audit and
  idempotency tables with tenant/study/site composite constraints.
- `backend/cra_app/governance/service.py`: trusted scope authorization,
  `expected_revision` commands, row-locked concurrent updates, actor/scope/input
  bound idempotency and same-transaction audit.
- `backend/cra_app/shared/db.py` and `config.py`: SQLAlchemy/psycopg PostgreSQL
  engine and environment configuration.
- `migrations/versions/0001_governance.py`: initial PostgreSQL migration.
- `tests/integration/test_governance.py`: six real-PostgreSQL acceptance tests.
- `pyproject.toml`, `.python-version` and `uv.lock`: CPython 3.13.15 and locked
  dependencies. `validation/W01_DEPENDENCIES.md` records versions and licences.

## Authoritative execution

- Implementation commit: `d06a3cc17ee35fe81525bdb24bc972d53e3c4c9f`.
- Tested commit: `ffe71849c9046d5f070bae1eb43aafd562a26cff`.
- GitHub Actions run:
  https://github.com/pyzz58/gpt-recommendations/actions/runs/41177038097
- Task job: `cra-w01`, committed step `migrate`, then committed step `test`.
- PostgreSQL runtime reported by the job: 18.6 Debian image pinned by digest.
- `migrate`: `0001_governance` applied to an empty temporary database.
- `test`: 6 passed, including isolation, composite constraints, idempotency,
  concurrent revision contention, same-key concurrency and audit-failure rollback.
- Baseline job: synchronization and 40 existing tests passed.
- Subject digest:
  `5c00b0745688cb459427b1e875d93377fec217ac9b388fcfe50baec2c8d3ae7f`.

Local reproduction used an isolated PostgreSQL 18.6 temporary cluster with the
same commands. Alembic `check` found no model/migration drift. Downgrade to base,
upgrade to head and all tests were rerun successfully.

## Remaining limits

- Authorization is a Python service boundary plus PostgreSQL constraints, not
  PostgreSQL RLS. An application-role/RLS design was not selected in W01.
- There is no formal OIDC adapter or FastAPI endpoint; W02 owns the API and
  browser shell. W01 tests construct a trusted `ScopeContext` only in synthetic
  fixtures.
- Membership grant is implemented; a full administration/revocation UI and
  release audit policy are later work. No later business table was created.
- No OCR, provider, report, EDC integration, production deployment or clinical
  effectiveness/time-saving claim is made.

Next task by dependency after W06: CRA-W07.
