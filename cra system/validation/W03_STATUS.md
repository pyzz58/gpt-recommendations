# CRA-W03 completion record

Status: verified. Date: 2026-10-31.

This record covers source document intake, immutable versions, deterministic
DOCX/text-PDF/text parsing, private storage, parse jobs and source review. It is
engineering/synthetic validation, not clinical-use or full-format validation.

## Delivered

- PostgreSQL migration `0002_documents_jobs` for source documents, versions,
  anchors, coverage, business jobs and outbox. Source-version fields are
  protected by a database immutability trigger.
- Authorized multipart upload and append-version APIs with CSRF, idempotency,
  source signatures, size limits, SHA-256 duplicate references and explicit
  source revision.
- Controlled OOXML DOCX parser: logical section paths, content controls,
  merged table cells, footnotes, headers/footers, run-level bold/italic/
  underline and embedded-media coverage. Embedded content is never executed.
- pdfplumber text-PDF parser: page numbers, line/cell coordinates and tables.
  Page failures are returned as coverage and cannot silently disappear.
- Private local and boto3 S3 adapters; every source-content read passes through
  CRA scope authorization and returns private/no-store content.
- Procrastinate queue/worker with transactional Outbox. Queueing locks suppress
  duplicate delivery; workers reload authorization and the input version before
  reading private content. Job retry reuses the same source version.
- React document workspace and locally bundled React-PDF/PDF.js viewer with
  page/bbox highlighting.
- Pure synthetic DOCX/PDF/TXT/XLSX/PNG/template corpus with hashes, development
  and independent evaluation groups.

## Authoritative execution

- Tested commit: `b6ccecb60ae7894bf9ca589509ef0d6aa12d1cdb`.
- GitHub Actions run:
  https://github.com/pyzz58/gpt-recommendations/actions/runs/41181003025
- Task job: `cra-w03`.
- PostgreSQL tests: 8 passed against PostgreSQL 18.6 and an S3-compatible HTTP
  service.
- Tests covered upload idempotency, CSRF rejection, source immutability,
  duplicate hashes, append revision, DOCX footnotes/merged cells/background/
  formatting/embedded media, PDF coordinates/tables, private content access,
  worker authorization changes, Outbox failure rollback, same-version retry and
  the actual Procrastinate worker.
- Contracts/frontend: OpenAPI drift check, frontend tests, typecheck and
  production build passed.
- Provider probe: Docling 2.145.0 passed the synthetic image with expected
  tokens and coordinates; PaddlePaddle 3.3.1 failed its Linux oneDNN runtime
  path. The failure is retained in `validation/PROVIDER_FEASIBILITY.md`.
- W01 and W02 independently revalidated after dependency/UI changes.
- Subject digest:
  `aaef6a167d0cbdefe9137df5263d26b1fa5a5ccc9d9ba134a17c5123cfaf19b0`.

Local validation used isolated PostgreSQL 18.6, an S3-compatible boto3 server,
migration upgrade/downgrade/re-upgrade, Alembic drift check and an actual browser
review of authorization selection, document versions, anchors and PDF page/
highlight rendering. The full local backend suite passed 60 tests.

Revalidated after W04 reused source anchors and changed shared fixtures/API.
Current evidence: run `41183652961`, tested commit
`f2bac7dcf527e7e54e6a5af27cb2663af862cccf`, digest
`3e1388a873201711177df48f560e6e179e586f57fe4e8368a68aee2e6f4a6352`.

## Remaining limits

- Scanned PDFs, photographs and other non-text formats are retained privately
  but not automatically OCR parsed in W03.
- XLSX is retained for W07 and images for W08; W03 does not invent their
  structured contents. DOCX embedded media is explicitly unsupported.
- The S3-compatible CI server and local emulator are engineering fixtures, not
  approval of a production storage service. W15 must validate the actual
  private provider, retention and recovery.
- Procrastinate queueing is relayed after the transactional Outbox; business
  commit and queue transaction are intentionally not claimed as one atomic
  transaction. Provider/service outages may delay processing.
- The PDF viewer is a bounded source viewer, not an OCR engine, matcher or
  clinical safety conclusion.
- No real clinical document, model credential, EDC write-back or external
  provider run was used.

Next task by dependency: CRA-W04.
