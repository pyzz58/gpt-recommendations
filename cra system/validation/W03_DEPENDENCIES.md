# CRA-W03 dependency and environment lock

Date: 2026-10-31. Engineering record only.

| Component | Locked version | Licence | Role |
| --- | --- | --- | --- |
| python-docx | 1.2.0 | MIT | DOCX fixture/source support |
| lxml | 6.1.3 | BSD-3-Clause | Controlled OOXML traversal |
| pdfplumber | 0.11.10 | MIT | Text PDF, coordinates and tables |
| openpyxl | 3.1.5 | MIT | Synthetic XLSX and later EDC ownership |
| boto3 | 1.43.123 | Apache-2.0 | Private S3 adapter |
| Procrastinate | 3.10.0 | MIT | PostgreSQL queue, locking and retry |
| python-multipart | 0.0.32 | Apache-2.0 | Authorized multipart upload |
| reportlab | 4.5.1 (development) | BSD | Deterministic synthetic PDF fixture |
| React-PDF | 11.0.0 | MIT | Browser source-PDF display |
| PDF.js (`pdfjs-dist`) | 6.4.299 | Apache-2.0 | Locally bundled PDF rendering worker |

The main environment remains CPython 3.13.15 and PostgreSQL 18.6. W03 tests use
a real PostgreSQL service and boto3 against an S3-compatible HTTP service.

## Isolated OCR probe candidates

These are deliberately **not** main-project runtime dependencies:

- PaddleOCR 3.7.0 / PaddlePaddle 3.3.1 under isolated CPython 3.12,
  Apache-2.0; PP-OCRv6 model cards declare Apache-2.0.
- Docling 2.145.0 under isolated CPython 3.12, MIT; checked model cards are
  Apache-2.0 or CDLA-Permissive-2.0.

Exact probe specs and commands are in `backend/cra_app/providers/probe.py`.
Model downloads and transitive components require a separate provider-image
SBOM/licence record before W08 deployment.
