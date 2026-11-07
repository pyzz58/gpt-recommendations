"""Checklist coverage, stale-plan propagation and acceptance-record boundaries."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sync_work_plan_tests', ROOT / 'tools/sync_spec.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class WorkPlanTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / 'intelligence'
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(
            '__pycache__', '*.pyc', '.venv', '.pytest_cache', '.mypy_cache', '.ruff_cache'))
        # Isolated fixtures establish known correspondence; production baselines
        # are never changed by the generator or this test suite.
        self.edit('WORK_PLAN', lambda c: [w.update(progress='NOT_STARTED', evidence=[]) for w in c['items']])
        self.review_technical_in_fixture()
        now = {w['id']: w for w in self.current()['items']}
        self.edit('WORK_PLAN', lambda c: [w.__setitem__('reviewed_basis_sha256', now[w['id']]['basis_sha256']) for w in c['items']])
        self.assertEqual(sync.synchronize(self.root, write=True), [])
        sync.assert_work_plan_current(self.root)

    def text(self):
        return (self.root / sync.SPEC).read_text(encoding='utf-8')

    def change(self, fn):
        (self.root / sync.SPEC).write_text(fn(self.text()), encoding='utf-8')

    def edit(self, name, fn):
        config = sync.trace.fenced_block(self.text(), name)
        fn(config)
        def replace(text):
            a, b = text.index('<!-- BEGIN ' + name + ' -->'), text.index('<!-- END ' + name + ' -->')
            return text[:a] + '<!-- BEGIN ' + name + ' -->\n```json\n' + json.dumps(config, ensure_ascii=False, indent=2) + '\n```\n' + text[b:]
        self.change(replace)

    def review_technical_in_fixture(self):
        text = self.text()
        trace = sync.trace.build(text, hashlib.sha256(text.encode()).hexdigest())
        now = {n['id']: n for n in trace['nodes']}
        self.edit('TECHNICAL_BINDINGS', lambda c: [n.__setitem__('reviewed_binding', now[n['id']]['current_binding']) for n in c['nodes']])

    def current(self):
        text = self.text()
        digest = hashlib.sha256(text.encode()).hexdigest()
        trace = sync.trace.build(text, digest)
        return sync.work_plan.build(text, digest, trace, sync.trace)

    def mutate_work(self, wid, fn):
        self.edit('WORK_PLAN', lambda c: fn(next(w for w in c['items'] if w['id'] == wid)))

    def evidence(self):
        return [dict(record_id='TEST_ONLY', artifact_refs=['isolated://actual-artifact'],
                     validation_refs=['isolated://validation-result'], reviewer='fixture',
                     result='test-only record', scope='Structural test, no production acceptance')]

    def test_inventory_and_original_logic_are_fully_covered(self):
        plan = self.current()
        self.assertEqual(plan['counts'], dict(functional_modules=13, routes=8, logic_items=72, work_packages=55, gates=4, steps=59))
        self.assertEqual([sum(w['kind'] == 'WORK' and w['phase'] == i for w in plan['items']) for i in range(1, 5)], [12, 29, 4, 10])
        self.assertEqual(len(plan['technical_coverage']), 21)
        self.assertEqual(len(plan['module_checklists']), 13)
        self.assertTrue(all(len(m['logic']) == 3 for m in plan['module_checklists'].values()))
        self.assertEqual(len(plan['logic_coverage']), 72)
        self.assertTrue(all(plan['logic_coverage'].values()))
        self.assertTrue(all(w['progress'] == 'NOT_STARTED' and not w['evidence'] for w in plan['items']))
        self.assertFalse(plan['review_required'])

    def test_theory_change_updates_impact_without_approving_plan(self):
        old = sync.trace.fenced_block(self.text(), 'WORK_PLAN')
        self.change(lambda s: s.replace('### 4.2 轻量候选卡（L1唯一必交）', '### 4.2 轻量候选卡（L1唯一必交）\n\n测试专用：候选理论变化。', 1))
        self.assertEqual(sync.synchronize(self.root, write=True), [])
        plan = self.current()
        self.assertIn('W02', plan['review_required'])
        self.assertIn('W20', plan['review_required'])
        self.assertIn('G02', plan['review_required'])
        # W01 also binds R07, whose complete recovery route conservatively
        # depends on changed research modules; it correctly needs review too.
        self.assertIn('R07', plan['items'][0]['pending_technical_nodes'])
        self.assertEqual(old, sync.trace.fenced_block(self.text(), 'WORK_PLAN'))
        with self.assertRaisesRegex(ValueError, 'requires review'):
            sync.assert_work_plan_current(self.root, ['W20'])
        sync.assert_technical_current(self.root, ['T04'])

    def test_revising_technical_baseline_alone_cannot_approve_old_checklist(self):
        self.change(lambda s: s.replace('- **设计**：从M02起提出知识、背景、比较和迁移问题', '- **设计**：从M02起提出测试专用变化的知识问题', 1))
        self.review_technical_in_fixture()
        self.assertEqual(sync.synchronize(self.root, write=True), [])
        sync.assert_technical_current(self.root)
        self.assertIn('W29', self.current()['review_required'])
        with self.assertRaises(ValueError):
            sync.assert_work_plan_current(self.root, ['W29'])

    def test_acceptance_change_affects_consumer_but_not_independent_work(self):
        self.mutate_work('W28', lambda w: w['acceptance'].append('测试专用：新的验收条件。'))
        plan = self.current()
        self.assertIn('W28', plan['review_required'])
        self.assertIn('W31', plan['review_required'])
        self.assertNotIn('W29', plan['review_required'])
        self.assertEqual(sync.synchronize(self.root, write=True), [])
        self.assertIn('W28', self.current()['review_required'])

    def test_plan_governance_change_invalidates_every_work_item(self):
        self.change(lambda s: s.replace('### 26.2 每个工作包和阶段门的共同验收Q01—Q07', '### 26.2 每个工作包和阶段门的共同验收Q01—Q07\n\n测试专用共用变化。', 1))
        self.assertEqual(len(self.current()['review_required']), 59)

    def test_context_source_cannot_be_removed_to_hide_a_change(self):
        self.edit('WORK_PLAN', lambda c: c['context_refs'].remove('tech-work-26-2'))
        with self.assertRaisesRegex(ValueError, 'context source'):
            self.current()

    def test_progress_and_evidence_updates_do_not_rewrite_design_basis(self):
        before = {w['id']: w['basis_sha256'] for w in self.current()['items']}
        self.mutate_work('W01', lambda w: w.update(progress='IN_PROGRESS', evidence=self.evidence()))
        after = self.current()
        self.assertEqual(before, {w['id']: w['basis_sha256'] for w in after['items']})
        self.assertFalse(after['review_required'])

    def test_w35_repair_branch_is_not_blocked_by_unfinished_w27(self):
        before = {w['id']: w for w in self.current()['items']}
        self.assertEqual(before['W35']['depends_on'], ['W14', 'W17'])
        self.assertNotIn('W27', before['W35']['pending_completion_dependencies'])
        self.mutate_work('W27', lambda w: w.update(progress='BLOCKED', evidence=self.evidence()))
        self.mutate_work('W35', lambda w: w.update(progress='IN_PROGRESS', evidence=self.evidence()))
        after = self.current()
        self.assertFalse(after['review_required'])
        repaired = {w['id']: w for w in after['items']}
        self.assertEqual(repaired['W35']['progress'], 'IN_PROGRESS')
        self.assertNotIn('W27', repaired['W35']['pending_completion_dependencies'])

    def test_missing_logic_coverage_blocks_all_projection_writes(self):
        before = {name: (self.root / name).read_bytes() for name in sync.OUTPUTS}
        self.edit('WORK_PLAN', lambda c: [w.__setitem__('logic_ids', [s for s in w['logic_ids'] if s != 'T13.L03']) for w in c['items']])
        with self.assertRaisesRegex(ValueError, 'Uncovered logic'):
            sync.synchronize(self.root, write=True)
        self.assertEqual(before, {name: (self.root / name).read_bytes() for name in sync.OUTPUTS})

    def test_missing_deliverable_or_specific_acceptance_is_rejected(self):
        original = self.text()
        for field, value in [('deliverables', []), ('acceptance', ['only one']), ('inputs', '')]:
            with self.subTest(field=field):
                (self.root / sync.SPEC).write_text(original)
                self.mutate_work('W28', lambda w: w.__setitem__(field, value))
                with self.assertRaises(ValueError):
                    self.current()

    def test_unknown_logic_duplicate_id_and_wrong_inventory_are_rejected(self):
        original = self.text()
        edits = [lambda c: c['items'][0]['logic_ids'].append('T99.L01'),
                 lambda c: c['items'][1].update(id='W01'),
                 lambda c: c['expected_counts'].update(steps=60)]
        for fn in edits:
            (self.root / sync.SPEC).write_text(original)
            self.edit('WORK_PLAN', fn)
            with self.assertRaises(ValueError):
                self.current()

    def test_forward_dependency_and_bypassed_stage_gate_are_rejected(self):
        original = self.text()
        for wid, deps, message in [('W01', ['W02'], 'dependency'), ('W13', [], 'phase gate')]:
            with self.subTest(wid=wid):
                (self.root / sync.SPEC).write_text(original)
                self.mutate_work(wid, lambda w: w.update(depends_on=deps))
                with self.assertRaisesRegex(ValueError, message):
                    self.current()

    def test_stage_gate_cannot_omit_a_work_package(self):
        self.mutate_work('G01', lambda w: w['depends_on'].remove('W03'))
        with self.assertRaisesRegex(ValueError, 'every work package'):
            self.current()

    def test_acceptance_requires_evidence_and_completed_dependencies(self):
        original = self.text()
        self.mutate_work('W01', lambda w: w.update(progress='ACCEPTED'))
        with self.assertRaisesRegex(ValueError, 'actual evidence'):
            self.current()
        (self.root / sync.SPEC).write_text(original)
        self.mutate_work('W02', lambda w: w.update(progress='ACCEPTED', evidence=self.evidence()))
        with self.assertRaisesRegex(ValueError, 'before its dependencies'):
            self.current()

    def test_not_applicable_is_limited_to_documented_conditional_work(self):
        original = self.text()
        self.mutate_work('W20', lambda w: w.update(progress='NOT_APPLICABLE', evidence=self.evidence()))
        with self.assertRaisesRegex(ValueError, 'progress'):
            self.current()
        (self.root / sync.SPEC).write_text(original)
        self.mutate_work('W35', lambda w: w.update(progress='NOT_APPLICABLE', evidence=self.evidence()))
        self.assertFalse(self.current()['review_required'])
        self.mutate_work('G01', lambda w: w.update(progress='NOT_APPLICABLE', evidence=self.evidence()))
        with self.assertRaises(ValueError):
            self.current()

    def test_hand_edited_projection_cannot_approve_or_complete_work(self):
        p = self.root / 'work_plan.json'
        value = json.loads(p.read_text())
        value['items'][0]['progress'] = 'ACCEPTED'
        p.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, 'Stale generated'):
            sync.assert_work_plan_current(self.root)
        self.assertEqual(sync.synchronize(self.root, write=True), [])
        self.assertEqual(json.loads(p.read_text())['items'][0]['progress'], 'NOT_STARTED')

    def test_unknown_selection_fails_and_regeneration_is_idempotent(self):
        with self.assertRaisesRegex(ValueError, 'Unknown work-plan'):
            sync.assert_work_plan_current(self.root, ['W99'])
        before = {name: (self.root / name).read_bytes() for name in sync.OUTPUTS}
        self.assertEqual(sync.synchronize(self.root, write=True), [])
        self.assertEqual(before, {name: (self.root / name).read_bytes() for name in sync.OUTPUTS})


if __name__ == '__main__':
    unittest.main()
