# CRA V1A acceptance and capability limits

Date: 2026-11-07. Release candidate:
`CRA-V1A-ENGINEERING-20261107`.

This is an engineering and synthetic acceptance record. It does not establish
clinical validation, representative hospital-format performance, workflow
time savings, or authorization to process real trial data.

## Outcome

The software has a demonstrable synthetic end-to-end path from documents and
rules through subject context, EDC and laboratory comparison, issue follow-up,
safety-review support, reports and a second monitoring visit. The core
laboratory route is **not yet accepted as a complete V1A release**: representative
real-world formats, an approved data set, key-error thresholds, human workload,
production recovery and an authorized trial remain outstanding.

The structured source of this summary is
[`capability-manifest.json`](capability-manifest.json). Run:

```bash
uv run --frozen pytest -q tests/acceptance/test_v1a.py
uv run --frozen python tools/build_validation_report.py --check
```

## Scenario ledger

| Scenario | Status | Evaluation group | Actual evidence or gap |
| --- | --- | --- | --- |
| CRA-S01 | synthetic validated | independent synthetic | Governance and API two-site isolation |
| CRA-S02 | not evaluated | not run | Prompt-injection and outbound-exfiltration scenario not executed |
| CRA-S03 | not evaluated | not run | Full combined missing-document behavior not executed |
| CRA-S04 | synthetic validated | independent synthetic | Duplicate rule, version carryover and source anchors |
| CRA-S05 | synthetic validated | independent synthetic | Table, footnote, natural Chinese candidate and user revision |
| CRA-S06 | synthetic validated | independent synthetic | Independent same-key site rule and unknown exception |
| CRA-S07 | synthetic validated | independent synthetic | Version start boundary and no retroactive replacement |
| CRA-S08 | synthetic validated | independent synthetic | Subject import, anchor reuse and cross-site isolation |
| CRA-S09 | synthetic validated | independent synthetic | Separate category coverage and breakpoints |
| CRA-S10 | synthetic validated | independent synthetic | Carryover before new review across refresh and login |
| CRA-S11 | synthetic validated | independent synthetic | Incomplete issues and timely safety work coexist |
| CRA-S12 | synthetic validated | independent synthetic | Stage lists and handover reuse the same issue records |
| CRA-S13 | synthetic validated | independent synthetic | Automated comparison remains limited to laboratory data |
| CRA-S14 | synthetic validated | independent synthetic | PD reporting and EDC correction actions complete independently |
| CRA-S15 | synthetic validated | independent synthetic | Direct CRA confirmation and reopen preserve history |
| CRA-S16 | synthetic validated | independent synthetic | Draft Query identity and deadline source are enforced |
| CRA-S17 | synthetic validated | independent synthetic | One issue remains stable over three visit records |
| CRA-S18 | synthetic validated | independent synthetic | Absence is represented as `not_seen_in_export` |
| CRA-S19 | synthetic validated | independent synthetic | Initial/repeat and ambiguous candidates do not auto-match |
| CRA-S20 | synthetic validated | independent synthetic | Missing unit and one-sided range remain unknown/review |
| CRA-S21 | synthetic validated | independent synthetic | User skip is scoped, not normal, and resumable |
| CRA-S22 | synthetic validated | independent synthetic | Text PDF continues while image OCR is unavailable |
| CRA-S23 | synthetic validated | independent synthetic | Fact, dimension candidate, CRA review and medical response stay separate |
| CRA-S24 | synthetic validated | independent synthetic | Timely alert appears without inventing awareness/deadline data |
| CRA-S25 | synthetic validated | independent synthetic | Fabricated anchors and evidence IDs are rejected |
| CRA-S26 | synthetic validated | independent synthetic | Reference-first directory comparison and incremental status |
| CRA-S27 | synthetic validated | independent synthetic | Two selected issues produce a draft without deleting the full list |
| CRA-S28 | synthetic validated | independent synthetic | Issued snapshot remains immutable after status changes |
| CRA-S29 | synthetic validated | independent synthetic | Unreviewed scope remains visible in output context |
| CRA-S30 | not evaluated | not run | Cross-provider replacement with reused business records not executed |
| CRA-S31 | engineering verified | engineering record | Theory-only mutation fails the synchronization check |
| CRA-S32 | engineering verified | engineering record | Missing binding and stale change reuse are rejected |
| CRA-S33 | engineering verified | engineering record | CRA-specific workflow and devcontainers passed in CI |
| CRA-S34 | unmet | not run | Machine durations exist; human baseline and new-workflow total do not |
| CRA-S35 | synthetic validated | independent synthetic | One CRA click completes an action without extra evidence gates |
| CRA-S36 | synthetic validated | independent synthetic | Missing anchor skips only dependent paths and can resume |
| CRA-S37 | synthetic validated | independent synthetic | C→B/D→F conditions, negation, exception and unknown regressions |
| CRA-S38 | synthetic validated | independent synthetic | Manual start dates and event-time version selection |
| CRA-S39 | synthetic validated | independent synthetic | Source file → EDC match → comparison → safety lead → report |
| CRA-S40 | synthetic validated | independent synthetic | Historical DOCX/XLSX/text carryover is confirmed and idempotent |

