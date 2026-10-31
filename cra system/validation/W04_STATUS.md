# CRA-W04 completion record

Status: verified. Date: 2026-10-31.

Revalidated after W05 began consuming rule versions and date windows. Current
evidence: run `41185363902`, tested commit
`f97fb13fe4557f9aa5fecef838ce596c8571f0a8`, digest
`956bdb247f4e6dac505398cab7c946911a0ee0e4121cab44aff0b0610df460b4`.

This record covers extraction of source-anchored rule candidates, user
confirmation, layered lists, item-level relations, manual activation windows
and event-date applicability. It is synthetic engineering validation, not
clinical-use, legal-policy or general-protocol validation.

## Delivered

- PostgreSQL migration `0003_rules_versions` adds rule snapshots, stable rules,
  immutable rule versions, source references, item relations, extraction
  coverage and manual version activations. Database triggers reject rule
  version updates and deletion.
- A closed condition AST supports `all`, `any`, `not`, presence, equality,
  ordering, membership and date intervals with explicit units and three-value
  true/false/unknown evaluation. No `eval` or model-supplied executable code is
  accepted.
- `anchored-rule-subset` is an actual deterministic provider over W03 DOCX/text
  anchors. It emits precondition, trigger, branches, exceptions, follow-up,
  completion, required facts, children and exact source references.
- Domain validation rejects unknown anchors, quotes not belonging to anchors,
  invented numbers and candidates that lose a source precondition, exception,
  negation or conjunction.
- User confirmation adds/removes/edits rules and creates a new immutable
  version with expected revision, idempotency key, AuditEvent and source refs.
  Historical versions remain read-only and selectable.
- New source versions create complete snapshots. Omitted old rules are carried
  forward as `unchanged`; meaning changes without explicit relation evidence
  are marked `conflict` rather than silently replaced or withdrawn.
- Manual activations keep `starts_on` inclusive and `ends_before` exclusive,
  reject invalid intervals, surface overlapping scope conflicts, and provide a
  correction preview with affected rules without retroactive reassessment.
- React workspace displays four layers, exceptions/branches, extraction and
  applicability unknowns, version history, item relations, manual starts and
  the event-date `OutputEnvelope`. Applicable queries show common/study/site
  policy versions separately.
- Pure synthetic development/evaluation DOCX and text artifacts cover an
  independent rule set and corruption probes. No expected result is supplied
  to the extractor.

## Authoritative execution

- Tested commit: `f2bac7dcf527e7e54e6a5af27cb2663af862cccf`.
- GitHub Actions:
  https://github.com/pyzz58/gpt-recommendations/actions/runs/41183652961
- Task job: `cra-w04`.
- Required steps: `test`, `rule-provider-evaluation`, `contracts`, `frontend`.
- PostgreSQL tests: 6 passed against PostgreSQL 18.6.
- Tests covered autonomous candidate formation, source/provider validation,
  conditions and exceptions, fake anchor and numeric-invention rejection,
  expected-revision confirmation, add/remove history and database
  immutability, omitted-rule carryover, overlapping activation detection,
  inclusive/exclusive date boundaries, duplicate signatures and site isolation.
- Independent rule evaluation: 2 evaluation rules extracted from the actual
  synthetic DOCX; branch expectations and three deliberate corruption cases
  (lost exception, lost negation, AND changed to OR) passed.
- Contracts/frontend: OpenAPI drift check, 6 frontend tests, TypeScript and
  production build passed.
- W01/W02/W03 independently revalidated after the shared changes.
- Subject digest:
  `efa354456d6afc84e55a69947759597494ece5315fb50b35d054e11f12aca108`.

Local validation additionally used an isolated PostgreSQL 18.6 database,
migration upgrade/downgrade/re-upgrade, Alembic drift check, 66 backend tests,
actual DOCX parsing and a browser review. In the browser, the synthetic
2020-12-31 event selected v1 without the later E3 exception, 2021-01-01 selected
v2 with E3, and selecting candidate v3 opened it read-only.

## Remaining limits

- The deterministic provider supports the documented W04 statement subset, not
  arbitrary protocols, IB, SOP or email prose. Unsupported text is
  retained as `analysis_required`.
- Syntax validation and independent synthetic conditions do not prove complete
  clinical meaning. Real protocol/IB coverage, missed premise/exception rates,
  specialist semantic review and format performance remain unvalidated.
- The common-policy fixture is a synthetic engineering illustration with
  `official_status=unknown`; it is not a GCP or legal-policy determination.
- Overlapping activation windows are surfaced but not auto-resolved. No report
  or assessment is retroactively rewritten.
- No real clinical document, external model, patient fact, OCR, report or EDC
  write-back was used. W04 does not add those workflows.

Next task by dependency after W05: CRA-W06.
