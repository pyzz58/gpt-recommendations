# CRA-W08 laboratory automation scope and evaluation

Date: 2026-11-01. Evidence level: synthetic/provider engineering validation.
This is not a clinical-use, all-format or time-saving claim.

## Supported and evaluated scope

| Source route | Component | Evaluated condition | Status |
| --- | --- | --- | --- |
| Text PDF | pdfplumber 0.11.x `pdfplumber-lab-table` | Selectable text, ruled table, clear English columns | supported |
| Text PDF with report context | Same text route | Clear Chinese header with subject/date/instance/revision and two result rows that do not repeat them | supported for the evaluated synthetic layout |
| Clear printed image | Docling 2.145.0 in isolated Python 3.12 | Synthetic 3200 x 1800 PNG, horizontal text, ruled table, no rotation/blur | provider validated on one independent sample |
| JPEG input | Same Docling route | Same clean-print assumption; a separate JPEG sample was not evaluated | implemented but not separately evaluated |
| Scanned PDF without useful text | Docling fallback | Not included in the current independent evaluation set | experimental |

The provider is selected by a replaceable `RecognizeLab` adapter. The main
application remains on CPython 3.13.15 and does not import Docling directly.
The OCR environment uses complete transitive hash locks selected by platform.
Each upload commits an immutable source version, a persistent
`lab_recognition_jobs` record and an Outbox event, then returns HTTP 202
`pending`; Procrastinate processes it in a worker. The worker reloads
authorization and the current source version, claims a lease, records attempts
and releases the lease on success or failure. An expired lease can be resumed
and a failed/provider-unavailable run can be explicitly requeued.

Not supported or validated: handwriting, severe blur/occlusion, arbitrary
unruled hospital layouts, arbitrary Chinese hospital templates, multi-page
continuation tables, all vendor revisions, real clinical data or clinical
safety decisions.

## Artifact and expected-answer design

- Text PDF: `tests/fixtures/labs/artifacts/synthetic_lab_report.pdf`,
  SHA-256 `328e1c152dff2de90f1da2f46c3ffaeec379982549bc41c4bfa4cbc8b0feae13`.
- Independent clear PNG:
  `tests/fixtures/labs/artifacts/synthetic_lab_report_eval.png`,
  SHA-256 `0b1ea5c232f81cca270b8f825701b284d4d4c60e04bf667b897e84bd45da64d9`.
- Chinese report-context PDF:
  `tests/fixtures/labs/artifacts/synthetic_lab_report_zh_context.pdf`,
  SHA-256 `bb5217282b642534a61b39b12d952954f3c4950b265339071dfc5cb209aaaf89`.
- Correct identities, dates, operators, values, units and instances are in
  the matching expected-answer files; those files are never passed to
  pdfplumber or Docling.
- The EDC side is the actual W07 synthetic XLSX snapshot. The PNG and Chinese
  context PDF belong to the evaluation group; the English PDF is the
  development artifact.

The English PDF and PNG contain five fictional observations, including
same-day Hemoglobin Initial `121` and Repeat `119`, an ALT absent from the EDC
export, and a Glucose result present in EDC without a unit. The Chinese
context PDF has identity/date/instance in the header, two result rows without
repeated identity/date, and report revision `FINAL`.

## Actual recognition, matching and comparison result

Command:

```bash
uv run --frozen python -m cra_app.providers.evaluate_labs \
  --dataset tests/fixtures/manifest.json
```

| Measure | Text PDF | Independent PNG | Chinese header context |
| --- | ---: | ---: | ---: |
| Expected rows | 5 | 5 | 2 |
| Recognized rows | 5 | 5 | 2 |
| Key-field errors | 0 | 0 | 0 |
| Source coordinates present | 5/5 | 5/5 | 2/2 |
| Manual correction/backfill | 0/5 | 0/5 | 0/2 |
| Comparison agreement | 2 | 2 | 0 |
| Focused review required | 3 | 3 | 2 |
| Provider validation | passed | passed | passed |

The current local isolated-image run emitted OCR lock SHA-256
`fcd0ec5ac7da801c69e8e2c9f608343f1ad4fcab76c3926e3fab6e61169bfcbd`
and Docling model-manifest SHA-256
`c5309aff4606055d82f24f07da522ce6830de7d664faaeb4f9fa44cd10d0705b`.
CI logs the authoritative values for its fresh environment. The image run used
about 3.1 GiB maximum RSS and 8.7 seconds in the provider process in the local
observation; these are resource observations, not production commitments.

The review items are expected scope behavior rather than OCR misses:

- Glucose comparison returns `unit_review` because the EDC side has no unit;
  the system does not infer or convert it.
- ALT returns `not_seen_in_export`; this does not prove EDC omission.
- Creatinine values and units agree, but the source and EDC reference limits
  differ. The comparison retains the independent limit difference and returns
  `logic_difference`; it does not make a medical assessment.
- The Chinese context rows are not present in the comparison export and return
  `not_seen_in_export`; this remains a scope limitation, not an EDC omission
  conclusion.

## User-review and failure behavior

- Structurally valid fields can be compared automatically and confirmed in a
  scoped batch; users are not required to click each normal field.
- Effective values are folded across the complete ordered decision chain.
  A correction remains effective after confirm/batch-confirm, and a later
  unit-only correction does not restore the original OCR value.
- The original provider candidates are immutable. Confirm/correct/skip advance
  the report revision; a field whose effective source state changed is
  returned as `stale`, while unchanged fields remain usable.
- Report-level subject/date/instance/revision can be bound once with source
  coordinates and reused by rows. A conflicting row value is marked for
  review rather than silently treated as the header identity.
- A user skip is limited to the selected observation and returns
  `not_checked_by_user`; it is not displayed as normal.
- With `CRA_OCR_PROVIDER=disabled`, selectable text PDF still works. Image files
  are preserved privately, the report is marked `provider_unavailable`, and a
  small manual candidate route remains available.
- Upload, worker interruption, timeout and explicit retry keep the same
  report/job identity. A revoked authorization cannot be replaced by the
  earlier API session that queued the work.
- Bound values such as `<12` are never converted to exact `12`; unmatched
  comparison forms return `not_comparable`.
- The system does not output `clinical_safe=true`, does not automatically
  create PD, and does not complete an M06 action merely because a comparison
  issue was linked.

## Remaining validation

- The evaluated Chinese report is a clear text PDF, not a photograph, complex
  hospital layout, rotated scan or arbitrary template.
- The independent set contains one clean synthetic image, one text PDF and one
  Chinese header-context PDF. Real layout distribution, photograph quality and
  vendor variation remain untested.
- A full comparison to an existing CRA manual workflow was not performed. The
  recorded review ratio and provider time are not total time-saving proof.
- Thresholds for acceptable key errors, auto agreement and review burden must
  be set with a representative approved dataset before clinical-use readiness.
- W09 owns medical/logic analysis; W11 owns reports; W14 may expand difficult
  formats; W15 owns approved environment deployment and an authorized trial.
