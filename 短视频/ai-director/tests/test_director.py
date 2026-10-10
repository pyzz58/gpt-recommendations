import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import director

class DirectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=director.read_json(ROOT/'examples/quit-smoking/plan.json')

    def test_example_valid_but_publication_blocked(self):
        errors,warnings=director.validate(self.plan)
        self.assertEqual(errors,[])
        self.assertTrue(any('PUBLISH BLOCKED' in x for x in warnings))

    def test_timing_rejects_gaps(self):
        p=copy.deepcopy(self.plan);p['shots'][1]['start']+=1
        e,_=director.validate(p)
        self.assertTrue(any('non-contiguous' in x for x in e))

    def test_claim_refs_reject_unknown(self):
        p=copy.deepcopy(self.plan);p['shots'][1]['claim_ids']=['C99']
        e,_=director.validate(p)
        self.assertTrue(any('unknown claim' in x for x in e))

    def test_no_fake_verified_claim(self):
        p=copy.deepcopy(self.plan);p['claims'][0]['status']='verified'
        e,_=director.validate(p)
        self.assertTrue(any('without evidence_url' in x for x in e))

    def test_ai_video_requires_action_chain(self):
        p=copy.deepcopy(self.plan);p['shots'][0]['action']['reaction']=''
        e,_=director.validate(p)
        self.assertTrue(any('action.reaction' in x for x in e))

    def test_prompts_are_only_generated_for_ai_video(self):
        prompts=director.compile_prompts(self.plan)
        self.assertEqual([x['shot_id'] for x in prompts],['S01','S08'])
        for p in prompts:
            self.assertIn('Do not generate words',p['models']['wan'])
            self.assertIn('seedance',p['models'])

    def test_preview_is_sanitized_and_generated(self):
        p=copy.deepcopy(self.plan);p['title']='<script>alert(1)</script>'
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'preview.html'
            director.render_preview(p,path)
            output=path.read_text(encoding='utf8')
            self.assertNotIn('<script>',output)
            self.assertIn('&lt;script&gt;',output)
            self.assertIn('本预演是文字分镜',output)

    def test_cli_offline_work_packet(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'job'
            result=subprocess.run([sys.executable,str(ROOT/'director.py'),'prepare','--input',str(ROOT/'examples/quit-smoking/input.md'),'--out',str(out)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue((out/'codex_task.md').exists())
            self.assertTrue((out/'source.md').exists())

if __name__=='__main__': unittest.main()
