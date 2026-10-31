# Branch-target gate and prevention integration

Date: 2026-11-01.

Status: verified. Source-bound CI:
https://github.com/pyzz58/gpt-recommendations/actions/runs/41251079001,
tested commit `12a7b38d577066424cb7cec9e29378923eeef406`.

## Original finding 03

The remaining defect was in the relationship between
`RuleBranch.target_node_ids` and child windows:

- a target's date trigger was removed merely because a branch referenced it;
- container targets did not inherit the branch-selection condition;
- false/unknown branch selection could therefore leave an out-of-window task.

The correction distinguishes a duplicated date expression from the target's own
obligation. A target date window is retained. Non-duplicate branch conditions
propagate through the target and descendants. Multiple entry paths to the same
target use OR reachability rather than an accidental AND.

Positive product regressions:

- `test_branch_target_preserves_window_and_selection_context`
- `test_multiple_branch_entries_to_one_target_use_or_semantics`
- existing ancestor, waiver, sibling-path and true out-of-window regressions.

The four public API/PostgreSQL cases cover:

1. direct target, condition true, actual result out of window;
2. container target, condition false, no dependent window task;
3. container target, condition unknown, unknown applicability;
4. container target, condition true, actual result out of window.

## Prevention integration

The development branch now contains:

- `architecture/REGRESSION_PREVENTION.md`;
- `audit/current_findings.json` as the mutable current-finding index;
- `tools/review_gate.py`;
- selector integration in `tools/next_task.py`;
- completion/evidence integration in `tools/task_evidence.py`;
- negative tests proving open findings become `review_required`, unrelated tasks
  are not frozen, and a closed finding cannot omit bound correct-behavior tests.

The W05 profile binds the policy, gate tools, gate unit tests and its PostgreSQL
integration file. The W05 task-specific job runs `review-gate-self-test` as a
required step.

## Local verification

- `tests/integration/test_subjects.py`: 14 passed.
- Branch/review-gate/evidence/execution focused set: 43 passed.
- Full non-S3 pytest: 130 passed.
- Unittest suite: 47 passed.
- Traceability and generated-view checks passed.

## Authoritative result

- W05 task job: 15 PostgreSQL/API tests and 4 review-gate tests passed.
- W05 passed `test`, `review-gate-self-test`, `contracts` and `frontend`.
- W06-W09 dependency-chain jobs passed.
- W09 ran 65 affected tests plus real Qwen and Docling evaluations.
- `task_evidence.py` reports 9 checked tasks with authoritative verification
  true; `review_gate.py --task CRA-W05` reports no blocker and the selector
  advances to W10.

Task digests:

- W05 `2712bc34d2f6d3afda66c48e823d8333617b2981695f9332006828581e93e29e`
- W06 `2c592b02f72172fae7d717c2236755b30e7419a1f099a1bab4e89f437a6825e0`
- W07 `a375158e26881828e16e1eda8e9d3ae5da0685f5ef55c640b303903c3759f128`
- W08 `ceb19f83da8dc43ea211530a5a0e1f4120e5580766ed45e8f627e85178fe97e7`
- W09 `b604f28c0dccebbd5b5aad58264101e350e3dcebb2b325f486b68684f1fa8747`
