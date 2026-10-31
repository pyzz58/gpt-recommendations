# CRA-W06 completion record

Status: verified. Date: 2026-10-31.

Revalidated after W08 expanded shared migrations, API, fixtures and frontend.
Current evidence: run `41193029019`, tested commit
`a9c699bf8196d6a1cbbe2aeafbbccaade6835fde`, digest
`163be945f8ecebc2162ac98e07c99e2a8b40ff55a2a11a03425fa64817a7fe16`.

Revalidated after W07 expanded the shared migration, API and frontend. Current
evidence: run `41189767787`, tested commit
`9fe48b4de8932ef3e4bbe250dbdddb1d6968fc59`, digest
`29aecbbff62cf1ea4bbcbd7cdf02949b293ef4156c49cdece7ff304ec5af44dc`.

This record covers carryover from synthetic historical reports, tracks and issue
text; stable Issue and per-action history; CRA click confirmation; Query draft
versus formal identity and deadline evidence; and the initial monitoring-visit
workbench. It is synthetic engineering validation, not a real monitoring visit,
clinical-use validation or evidence of time savings.

## Delivered

- PostgreSQL migration `0005_issues_monitoring` adds stable Issues, per-action
  completion, append-only Issue history, Query links, monitoring visits,
  previsit selections and mapped carryover candidates. Cross-study/site foreign
  keys and database checks prevent mixed scopes and unsupported deadline/Query
  claims.
- `backend/cra_app/issues/service.py` records `user_confirmation`, server actor
  and confirmation time for selected non-PD actions. It does not require a CRC
  reply, attachment, location update or extra approval.
- PD reporting uses `confirm-reported` only for the `pd_reporting` action.
  Confirming it does not complete data correction, document supply or other
  actions. Reopening an action clears its current completion state while its
  confirmation/reopen history remains append-only.
- Issue actions retain independent `open`, `reported_done`, `completed` and
  `needs_correction` states. The Issue list exposes an aggregate display state
  without replacing action-level completion.
- Draft and formal Query links are separate. Formal Query requires a real
  external identifier and opening date; a known due date requires an explicit
  deadline source. Missing deadline evidence returns `due_date_unknown` and no
  invented overdue days.
- `backend/cra_app/issues/carryover_import.py` parses actual W03 DOCX/PDF
  anchors, XLSX track rows and issue text into preview candidates. It preserves
  original issue number, finding, location, recommendation/source, known
  progress, actions, anchor/cell locations and unknown fields.
- User corrections are stored with the preview import. Confirmation maps exact
  existing issue numbers to the stable Issue instead of creating duplicates;
  source hash/parser fingerprints and idempotency prevent repeated import.
- `backend/cra_app/monitoring/service.py` starts a monitoring visit with all
  unresolved site issues and only M02 `reference_only` source references.
  Previsit selection is saved separately and never removes unselected Issues.
- React workbench components add expandable carryover, source/history display,
  per-action confirmation/reopen, Query linkage, selection and preview/correction
  before import in `web/src/features/issues/`.
- Pure synthetic fixtures under `tests/fixtures/issues/` are deterministically
  generated DOCX/XLSX inputs with committed SHA-256 values. Tests do not import
  carryover from a prebuilt JSON answer.

## Authoritative execution

- Tested commit: `713440c1c32aaa738093f23a6fb92e6c68520421`.
- GitHub Actions:
  https://github.com/pyzz58/gpt-recommendations/actions/runs/41187245522
- Task job: `cra-w06`.
- Required steps: `test`, `contracts`, `frontend`.
- PostgreSQL tests: 5 issue/action tests and 3 file/text carryover tests passed
  against PostgreSQL 18.6 in the task-specific CI job.
- The tests cover independent PD/correction completion, no-reply CRA click
  confirmation, reopen with preserved history, complete carryover after a
  two-item previsit selection, third-visit stable issue number, Query identity
  and deadline evidence, cross-site denial, append-only history, DOCX/XLSX/text
  extraction, unknown fields, source locations, exact-number reuse and duplicate
  import replay.
- Contracts/frontend: OpenAPI drift check, 8 frontend tests, TypeScript and
  production build passed.
- W01-W05 were independently revalidated in the same successful run, including
  W03 PostgreSQL/S3/provider steps and W02 runtime/devcontainer smoke.
- Subject digest:
  `25ac8bb783e93612018a4afb5f88e3eb355c3115a3fea086be9fef17f8b84887`.

Local validation used an isolated temporary PostgreSQL 18.6 cluster. The two
W06 integration files passed 8 tests, W01/W04/W05 regressions passed 27 tests,
and the baseline suite passed 43 tests. Alembic found no model/migration drift;
`0005` downgrade and re-upgrade passed. Frontend tests, typecheck and production
build also passed locally.

Browser checks against the local API and Vite used only synthetic data:

- A synthetic DOCX report was uploaded through M02, parsed, previewed and
  confirmed. `CRA-SYN-101` and `CRA-SYN-102` entered the unresolved issue list only
  after confirmation; `CRA-SYN-102` retained unknown location/recommendation
  until the test correction was saved.
- Starting the monitoring visit brought both Issues into complete carryover.
  Confirming the PD action removed that resolved Issue from the remaining list,
  while the separate correction Issue remained and the server kept append-only
  history.
- Selecting one Issue for previsit showed `已选 1 / 1`; the full remaining
  carryover was still present. No letter/template was generated.

## Remaining limits

- Carryover extraction is deterministic for the documented English/Chinese
  header aliases and paragraph-label forms. Arbitrary report prose, unusual
  tables, spreadsheet layouts, scanned PDFs and OCR are not supported in W06.
- W06 does not call a model to fill missing findings, recommendations, sources
  or actions. Users must review/correct incomplete candidates.
- M10 directory status remains unimplemented. M02 references are
  `reference_only` and cannot be presented as a complete ISF/TMF verification.
- Query records do not synchronize with or submit to a real EDC. Previsit
  selections are saved only; the final template-based letter belongs to W11.
- No real clinical report, subject data, EDC export, external model credential,
  email, report or EDC write-back was used. Real-format coverage, clinical
  appropriateness and time-saving benefit remain unvalidated.

Next task by dependency after W09: CRA-W10.
