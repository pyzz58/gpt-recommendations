# Restore and recovery readiness

Date: 2026-11-07. Scope: engineering review, not a production restore claim.

## Demonstrated at application level

- The W12 PostgreSQL test recreates server-side monitoring visits after a new
  client/session and checks that selected issues, PD/correction action state,
  subject coverage and active skips remain available.
- Laboratory worker tests cover interruption, expired lease recovery, active
  lease protection, completed-job replay and attempt fencing.
- Report, issue, rule and monitoring histories are append-only or revisioned
  in their module tests; a signed report snapshot is not rewritten by later
  status changes.
- CI starts a fresh PostgreSQL 18.6 service, migrates from zero and executes
  the relevant task-specific tests.

These checks demonstrate application behavior with synthetic records. They do
not demonstrate a production backup, restore or disaster-recovery procedure.

## Not yet demonstrated

- backup cadence, encryption, retention and deletion policy;
- restore into a separate environment from the approved backup service;
- recovery point and recovery time objectives;
- object-storage recovery and all database-to-file references;
- post-restore consistency for issue numbers, rule versions, audit, outbox,
  unsigned drafts and immutable issued snapshots;
- revoked identity/membership behavior after restore;
- rollback after an incompatible migration;
- real device, weak-network or regional outage recovery.

W13 therefore records production restore readiness as **disabled**. W15 owns
the approved environment and actual restore exercise.

## Required restore acceptance for W15

1. Create a synthetic private project, issue, rule version, subject, coverage
   breakpoint, EDC snapshot, laboratory report, safety assessment, report
   snapshot and export in the approved environment.
2. Take a backup, record its identifier and hash, then verify it can be read
   by the approved service.
3. Restore to an isolated environment using only the document and tested
   runbook steps.
4. Verify database readiness and migration head.
5. Open each restored object through the public API and browser, checking
   authorization and object links rather than only counting rows.
6. Verify every file reference resolves to the expected hash and that a signed
   report equal to its pre-backup immutable content.
7. Revoke a membership and confirm that a restored session or client cannot
   bypass server-side scope checks.
8. Record restore duration, missing/corrupt objects, operator time, rollback
   result and any manual repair. Do not publish patient/raw source content.
9. Keep the prior production dataset untouched and document the cutover
   decision separately.

## Pause rule

If restored file references, authorization, append-only history or issued
snapshots fail, the affected automatic function must be paused for that
release. Existing source files, lists, facts and issue records remain
available; recovery resumes only after a repeatable test passes.
