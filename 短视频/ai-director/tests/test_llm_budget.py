"""All tests in this file are offline. No paid model or network requests."""
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import local_director as local
import llm_budget as budget


class BudgetSafetyTests(TestCase):
    def session(self, folder, **kwargs):
        values=dict(job=folder,model='deepseek-flash',base_url='https://api.deepseek.com/v1',
                    cap_cny=1.0,input_cny_m=2.0,output_cny_m=8.0,
                    max_calls=3,max_retries=0,max_output_tokens=256)
        values.update(kwargs)
        return budget.BudgetSession(**values)

    def test_requires_explicit_maximum_budget_before_any_api_call(self):
        with tempfile.TemporaryDirectory() as t:
            source=Path(t)/'source.md';source.write_text('测试',encoding='utf8')
            args=SimpleNamespace(input=str(source),out=str(Path(t)/'job'),approve_model_cost=True,
                model='deepseek-flash',base_url='https://api.deepseek.com/v1',resume=False)
            with patch.dict(local.os.environ,{'AI_API_KEY':'NOT_A_REAL_KEY'}), patch.object(local,'llm_json') as api:
                with self.assertRaisesRegex(local.DirectorError, '--max-cost-cny'):
                    local.run_job(args)
                api.assert_not_called()

    def test_rejects_budget_smaller_than_next_full_response_reservation(self):
        with tempfile.TemporaryDirectory() as t:
            b=self.session(Path(t),cap_cny=0.00001)
            try:
                calls=[]
                with self.assertRaisesRegex(budget.BudgetError,'超过上限'):
                    b.invoke(stage='series',system='JSON',user='测试',caller=lambda h:calls.append(True))
                self.assertEqual(calls,[])
                self.assertEqual(b.data['attempts'],[])
            finally:b.close()

    def test_retries_empty_json_once_with_two_budget_reservations(self):
        with tempfile.TemporaryDirectory() as t:
            b=self.session(Path(t),max_retries=1,max_calls=2)
            try:
                attempts=[]
                def caller(hook):
                    attempts.append(1)
                    if len(attempts)==1:raise budget.RetryableLLMError('empty output')
                    return {'good':True}
                actual=b.invoke(stage='ep01.direction',system='JSON',user='中文',caller=caller)
                self.assertEqual(actual,{'good':True})
                self.assertEqual(len(attempts),2)
                self.assertEqual([a['state'] for a in b.data['attempts']], ['retryable_failure','completed'])
                self.assertGreater(b.reserved_cny(),0)
            finally:b.close()

    def test_network_timeout_never_retries_even_with_max_retries_two(self):
        with tempfile.TemporaryDirectory() as t:
            b=self.session(Path(t),max_retries=2)
            tries=[]
            try:
                def fail(hook):
                    tries.append(1)
                    raise TimeoutError('may have reached server')
                with self.assertRaises(TimeoutError):
                    b.invoke(stage='series',system='JSON',user='文本',caller=fail)
                self.assertEqual(len(tries),1)
                self.assertEqual(b.data['attempts'][0]['state'],'failure_or_unknown_charge')
            finally:b.close()

    def test_attempt_limit_also_applies_to_retry(self):
        with tempfile.TemporaryDirectory() as t:
            b=self.session(Path(t),max_retries=2,max_calls=1)
            try:
                calls=[]
                def fail(hook):
                    calls.append(1)
                    raise budget.RetryableLLMError('empty')
                with self.assertRaisesRegex(budget.BudgetError,'调用次数已达上限'):
                    b.invoke(stage='series',system='JSON',user='文本',caller=fail)
                self.assertEqual(len(calls),1)
            finally:b.close()

    def test_spend_reservation_survives_restart_and_same_model_price_lock(self):
        with tempfile.TemporaryDirectory() as t:
            b=self.session(Path(t),max_calls=2)
            b.invoke(stage='series',system='JSON',user='中文',caller=lambda hook:{'ok':1})
            old=b.reserved_cny()
            b.close()
            resumed=self.session(Path(t),max_calls=2)
            try:
                self.assertEqual(len(resumed.data['attempts']),1)
                self.assertEqual(resumed.reserved_cny(),old)
            finally:resumed.close()
            with self.assertRaisesRegex(budget.BudgetError,'配置与现有费用账本不一致'):
                self.session(Path(t),output_cny_m=9.0)

    def test_concurrent_same_job_refused_before_call(self):
        with tempfile.TemporaryDirectory() as t:
            first=self.session(Path(t))
            try:
                with self.assertRaisesRegex(budget.BudgetError,'另一个API导演任务'):
                    self.session(Path(t))
            finally:first.close()

    def test_deepseek_price_guard_and_unknown_provider_guard(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(budget.BudgetError,'不能低于'):
                self.session(Path(t),input_cny_m=0.01)
            with self.assertRaisesRegex(budget.BudgetError,'第三方或未知模型'):
                self.session(Path(t),model='unverified-model')

    def test_true_usage_metadata_is_recorded_without_storing_prompt_text(self):
        with tempfile.TemporaryDirectory() as t:
            b=self.session(Path(t))
            try:
                def successful(hook):
                    hook({'prompt_tokens':102, 'completion_tokens':40,'total_tokens':142})
                    return {'success':True}
                b.invoke(stage='series',system='JSON',user='私密导演内容',caller=successful)
                a=b.data['attempts'][0]
                self.assertEqual(a['provider_usage']['total_tokens'],142)
                self.assertNotIn('私密导演内容',Path(t,'api_usage.generated.json').read_text(encoding='utf-8'))
            finally:b.close()

    def test_full_pipeline_stops_at_call_cap_then_resume_without_repeating_series(self):
        import copy
        with tempfile.TemporaryDirectory() as t:
            source=Path(t)/'input.md';source.write_text('戒烟，越早越好：简短长文样例',encoding='utf-8')
            job=Path(t)/'job'
            args=SimpleNamespace(input=str(source),out=str(job),approve_model_cost=True,
                max_cost_cny=10.0,max_calls=1,max_retries=0,max_output_tokens=16384,
                model='deepseek-flash',base_url='https://api.deepseek.com/v1',resume=False)
            from test_local_director import LocalDirectorV03Tests
            fixtures=LocalDirectorV03Tests
            fixtures.setUpClass()
            fixture_series=copy.deepcopy(fixtures.series)
            fixture_base=copy.deepcopy(fixtures.base)
            fixture_direction=copy.deepcopy(fixtures.direction)
            with patch.dict(local.os.environ,{'AI_API_KEY':'TEST-KEY'}):
                with patch.object(local,'llm_json',side_effect=[fixture_series]) as mock_model:
                    with self.assertRaisesRegex(budget.BudgetError,'调用次数已达上限'):
                        local.run_job(args)
                    self.assertEqual(mock_model.call_count,1)
            self.assertTrue((job/'series.json').exists())
            self.assertFalse((job/'episodes/ep01/plan.json').exists())
            self.assertEqual(len(local.load(job/'api_usage.generated.json')['attempts']),1)
            args.resume=True;args.max_calls=3
            with patch.dict(local.os.environ,{'AI_API_KEY':'TEST-KEY'}):
                with patch.object(local,'llm_json',side_effect=[fixture_base,fixture_direction]) as model:
                    local.run_job(args)
                    self.assertEqual(model.call_count,2)
            self.assertTrue((job/'index.html').exists())
            ledger=local.load(job/'api_usage.generated.json')
            self.assertEqual([a['stage'] for a in ledger['attempts']],['series','ep01.plan','ep01.direction'])
            self.assertEqual(len(ledger['attempts']),3)

    def test_llm_json_parses_response_and_calls_usage_hook_no_network(self):
        payload={'choices':[{'finish_reason':'stop','message':{'content':'{"series_title":"test"}'}}],
                 'usage':{'prompt_tokens':10,'completion_tokens':9,'total_tokens':19}}
        reported=[]
        fake=io.BytesIO(json.dumps(payload).encode('utf-8'))
        with patch.object(local.urllib.request,'urlopen',return_value=fake) as urlopen:
            actual=local.llm_json(system='JSON',user='hello',model='deepseek-flash',
                url='https://api.deepseek.com/v1',key='TEST-KEY',max_tokens=400,
                usage_hook=reported.append)
        self.assertEqual(actual['series_title'],'test')
        self.assertEqual(reported[0]['total_tokens'],19)
        self.assertEqual(urlopen.call_args.kwargs['timeout'],160)

    def test_llm_json_empty_output_retryable_and_5xx_not_retryable(self):
        payload={'choices':[{'finish_reason':'stop','message':{'content':''}}],
                 'usage':{'prompt_tokens':30,'completion_tokens':5}}
        with patch.object(local.urllib.request,'urlopen',return_value=io.BytesIO(json.dumps(payload).encode())):
            with self.assertRaises(budget.RetryableLLMError):
                local.llm_json(system='JSON',user='x',model='deepseek-flash',url='https://api.deepseek.com/v1',key='test')
        err=HTTPError('https://api.deepseek.com/v1/chat/completions',503,'unavailable',{},None)
        with patch.object(local.urllib.request,'urlopen',side_effect=err):
            with self.assertRaises(local.DirectorError):
                local.llm_json(system='JSON',user='x',model='deepseek-flash',url='https://api.deepseek.com/v1',key='test')

    def test_no_approval_or_budget_change_on_resume_silently(self):
        with tempfile.TemporaryDirectory() as t:
            b=self.session(Path(t),cap_cny=1.0)
            b.invoke(stage='series',system='JSON',user='中文',caller=lambda h:{'x':1})
            spent=b.reserved_cny();b.close()
            with self.assertRaisesRegex(budget.BudgetError,'新预算低于'):
                self.session(Path(t),cap_cny=spent/2)

class LocalHTTPContractTests(TestCase):
    def test_real_http_roundtrip_against_local_fake_chat_completions(self):
        """Uses actual HTTP transport to localhost, no DeepSeek account/API."""
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        seen=[]
        class FakeDeepSeek(BaseHTTPRequestHandler):
            def do_POST(self):
                raw=self.rfile.read(int(self.headers['Content-Length']))
                req=json.loads(raw)
                seen.append({'path':self.path,'model':req['model'], 'tokens':req['max_tokens']})
                payload=json.dumps({'choices':[{'finish_reason':'stop','message':{'content':'{"ok":true,"three_episodes":3}'}}],
                    'usage':{'prompt_tokens':77,'completion_tokens':18,'total_tokens':95}}).encode()
                self.send_response(200)
                self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            def log_message(self, *args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),FakeDeepSeek)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            usage=[]
            response=local.llm_json(system='Please return JSON',user='Make story plan',
                model='deepseek-flash',url=f'http://127.0.0.1:{server.server_port}/v1',
                key='LOCAL_TEST_KEY',max_tokens=777,usage_hook=usage.append)
            self.assertEqual(response['three_episodes'],3)
            self.assertEqual(seen,[{'path':'/v1/chat/completions','model':'deepseek-flash','tokens':777}])
            self.assertEqual(usage[0]['total_tokens'],95)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=4)

class RepairWorkflowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        from test_local_director import LocalDirectorV03Tests
        LocalDirectorV03Tests.setUpClass()
        cls.fixtures=LocalDirectorV03Tests

    def args(self, tmp, **updates):
        src=Path(tmp)/'input.md';src.write_text('戒烟，越早越好：科学而克制地讲清楚。',encoding='utf-8')
        values=dict(input=str(src),out=str(Path(tmp)/'job'),approve_model_cost=True,
           model='deepseek-flash',base_url='https://api.deepseek.com/v1',resume=False,
           max_cost_cny=10.0,max_calls=4,max_retries=1,max_output_tokens=16384)
        values.update(updates)
        return SimpleNamespace(**values)

    def test_structurally_invalid_episode_is_repaired_only_in_generated_draft(self):
        import copy
        with tempfile.TemporaryDirectory() as t:
            args=self.args(t)
            results=[copy.deepcopy(self.fixtures.series),{'title':'valid JSON but missing shots'},
                copy.deepcopy(self.fixtures.base),copy.deepcopy(self.fixtures.direction)]
            with patch.dict(local.os.environ,{'AI_API_KEY':'TEST-KEY'}),patch.object(local,'llm_json',side_effect=results) as llm:
                local.run_job(args)
                self.assertEqual(llm.call_count,4)
            self.assertTrue((Path(t)/'job/index.html').exists())
            ledger=local.load(Path(t)/'job/api_usage.generated.json')
            self.assertEqual([a['stage'] for a in ledger['attempts']],
                ['series','ep01.plan','ep01.plan.repair','ep01.direction'])

    def test_insufficient_budget_for_semantic_repair_preserves_original_draft(self):
        import copy
        with tempfile.TemporaryDirectory() as t:
            args=self.args(t,max_calls=2)
            results=[copy.deepcopy(self.fixtures.series),{'bad_plan':'JSON is valid, schema is not'}]
            with patch.dict(local.os.environ,{'AI_API_KEY':'TEST-KEY'}),patch.object(local,'llm_json',side_effect=results) as llm:
                with self.assertRaisesRegex(budget.BudgetError,'调用次数已达上限'):
                    local.run_job(args)
                self.assertEqual(llm.call_count,2)
            job=Path(t)/'job'
            self.assertTrue((job/'episodes/ep01/draft_invalid.json').exists())
            self.assertFalse((job/'episodes/ep01/plan.json').exists())
            self.assertEqual(len(local.load(job/'api_usage.generated.json')['attempts']),2)

    def test_structurally_invalid_series_can_be_repaired_within_cap(self):
        import copy
        with tempfile.TemporaryDirectory() as t:
            args=self.args(t)
            results=[{'episodes':[]},copy.deepcopy(self.fixtures.series),
                copy.deepcopy(self.fixtures.base),copy.deepcopy(self.fixtures.direction)]
            with patch.dict(local.os.environ,{'AI_API_KEY':'TEST-KEY'}),patch.object(local,'llm_json',side_effect=results) as llm:
                local.run_job(args)
                self.assertEqual(llm.call_count,4)
            self.assertTrue((Path(t)/'job/series.json').exists())