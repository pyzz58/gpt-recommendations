# Branch-target gate and prevention integration

Date: 2026-11-01.

Status: local implementation complete; source-bound CI and independent closure
evidence remain required.

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

The authoritative commit, GitHub run, task digests and finding closure evidence
are added after CI.
