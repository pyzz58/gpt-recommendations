"""Offline continuity validation; no real model calls or provider credentials."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
from unittest import TestCase
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import continuity_audit as ca
import local_director as director


class ContinuityAuditTests(TestCase):
    @staticmethod
    def simple(put_back=False):
        a={'id':'S01', 'scene_id':'LOC01', 'character_ids':['CH1'],
           'action':{'action':'他把手机扣在沙发扶手上'},'visual':'手机在沙发扶手'}
        b={'id':'S02', 'scene_id':'LOC02', 'character_ids':['CH1'],
           'action':{'start':'手伸向抽屉把手', 'action':('拿起手机，再把手机放进抽屉' if put_back else '把手机放进抽屉')},
           'visual':'手机放进抽屉'}
        return {'shots':[a,b], 'scenes':[{'id':'LOC01','description':'客厅沙发'}, {'id':'LOC02','description':'书桌'}]}

    def test_phone_teleport_blocks(self):
        report=ca.audit_plan(self.simple())
        self.assertEqual(report['blockers'],1)
        self.assertIn('PROP_TRANSFER_MISSING_PHONE',[x['code'] for x in report['findings']])

    def test_pickup_clears_block(self):
        report=ca.audit_plan(self.simple(True))
        self.assertEqual(report['blockers'],0)

    def test_explicit_pickup_in_prior_shot_carries_prop(self):
        p=self.simple()
        p['shots'].insert(1, {'id':'S01b','scene_id':'LOC01',
                              'action':{'action':'他从沙发扶手拿起手机'}})
        self.assertEqual(ca.audit_plan(p)['blockers'],0)

    def test_malformed_manifest_is_reported_not_crashed(self):
        p={'shots':[{'id':'S1','continuity_state':'bad'}],'scenes':[]}
        r=ca.audit_plan(p)
        self.assertEqual(r['blockers'],1)

    def test_explicit_manifest_any_prop_detects_transfer(self):
        p={'shots':[
            {'id':'S1','continuity_state':{'props_before':{'杯子':'桌面'},'prop_moves':[],'props_after':{'杯子':'桌面'}}},
            {'id':'S2','continuity_state':{'props_before':{'杯子':'柜子'},'prop_moves':[],'props_after':{'杯子':'柜子'}}}], 'scenes':[]}
        r=ca.audit_plan(p)
        self.assertGreaterEqual(r['blockers'],1)
        self.assertIn('DECLARED_PROP_STATE_MISMATCH',[x['code'] for x in r['findings']])

    def test_sample_existing_series_does_not_false_block(self):
        p=director.load(ROOT/'examples/quit-smoking/plan.json')
        r=ca.audit_plan(p)
        self.assertEqual(r['blockers'],0)

    def test_audit_cli_creates_only_sidecars_and_preserves_input(self):
        import io
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'plan.json'
            p=self.simple()
            path.write_text(json.dumps(p,ensure_ascii=False),encoding='utf-8')
            original=path.read_bytes()
            with patch('sys.stdout',new_callable=io.StringIO) as output:
                self.assertEqual(director.main(['audit','--plan',str(path)]),0)
            self.assertIn('1项阻断',output.getvalue())
            self.assertEqual(path.read_bytes(),original)
            self.assertTrue((path.parent/'continuity_repair.generated.md').exists())
            self.assertTrue((path.parent/'continuity_audit.generated.json').exists())

    def test_real_pilot_chains_flagged_only_if_fixture_is_present(self):
        # This fixture is synthesised. Never commit private user text to GitHub.
        p={'scenes':[{'id':'L1','description':'茶几上放一本书'},
                     {'id':'L2','description':'书桌放台灯'}],
           'shots':[{'id':'S02','scene_id':'L1','visual':'他手里拿着一本书从门口进来',
                     'action':{'start':'右手握着一本书'}},
                    {'id':'S03','scene_id':'L1','action':{'action':'把书放在茶几上'}},
                    {'id':'S08','scene_id':'L1','action':{'action':'把手机扣在沙发扶手上'}},
                    {'id':'S10','scene_id':'L2','art':{'set_props':'台灯、同一本书'},
                     'action':{'action':'拉开抽屉，把手机放进抽屉'}}]}
        issues=ca.audit_plan(p)['findings']
        codes={f['code'] for f in issues}
        self.assertIn('SCENE_PROP_DOUBLE_BOOK',codes)
        self.assertIn('PROP_APPEARANCE_UNEXPLAINED_BOOK',codes)
        self.assertIn('PROP_TRANSFER_MISSING_PHONE',codes)
