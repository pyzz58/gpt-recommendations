# CRA W14 complex laboratory format evaluation

Date: 2026-11-07. Evidence level: independent synthetic provider evaluation.
This is not clinical validation, hospital-format coverage or a workflow-time
claim.

## Supported addition

Support profile `synthetic-lab-v2` adds two narrow, independently evaluated
routes:

| Route | Evaluated condition | Provider |
| --- | --- | --- |
| Scanned PDF | Two-page image-only report with visible rules, stable columns and a continuation table on page 2 | Docling 2.145.0 in isolated Python 3.12 |
| JPEG | Clear printed laboratory table with 0.5-degree rotation and JPEG compression | Docling 2.145.0 in isolated Python 3.12 |

The scan also contains a key/value report-context table for subject, visit,
collection date/time, instance and report revision. The extraction layer binds
those values to result rows while retaining their source page and coordinates.
If a later table has no recognizable header, the system reuses the immediately
preceding compatible header and records `header_inherited`, its source table and
page. It does not reuse a header when the column structure is incompatible.

This does not support arbitrary multi-page hospital reports, interleaved
columns, handwriting, severe blur/occlusion, perspective distortion or
unruled/free-form layouts. JPEG routing previously existed but was not
separately evaluated; the new sample covers only the stated clear print and
mild rotation.

## Artifact and expected-answer separation

- Multi-page scan:
  `tests/w14_fixtures/artifacts/synthetic_lab_multipage_scan.pdf`
  - SHA-256 `875413e457f5f168e0281cb3d80cde3b104d961f37c0a89918a702b97c991a31`
- Mild-rotation JPEG:
  `tests/w14_fixtures/artifacts/synthetic_lab_mild_rotation_eval.jpeg`
  - SHA-256 `0f8d59a98a6613cdf8eab2c95323b9760ad0455c88426d112c3be10d88773723`

Expected values are in `tests/w14_fixtures/manifest.json` and are never passed
to Docling. All identifiers and values are fictional.

## Actual recognition result

Command:

```bash
uv run --frozen python -m cra_app.providers.evaluate_complex_labs \
  --dataset tests/w14_fixtures/manifest.json
```

| Measure | Two-page scan | Mild-rotation JPEG |
| --- | ---: | ---: |
| Expected rows | 4 | 2 |
| Recognized rows | 4 | 2 |
| Key-field errors | 0 | 0 |
| Source coordinates | 4/4 | 2/2 |
| Automatic-usable rows | 3/4 | 2/2 |
| Focused-review rows | 1 | 0 |
| Manual correction/backfill | 0 | 0 |
| Comparison agreement | 3 | 2 |
| Not directly comparable | 1 | 0 |

Across 6 rows, 5 were structurally usable for the existing matching and
comparison service (83.3%) and 1 required focused review. The comma-form
`5,1` result remains `needs_review`; it is not silently converted to `5.1`,
does not enter automatic comparison and is not marked normal.

The local independent evaluation took 25.236 seconds in total: 15.427 seconds
for the multi-page scan and 9.809 seconds for JPEG. Docling/model versions and
the complete dependency-lock hash are emitted with every run. These are
machine/provider observations, not CRA review time or production throughput.

Artifact execution was:

- model manifest SHA-256
  `c5309aff4606055d82f24f07da522ce6830de7d664faaeb4f9fa44cd10d0705b`;
- local macOS OCR lock SHA-256
  `c0ffdc03a0cf991f478b168c7ab201b5edb6f6144dde42354ed121220e74e449`;
- provider maximum RSS observations were approximately 4.5 GiB for the
  two-page scan and 3.7 GiB for JPEG on the local run.

CI logs remain authoritative for the fresh Linux environment and are recorded
in the W14 completion evidence.

## Regression boundaries

- Headerless continuation reuses a prior header only when required analyte and
  result columns remain structurally compatible.
- Incompatible continuation is left unparsed with a visible warning.
- A caption stretched across all table cells is discarded instead of becoming a
  laboratory row.
- A suspicious unit without letters, such as OCR output `7/`, remains a review
  issue rather than being guessed from the analyte.
- Bound values such as `<12` remain bounds.
- Scanned PDFs use the PDF source viewer; JPEG/PNG use an image highlight based
  on the source coordinates.
- Unsupported TIFF and other formats return an explicit unsupported-route
  message.

The existing M08 confirmation, correction, skip, matching, comparison, issue
link and report paths remain the only downstream services. W14 does not create a
second issue or report store.

## Remaining limits

- Two synthetic samples cannot estimate real hospital field accuracy.
- The JPEG test is 0.5-degree rotation only; blur, glare, folds, shadows,
  perspective and camera-photo variation remain outside the validated scope.
- Only a two-page continuation and a small set of columns were evaluated.
- No real project document, clinical data, authorization or CRA manual-time
  comparison was used.
- Production device, model mirror, object storage, identity and restore remain
  W15 work.
