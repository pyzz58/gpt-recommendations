import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import director_v2 as v2

class ProfessionalDirectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=v2.read_json(ROOT/'examples/quit-smoking/plan.json')
        cls.direction=v2.read_json(ROOT/'examples/quit-smoking/direction_v02.json')

    def test_professional_example_structurally_valid_but_publish_blocked(self):
        errors,warnings=v2.validate(self.base,self.direction)
        self.assertEqual(errors, [])
        self.assertTrue(any('PUBLISH BLOCKED' in w for w in warnings))

    def test_scaffold_is_not_presented_as_a_finished_direction(self):
        draft=v2.scaffold(self.base)
        errors,_=v2.validate(self.base,draft)
        self.assertTrue(any('placeholder' in e for e in errors))

    def test_invalid_beat_gap_rejected(self):
        d=copy.deepcopy(self.direction)
        d['shots'][0]['beats'][1]['from_s']+=0.5
        errors,_=v2.validate(self.base,d)
        self.assertTrue(any('gap/overlap' in e for e in errors))

    def test_beat_durations_must_cover_entire_shot(self):
        d=copy.deepcopy(self.direction)
        d['shots'][7]['beats'][-1]['to_s']-=1
        errors,_=v2.validate(self.base,d)
        self.assertTrue(any('beat timeline' in e for e in errors))

    def test_mismatched_claim_ids_rejected(self):
        d=copy.deepcopy(self.direction)
        d['shots'][5]['graphics']['claims_used']=[]
        errors,_=v2.validate(self.base,d)
        self.assertTrue(any('claims_used must match' in e for e in errors))

    def test_paid_execution_route_rejected(self):
        d=copy.deepcopy(self.direction)
        d['shots'][0]['generation']['route']='paid_video_generation'
        errors,_=v2.validate(self.base,d)
        self.assertTrue(any('disallowed execution route' in e for e in errors))

    def test_camera_move_trigger_must_be_inside_shot(self):
        d=copy.deepcopy(self.direction)
        d['shots'][0]['camera']['move_trigger_s']=100
        errors,_=v2.validate(self.base,d)
        self.assertTrue(any('trigger outside shot' in e for e in errors))

    def test_professional_compiler_only_requests_two_ai_clips(self):
        package=v2.compile_package(self.base,self.direction)
        ai=[j for j in package['shots'] if j['prompts']]
        non_ai=[j for j in package['shots'] if not j['prompts']]
        self.assertEqual([j['shot_id'] for j in ai],['S01','S08'])
        self.assertEqual(len(non_ai),6)
        self.assertIn('3.1',ai[0]['prompts']['wan'])
        self.assertIn('Final state',ai[0]['prompts']['seedance'])
        self.assertFalse(package['publishing_allowed'])
        self.assertTrue(package['not_generated_video'])

    def test_specificity_per_shot(self):
        for direction in self.direction['shots']:
            self.assertGreaterEqual(len(direction['beats']),3)
            self.assertGreaterEqual(len(direction['qa']['acceptance_tests']),3)
            self.assertFalse(direction['qa']['human_approved'])
            self.assertNotIn('待填',str(direction))

    def test_preview_escapes_html(self):
        b=copy.deepcopy(self.base)
        b['title']='<script>attack()</script>'
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'review.html'
            v2.render_compare(b,self.direction,out)
            contents=out.read_text(encoding='utf-8')
            self.assertNotIn('<script>attack()',contents)
            self.assertIn('&lt;script&gt;',contents)
            self.assertIn('不是真正的视频',contents)

    def test_cli_validate_compile_preview_offline(self):
        with tempfile.TemporaryDirectory() as d:
            v=Path(d)
            command=[sys.executable,str(ROOT/'director_v2.py')]
            base=str(ROOT/'examples/quit-smoking/plan.json')
            direction=str(ROOT/'examples/quit-smoking/direction_v02.json')
            for task,ext in [('validate',None),('compile','prompts.json'),('preview','preview.html')]:
                cmd=command+[task,'--base',base,'--direction',direction]
                if ext: cmd+=['--out',str(v/ext)]
                p=subprocess.run(cmd,text=True,capture_output=True)
                self.assertEqual(p.returncode,0,p.stdout+p.stderr)
                if ext:self.assertTrue((v/ext).exists())

    def test_codex_task_is_offline_and_does_not_change_model(self):
        task=v2.build_codex_task('base.json','direction.json')
        self.assertIn('DeepSeek',task)
        self.assertIn('不要更改模型',task)
        self.assertIn('不触发付费',task) if '不触发付费' in task else self.assertIn('不调用付费',task)


    def test_long_script_compact_credit_examples(self):
        for episode in ("ep01-attention","ep02-sleep","ep03-emotions"):
            folder=ROOT/"examples"/"energy-trilogy"/episode
            base=v2.read_json(folder/"plan.json")
            directions=v2.read_json(folder/"direction_v02.json")
            errors,warnings=v2.validate(base,directions)
            self.assertEqual(errors, [], f"{episode}: {errors}")
            card=base["shots"][-1]
            self.assertEqual(card["purpose"],"sources")
            self.assertEqual(card["visual_type"],"text_card")
            self.assertEqual(card["duration"],5)
            self.assertEqual(card["narration"],"")
            self.assertGreaterEqual(len(card["claim_ids"]),2)
            self.assertLessEqual(len(card["claim_ids"]),3)
            self.assertEqual(len(base["shots"]),9)
            self.assertTrue(any("PUBLISH BLOCKED" in w for w in warnings))
            self.assertFalse(v2.compile_package(base,directions)["publishing_allowed"])

    def test_credits_reject_six_seconds_even_with_matching_timeline(self):
        folder=ROOT/"examples"/"energy-trilogy"/"ep01-attention"
        base=v2.read_json(folder/"plan.json")
        directions=v2.read_json(folder/"direction_v02.json")
        base["shots"][-1]["duration"]=6
        base["duration"]+=1
        directions["shots"][-1]["beats"][-1]["to_s"]=6
        errors,_=v2.validate(base,directions)
        self.assertTrue(any("source credit card must be 5 seconds" in e for e in errors))

    def test_credits_reject_more_than_three_sources(self):
        folder=ROOT/"examples"/"energy-trilogy"/"ep01-attention"
        base=v2.read_json(folder/"plan.json")
        directions=v2.read_json(folder/"direction_v02.json")
        extra="S02"
        base["shots"][-1]["claim_ids"].append(extra)
        directions["shots"][-1]["graphics"]["claims_used"].append(extra)
        errors,_=v2.validate(base,directions)
        self.assertTrue(any("show 2-3 primary research" in e for e in errors))

if __name__=='__main__':
    unittest.main()