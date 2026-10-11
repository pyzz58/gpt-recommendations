"""Offline production-routing regression suite: never calls a video or LLM API."""
import copy
from pathlib import Path
import sys
from unittest import TestCase

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import director_v2 as v2


class ProductionRoutingTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=v2.read_json(ROOT/'examples/quit-smoking/plan.json')
        cls.directions=v2.read_json(ROOT/'examples/quit-smoking/direction_v02.json')
        cls.index=next(i for i,s in enumerate(cls.base['shots']) if s['visual_type']=='ai_video')

    def scenario(self, route='ai_video', method=None):
        direction=copy.deepcopy(self.directions)
        gen=direction['shots'][self.index]['generation']
        gen['route']=route
        if method is not None:
            gen['production_method']=method
        return direction

    def test_explicit_still_overrides_conceptual_ai_video(self):
        d=self.scenario('static_post')
        errors,_=v2.validate(self.base,d)
        self.assertEqual(errors,[])
        job=v2.compile_package(self.base,d)['shots'][self.index]
        self.assertEqual(job['execution_route'],'static_post')
        self.assertEqual(job['prompts'],{})
        self.assertEqual(job['postproduction_job']['voiceover'],self.base['shots'][self.index]['narration'])
        self.assertTrue(job['postproduction_job']['requires_operator_review'])

    def test_legacy_ai_video_route_uses_known_production_method(self):
        d=self.scenario(method='静态图+后期')
        self.assertEqual(v2.validate(self.base,d)[0],[])
        job=v2.compile_package(self.base,d)['shots'][self.index]
        self.assertEqual(job['execution_route'],'static_post')
        self.assertEqual(job['prompts'],{})

    def test_edit_insert_and_lighting_still_have_no_ai_video_prompts(self):
        for method, expected in [('剪辑合成','edit_composite'),('实拍插入','live_action_insert'),
                                 ('静态关键帧+后期灯光','static_post')]:
            with self.subTest(method=method):
                d=self.scenario(method=method)
                self.assertEqual(v2.validate(self.base,d)[0],[])
                result=v2.compile_package(self.base,d)['shots'][self.index]
                self.assertEqual(result['execution_route'],expected)
                self.assertEqual(result['prompts'],{})

    def test_legacy_ai_video_still_generates_candidate_video_prompts(self):
        d=self.scenario()
        job=v2.compile_package(self.base,d)['shots'][self.index]
        self.assertEqual(job['execution_route'],'ai_video')
        self.assertIn('wan',job['prompts'])

    def test_unknown_production_method_fails_closed(self):
        d=self.scenario(method='在后期处理一下')
        errors,_=v2.validate(self.base,d)
        self.assertTrue(any('unrecognized production_method' in e for e in errors))
        with self.assertRaises(ValueError):
            v2.compile_package(self.base,d)

    def test_reject_route_and_method_conflict_or_paid_route(self):
        d=self.scenario('static_post','ai_video')
        self.assertTrue(any('contradicts' in e for e in v2.validate(self.base,d)[0]))
        d=self.scenario('paid_video_generation')
        self.assertTrue(any('disallowed execution route' in e for e in v2.validate(self.base,d)[0]))

    def test_non_video_base_cannot_become_video(self):
        d=copy.deepcopy(self.directions)
        idx=next(i for i,s in enumerate(self.base['shots']) if s['visual_type']!='ai_video')
        d['shots'][idx]['generation']['route']='ai_video'
        self.assertTrue(any('contradicts base' in e for e in v2.validate(self.base,d)[0]))

    def test_nonvideo_contract_never_claims_video_or_license(self):
        d=self.scenario(method='剪辑合成')
        pkg=v2.compile_package(self.base,d)
        self.assertTrue(pkg['not_generated_video'])
        self.assertFalse(pkg['publishing_allowed'])
        job=pkg['shots'][self.index]
        self.assertEqual(job['postproduction_job']['asset_status'],'not_verified')
        self.assertEqual(job['postproduction_job']['voiceover_source'],'base.narration')
