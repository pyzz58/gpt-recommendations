"""Offline no-provider regression cases for explicit cross-shot prop continuity."""
import copy
from pathlib import Path
import sys
from unittest import TestCase
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import continuity_contract as cc

def scenario():
    a={'CH_MAIN':{'initial':'LOC02:sofa'}}
    p={'PROP_PHONE':{'initial':'LOC02:sofa_arm'}, 'PROP_BOOK':{'initial':'LOC02:coffee_table'}}
    first={'actors_before':{'CH_MAIN':'LOC02:sofa'},'actors_after':{'CH_MAIN':'LOC02:sofa'},
           'props_before':{'PROP_PHONE':'LOC02:sofa_arm','PROP_BOOK':'LOC02:coffee_table'},
           'props_after':{'PROP_PHONE':'LOC02:sofa_arm','PROP_BOOK':'LOC02:coffee_table'},
           'actor_moves':[],'prop_moves':[]}
    second=copy.deepcopy(first)
    second['prop_moves']=[{'order':1,'prop':'PROP_PHONE','from':'LOC02:sofa_arm','to':'CH_MAIN:hand','kind':'pickup','visible':True},
                          {'order':2,'prop':'PROP_BOOK','from':'LOC02:coffee_table','to':'CH_MAIN:hand','kind':'pickup','visible':True}]
    second['actor_moves']=[{'order':3,'actor':'CH_MAIN','from':'LOC02:sofa','to':'LOC03:desk','kind':'walk','visible':True}]
    second['prop_moves'] += [{'order':4,'prop':'PROP_PHONE','from':'CH_MAIN:hand','to':'LOC03:drawer','kind':'place','visible':True},
                             {'order':5,'prop':'PROP_BOOK','from':'CH_MAIN:hand','to':'LOC03:desk','kind':'place','visible':True}]
    second['props_after']={'PROP_PHONE':'LOC03:drawer','PROP_BOOK':'LOC03:desk'}
    second['actors_after']={'CH_MAIN':'LOC03:desk'}
    return {'continuity_contract':{'version':1,'coverage':'complete','props':p,'actors':a},
            'characters':[{'id':'CH_MAIN'}],
            'shots':[{'id':'S01','continuity_state':first}, {'id':'S02','continuity_state':second}]}

class ContinuityContractTests(TestCase):
    def test_explicit_legal_story(self):
        self.assertEqual(cc.audit_contract(scenario()),[])
    def test_missing_shot_contract_is_blocked(self):
        p=scenario();del p['shots'][1]['continuity_state']
        self.assertIn('SHOT_STATE_MISSING',[x['code'] for x in cc.audit_contract(p)])
    def test_phone_teleport_is_blocked(self):
        p=scenario();m=p['shots'][1]['continuity_state']['prop_moves'];m[:]=[{'order':1,'prop':'PROP_PHONE','from':'LOC02:sofa_arm','to':'LOC03:drawer','kind':'place','visible':True}]
        self.assertIn('ILLEGAL_PROP_TRANSITION',[x['code'] for x in cc.audit_contract(p)])
    def test_actor_must_be_in_pickup_scene(self):
        p=scenario();m=p['shots'][1]['continuity_state'];m['actor_moves']=[{'order':0,'actor':'CH_MAIN','from':'LOC02:sofa','to':'LOC03:desk','kind':'walk','visible':True}]
        self.assertIn('ACTOR_PROP_SCENE_MISMATCH',[x['code'] for x in cc.audit_contract(p)])
    def test_missing_asset_coverage_is_blocked(self):
        p=scenario();p['shots'][1]['continuity_state']['props_after'].pop('PROP_BOOK')
        self.assertIn('STATE_COVERAGE_GAP',[x['code'] for x in cc.audit_contract(p)])
    def test_offscreen_movement_requires_note(self):
        p=scenario();p['shots'][1]['continuity_state']['actor_moves'][0]['visible']=False
        self.assertIn('ELLIPSIS_UNJUSTIFIED',[x['code'] for x in cc.audit_contract(p)])
    def test_offscreen_with_note_requires_review(self):
        p=scenario();p['shots'][1]['continuity_state']['actor_moves'][0].update(visible=False,note='离开沙发走到书桌，故意跳切')
        f=cc.audit_contract(p)
        self.assertFalse(any(x['severity']=='blocker' for x in f),f)
        self.assertIn('ELLIPSIS_REVIEW',[x['code'] for x in f])
    def test_reject_duplicate_move_order(self):
        p=scenario();p['shots'][1]['continuity_state']['prop_moves'][0]['order']=3
        self.assertIn('EVENT_ORDER_DUPLICATED',[x['code'] for x in cc.audit_contract(p)])
