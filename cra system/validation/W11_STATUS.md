# CRA-W11 implementation record

Status: in progress pending task-specific GitHub Actions evidence.
Date: 2026-11-01.

## Delivered behavior

- DOCX and XLSX templates bind to immutable M02 template versions through
  explicit fields, cell mappings and repeated regions.
- DOCX templates accept only declared variables and simple `for`/`endfor`
  loops; the renderer also uses a sandboxed Jinja environment and rejects
  arbitrary control expressions.
- A visit letter renders only the explicitly selected issues and does not
  remove or modify the complete issue list.
- A monitoring report renders prior issues and current findings in separate
  sections and reuses coverage, facts, rules, safety assessments and directory
  state from the same monitoring scope.
- `prepared` and `issued` snapshots are separate. Issuing requires an explicit
  user statement; missing, unknown or not-checked scope also requires explicit
  acknowledgement.
- Report and Excel track files are rendered from one immutable snapshot.
  Existing openpyxl workbook templates are filled instead of replaced by a new
  export engine.
- Sent, submitted and archived events are separate append-only records. Export
  success is never labelled as an external send.

## Code and migration

- `backend/cra_app/reports/models.py`
- `backend/cra_app/reports/service.py`
- `backend/cra_app/reports/template_mapping.py`
- `backend/cra_app/reports/docx_export.py`
- `backend/cra_app/reports/xlsx_export.py`
- `backend/cra_app/reports/api.py`
- `migrations/versions/0011_reports_outputs.py`
- `web/src/features/reports/ReportPreview.tsx`
- `tests/integration/test_reports.py`
- `tests/fixtures/reports/artifacts/`

## Locked dependency

- `docxtpl 0.20.2`, LGPL-2.1-only, locked in `uv.lock`.
- `openpyxl` remains the XLSX reader/writer and preserves the existing
  template's workbook structure.

## Local synthetic verification

- Temporary PostgreSQL 18.6: all migrations through
  `0011_reports_outputs`.
- Downgrade to `0010_site_files`, upgrade to head and `alembic check`: passed;
  no model/migration drift.
- `tests/integration/test_reports.py`: 3 passed with real PostgreSQL and real
  Office files.
- Combined governance, rules, subjects, issues, carryover, EDC, laboratory,
  recognition, safety, site-file, report and platform API suites: 85 passed.
- Python unittest discovery: 49 passed.
- Frontend: 17 passed; TypeScript and production build passed.
- Synthetic only; no real template, clinical data, external send, signature or
  EDC write-back.

## Remaining limits

- DOCX support covers declared fields and simple loop regions. Content
  controls, macro-enabled documents, split-run placeholders, nested layouts and
  arbitrary formatting are not promised.
- The supplied project template still determines layout and wording. This
  implementation does not infer an arbitrary Word/Excel template mapping.
- Export creates a private file but does not send or submit it. Actual delivery
  must be recorded separately after the user performs the action.
- Report quality, authentic site templates, cross-device workflow and clinical
  time-saving effects remain for W12/W15 validation.
