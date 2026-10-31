# Core service

W13 adds immutable raw and cleaned dataset versions, CSV/XLSX import manifests,
pre-specified deterministic descriptive/group/proportion analyses, chart specs
and analysis review records. W14 renders reviewed analyses into versioned DOCX,
PPTX, recalculated XLSX and PDF files, with rendered previews, source/template
hashes and export validation. File generation does not prove data quality,
study design or scientific conclusions. W15 adds an in-process mock mailbox,
owner inbox, explicit thread linking, project-scoped drafts, attachment hashes,
time/count-bounded send authorization and an uncertain-outcome reconciliation
ledger. No live mailbox or real send is connected.
W16 adds project-scoped external organizations/contacts, expert candidates,
engagement scopes, quote and contract records, external authorizations,
deliverable receipt/acceptance, and separate regulatory, patent, financial and
commercial fact records. These are records of supplied evidence, not proof that
an institution was contacted, contracted, paid or executed work.
W17 adds immutable audit snapshots for claim versions, analysis runs and external
deliverables; separate deterministic A25/A26 rule sets; critical/major downstream
blocking; claim dispute propagation; append-oriented finding dispositions; and a
synthetic seven-case regression fixture. These rules are not live independent
agents, human expert reviews, complete scientific validation or evidence that
unseen medical claims will be detected.

Run from the project root after creating an external PostgreSQL database:

```bash
cp .env.example .env
make db-upgrade
make db-bootstrap
make dev-api
```

The API binds to `127.0.0.1:8000`. OpenAPI is available at `/docs`. Readiness
requires PostgreSQL at the migration revision expected by the application.
W14 requires LibreOffice headless, Poppler and an installed CJK font for Office
preview validation. Set `MEDICAL_ONE_OFFICE_SOFFICE_PATH`,
`MEDICAL_ONE_OFFICE_PDFTOPPM_PATH`, and optionally
`MEDICAL_ONE_OFFICE_PDF_FONT_PATH`; the export runtime reports `unavailable`
instead of silently generating broken previews. Real external scholarly access,
live models, real email delivery, external side effects and a continuously running
background worker remain unavailable. W14—W17 do not claim scientific validity,
correct study design, regulatory applicability, complete typographic QA, real
email delivery, human/non-mock independent review, complex statistical modelling,
complete upload controls, deletion/recovery, real external verification, or
container isolation.
