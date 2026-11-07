# CRA V1A time study

Date: 2026-11-07.

## Conclusion

Machine execution time for the synthetic provider route and browser journey is
available. The human total time for the existing CRA workflow and the same
task performed with this system has **not** been measured. Therefore this
release makes no time-saving, productivity or reduced-workload claim.

## Recorded measurements

| Component | Measured | Scope | Evidence |
| --- | ---: | --- | --- |
| Recognition and comparison | 53.049 s | Text PDF and clear PNG provider route; W08 synthetic evaluation | [W08 status](W08_STATUS.md) |
| Complex provider recognition | 25.236 s | Two-page scan and 0.5-degree JPEG; W14 synthetic evaluation | [OCR evaluation](OCR_EVALUATION.md) |
| Safety analysis provider | 40.534 s | Three synthetic cases plus grounding checks | [W09 status](W09_STATUS.md) |
| Browser end-to-end step | 16 s | Automated Chromium journey, excluding cloud setup and human reading | [run 42354648562](https://github.com/pyzz58/gpt-recommendations/actions/runs/42354648562), `cra-w12` step `e2e` |
| Human workflow total | not measured | Import, confirmation, focused review, reporting and rework | No authorized representative CRA timing study |
| Manual baseline total | not measured | Same end-to-end task and sample without this system | No matched manual baseline |

These are elapsed-time observations, not service-level commitments. Cold model
downloads, artifact installation, real hospital scans, concurrency and network
variability can change provider time.

## Coverage and burden counters

The declared synthetic laboratory evaluation contains 12 expected rows. It
recovered 12 rows with source coordinates and no declared key-field errors.
The zero correction/backfill count is limited to that fixture set. Eight review
items demonstrate expected ambiguity, missing unit/range, absent export rows or
scope mismatch behavior; they are not silently normal.

The W14 complex set adds 6 expected rows: 6 recovered, zero declared key-field
errors, 5 structurally usable and one focused review for comma-form output.
There were no manual corrections/backfills in the synthetic set. This still
does not measure CRA review time or real-format burden.

Required future counters are:

- identity, date, analyte, value, unit and instance mismatches;
- missed conditions, false issues and incorrectly closed actions;
- automatically usable fields versus correction/backfill fields;
- focused review, import, confirmation, report and rework time;
- total elapsed time from opening the task to a usable report.

## Measurement protocol for W15

Use the same authorized, representative task and sample for both workflows.
Record start/end timestamps, interruptions, corrections, clarifications,
rework and the final output. Do not include setup time in the CRA task total
unless the existing workflow also includes it. Keep raw timing data in the
approved private environment and publish only deidentified aggregates.

Do not set an acceptance threshold after looking at a favorable result. Define
the threshold with the approved use, sample representativeness and critical
error risk before the trial.

## Current release decision

`human_workflow_comparison_status = not_measured`.

`time_saving_claim = false`.

The core-automation release question remains open even though some automated
steps execute successfully.