Summary: 33 synthetic-validated, 3 engineering-verified, 3 not-evaluated and
1 unmet scenario. A scenario is not `verified` merely because another module's
unit test passed; the manifest records the specific case used for each claim.

## Independent sample and provider evidence

- W04 anchored rule extraction ran on the independent synthetic rule document
  and rejected lost exceptions, changed negation and AND/OR corruption.
- W08 evaluated selectable-text PDF, clear printed PNG and a Chinese
  header-context PDF. The clear PNG is in the independent evaluation group and
  is never supplied with its expected answers.
- The W08 rows were 12/12 recovered with source coordinates and no declared
  key-field errors. This small set is not a clinical error-rate estimate.
- W14 added a two-page image-only scan with report context and continuation
  structure, plus a clear JPEG with 0.5-degree rotation. Both passed with
  6/6 rows and zero declared key-field errors; 5/6 rows were structurally
  usable and one comma-form value stayed in focused review.
- W09 evaluated three independent synthetic safety cases for dimension
  separation, question topics and grounding. The model output remains a
  limited explanation candidate and cannot close an issue or make a medical
  determination.
- Current source-bound task execution is recorded in
  [run 42444079396](https://github.com/pyzz58/gpt-recommendations/actions/runs/42444079396).
  W13 adds its own source-bound acceptance run before this work package can be
  marked verified.

## Automatic coverage and human work

- All 12 W08 rows and 5/6 W14 complex rows were structurally available for
  matching. One W14 row remains focused review because its printed comma is not
  silently converted to a decimal point. This applies only to the synthetic
  set.
- The expected review items concern absent export rows, missing units,
  reference-limit differences and Chinese context rows absent from the current
  EDC export. They are not hidden as normal and do not prove EDC omission.
- No numeric percentage is presented as workflow savings. Recognition,
  comparison and automation durations are in [TIME_STUDY.md](TIME_STUDY.md).
- Human correction/backfill counts are zero on the synthetic rows, but this
  does **not** establish low burden in real use.

## Release decision

| Release question | Decision |
| --- | --- |
| Can the synthetic engineering journey be demonstrated? | Yes |
| Is every business scenario complete? | No: S02, S03 and S30 are not evaluated; S34 is unmet |
| Is V1A core automation fully accepted? | No |
| Is an authorized trial ready to start? | No |
| Is clinical use validated? | No |
| Can generated material be sent, signed or written back automatically? | No |

The next controlled step is W15 only after its environment and authorization
prerequisites exist. W13 does not deploy the application, call external model
or OCR services, process real clinical material, send mail, sign documents or
write back to EDC.
