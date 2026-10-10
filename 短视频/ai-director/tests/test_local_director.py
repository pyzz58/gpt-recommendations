import copy
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import local_director as local


class LocalDirectorV03Tests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = local.load(ROOT / 'examples/quit-smoking/plan.json')
        cls.direction = local.load(ROOT / 'examples/quit-smoking/direction_v02.json')
        cls.series = {
            'series_title': '戒烟，越早越好',
            'episodes': [{'title': '戒烟的收益', 'core_message': '越早戒烟越好',
                          'narrative_arc': '犹豫到行动', 'content_focus': '钱与健康', 'target_seconds': 53}],
            'characters': copy.deepcopy(cls.base['characters']),
            'visual_bible': copy.deepcopy(cls.base['visual_bible'])
        }

    def test_prepare_is_offline_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)/'source.md'
            src.write_text('长文案',encoding='utf-8')
            dest=Path(t)/'job'
            local.create_prepare(src,dest)
            self.assertIn('Codex', (dest/'CODEX_TASK.md').read_text())
            self.assertTrue((dest/'source.md').exists())
            with self.assertRaises(local.DirectorError):local.create_prepare(src,dest)

    def test_series_disallows_unbounded_cost(self):
        s=copy.deepcopy(self.series)
        s['episodes'] *= 4
        with self.assertRaises(local.DirectorError):local.check_series(s)

    def test_high_impact_claims_remain_unverified_even_with_url(self):
        p=copy.deepcopy(self.base)
        p['claims'][0]['status']='verified'
        p['claims'][0]['evidence_url']='https://doi.org/demo'
        local.warn_publishing(p)
        self.assertEqual(p['claims'][0]['status'],'needs_review')
        self.assertEqual(p['production']['publishing_status'],'review_required')

    def test_character_identity_must_match_series(self):
        p=copy.deepcopy(self.base)
        p['characters'][0]['description']='a different person'
        err,_=local.check_episode_against_series(p,self.series)
        self.assertTrue(any('外形描述发生变化' in e for e in err))

    def test_no_api_request_without_explicit_permission(self):
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)/'input.md'
            src.write_text('戒烟',encoding='utf-8')
            args=SimpleNamespace(input=str(src),out=str(Path(t)/'job'),approve_model_cost=False,
                model='deepseek-flash',base_url='https://api.deepseek.com/v1',resume=False)
            with patch.dict(os.environ,{'AI_API_KEY':'fake-test-key'}):
                with patch.object(local,'llm_json') as fn:
                    with self.assertRaises(local.DirectorError):local.run_job(args)
                    fn.assert_not_called()

    def test_mocked_api_full_run_and_offline_review(self):
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)/'source.md'
            src.write_text('戒烟，越早越好\n含若干研究证据',encoding='utf-8')
            job=Path(t)/'testproject'
            args=SimpleNamespace(input=str(src),out=str(job),approve_model_cost=True,
                model='deepseek-flash',base_url='https://api.deepseek.com/v1',resume=False)
            responses=[copy.deepcopy(self.series),copy.deepcopy(self.base),copy.deepcopy(self.direction)]
            with patch.dict(os.environ,{'AI_API_KEY':'fake-test-key'}):
                with patch.object(local,'llm_json',side_effect=responses) as model:
                    local.run_job(args)
                    self.assertEqual(model.call_count,3)
            self.assertTrue((job/'index.html').exists())
            self.assertTrue((job/'character_bible.json').exists())
            self.assertTrue((job/'episodes/ep01/prompts.json').exists())
            self.assertFalse(local.load(job/'review_status.json')['publishing_allowed'])
            # resume should make zero paid calls if phases already persisted
            args.resume=True
            with patch.dict(os.environ,{'AI_API_KEY':'fake-test-key'}):
                with patch.object(local,'llm_json') as model:
                    local.run_job(args)
                    model.assert_not_called()
            self.assertIn('导演预演',local.review_job(job).read_text(encoding='utf-8'))

    def test_model_api_rejects_unsafe_endpoint(self):
        with self.assertRaises(local.DirectorError):
            local.llm_json(system='JSON',user='x',model='whatever',url='http://example.com/v1',key='abc')

    def test_backup_excludes_credentials(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'project'
            root.mkdir()
            (root/'AGENTS.md').write_text('test',encoding='utf-8')
            (root/'.env').write_text('API_KEY=SECRET',encoding='utf-8')
            archive=Path(t)/'backup.zip'
            n,digest=local.backup(root,archive)
            import zipfile
            with zipfile.ZipFile(archive) as z:
                self.assertIn('AGENTS.md',z.namelist())
                self.assertNotIn('.env',z.namelist())
            self.assertEqual(len(digest),64)

    def test_reference_card_must_be_short_and_credible(self):
        p=copy.deepcopy(self.base)
        p['shots'].append({
            'id':'S09','purpose':'sources','duration':5,'narration':'',
            'visual_type':'text_card','claim_ids':['C01','C02']
        })
        local.check_reference_card(p)
        p['shots'][-1]['duration']=10
        with self.assertRaises(local.DirectorError):local.check_reference_card(p)

if __name__=='__main__':
    import unittest
    unittest.main()