# CRA trial feedback register

状态：EMPTY

No authorized real-use feedback has been received. This register is a template
for deidentified feedback after an approved trial; it is not evidence that a
trial occurred.

## Required fields

| Field | Required content |
| --- | --- |
| Feedback ID | Stable anonymous identifier |
| Date | Observation date |
| User role | CRA, data manager, monitor lead or other approved role |
| Scenario | CRA-Sxx and task/use-case identifier |
| Facts observed | What happened, without patient identifiers or raw clinical content |
| Expected behavior | Relevant CRA-R / module contract |
| Classification | theory_change, data_gap, code_error, presentation or no_change |
| Theory/module/task | Exact CRA-Rxxx、Mxx and CRA-Wxx links |
| Severity | Critical, major, minor or suggestion with consequence |
| Immediate scope control | Continue, limited use or pause affected automatic function |
| Evidence | Private deidentified log/sample reference |
| Owner / due state | Accountable follow-up owner and next checkpoint |

## Classification rules

- `theory_change`: user-confirmed business meaning changed. Apply the
  traceability revision and impact process before code changes.
- `data_gap`: required approved source information was missing. Adjust sample
  scope or targeted data request; do not invent a rule.
- `code_error`: current implementation violated an existing CRA-R or module
  contract. Add a failing regression and preserve neighboring behavior.
- `presentation`: evidence/state is correct but the workbench wording, layout or
  navigation caused avoidable CRA effort.
- `no_change`: observed behavior already matches the confirmed requirement.

## Pause and resume

Pause only the affected automatic use when a critical identity/date/value error,
unsupported clinical conclusion, false reported/closed action, permission
failure or restore failure is observed. Preserve source files, facts, lists,
issues and issued snapshots. Resume after regression, source-bound verification
and revalidation of the affected scope.

## Entries

None.
