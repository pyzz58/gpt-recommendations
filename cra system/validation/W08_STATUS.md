# CRA-W08 completion record

Status: verified. Date: 2026-10-31.

This record covers source laboratory report recognition, field-level review,
exact instance matching and deterministic EDC comparison for the declared
synthetic scope. It is provider/synthetic engineering validation, not clinical
use validation or proof of time savings.

## Delivered

- PostgreSQL migration
  `migrations/versions/0007_laboratory_comparison.py` adds persistent
  laboratory recognition jobs, source candidates, append-only review actions,
  immutable comparisons, field results and explicit M06 issue links. It also
  adds optional EDC `report_revision` mapping and authorized snapshot listing.
- `backend/cra_app/providers/lab_ocr.py` routes selectable text PDFs to the
  pdfplumber table adapter and images/scanned PDFs to Docling 2.145.0 in an
  isolated Python 3.12 process. The main application remains on Python 3.13.
- `backend/cra_app/laboratory/recognition.py` validates provider tables,
  preserves page/table/row/cell coordinates and converts source strings into
  typed dates, Decimal values, operators, units, initial/repeat instances and
  report revisions.
- `backend/cra_app/laboratory/matching.py` matches exact subject, analyte,
  collection date, available time, visit/specimen, report revision and
  initial/repeat identity. Multiple candidates remain ambiguous; numerical
  proximity is never used to select a match.
- `backend/cra_app/laboratory/comparison.py` compares values and bounds with
  Decimal, distinguishes unit review, value difference, range/logic difference,
  not seen, unreadable and user skip, and never turns `<value` into an exact
  value.
- Review decisions are append-only. Confirm/correct/skip advance the report
  revision; changed fields become stale and cannot be linked to M06 until the
  comparison is rerun. Unchanged fields remain usable.
- `backend/cra_app/laboratory/service.py` creates the persistent
  `lab_recognition_jobs` record, idempotently stores provider output and
  comparisons, and creates only selected `edc_correction` issues through the
  M06 public service. It does not create PD reporting or complete an action.
- `web/src/features/laboratory/RecognitionReview.tsx` provides AG Grid review,
  source PDF/image positioning, focused correction/skip and scoped batch
  confirmation. `LabComparison.tsx` renders the side-by-side source/EDC result,
  stale-field state, React-PDF source view and explicit M06 issue linking.
- Pure synthetic fixtures and expected answers are under
  `tests/fixtures/labs/`. Expected answers are never provided to recognition
  adapters.

## Public entry points

- `POST /api/v1/studies/{study_id}/lab-reports`
- `GET /api/v1/studies/{study_id}/lab-reports`
- `GET /api/v1/lab-reports/{id}`
- `POST /api/v1/lab-reports/{id}/observations/{observation_id}/decision`
- `POST /api/v1/lab-reports/{id}/observations/batch-confirm`
- `POST /api/v1/lab-reports/{id}/observations`
- `POST /api/v1/lab-comparisons`
- `GET /api/v1/lab-comparisons/{id}`
- `POST /api/v1/lab-comparisons/{id}/issues`
- `GET /api/v1/studies/{study_id}/edc-snapshots`

## Authoritative execution

- Tested commit: `a9c699bf8196d6a1cbbe2aeafbbccaade6835fde`.
- GitHub Actions:
  https://github.com/pyzz58/gpt-recommendations/actions/runs/41193029019
- Final gate commit `9071889cd1cdd060bfc7b5e3dbff667edb86e4c4`
  and run
  https://github.com/pyzz58/gpt-recommendations/actions/runs/41193468497
  also passed baseline and every W01-W08 job after the dependency-invalidation
  test fixture was fixed.
- Task job: `cra-w08`.
- Required steps: `test`, `lab-provider-evaluation`, `contracts`, `frontend`.
- W08 PostgreSQL/recognition tests: 6 laboratory integration tests and
  3 source-file recognition tests passed against PostgreSQL 18.6.
- Independent provider result from the CI log: text PDF and clear PNG both
  recovered 5/5 rows with coordinates and no key identity/date/value/unit/
  operator/initial-repeat errors.
- Both formats produced `agreement`, `agreement`, `unit_review`,
  `not_seen_in_export` and `logic_difference`. This is 2 automatic agreements
  and 3 fields requiring focused review, not an OCR failure rate.
- Contracts/frontend: OpenAPI drift check, 12 frontend tests, TypeScript and
  production build passed.
- W01-W07 were independently revalidated in the same successful run, including
  W03 PostgreSQL/S3/provider and W02 runtime/devcontainer smoke.
- Subject digest:
  `59d1d3010af6129c5e01d40458fd3564a5c8c3627104c2cc83a3a089a9e88077`.

Local validation used a fresh PostgreSQL 18.6 cluster. Baseline passed 43
tests; API plus W01-W08 cross-module tests passed 47 tests. Migration upgrade,
downgrade from `0007` to `0006` with data present, and re-upgrade succeeded;
Alembic found no drift.

CI provider evaluation observed 0.057 s for text PDF recognition/comparison
and 61.313 s end-to-end for the isolated PNG, with 34.771 s inside Docling and
2,824,749,056 bytes maximum RSS. These are one synthetic CI run, not production
capacity or workflow-time claims.

Browser checks used synthetic data. The workbench showed the parsed source PDF,
five source rows, same-day Hemoglobin Initial/Repeat separation, source
coordinates, batch confirmation of five structurally valid candidates and a
five-field comparison. Selected Glucose showed `unit_review` and the source
rectangle at page 1/table 1/row 3. The comparison explicitly displayed
`not_seen_in_export` scope and “医学安全判断 未执行”.

## Remaining limits

- Only selectable-text ruled PDFs and one clear synthetic PNG are validated.
  JPEG uses the same route but lacks a separate sample; scanned PDF is
  experimental. Handwriting, blur, arbitrary hospital templates, Chinese
  layouts, multi-page continuation tables and all vendor revisions remain
  untested.
- Header aliases and field extraction cover only the documented synthetic
  English/Chinese subset. Unknown values, text mappings or units remain under
  review rather than being guessed.
- Docling runs in an isolated development/CI environment. W15 still owns an
  approved production image, model mirror, SBOM/license review, concurrency and
  recovery validation. The CI PNG used approximately 2.8 GiB RSS.
- The active runtime performs recognition in the API process after persisting a
  job; it does not yet run that job through a dedicated distributed OCR worker.
  A production worker/isolation decision remains part of release enablement.
- Only one synthetic text PDF and one independent synthetic image were used.
  There is no real-format clinical accuracy, approved trial, key-error threshold
  or full manual-workflow time comparison.
- W09 medical/safety analysis was completed separately after this W08 record.
  W11 reports, W14 difficult formats and EDC write-back remain unimplemented.
  M06 receives only an explicitly selected `edc_correction` action from W08,
  not a PD or safety conclusion.
- Vite still warns about a main JavaScript chunk of approximately 2.1 MB.

Next task by dependency after W09: CRA-W10.
