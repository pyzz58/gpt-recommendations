# CRA-W07 completion record

Status: verified. Date: 2026-10-31.

Revalidated after W08 added optional EDC report-revision mapping, authorized
snapshot listing and the shared laboratory comparison consumer. Current
evidence: run `41193029019`, tested commit
`a9c699bf8196d6a1cbbe2aeafbbccaade6835fde`, digest
`f49038ec3b804a87bc7923f6450e3afe91c9142ceea4ef61e3f5e6848421c782`.

This record covers previewing an EDC laboratory `.xlsx` export, confirming a
reusable column mapping and export scope, and storing an immutable snapshot with
normalized laboratory records that retain source positions. It is synthetic
engineering validation, not a source-report comparison, clinical-use validation
or evidence that an EDC export is complete.

## Delivered

- PostgreSQL migration `migrations/versions/0006_edc_import.py` adds EDC import
  previews, reusable mappings, sheet/cell previews, immutable snapshots,
  immutable raw rows and normalized laboratory records. Database triggers reject
  updates and deletion of snapshots, raw rows and normalized records.
- `backend/cra_app/edc_import/excel.py` reads macro-free multi-sheet XLSX files
  with openpyxl 3.1.5. It preserves sheet visibility, row/cell coordinates,
  raw text, formulas and formula cache values, infers headers and proposes a
  mapping. It never executes macros or evaluates formulas.
- `backend/cra_app/edc_import/service.py` implements authorized preview and
  confirmation. A confirmed mapping is reused for a matching header signature;
  ambiguous patient, visit, date or repeat-instance fields remain visible for
  review. Confirmation runs in one PostgreSQL transaction and stores the source
  version, hash, mapping digest and export scope idempotently.
- Same-day initial and repeat laboratory results use a stable `instance_key` and
  remain separate records. A result based on a formula is deterministic only
  when the XLSX contains a cached value; without that cache it returns
  `formula_cache_missing`, sets `needs_review` and does not invent a value.
- A miss is fixed to `not_seen_in_export` with
  `edc_omission_inferred=false`. It cannot be surfaced as proof that the source
  report or EDC omitted a result.
- Repeating the same file, mapping and scope returns the original snapshot.
  A corrected export creates a new immutable snapshot while retaining the old
  one.
- `web/src/features/edc/ImportPreview.tsx` uses the MIT-licensed AG Grid
  Community/React 36.2.0 packages for multi-sheet preview and mapping review.
  Browser filtering/sorting does not change the server-owned snapshot.
- The synthetic fixture
  `tests/fixtures/edc/artifacts/synthetic_edc_lab.xlsx` has SHA-256
  `4ddc541175828b38fd1667d9226f28a8fba9a5c57dddc06816e0392409bb1a7b`.

Public API routes:

- `POST /api/v1/studies/{study_id}/edc-imports/preview`
- `GET /api/v1/edc-imports/{id}`
- `POST /api/v1/edc-imports/{id}/confirm`
- `GET /api/v1/edc-snapshots/{id}`
- `POST /api/v1/edc-snapshots/{id}/lookup`
- `GET /api/v1/studies/{study_id}/edc-import-mappings`

## Authoritative execution

- Tested commit: `9fe48b4de8932ef3e4bbe250dbdddb1d6968fc59`.
- GitHub Actions:
  https://github.com/pyzz58/gpt-recommendations/actions/runs/41189767787
- Task job: `cra-w07`.
- Required steps: `test`, `contracts`, `frontend`; the job also applied the
  migration with `migrate`.
- PostgreSQL 18.6 integration tests:
  `uv run --frozen pytest -q tests/integration/test_edc_import.py` passed
  5 tests. They cover multi-sheet formula/cache preservation, mapping and range
  confirmation, same-day initial/repeat separation, source-cell traceability,
  mapping reuse, duplicate confirmation, cross-site denial, corrected-version
  snapshots and immutability.
- Contracts/frontend: OpenAPI drift check, 10 frontend tests, TypeScript and the
  production build passed.
- W01-W06 were independently revalidated in the same successful run, including
  W03 PostgreSQL/S3/provider steps and W02 runtime/devcontainer smoke.
- Subject digest:
  `0841f1ac364c984ecc49549dd3444566a2f68edebf13ac2084f79471d3564e0b`.

Local validation used the isolated PostgreSQL 18.6 cluster on port 55435. The
W07 integration file passed 5 tests and cross-module sequential regressions
passed 32 tests. The baseline passed 43 tests. A clean migration through `0006`,
downgrade from `0006` to `0005` and re-upgrade succeeded; Alembic reported no
model/migration drift.

Browser checks used only synthetic data. The UI displayed all three sheets,
formula text and cached values, mapping and scope. Confirmation produced a
snapshot with 5 raw rows and 5 normalized laboratory records. A same-day
Hemoglobin Initial `121` and Repeat `119` remained separate, and the lookup UI
kept the fixed `not_seen_in_export` semantics. Because the browser automation
did not expose direct local-file injection, the preview was created through an
authenticated FastAPI TestClient and then opened at `?edcPreview=<id>` for the
actual UI confirmation.

## Remaining limits

- Only macro-free `.xlsx` is supported. Macros and external links are not
  executed, and formulas are not evaluated.
- A formula without a cached value is not assigned a numeric result; the row is
  retained as `needs_review` with `formula_cache_missing`.
- Header aliases, mapping suggestions and field coverage are validated only for
  the documented synthetic English/Chinese fixture. Unusual EDC templates and
  real vendor export variations are not validated.
- A fixed miss means only `not_seen_in_export`. It does not prove source or EDC
  omission and must not be described as an EDC missing-entry finding.
- W07's own scope imports and standardizes EDC results only. W08 subsequently
  implements source-report extraction, identity/instance matching,
  comparison and difference work items; reports, Query submission and EDC
  write-back remain outside both tasks.
- No real clinical data, real EDC export, external model credential, provider
  call or approved clinical trial was used. Clinical appropriateness,
  real-format coverage, safety and time-saving benefit remain unvalidated.
- Vite continues to report a chunk larger than 900 kB; after adding AG Grid the
  main JavaScript bundle is about 2.1 MB. This is a delivery/maintenance limit,
  not a correctness result.

Next task by dependency after W09: CRA-W10.
