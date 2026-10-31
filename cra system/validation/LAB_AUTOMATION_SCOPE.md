# CRA-W08 laboratory automation scope and evaluation

Date: 2026-10-31. Evidence level: synthetic/provider engineering validation.
This is not a clinical-use, all-format or time-saving claim.

## Supported and evaluated scope

| Source route | Component | Evaluated condition | Status |
| --- | --- | --- | --- |
| Text PDF | pdfplumber 0.11.x `pdfplumber-lab-table` | Selectable text, ruled table, clear English columns | supported |
| Clear printed image | Docling 2.145.0 in isolated Python 3.12 | Synthetic 3200 x 1800 PNG, horizontal text, ruled table, no rotation/blur | provider validated on one independent sample |
| JPEG input | Same Docling route | Same clean-print assumption; separate JPEG sample not evaluated | implemented but not separately evaluated |
| Scanned PDF without useful text | Docling fallback | Not included in the current independent evaluation set | experimental |

The provider is selected by a replaceable `RecognizeLab` adapter. The main
application remains on CPython 3.13.15 and does not import Docling directly.
Docling is pinned for the isolated provider process; a production image,
model mirror, SBOM and resource limit still require W15 environment approval.
Each upload creates a persistent `lab_recognition_jobs` record linked from
`lab_report_versions.recognition_job_id`; this scope runs it through the API
process and records queued/running/succeeded/failed state and provider output.

Not supported or not validated: handwriting, severe blur/occlusion, arbitrary
unruled hospital layouts, Chinese sample layouts, multi-page continuation
tables, all vendor revisions, real clinical data and clinical safety decisions.

## Artifact and expected-answer design

- Text PDF: `tests/fixtures/labs/artifacts/synthetic_lab_report.pdf`,
  SHA-256 `328e1c152dff2de90f1da2f46c3ffaeec379982549bc41c4bfa4cbc8b0feae13`.
- Independent clear PNG:
  `tests/fixtures/labs/artifacts/synthetic_lab_report_eval.png`,
  SHA-256 `0b1ea5c232f81cca270b8f825701b284d4d4c60e04bf667b897e84bd45da64d9`.
- Correct identities, dates, operators, values, units and instances are in
  `tests/fixtures/labs/evaluation_cases.json`; that answer file is never passed
  to pdfplumber or Docling.
- The EDC side is the actual W07 synthetic XLSX snapshot. The PNG belongs to
  the evaluation group; the PDF is the development artifact.

Both files contain five fictional observations, including same-day Hemoglobin
Initial `121` and Repeat `119`, an ALT absent from the EDC export, and a
Glucose result present in EDC without a unit.

## Actual recognition, matching and comparison result

Command:

```bash
uv run --frozen python -m cra_app.providers.evaluate_labs \
  --dataset tests/fixtures/manifest.json
```

| Measure | Text PDF | Independent PNG |
| --- | ---: | ---: |
| Expected rows | 5 | 5 |
| Recognized rows | 5 | 5 |
| Key-field errors in subject/visit/analyte/value/unit/date/time/instance | 0 | 0 |
| Source coordinates present | 5/5 | 5/5 |
| Structurally usable automatic rows | 5/5 | 5/5 |
| Manual correction/backfill | 0/5 | 0/5 |
| Comparison agreement | 2 | 2 |
| Focused review required | 3 | 3 |
| Auto agreement ratio | 40% | 40% |
| Provider validation | passed | passed |

The three review items are expected scope behavior rather than OCR misses:

- Glucose comparison returns `unit_review` because the EDC side has no unit;
  the system does not infer or convert it.
- ALT returns `not_seen_in_export`; this does not prove EDC omission.
- Creatinine values and units agree, but the source reference upper limit is
  `110 umol/L` while the synthetic EDC row records `160 umol/L`. The comparison
  returns `logic_difference` with
  `reference_range_flag_difference`; it does not make a medical assessment.

Local observation: text PDF recognition plus comparison took roughly 0.02 s;
the isolated Docling process took roughly 9–17 s end-to-end and approximately
2.7–3.9 GiB maximum RSS across warm-cache runs. These are synthetic
observations, not production latency or capacity commitments. CI must rerun
the same command for authoritative evidence.

## User-review and failure behavior

- Structurally valid fields can be compared automatically and confirmed in a
  scoped batch; users are not required to click each normal field.
- A correction is appended as `user_corrected`; the original provider result
  remains immutable and a new comparison is required.
- Confirm/correct/skip changes advance the report revision. A field whose
  effective source state changed is returned as `stale`; unchanged fields
  remain usable, while stale fields cannot be linked to new M06 issues.
- A user skip is limited to the selected observation and returns
  `not_checked_by_user`; it is not displayed as normal.
- With `CRA_OCR_PROVIDER=disabled`, selectable text PDF still works. Image files
  are preserved privately, the report is marked `provider_unavailable`, and a
  small manual candidate route remains available.
- Multiple matching EDC instances return `ambiguous`. No numerical closeness
  is used to choose a match.
- Bound values such as `<12` are never converted to exact `12`; unmatched
  comparison forms return `not_comparable` with a bound-review unknown.
- The system does not output `clinical_safe=true`, does not automatically
  create PD, and does not complete an M06 action merely because a comparison
  issue was linked.

## Remaining validation

- The independent set contains one clean synthetic image and one text PDF;
  real layout distribution, photograph quality and Chinese reports remain
  untested.
- A full comparison to an existing CRA manual workflow was not performed.
  The recorded review ratio and provider time are not total time-saving proof.
- Thresholds for acceptable key errors, auto agreement and review burden must
  be set with a representative approved dataset before clinical-use readiness.
- W09 owns medical/logic analysis; W11 owns reports; W14 may expand difficult
  formats; W15 owns approved environment deployment and real authorized trial.
