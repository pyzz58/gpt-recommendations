# CRA-W09 completion record

Status: verified. Date: 2026-11-01.

This record covers evidence-grounded AE, SAE, special-standard and
protocol-deviation analysis support for the declared synthetic/provider scope.
It is engineering validation, not clinical validation or proof of workflow-time
savings.

## Review-remediation delivery

- Safety analysis selects an explicit current event fact. When only one current
  AE fact exists it may be selected automatically; multiple current AE events
  require a choice. Facts from the same nonblank repeat instance are scoped
  together, while blank/unknown instances do not pull unrelated events in.
- Explicit related current or historical facts can be added as context.
  Historical related facts preserve occurrence/observation/record time and a
  `related_history` role but cannot drive deterministic rule evaluation.
- The study's persisted jurisdiction is used for applicable-rule selection.
  W04 common-policy and rule unknowns/conflicts are visible downstream.
- Laboratory agreement and abnormality are separate. Agreement with a
  below/above-range result remains a safety lead; a data difference is a review
  question, not an automatic AE. Field-specific skips are not repeated, and
  stale comparisons are rejected until rerun.
- A provider explanation is a separate persistent `safety_provider_run` with
  request snapshot, attempt, lease, provider/model version, model-weight hash,
  dependency-lock hash, raw output, grounding result and error history.
- The main immutable assessment is not rewritten when the provider finishes.
  API status is derived from the independent run, and accepted grounding keeps
  capability at `limited/validated=false`.
- Analysis worker commands use complete platform-specific hash locks and the
  explicit PyTorch CPU index. The pinned Qwen weights are hashed before load.

## Public entry points

- `POST /api/v1/safety-assessments`
- `GET /api/v1/safety-assessments/{id}`
- `GET /api/v1/studies/{study_id}/safety-assessments?site_id=&subject_id=`
- `POST /api/v1/safety-assessments/{id}/analysis-retry`
- `POST /api/v1/safety-assessments/{id}/cra-review`
- `POST /api/v1/safety-assessments/{id}/medical-response`
- `POST /api/v1/safety-assessments/{id}/issues`

## Authoritative execution

- Tested commit:
  `12a7b38d577066424cb7cec9e29378923eeef406`.
- GitHub Actions:
  https://github.com/pyzz58/gpt-recommendations/actions/runs/41251079001
- Task job: `cra-w09`.
- Required steps: `migration-roundtrip`, `test`,
  `analysis-provider-evaluation`, `lab-provider-evaluation`, `contracts`,
  `frontend`.
- PostgreSQL 18.6 service. Migration `0009_review_remediation` downgraded to
  `0008_safety_assessment` and re-upgraded successfully.
- W09 job's combined review/rule/subject/lab/recognition/safety/platform test
  step: 65 passed in 20.86 seconds.
- Actual Qwen evaluation: 3/3 dimension matches, 3/3 required-question topic
  matches, 3/3 grounded outputs. Fabricated evidence, unsupported
  numbers/dates, medical conclusions and grade-to-SAE control were rejected.
- Qwen run emitted analysis lock SHA-256
  `0e94391c3ffb1d11612bc37bf0000ece9e1d96f1e3b3c3ebb6d0300dbf48b6d1`
  and model-weight SHA-256
  `fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe`.
- Qwen evaluation took 40.534 seconds; maximum RSS was 3,448,303,616 bytes.
- Actual laboratory evaluation in the same task: text PDF, clear PNG and Chinese
  header-context PDF all passed. OCR lock SHA-256 was
  `b63ebded2cb330b5b68a67f24988c28733798336874cabc5d157983f5c7b1e01`;
  Docling model-manifest SHA-256 was
  `c5309aff4606055d82f24f07da522ce6830de7d664faaeb4f9fa44cd10d0705b`.
  The isolated image provider took 35.499 seconds with 2,358,734,848 bytes
  maximum RSS.
- OpenAPI drift check, 13 frontend tests, TypeScript and production build
  passed.
- Subject digest:
  `b604f28c0dccebbd5b5aad58264101e350e3dcebb2b325f486b68684f1fa8747`.

## Remaining limits

- Only three independent synthetic safety cases and authored safety rules were
  used. No real protocol, IB, AESI list, DLT definition, safety database or
  clinical record was processed.
- The small local model does not perform clinical reasoning. It selects a
  server-allowed explanation template and supplied evidence IDs.
- Candidate means review material only. It is not investigator confirmation,
  an SAE/PD determination, a causality judgment or a reportability decision.
- Missing source facts, adopted reference-safety version, AESI/DLT definitions,
  awareness time or project deadline remain unknown. No deadline is inferred.
- The current Chinese laboratory fixture is a clear text PDF, not a real
  photograph or arbitrary hospital layout.
- No clinical accuracy, key-error threshold, representative hospital format,
  total manual effort or time-saving comparison has been established.
- A production model/image/mirror, concurrency/resource plan, approved data
  processing terms and a real authorized trial remain for W15.
- W10-W15 were not started. OCR remains limited to laboratory reports; reports,
  directory status, EDC write-back and sending/signature are outside W09.

Next task by dependency after W09: CRA-W10. W10 was not started.
