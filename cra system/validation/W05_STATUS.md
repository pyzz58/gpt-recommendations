# CRA-W05 completion record

Status: verified. Date: 2026-10-31.

Revalidated after W06 expanded the shared API, migration chain and frontend.
Current evidence: run `41187245522`, tested commit
`713440c1c32aaa738093f23a6fb92e6c68520421`, digest
`e9609c19d578de58ce809d34ec571a0f91af076dd877a8adf42d5e62ff10cffb`.

This record covers structured subject-context import, source-preserving patient
facts, rule-driven visit timing, independent category checkpoints and local
skip/recovery decisions. It is synthetic engineering validation, not
clinical-use validation, a complete-history import or an EDC integration.

## Delivered

- PostgreSQL migration `0004_subjects_coverage` adds stable patient identities,
  append-only clinical facts, planned/actual visit instances, rule-driven visit
  requirements, fact-change impact records, category coverage breakpoints and
  local check decisions. Database triggers reject updates and deletion of
  clinical facts and breakpoint versions.
- `backend/cra_app/subjects/context_import.py` imports the documented synthetic
  JSON, CSV and XLSX structures. Facts retain their external identity mapping,
  source, raw value, parsed value, unit and repeated-instance identity.
- Date-only values remain dates without invented clock times. Datetimes require
  an explicit UTC offset. Conflicting or malformed structured input is rejected
  before it can become a deterministic fact.
- Deterministic calculations use original-record or CRA-confirmed facts. They
  do not treat other-user replies or model suggestions as established facts.
- `backend/cra_app/subjects/calendar.py` and `service.py` evaluate visit windows
  from the applicable W04 rule version. Results expose the anchor, actual date,
  interval bounds, prerequisite facts, allowed sources, affected paths,
  continuable work and `unknown_anchor`/`unknown_actual` states.
- A missing anchor can be skipped only for the affected paths. Later input sets
  `recovery_available`; it does not silently resume the check or widen the
  decision to another subject or category.
- Fact revisions preserve earlier rows and mark dependent requirements for
  review. Per-subject/per-category breakpoint versions retain normal-scope notes,
  checked-through scope, unverified scope and revision history independently.
- The React subject timeline supports structured import, visit evaluation,
  local skip/resume and category checkpoints at
  `web/src/features/subjects/SubjectTimeline.tsx`.
- Pure synthetic fixtures under `tests/fixtures/subjects/` exercise identity
  reuse, date precision, repeated facts, missing anchors, revision impact and
  category/site isolation.

## Authoritative execution

- Tested commit: `f97fb13fe4557f9aa5fecef838ce596c8571f0a8`.
- GitHub Actions:
  https://github.com/pyzz58/gpt-recommendations/actions/runs/41185363902
- Task job: `cra-w05`.
- Required steps: `test`, `contracts`, `frontend`.
- PostgreSQL tests: 7 passed against PostgreSQL 18.6.
- The tests covered JSON/CSV/XLSX equivalence, authorized file import,
  identity/timeline reuse and cross-site isolation, rule-driven window
  boundaries and stage selection, missing-anchor skip/recovery while other work
  continues, append-only fact revision and separate category breakpoints, plus
  rejection of model suggestions as factual input.
- Contracts/frontend: OpenAPI drift check, 6 frontend tests, TypeScript and
  production build passed.
- W01-W04 were independently revalidated on the same tested commit and run.
- Subject digest:
  `2ce2fd057639285bc0f8343043d216b05e32b37d45dd23f63115932a67aa2f5b`.

Local validation also used an isolated temporary PostgreSQL 18.6 cluster. The
W05 integration file passed 7 tests, related backend regressions passed 25
tests, and the baseline suite passed 40 tests. Alembic found no model/migration
drift; W05 downgrade and re-upgrade passed.

Browser checks with synthetic data showed:

- `SYN-001` on 2021-01-02 was inside Branch V's
  `2020-12-30..2021-01-03` window and outside Branch L's window, with anchor,
  actual date and rule version visible.
- `SYN-002` without `infusion_date` showed two `unknown_anchor` paths. Choosing
  local non-completion changed those paths to `not_checked_by_user` without
  inventing a date or blocking unrelated checks.
- A laboratory breakpoint was saved independently at version 3 with the
  unverified scope recorded as `复查生化`.

## Remaining limits

- W05 accepts only the documented structured JSON/CSV/XLSX synthetic input
  contracts. It does not perform OCR, laboratory extraction, free-text clinical
  history ingestion or live EDC synchronization.
- A partial structured import is not a complete medical history. Absence from
  the imported context is not treated as proof that a clinical event did not
  occur.
- Visit timing is validated only against the synthetic W04 rule subset. Real
  protocol wording, actual visit calendars, clock/day conventions and window
  exceptions have not been clinically validated.
- No real clinical data, external model credential, report, EDC write-back or
  production deployment was used. No clinical-use or time-saving benefit is
  claimed.

Next task by dependency after W06: CRA-W07.
