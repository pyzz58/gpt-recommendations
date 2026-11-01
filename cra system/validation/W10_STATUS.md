# CRA-W10 implementation record

Status: verified.
Date: 2026-11-01.

## Delivered behavior

- W03 directory-purpose versions can be referenced directly without
  reconstructing the full ISF/TMF directory.
- Directory entries are added incrementally with separate applicability,
  acquisition and verification states.
- File status changes keep append-only history and can explicitly link an
  existing M06 Issue/Action without changing that Action's state.
- A newer structured directory can be compared with the previous reference of
  the same kind for new, removed and changed item keys. Comparison remains
  unknown if either version is `reference_only`.
- Startup and closeout checklist items require an M02 project-document version
  and source locator. Checklist confirmation never creates center-close
  approval.
- Handover summaries reuse remaining M06 issues, source-progress, next actions
  and incomplete checklist items without an additional approval object.

## Code and migration

- `backend/cra_app/site_files/models.py`
- `backend/cra_app/site_files/service.py`
- `backend/cra_app/site_files/api.py`
- `backend/cra_app/monitoring/stages.py`
- `migrations/versions/0010_site_files.py`
- `web/src/features/site-files/DirectoryReview.tsx`
- `web/src/features/monitoring/StageChecklist.tsx`
- `tests/integration/test_site_files.py`

## Local synthetic verification

- Temporary PostgreSQL 18.6: all migrations through `0010_site_files`.
- `alembic downgrade 0009_review_remediation`, upgrade to head and
  `alembic check`: passed; no model/migration drift.
- `tests/integration/test_site_files.py`: 6 passed against real PostgreSQL.
- Combined affected requirements, subject, laboratory, safety, API and site-file
  suites: 70 passed.
- Python unittest discovery: 48 passed.
- Frontend: 15 passed; TypeScript and production build passed.
- Synthetic data only; no real clinical document, model call, external send or
  EDC write-back.

## Review evidence enforcement

`tools/task_evidence.py` now checks every closed finding against the successful
GitHub Actions run, exact tested commit, task job, required steps and the job log
line for each required `test::case`. Local unit tests for missing/wrong run, job,
step and test-case log binding pass.

## Authoritative execution

- Product implementation commit:
  `8c733e97ac35496ca463b171dd1cecfce73246a8`.
- Product implementation run:
  https://github.com/pyzz58/gpt-recommendations/actions/runs/41254143718
- Final exact-log/tool-bound test commit:
  `79ee1a1743946dcab4125acc9c6250d67b8f3ede`.
- Final source-bound run:
  https://github.com/pyzz58/gpt-recommendations/actions/runs/41254636286
- `cra-w10` job: real PostgreSQL 18.6 migration and migration round-trip;
  `tests/integration/test_site_files.py` 6 passed; review-gate self-tests;
  OpenAPI drift check; 15 frontend tests; TypeScript and production build.
- The same successful run reran all W01-W09 task jobs. Their current source
  digests and completion evidence were rebound to this tested commit; prior
  evidence remains in `completion_history`.
- Closed findings 03/04/08 are rebound to this run and require the exact named
  tests in their successful job logs.

## Remaining limits

- Directory extraction is incremental and user-guided; this is not a complete
  eTMF/file repository or automatic full-directory audit.
- `reference_only` cannot support complete missing/new comparisons until entries
  are structured.
- Stage requirements must be provided from project sources; the system does not
  invent a universal ISF/TMF or center-close checklist.
- Checklist completion and handover are records only. They are not project-team
  close approval, signature, archive completion or a database lock.
- W12/W15 still own integrated real-browser, iPad/weak-network/cross-device and
  authorized-use validation. No clinical time-saving claim is made.
