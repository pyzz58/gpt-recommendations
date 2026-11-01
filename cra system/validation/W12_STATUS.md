# CRA-W12 implementation record

Status: in progress pending task-specific GitHub Actions evidence.
Date: 2026-11-01.

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
- Combined governance, rules, subjects, issues, carryover, EDC, laboratory,
  recognition, safety, site-file, report, platform API and continuity suites:
  87 passed.
- Playwright Chromium full journey: 1 passed. It uses real FastAPI,
  PostgreSQL, private local storage and the background worker, not page mocks.
- Python unittest discovery: 49 passed.
- Frontend: 17 passed; TypeScript and production build passed.
- Synthetic only; no real clinical material, external send or EDC write-back.

## Remaining limits

- Tablet behavior is Chromium viewport/user-agent emulation. Physical iPad,
  camera, touch ergonomics and weak-network/offline behavior still require
  W15 authorized device testing.
- The browser upload uses a synthetic text PDF. Clear PNG OCR and complex photo
  formats remain limited by the validated W08/W14 provider scope.
- Browser E2E proves orchestration and persistence, not clinical report quality
  or total workflow time savings.
- There is no external message delivery, signature service, EDC write-back or
  production deployment in W12.
