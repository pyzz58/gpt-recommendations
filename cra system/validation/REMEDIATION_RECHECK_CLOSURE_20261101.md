# 2026-11-01 remediation recheck closure

Status: verified. Source-bound CI:
https://github.com/pyzz58/gpt-recommendations/actions/runs/41248250769,
tested commit `f66750c9fac58dbf2e03189582a3544fc039bfd4`.

The independent review at
https://github.com/pyzz58/gpt-recommendations/actions/runs/41247079903
reproduced three residuals. Its five green diagnostic cases meant
`acceptance_passed=false`; this record does not reuse them as product
acceptance.

## CRA-REV-20261101-03

Date-interval extraction now carries all ancestor preconditions, exceptions
and non-date branch gates into child nodes at any depth. Window identity
includes the RuleNode path and gate-condition signature, so equal sibling
intervals under distinct paths remain separate.

Forward PostgreSQL/API regressions:

- `test_nested_visit_windows_inherit_parent_gates_and_keep_out_of_window`
- `test_sibling_equal_visit_windows_keep_distinct_condition_paths`

The tests cover false parent prerequisite, true parent waiver, unknown ancestor
applicability, equal sibling windows and a genuinely applicable visit outside
the window.

## CRA-REV-20261101-04

Project-default suppression now uses the explicit Rule identity/version
lineage. A site adoption of the same shared Rule can select the center's
effective version without creating a duplicate project rule. An independently
extracted center SOP with the same `rule_key` is a different Rule and remains in
the three-layer result alongside the project rule.

Forward PostgreSQL regressions:

- `test_shared_project_rule_can_have_independent_site_adoption_dates`
- `test_independent_site_rule_cannot_hide_same_key_project_rule`

The tests cover project default plus two center adoption dates and independent
same-key project/site requirements.

## CRA-REV-20261101-08

Recognition job claims now distinguish already-succeeded replay from active
work. A repeated delivery of a succeeded job returns the existing report before
source read, provider inference or candidate persistence.

Running retries protect a live lease and accept only an expired lease. The
attempt number, worker owner and unexpired lease are checked transactionally
before any result write. A late obsolete attempt therefore returns the current
report without changing observations, revision or CRA corrections.

Forward PostgreSQL/API/worker regressions:

- `test_succeeded_job_redelivery_is_noop_before_provider`
- `test_public_retry_recovers_expired_lease_but_protects_live_lease`
- `test_obsolete_attempt_cannot_overwrite_new_result_or_cra_correction`
- existing `test_real_procrastinate_worker_processes_laboratory_job`

## Preserved limits

- Ordinary Chinese text still produces reviewable `analysis_required`
  candidates rather than a complete arbitrary-protocol AST.
- Laboratory recognition remains limited to the declared synthetic text,
  clear-print image and Chinese header-context formats.
- iPad, weak-network and cross-device validation remain under W12/W15.
- No real clinical data, deployment, external send or EDC write-back was used.

Local verification at the implementation checkpoint:

- full non-S3 pytest: 122 passed;
- W04/W05/W08 focused PostgreSQL tests: 40 passed;
- frontend: 13 passed, TypeScript and production build passed;
- traceability and synchronization checks passed.

## Authoritative cloud result

- W04: 17 rule/review-unit tests, rule provider evaluation, contracts and
  frontend passed; digest
  `13521d2ec37a9c11fce187c210e87dd06858dd7ca4c29f8f299c60bb092ac594`.
- W05: 10 PostgreSQL/API tests passed; digest
  `0057da1039e992312002af5c7e324edb32dae2529088ab42579cd3a8df63ad66`.
- W06/W07 dependency-chain jobs passed; digests
  `2df3d12dbbe1dc7ae1492623fc6119878a94715965ba3b34e2a69b3229226157`
  and `4e7c96f9cee4dc2730b99ea2a34287e732efc91123205850487e5ae3b7a938fd`.
- W08: 7 review-unit, 13 laboratory and 4 recognition tests passed; real
  Docling evaluation passed; digest
  `d92da00ab44a893f7f5bfbd6195eca4ded8bcfbd9921927f0e2587cc3f4c0932`.
- W09: 60 affected tests, real Qwen and Docling evaluations, contracts and
  frontend passed; digest
  `72c1ade1c9a043e30ea9838d2fdaa10463955cc65eb10aa08bc2b1107919dfd7`.

`tools/task_evidence.py` reports 9 tasks checked with authoritative
verification true. The selector advances to CRA-W10.
