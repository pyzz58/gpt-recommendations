"""No-cost fail-closed production gate regression tests."""
import copy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import production_gate as gate


def sample():
    return {
      "not_generated_video":True,"publishing_allowed":False,
      "reference_asset_preflight":{"status":"preflight_only","ready_for_reference_preflight":True,
          "blockers":0,"missing":0,"human_visual_consistency_verified":False,"media_generated":False},
      "production_summary":{"ai_video_jobs":1},
      "shots":[{"shot_id":"S01","execution_route":"ai_video","human_review_required":True,
          "direction":{"qa":{"human_approved":True}},"reference_preflight_ready":True,
          "reference_media_supplied":True,"prompts":{"wan":"candidate only"},"postproduction_job":{}}]
    }

class GateTests(unittest.TestCase):
    def test_even_passing_metadata_does_not_authorize_api_or_publication(self):
        r=gate.evaluate(sample())
        self.assertEqual(r["blocker_count"],0)
        self.assertTrue(r["metadata_preflight_passed"])
        self.assertFalse(r["execution_authorized"])
        self.assertFalse(r["paid_api_enabled"])
        self.assertFalse(r["publishing_authorized"])

    def test_current_director_draft_blocked(self):
        p=sample();s=p['shots'][0]
        s['direction']['qa']['human_approved']=False
        s['reference_media_supplied']=False
        p['reference_asset_preflight']['ready_for_reference_preflight']=False
        f={x['code'] for x in gate.evaluate(p)['findings']}
        self.assertEqual(f,{'HUMAN_SHOT_REVIEW_PENDING','REFERENCES_NOT_VERIFIED','REFERENCE_MEDIA_NOT_DELIVERED'})

    def test_missing_reference_catalog_blocked(self):
        p=sample();p.pop('reference_asset_preflight')
        self.assertIn('REFERENCES_NOT_VERIFIED',[f['code'] for f in gate.evaluate(p)['findings']])

    def test_no_review_allowed(self):
        p=sample();p['shots'][0]['human_review_required']=False
        self.assertIn('HUMAN_REVIEW_FLAG_MISSING',[f['code'] for f in gate.evaluate(p)['findings']])

    def test_non_video_ai_prompts_blocked(self):
        p=sample();s=p['shots'][0]
        s['execution_route']='edit_composite';p['production_summary']['ai_video_jobs']=0
        self.assertIn('NON_VIDEO_HAS_VIDEO_PROMPTS',[f['code'] for f in gate.evaluate(p)['findings']])

    def test_missing_work_order_blocked(self):
        p=sample();s=p['shots'][0]
        s['execution_route']='static_post';s.pop('postproduction_job')
        p['production_summary']['ai_video_jobs']=0
        self.assertIn('POSTPRODUCTION_JOB_MISSING',[f['code'] for f in gate.evaluate(p)['findings']])

    def test_forged_safety_flags_blocked(self):
        p=sample();p['publishing_allowed']=True
        self.assertIn('INVALID_SAFETY_FLAGS',[f['code'] for f in gate.evaluate(p)['findings']])

    def test_duplicate_shots_and_wrong_count_blocked(self):
        p=sample();p['shots'].append(copy.deepcopy(p['shots'][0]))
        self.assertIn('INVALID_SHOT_ID',[f['code'] for f in gate.evaluate(p)['findings']])
        p=sample();p['production_summary']['ai_video_jobs']=7
        self.assertIn('PRODUCTION_COUNT_MISMATCH',[f['code'] for f in gate.evaluate(p)['findings']])

    def test_invalid_packages_never_permit_execution(self):
        for item in (None,[],{}, {'shots':["wrong"]}, {"shots":[]}):
            with self.subTest(item=item):
                r=gate.evaluate(item)
                self.assertGreater(r['blocker_count'],0)
                self.assertFalse(r['execution_authorized'])

    def test_not_created_image_preflight_not_trusted(self):
        p=sample();p['reference_asset_preflight']['status']='not_assessed'
        self.assertIn('REFERENCES_NOT_VERIFIED',[f['code'] for f in gate.evaluate(p)['findings']])


    def test_public_example_compiler_attaches_blocked_generation_gate(self):
        import director_v2 as director
        base=director.read_json(ROOT/"examples/quit-smoking/plan.json")
        direction=director.read_json(ROOT/"examples/quit-smoking/direction_v02.json")
        compiled=director.compile_package(base,direction)
        self.assertIn("generation_gate",compiled)
        gate_report=compiled["generation_gate"]
        self.assertGreater(gate_report["blocker_count"],0)
        self.assertFalse(gate_report["execution_authorized"])
        self.assertFalse(gate_report["paid_api_enabled"])
        self.assertFalse(gate_report["publishing_authorized"])
        self.assertEqual(gate_report["shot_count"],len(base["shots"]))

if __name__=='__main__':
    unittest.main()
