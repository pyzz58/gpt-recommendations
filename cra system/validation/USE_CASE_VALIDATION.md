# CRA V1A use-case validation and release control

Date: 2026-11-07. All current evidence is synthetic/engineering evidence.

| Use case | User and output | Demonstrated scope | Material risk | Release responsibility and control |
| --- | --- | --- | --- | --- |
| Text-PDF laboratory review | CRA reviews source values against an EDC Excel snapshot | Selectable-text ruled PDF, deterministic matching and comparison | Wrong identity/date/instance creates an incorrect review statement | CRA reviews traceable candidates; release engineering keeps the route limited to the declared format |
| Clear-image laboratory review | CRA reviews an uploaded clear report and source region | One independent clear synthetic PNG via Docling | OCR, row ownership, blur, rotation and real layouts can cause critical errors | Provider evidence, candidate review and source-region display required; unclear images use limited backfill/skip |
| Historical carryover | CRA confirms previous-report/track issues and continues | Synthetic DOCX, XLSX and text preview with user confirmation | Wrong number/location or duplicate issue obscures unfinished work | CRA confirms corrected extraction; source anchors and import idempotency remain visible |
| Rules and visit context | CRA reviews conditional lists and subject requirements | Authored/anchored synthetic rule subset; deterministic three-value evaluation | Lost negation/exception or wrong adopted version changes the check path | CRA adds/removes candidates; unknown and conflict remain visible; no arbitrary-protocol completeness claim |
| Safety support | CRA reviews facts, candidate dimensions and questions | Three independent synthetic cases and grounded local model output | Treating a candidate as a medical conclusion or missing urgent work | Candidates, CRA review and medical response are separate; no automatic final determination |
| Reports and handover | CRA reviews selected letters, report and track | Synthetic mapped DOCX/XLSX and immutable snapshot | Unsent material mistaken for sent, or late changes rewriting an issued report | Generate, send, sign and archive are separate; user signs off and confirms delivery |
| ISF/TMF and stage lists | CRA compares the uploaded directory and reviews stages | Synthetic reference directory, checklists and handover | File existence mistaken for current/applicable content | File presence, content applicability and user confirmation remain separate |
| Authorized production trial | Approved CRA and study team use real data in an approved environment | Not demonstrated | Privacy, authorization, clinical error and recovery failure | Disabled. W15 requires approved OIDC, private storage, restore test and documented trial scope |

## Version and monitoring

The release identifier is `CRA-V1A-ENGINEERING-20261107`. Provider locks are
recorded under `provider-locks/`; the W08/W09 task records identify the tested
source commit and model/dependency hashes. A provider, model, mapping, parsing
or dependency change that affects an automatically validated use case requires
the corresponding independent regression before that use case is restored.

Feedback and incident monitoring should record affected use case, release,
input format, critical error, scope of impact, user-visible unknown/not-checked
state and source references. Raw clinical material and logs stay in the
approved private environment.

## Pause and resume

Pause the affected automatic function when evidence shows a critical identity,
date, analyte, value, unit, instance, condition or authorization error; an
unsupported deterministic safety conclusion; a false reported/closed action;
or a restore failure. Preserve source files, facts, lists, issues and issued
snapshots. Users may continue unaffected review and manual recording.

Resume only after the failing case and neighboring boundaries pass through the
real consumer, the tested release is recorded and the affected scope is
revalidated. Pause/resume is a developer/release-control action and does not add
a per-monitoring CRA approval.
