# CRA-W08 completion record

Status: verified. Date: 2026-11-01.

This record covers source laboratory report recognition, field-level review,
exact instance matching and deterministic EDC comparison for the declared
synthetic/provider scope. It is engineering validation, not clinical-use
validation or proof of workflow time savings.

## Review-remediation delivery

- Effective observation values are folded across the complete ordered
  correction chain. A confirm or batch-confirm cannot restore the original OCR
  value, and a later partial correction preserves earlier corrected fields.
- Report-level subject/date/instance/revision context is parsed from
  non-table lines, receives source coordinates and is reused by rows that omit
  repeated identity fields. Conflicting row and header identity requires review.
- Lower and upper reference limits, range flags, report date and report
  revision are independently compared. Different limits are retained even when
  both sides produce the same normal/abnormal flag.
- Upload returns HTTP 202 after persisting the source version, report/job and
  Outbox event. Procrastinate processes recognition in a worker with lease,
  attempt, authorization and current-source checks. Expired leases and explicit
  retry can resume failed work without duplicating candidates.
- The isolated OCR environment uses complete platform-specific hash locks and
  an explicit PyTorch CPU index. Provider output includes the selected lock and
  Docling model-manifest SHA-256.
- The main runtime remains on Python 3.13; the application does not import
  Docling or torch.

## Public entry points

- `POST /api/v1/studies/{study_id}/lab-reports` returns 202 and a queued job.
- `GET /api/v1/studies/{study_id}/lab-reports`
- `GET /api/v1/lab-reports/{id}`
- `POST /api/v1/lab-reports/{id}/retry-recognition`
- `POST /api/v1/lab-reports/{id}/observations/{observation_id}/decision`
- `POST /api/v1/lab-reports/{id}/observations/batch-confirm`
- `POST /api/v1/lab-reports/{id}/observations`
- `POST /api/v1/lab-comparisons`
- `GET /api/v1/lab-comparisons/{id}`
- `POST /api/v1/lab-comparisons/{id}/issues`
- `GET /api/v1/studies/{study_id}/edc-snapshots`

## Authoritative execution

- Tested commit:
  `5148684064a57e50077dd32d02e76b57b2221fc4`.
- GitHub Actions:
  https://github.com/pyzz58/gpt-recommendations/actions/runs/41245438323
- Task job: `cra-w08`.
- Required steps: `test`, `lab-provider-evaluation`, `contracts`, `frontend`.
- PostgreSQL 18.6 service, migration `0009_review_remediation`, source-bound
  task profile and all six W08 review unit regressions passed.
- W08 PostgreSQL/recognition tests: 10 laboratory integration, 4 source-file
  recognition and 7 review-unit tests passed.
- Actual Docling evaluation passed against the text PDF, clear PNG and Chinese
  header-context PDF. All expected rows and source coordinates were recovered
  with zero key-field errors in the declared synthetic samples.
- The three evaluated formats produced two automatic agreements and three
  focused-review items for the English/PNG pair, and two `not_seen_in_export`
  review items for the Chinese context pair. They are expected scope behavior,
  not clinical conclusions.
- CI OCR lock SHA-256:
  `b63ebded2cb330b5b68a67f24988c28733798336874cabc5d157983f5c7b1e01`.
- CI Docling model-manifest SHA-256:
  `c5309aff4606055d82f24f07da522ce6830de7d664faaeb4f9fa44cd10d0705b`.
- CI isolated-image provider time: 38.468 seconds; maximum RSS:
  2,371,555,328 bytes. Total W08 lab evaluation: 53.033 seconds.
- OpenAPI drift check, 13 frontend tests, TypeScript and production build
  passed.
- Subject digest:
  `c3581509bb54111ccf75fddc7d5e1c160b3741c40d2d2673b10ecdc9cec12ab0`.

## Remaining limits

- Only selectable-text ruled PDFs and one clear synthetic PNG are validated.
  The Chinese evidence is a clear text PDF, not a photograph or complex hospital
  template. JPEG shares the implemented route but lacks a separate sample.
- Handwriting, severe blur/occlusion, arbitrary unruled layouts, arbitrary
  Chinese templates, multi-page continuation tables and all vendor revisions
  remain untested.
- The application-side authentication and worker recovery are tested, but W15
  still owns an approved production image, model mirror, SBOM/license review,
  capacity plan and real authorized environment.
- No real clinical accuracy, key-error threshold, representative hospital
  corpus or full manual-workflow time comparison exists.
- W11 reports, W14 difficult formats and EDC write-back remain unimplemented.
  M06 receives only an explicitly selected `edc_correction` action.

Next task by dependency after W09: CRA-W10. W10 was not started.
