# CRA-W03 OCR provider feasibility

Date: 2026-10-31. Scope: one pure-synthetic laboratory image. This is an
environment and output-shape probe, not clinical validation and not the W08
comparison acceptance.

## Input

- Artifact: `tests/fixtures/documents/artifacts/synthetic_lab_report.png`
- SHA-256:
  `5583ff2ff4f57d8f6a37d1116f05378248cb946c09075a6fc2c64ec01951c8fb`
- Image: 1200 × 600, clear printed Latin text, no real or de-identified patient
  material.
- Group: development only. A PDF report is held separately in the synthetic
  evaluation group, but was not used to tune this OCR probe.

## Actual isolated run

Both candidates were installed and executed in isolated Python 3.12
environments. The main application remains on Python 3.13.15; no candidate
dependency is added to the runtime lock.

| Candidate | Exact package | Code/model licence | Expected tokens | Coordinates | Warm probe elapsed | Process max RSS |
| --- | --- | --- | --- | --- | ---: | ---: |
| PaddleOCR | paddleocr 3.7.0 / paddlepaddle 3.3.1 | Apache-2.0; PP-OCRv6 models Apache-2.0 | 3/3 | 4 boxes | 2.46 s | 1,528,315,904 bytes |
| Docling | docling 2.145.0 | MIT; layout/model cards checked Apache-2.0 or CDLA-Permissive-2.0 | 3/3 | 4 boxes | 5.79 s | 2,935,341,056 bytes |

PaddleOCR used `PP-OCRv6_medium_det` and `PP-OCRv6_medium_rec`. Docling used the
default document/layout pipeline. Both emitted the three expected synthetic
tokens (`SYNTH-Hb`, `121`, `g/L`) and source bounding boxes. These numbers are
one-run observations after model caches were warm; they are not service-level
benchmarks.

Command:

```bash
PYTHONPATH=backend uv run --frozen python \
  -m cra_app.providers.probe --synthetic
```

The command downloads official packages/models on a cache miss, checks the same
image against both pipelines, verifies expected tokens and coordinate presence,
and selects the lower-latency passing candidate. CI uses isolated processes so
the candidate dependency trees do not modify the main application environment.

## Decision

Select **PaddleOCR/PP-Structure as the first W08 integration candidate**. It was
faster and used less memory on the same output, while retaining per-line text
and coordinates. Docling remains the controlled comparison/fallback candidate.

This selection does not make OCR available in W03. `RecognizeLab` remains
explicitly disabled; W08 owns the supported-format intake, field extraction,
identity/instance matching and EDC comparison. A later W08 evaluation must add
representative formats and evaluate numeric values, operators, decimal points,
units, row/column ownership, dates, initial/repeat instances, critical errors,
manual review burden and total time.

## Remaining risks

- One synthetic image cannot establish accuracy or format coverage.
- The warm probes consumed approximately 1.4 GiB (PaddleOCR) and 2.7 GiB
  (Docling) maximum resident memory in this process; production resource limits
  and concurrency must be measured again in the approved Linux runtime.
- Model downloads require explicit network/mirror approval in an isolated
  provider image. CI cache absence may produce a much longer first run.
- Package/model declarations were checked, but transitive dependencies and the
  final provider image still require a locked SBOM/licence review before W08.
- No clinical performance, safety or time-saving claim is made.
