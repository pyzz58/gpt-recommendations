import copy
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
import llm_budget

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
            args=SimpleNamespace(input=str(src),out=str(job),approve_model_cost=True,max_cost_cny=10.0,
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
        p['references'] = [
            {'claim_id': cid, 'author': 'Fixture Author', 'year': 2020, 'journal': 'Test Journal',
             'study_type': 'test study', 'url': f'https://example.org/{cid}', 'status':'needs_review'}
            for cid in ('C01','C02')
        ]
        local.check_reference_card(p)
        p['shots'][-1]['duration']=10
        with self.assertRaises(local.DirectorError):local.check_reference_card(p)


    def test_source_card_rejects_missing_metadata_and_unverified_citation(self):
        p=copy.deepcopy(self.base)
        p['shots'].append({'id':'S09','purpose':'sources','duration':5,'narration':'',
                          'visual_type':'text_card','claim_ids':['C01','C02']})
        with self.assertRaisesRegex(local.DirectorError, 'references'):
            local.check_reference_card(p)
        p['references']=[{'claim_id':c,'author':'Researcher','year':2020,'journal':'Journal',
                          'study_type':'randomized trial','url':'https://example.org/'+c,
                          'status':'needs_review'} for c in ('C01','C02')]
        local.check_reference_card(p)
        p['references'][0]['status']='verified'
        with self.assertRaisesRegex(local.DirectorError, 'needs_review'):
            local.check_reference_card(p)
        p['references'][0]['status']='needs_review'
        p['references'][1]['url']='http://example.org/paper'
        with self.assertRaisesRegex(local.DirectorError, 'HTTPS'):
            local.check_reference_card(p)

    def test_source_card_rejects_duplicate_and_missing_claim(self):
        p=copy.deepcopy(self.base)
        p['shots'].append({'id':'S09','purpose':'sources','duration':5,'narration':'',
                          'visual_type':'text_card','claim_ids':['C01','C01']})
        with self.assertRaisesRegex(local.DirectorError, '不重复'):
            local.check_reference_card(p)
        p['shots'][-1]['claim_ids']=['C01','DNE']
        p['references']=[{'claim_id':c,'author':'Researcher','year':2020,'journal':'Journal',
                          'study_type':'trial','url':'https://example.org/'+c,'status':'needs_review'}
                         for c in ('C01','DNE')]
        with self.assertRaisesRegex(local.DirectorError, '没有同时出现在'):
            local.check_reference_card(p)

    def test_scene_wardrobe_identity_and_global_style_cannot_drift(self):
        for char_key in ('wardrobe','identity_anchor'):
            p=copy.deepcopy(self.base)
            p['characters'][0][char_key]='Changed / wrong'
            errors,_=local.check_episode_against_series(p,self.series)
            self.assertTrue(any('跨集角色' in msg for msg in errors),char_key)
        p=copy.deepcopy(self.base)
        p['visual_bible']['palette']='Neon green'
        errors,_=local.check_episode_against_series(p,self.series)
        self.assertTrue(any('visual_bible.palette' in msg for msg in errors))

    def test_review_does_not_destroy_human_metadata_or_prompts(self):
        with tempfile.TemporaryDirectory() as t:
            job=Path(t)/'job';ep=job/'episodes'/'ep01';ep.mkdir(parents=True)
            local.save(job/'series.json',copy.deepcopy(self.series))
            local.save(ep/'plan.json',copy.deepcopy(self.base))
            local.save(ep/'direction_v02.json',copy.deepcopy(self.direction))
            local.review_job(job)
            protected='## My verified notes from primary paper - do not erase\n'
            (ep/'description.md').write_text(protected,encoding='utf8')
            (ep/'prompts.json').write_text('MY CUSTOM PROMPTS',encoding='utf8')
            status=local.load(job/'review_status.json');status['manual_notes']='Approved by editor';local.save(job/'review_status.json',status)
            local.review_job(job)
            self.assertEqual((ep/'description.md').read_text(encoding='utf8'),protected)
            self.assertEqual((ep/'prompts.json').read_text(encoding='utf8'),'MY CUSTOM PROMPTS')
            self.assertEqual(local.load(job/'review_status.json')['manual_notes'],'Approved by editor')
            self.assertTrue((ep/'description.generated.md').exists())
            self.assertTrue((ep/'prompts.generated.json').exists())
            self.assertTrue((job/'review_status.generated.json').exists())

    def test_resume_preserves_approved_character_bible_and_manual_status(self):
        with tempfile.TemporaryDirectory() as t:
            source=Path(t)/'source.md';source.write_text('health information',encoding='utf8')
            job=Path(t)/'job'
            args=SimpleNamespace(input=str(source),out=str(job),approve_model_cost=True,max_cost_cny=10.0,
                model='deepseek-flash',base_url='https://api.deepseek.com/v1',resume=False)
            with patch.dict(os.environ,{'AI_API_KEY':'TEST-KEY'}):
                with patch.object(local,'llm_json',side_effect=[copy.deepcopy(self.series),copy.deepcopy(self.base),copy.deepcopy(self.direction)]):
                    local.run_job(args)
            bible=local.load(job/'character_bible.json')
            bible['approved']=True;bible['custom_notes']='User selected this face'
            local.save(job/'character_bible.json',bible)
            status=local.load(job/'status.json');status['phase']='manually_reviewed';status['custom_notes']='Never overwrite this approval'
            local.save(job/'status.json',status)
            args.resume=True
            with patch.dict(os.environ,{'AI_API_KEY':'TEST-KEY'}):
                with patch.object(local,'llm_json') as llm:
                    local.run_job(args)
                    llm.assert_not_called()
            self.assertTrue(local.load(job/'character_bible.json')['approved'])
            self.assertEqual(local.load(job/'character_bible.json')['custom_notes'],'User selected this face')
            self.assertEqual(local.load(job/'status.json')['phase'],'manually_reviewed')
            self.assertEqual(local.load(job/'status.json')['custom_notes'],'Never overwrite this approval')
            bible['characters'][0]['wardrobe']='New user-approved white outfit'
            local.save(job/'character_bible.json',bible)
            with patch.dict(os.environ,{'AI_API_KEY':'TEST-KEY'}):
                with patch.object(local,'llm_json') as llm:
                    with self.assertRaisesRegex(local.DirectorError,'服装'):
                        local.run_job(args)
                    llm.assert_not_called()
            self.assertEqual(local.load(job/'character_bible.json')['characters'][0]['wardrobe'],'New user-approved white outfit')

    def test_malformed_generated_episode_does_not_count_as_success_and_resume(self):
        with tempfile.TemporaryDirectory() as t:
            source=Path(t)/'source.md';source.write_text('healthy sleeping habits',encoding='utf8')
            job=Path(t)/'job';args=SimpleNamespace(input=str(source),out=str(job),approve_model_cost=True,max_cost_cny=10.0,
                model='deepseek-flash',base_url='https://api.deepseek.com/v1',resume=False)
            with patch.dict(os.environ,{'AI_API_KEY':'TEST-KEY'}):
                with patch.object(local,'llm_json',side_effect=[copy.deepcopy(self.series), {'garbled':'broken'}]):
                    with self.assertRaises(local.DirectorError):local.run_job(args)
            self.assertTrue((job/'series.json').exists())
            self.assertTrue((job/'episodes/ep01/draft_invalid.json').exists())
            self.assertFalse((job/'episodes/ep01/plan.json').exists())
            args.resume=True
            with patch.dict(os.environ,{'AI_API_KEY':'TEST-KEY'}):
                with patch.object(local,'llm_json',side_effect=[copy.deepcopy(self.base),copy.deepcopy(self.direction)]) as fn:
                    local.run_job(args)
                    self.assertEqual(fn.call_count,2)
            self.assertTrue((job/'index.html').exists())

    def test_real_length_chinese_article_browser_post_no_http_400(self):
        import threading
        from http.server import ThreadingHTTPServer
        from urllib.parse import urlencode
        from urllib.request import urlopen, Request
        import local_ui
        with tempfile.TemporaryDirectory() as t:
            sample='# 不要浪费精力\n'+('研究、注意力与睡眠：每天都要合理安排。\n'*1100)
            self.assertGreater(len(urlencode({'slug':'energy2026','article':sample}).encode()),130000)
            with patch.object(local_ui,'JOBS',Path(t)):
                server=ThreadingHTTPServer(('127.0.0.1',0),local_ui.App)
                server.daemon_threads=True
                server.log_message=lambda *args,**kwargs:None
                th=threading.Thread(target=server.serve_forever,daemon=True);th.start()
                try:
                    port=server.server_port
                    data=urlencode({'slug':'energy2026','article':sample}).encode('utf8')
                    req=Request(f'http://127.0.0.1:{port}/prepare',data=data,
                                headers={'Content-Type':'application/x-www-form-urlencoded','Origin':f'http://127.0.0.1:{port}'})
                    with urlopen(req,timeout=8) as response:
                        self.assertEqual(response.status,200)
                    self.assertEqual((Path(t)/'energy2026'/'source.md').read_text(encoding='utf8'),sample)
                finally:
                    server.shutdown();server.server_close();th.join(timeout=3)

    def test_mocked_three_episode_pipeline_with_resume(self):
        with tempfile.TemporaryDirectory() as t:
            input_file=Path(t)/'article.md'
            input_file.write_text('第一部分：注意力；第二部分：睡眠；第三部分：情绪。'*200,encoding='utf-8')
            job=Path(t)/'series-job'
            series=copy.deepcopy(self.series)
            series['episodes']=[dict(e,title=f'第{i}集') for i,e in enumerate([series['episodes'][0]]*3,1)]
            responses=[series]
            for _ in range(3):
                responses.extend([copy.deepcopy(self.base),copy.deepcopy(self.direction)])
            args=SimpleNamespace(input=str(input_file),out=str(job),approve_model_cost=True,max_cost_cny=10.0,
                model='deepseek-flash',base_url='https://api.deepseek.com/v1',resume=False)
            with patch.dict(os.environ,{'AI_API_KEY':'TEST-KEY'}):
                with patch.object(local,'llm_json',side_effect=responses) as llm:
                    local.run_job(args)
                    self.assertEqual(llm.call_count,7)
            self.assertTrue((job/'index.html').exists())
            self.assertEqual(len(local.load(job/'review_status.generated.json')['episodes']),3)
            for index in range(1,4):
                ep=job/'episodes'/f'ep{index:02d}'
                self.assertTrue((ep/'preview.html').exists())
                self.assertTrue((ep/'description.md').exists())
            args.resume=True
            with patch.dict(os.environ,{'AI_API_KEY':'TEST-KEY'}):
                with patch.object(local,'llm_json') as llm:
                    local.run_job(args)
                    llm.assert_not_called()

if __name__=='__main__':
    import unittest
    unittest.main()