# CRA-W12 implementation record

Status: verified.
Date: 2026-11-08.

## Delivered behavior

- The workbench starts at a four-stage journey: previsit, carryover review,
  subject review, and report/handover.
- A server-side journey projection combines existing issue, subject/coverage,
  active skip, laboratory, EDC, directory, checklist, draft and snapshot
  records. It does not create a second completion store.
- Stage changes use the monitoring visit revision, idempotency and audit. They
  never create a global lock; urgent PD/safety work remains visible.
- Existing module pages are reused by stage instead of copied. Technical
  document/rule setup is collapsed under previsit details.
- Visits are listed from the server, so browser refresh, a new login, a cleared
  localStorage, or a new device context can recover the same latest visit.
- The browser journey covers previous XLSX track import, selection of two
  issues, carryover review, PD and correction completion, EDC import, safety
  analysis, report snapshot, track export and a second monitoring visit.
- The subject review workbench keeps patient context, EDC data, original
  laboratory files, source-to-EDC comparison and protocol/IB-based safety
  review in one visible five-step rail.
- Existing confirmed EDC snapshots are listed and opened by default, so a
  seeded synthetic export does not require a special URL parameter.
- Clear-image Docling OCR is enabled for the bundled synthetic PNG while the
  analysis model remains disabled; manual review and `unknown` remain visible.
- A tablet-sized browser context uploads a synthetic text-PDF laboratory
  report, views/confirms candidates and leaves the same record visible after
  desktop refresh.

## Code and interfaces

- `backend/cra_app/monitoring/journey.py`
- `backend/cra_app/monitoring/service.py`
- `backend/cra_app/monitoring/api.py`
- `web/src/pages/MonitoringVisitPage.tsx`
- `web/src/pages/SubjectReviewPage.tsx`
- `web/src/pages/HandoverPage.tsx`
- `web/playwright.config.ts`
- `web/tests/e2e/monitoring-flow.spec.ts`
- `tests/integration/test_visit_continuity.py`
- `tests/fixtures/w12/seed_e2e.py`

No W12 schema migration was required: the journey is a server-side read model
over existing records and `MonitoringVisit` already owns stage/revision/status.

## Local synthetic verification

- Temporary PostgreSQL 18.6.
- `tests/integration/test_visit_continuity.py`: 1 passed.
- `tests/acceptance/test_local_experience.py` and
  `tests/acceptance/test_v1a.py`: 16 passed.
- Playwright Chromium full journey: 1 passed. It uses real FastAPI,
  PostgreSQL, private local storage and the background worker, not page mocks.
- Frontend: 19 passed; TypeScript and production build passed.
- Synthetic only; no real clinical material, external send or EDC write-back.

## Authoritative execution

- Tested source commit:
  `0107bff1782649033b1d8125a25c04ec4798241f`.
- GitHub Actions run:
  https://github.com/pyzz58/gpt-recommendations/actions/runs/42444079396
- `cra-w12` job: real PostgreSQL continuity test, Playwright full two-visit
  journey, automatic display of a confirmed EDC snapshot, browser PDF
  upload/worker confirmation, OpenAPI drift check, 19 frontend tests,
  TypeScript and production build.
- The same successful run passed all W01-W11 jobs. Their source digests and
  completion evidence were rebound to this tested commit; previous evidence
  remains in `completion_history`.
- Evidence subject hashing now excludes Git-ignored runtime output while
  retaining tracked files and untracked non-ignored source changes. Regression
  tests cover both sides of that boundary.
- Closed findings remain bound to successful job logs with exact test cases.

## Remaining limits

- Tablet behavior is Chromium viewport/user-agent emulation. Physical iPad,
  camera, touch ergonomics and weak-network/offline behavior still require
  W15 authorized device testing.
- The browser upload uses a synthetic text PDF. Clear PNG OCR is exercised in
  the local synthetic experience, but arbitrary photographs, handwriting and
  hospital layouts remain outside the validated scope.
- Browser E2E proves orchestration and persistence, not clinical report quality
  or total workflow time savings.
- There is no external message delivery, signature service, EDC write-back or
  production deployment in W12.
