# 2026-11-01 review remediation record

Status: verified. Source-bound cloud verification:
https://github.com/pyzz58/gpt-recommendations/actions/runs/41245438323,
tested commit `5148684064a57e50077dd32d02e76b57b2221fc4`.

The reviewed implementation claims were reopened rather than silently retaining
the earlier W01-W09 `verified` state. Old completion evidence remains in
`plan/tasks.json.completion_history`.

## Finding closure map

| Finding | Implemented correction | Primary regression proof |
| --- | --- | --- |
| CRA-REV-20261101-01 | Effective laboratory values are folded across the complete ordered decision chain; confirm/batch confirm/successive partial corrections preserve the latest current value while source candidates remain immutable. | `test_confirm_and_successive_corrections_keep_current_effective_value` |
| CRA-REV-20261101-02 | Unknown exceptions now keep a rule unknown; required dimensioned units must be present on both numeric operands; false preconditions still take precedence. | `test_unknown_exception_keeps_rule_unknown`, `test_missing_dimensioned_unit_stays_unknown` |
| CRA-REV-20261101-03 | Visit-window specs carry applicability gates; not-applicable paths expose no window task, unknown gates remain unknown, unknown/malformed actual dates remain `unknown_actual`, and automatic window claims are `auto_candidate/needs_review`. Upstream rule unknowns are inherited. | `test_visit_window_respects_gate_unknown_date_and_auto_candidate_status` |
| CRA-REV-20261101-04 | A project-wide document can have independent center adoption intervals; a site adoption overrides the project default for the same rule key while true same-site overlaps remain conflicts. | `test_shared_project_rule_can_have_independent_site_adoption_dates` |
| CRA-REV-20261101-05 | Rule nodes carry bilingual purpose tags. Ordinary Chinese requirement prose is preserved as an `analysis_required` source-backed candidate instead of being silently classified as non-rule context. | `test_ordinary_chinese_requirement_is_preserved_for_review`, `test_natural_chinese_rule_prose_becomes_reviewable_candidate` |
| CRA-REV-20261101-06 | Lower/upper limits, bounds, units, report date and report revision are independently retained; different limits are reported even when both range flags agree. | `test_reference_limits_are_compared_independently` and laboratory integration tests |
| CRA-REV-20261101-07 | Report-level subject/date/instance/version context is parsed from non-table lines, bound to source coordinates once and reused by rows that omit repeated header fields. | Chinese context PDF recognition and PostgreSQL/API test |
| CRA-REV-20261101-08 | Laboratory upload persists a queued report/job and outbox event, returns 202, processes in Procrastinate, uses leases and retry, and rechecks authorization/input when a worker resumes. | Queue recovery and real Procrastinate worker tests |
| CRA-REV-20261101-09 | Hashed transitive dependency locks exist for OCR and analysis environments; model revision and weight SHA-256 are verified before inference and emitted as run evidence. | Provider evaluations and `validation/W09_DEPENDENCIES.md` |
| CRA-REV-20261101-10 | Original W02/W03/W04/W12/W15 tasks now explicitly track iPad Safari/upload/view, desktop Excel, cross-device same-record continuation, weak-network recovery and authorized-device validation, without inventing offline scope. | Task/spec traceability check |
| CRA-REV-20261101-11 | Safety handoff separates agreement, consistent-but-abnormal, difference, uncomparable, user skip and stale. Consistent abnormalities remain safety leads; skipped fields are not re-prompted; stale comparisons are rejected until rerun; data difference is not labeled AE. | Safety laboratory integration tests including abnormal-consistency, skip and stale |
| CRA-REV-20261101-12 | Study jurisdiction is persisted and used; upstream common/rule unknowns are inherited; model input classification comes from trusted runtime settings; model response `accepted` stays `limited/validated=false`. | Safety integration assertions and platform capability tests |
| CRA-REV-20261101-13 | Safety commands identify a current event fact and select its repeated-instance fact scope, with explicit related facts allowed. Multiple AE events are not merged by fact key. | `test_safety_facts_are_scoped_to_the_selected_event_instance` |

## Verification performed locally

- Fresh temporary PostgreSQL 18.6 cluster.
- `0009_review_remediation` upgrade and downgrade/re-upgrade round trip.
- Full non-S3 suite: 115 tests passed at the implementation checkpoint.
- Actual Qwen evaluation: three cases have correct dimensions/questions and
  three grounded responses; fabrication, unsupported value, medical conclusion
  and grade-to-SAE controls are rejected. The selected macOS dependency lock
  hash and pinned weight SHA-256 are included in the evaluation output.
- Actual laboratory evaluation: text PDF, clear PNG and Chinese header-context
  PDF all passed their declared synthetic row/source checks. The image run
  emitted the selected OCR lock and Docling model-manifest hashes.
- Frontend tests, TypeScript and production build passed.

## Authoritative cloud result

The complete CRA workflow run finished successfully with baseline and
`cra-w01` through `cra-w09` all green. The W09 task job ran the 0009→0008→head
migration round trip, 54 affected PostgreSQL/API tests, the real pinned Qwen
evaluation and the real Docling/PDF evaluation, then the OpenAPI drift check,
13 frontend tests, TypeScript and production build. W08 independently passed
its 7 review-unit, 10 laboratory and 4 recognition tests plus the same real
Docling evaluation.

The Linux Qwen run emitted lock SHA-256
`0e94391c3ffb1d11612bc37bf0000ece9e1d96f1e3b3c3ebb6d0300dbf48b6d1`
and model-weight SHA-256
`fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe`.
The Linux Docling run emitted OCR lock SHA-256
`b63ebded2cb330b5b68a67f24988c28733798336874cabc5d157983f5c7b1e01`
and model-manifest SHA-256
`c5309aff4606055d82f24f07da522ce6830de7d664faaeb4f9fa44cd10d0705b`.

Task evidence was rebound to the tested commit with nine source/subject digests;
`tools/task_evidence.py` reports 9 checked tasks and authoritative verification
true. Local success is not substituted for this task-specific CI gate.
