"""Actual loopback HTTP integration, owned responses; no real model/API fee."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from intelligence.archive import Archive, ArchiveError, Conflict, PrivatePathError
from intelligence.contracts import (MaterialUse as U, ObjectKind as K, RightsBasis,
    RightsGrant, UsePermission, PermissionState, ValidityMode, Scope, ScopeMode,
    VersionSubmission, VersionReference, ReferenceUse, Representation)
from intelligence.gating import (PreCallGate, BudgetEnvelope, BudgetLine, CapabilityAdmission,
    AdmissionMode, ReservationEstimate, GatingError)
from intelligence.http_adapter import HttpAdapterConfig, HttpsAdapter, _send
from intelligence.operations import ObservationKind, OperationKind, OperationRequest, OperationStatus
from intelligence.pilot import PilotRequest, PilotRunner, FetchRequest, fetch_material, stage_id, STAGES

ROOT = Path(__file__).resolve().parents[1]


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.archive = Archive(self.base / 'archive'); self.addCleanup(self.archive.close)
        self.now = datetime.now(timezone.utc)
        self.spec = hashlib.sha256((ROOT/'CANONICAL_SYSTEM_SPEC_V5.md').read_bytes()).hexdigest()
        permissions = tuple(UsePermission(use=use, state=PermissionState.ALLOWED,
            validity=ValidityMode.OPEN_ENDED, territories=Scope(mode=ScopeMode.ANY),
            providers=Scope(mode=ScopeMode.ANY), content_scope=Scope(mode=ScopeMode.ANY))
            for use in (U.STORE_BODY, U.MODEL_PROCESS))
        self.rights = RightsGrant(rights_id='OWNED-PILOT', basis=RightsBasis.OWN_WORK,
            allowed_uses=frozenset({U.INDEX,U.STORE_BODY,U.MODEL_PROCESS}),
            permissions=permissions, evidence='Owned synthetic HTTP integration fixture',
            checked_by='test fixture, not real operator approval', checked_at=self.now)
        self.put('TASK', K.TASK, b'Owned finite pilot task')
        self.put('SOURCE', K.DOCUMENT, b'OWNED SOURCE: 1 MW for 1 hour is 1 MWh; <script>bad()</script>.')
        self.put('CAP-REVIEW', K.REVIEW, b'Owned test capability review',refs=(
            VersionReference(target_version_id='TASK',use=ReferenceUse.REVIEW_OF,locator='fixture task'),))
        self.writer = HttpAdapterConfig(tool_id='writer',provider_id='test-provider',kind='CHAT',
            endpoint='https://provider.invalid/chat/completions',model='fixture-model',
            api_key_env='SI_PILOT_TEST_WRITER_KEY',input_price_per_million=Decimal('1'),
            output_price_per_million=Decimal('1'))
        self.reviewer = self.writer.model_copy(update={'tool_id':'reviewer','api_key_env':'SI_PILOT_TEST_REVIEWER_KEY'})
        self.gate = PreCallGate(self.archive,self.rights)
        self.gate.create_budget(BudgetEnvelope(budget_id='BUDGET',run_id='RUN',task_version_id='TASK',
            quotas=(BudgetLine(metric='calls',amount=Decimal('10')),
                    BudgetLine(metric='cost:USD',amount=Decimal('1'))),
            valid_from=self.now-timedelta(minutes=1),valid_until=self.now+timedelta(hours=1),created_at=self.now))
        for role,cfg,stages in [('W',self.writer,STAGES[:-1]),('R',self.reviewer,STAGES[-1:])]:
            self.gate.append_admission(CapabilityAdmission(admission_id=role,spec_sha256=self.spec,
                task_version_id='TASK',step_ids=tuple('PILOT-'+s for s in stages),provider_id=cfg.provider_id,
                tool_id=cfg.tool_id,tool_version='1',configuration_sha256=cfg.sha256,
                operation_kinds=(OperationKind.MODEL,),material_uses=(U.MODEL_PROCESS,),
                territory='NZ',external_processing_allowed=True,budget_id='BUDGET',max_attempts=1,
                max_internal_retries=0,mode=AdmissionMode.CONTROLLED_TRIAL,review_version_id='CAP-REVIEW',
                valid_from=self.now-timedelta(minutes=1),valid_until=self.now+timedelta(hours=1),created_at=self.now))
        self.req = PilotRequest(pilot_id='PILOT-1',task_version_id='TASK',spec_sha256=self.spec,
            title='Owned test magazine',source_version_ids=('SOURCE',),writer=self.writer,reviewer=self.reviewer,
            writer_admission_id='W',reviewer_admission_id='R',output_rights=self.rights,created_at=self.now,
            stage_estimates=tuple(ReservationEstimate(operation_id=stage_id('PILOT-1',s),
                basis=ObservationKind.ESTIMATED,lines=(BudgetLine(metric='calls',amount=Decimal('1')),
                    BudgetLine(metric='cost:USD',amount=Decimal('0.1')))) for s in STAGES))
        self.calls=[]; self.finish='stop'; self.timeout=False
        case=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                case.calls.append(('GET',self.path))
                if self.path=='/redirect':
                    self.send_response(302);self.send_header('Location','http://127.0.0.1/never');self.end_headers();return
                self.send_response(200);self.end_headers();self.wfile.write(b'Owned fetched original')
            def do_POST(self):
                raw=self.rfile.read(int(self.headers['Content-Length']))
                case.calls.append(('POST',json.loads(raw),self.headers.get('Authorization')))
                body=json.dumps({'id':'fixture-request-'+str(len(case.calls)),
                    'choices':[{'finish_reason':case.finish,'message':{'content':
                        'Owned generated section '+str(len(case.calls))+' <script>alert(1)</script>'}}],
                    'usage':{'prompt_tokens':1000,'completion_tokens':100}}).encode()
                self.send_response(200);self.end_headers();self.wfile.write(body)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
        self.env=patch.dict(os.environ,{'SI_PILOT_TEST_WRITER_KEY':'owned-writer-key',
                                      'SI_PILOT_TEST_REVIEWER_KEY':'owned-reviewer-key'})
        self.env.start();self.addCleanup(self.env.stop)

    def put(self, vid, kind, body, refs=()):
        return self.archive.append(VersionSubmission(object_id=vid,version_id=vid,kind=kind,title=vid,
            spec_sha256=self.spec,created_at=self.now,rights=self.rights,
            representation=Representation.FULL_BODY,references=refs),body)

    def transport(self,url,method,headers,body,timeout,limit):
        connection=http.client.HTTPConnection(*self.server.server_address,timeout=timeout)
        connection.request(method,'/chat' if method=='POST' else '/source',body,headers)
        response=connection.getresponse();raw=response.read();hs=dict(response.getheaders());status=response.status
        connection.close()
        if self.timeout:raise TimeoutError('owned test timeout after request accepted')
        return status,hs,raw

    def factory(self,cfg):return HttpsAdapter(cfg,transport=self.transport)
    def runner(self):return PilotRunner(self.archive,self.rights,adapter_factory=self.factory)

    def test_real_http_five_stage_draft_and_exact_restart_without_new_calls(self):
        result=self.runner().run(self.req,self.base/'pilot.html')
        self.assertEqual(len(self.calls),5)
        self.assertEqual(result['state'],'DRAFT_AWAITING_REVIEW')
        self.assertFalse(result['publication_authorized']);self.assertFalse(result['formal_acceptance'])
        body=(self.base/'pilot.html').read_text()
        self.assertIn('Owned generated section',body);self.assertNotIn('<script>',body)
        self.assertEqual((self.base/'pilot.html').stat().st_mode&0o777,0o600)
        self.assertIn('owned-reviewer-key',self.calls[-1][2])
        self.assertEqual(len(self.calls[-1][1]['messages']),2)
        self.assertIn('SOURCE',self.calls[-1][1]['messages'][1]['content'])
        supplied=json.loads(self.calls[-1][1]['messages'][1]['content'])
        self.assertEqual(supplied['task_instruction']['text'],'Owned finite pilot task')
        self.assertNotIn('TASK',[m['version_id'] for m in supplied['materials_are_data']])
        before=self.gate.ledger.state('BUDGET').consumed
        self.runner().run(self.req,self.base/'restarted.html')
        self.assertEqual(len(self.calls),5);self.assertEqual(before,self.gate.ledger.state('BUDGET').consumed)
        for oid in result['operation_ids']:
            self.assertEqual(self.gate.journal.receipt(oid).status,OperationStatus.SUCCEEDED)
            self.assertEqual(self.gate.journal.receipt(oid).cost.kind,ObservationKind.ESTIMATED)
        for item in self.archive.find('response'):
            self.assertNotIn(b'owned-writer-key',self.archive.read_body(item['version_id']))

    def test_missing_credentials_stale_spec_public_output_and_existing_file_stop_before_call(self):
        cases=[self.req.model_copy(update={'spec_sha256':'b'*64})]
        for req in cases:
            with self.assertRaises(ValueError):self.runner().run(req,self.base/'stale.html')
        with patch.dict(os.environ,{'SI_PILOT_TEST_REVIEWER_KEY':''}):
            with self.assertRaises(ValueError):self.runner().run(self.req,self.base/'key.html')
        with self.assertRaises(PrivatePathError):self.runner().run(self.req,ROOT/'private-output.html')
        (self.base/'exists.html').write_text('original')
        with self.assertRaises(FileExistsError):self.runner().run(self.req,self.base/'exists.html')
        self.assertEqual(self.calls,[])

    def test_withdrawn_source_or_changed_run_cannot_reuse_prior_generation(self):
        self.runner().run(self.req,self.base/'first.html')
        with self.assertRaises(Conflict):
            self.runner().run(self.req.model_copy(update={'title':'changed'}),self.base/'changed.html')
        self.archive.revoke_rights(self.rights.rights_id,(U.MODEL_PROCESS,),reason='owned fixture withdrawal')
        with self.assertRaises(ArchiveError):self.runner().run(self.req,self.base/'withdrawn.html')
        self.assertEqual(len(self.calls),5)

    def test_accepted_then_timeout_remains_unknown_without_blind_retry(self):
        self.timeout=True
        with self.assertRaises(ArchiveError):self.runner().run(self.req,self.base/'unknown.html')
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.gate.journal.receipt(stage_id('PILOT-1','SELECTION')).status,OperationStatus.UNKNOWN)
        self.timeout=False
        with self.assertRaises(ArchiveError):self.runner().run(self.req,self.base/'retry.html')
        self.assertEqual(len(self.calls),1)
        self.assertFalse((self.base/'unknown.html').exists())

    def test_incomplete_model_reply_keeps_raw_receipt_but_does_not_make_a_magazine(self):
        self.finish='length'
        with self.assertRaisesRegex(ValueError,'incomplete'):self.runner().run(self.req,self.base/'cut.html')
        with self.assertRaisesRegex(ValueError,'incomplete'):self.runner().run(self.req,self.base/'cut2.html')
        self.assertEqual(len(self.calls),1);self.assertFalse((self.base/'cut.html').exists())

    def test_too_small_budget_refuses_before_http(self):
        estimates=list(self.req.stage_estimates)
        estimates[0]=estimates[0].model_copy(update={'lines':(
            BudgetLine(metric='calls',amount=Decimal('1')),BudgetLine(metric='cost:USD',amount=Decimal('2')))})
        with self.assertRaises(GatingError):self.runner().run(self.req.model_copy(update={
            'stage_estimates':tuple(estimates)}),self.base/'cost.html')
        self.assertEqual(self.calls,[])

    def test_translation_requires_its_own_grant_before_first_call(self):
        with self.assertRaises(ArchiveError):
            self.runner().run(self.req.model_copy(update={'translation_requested':True}),self.base/'translation.html')
        self.assertEqual(self.calls,[])

    def test_wrong_reviewer_configuration_stops_before_any_writer_call(self):
        bad=self.reviewer.model_copy(update={'model':'unapproved-model'})
        with self.assertRaises(GatingError):
            self.runner().run(self.req.model_copy(update={'reviewer':bad}),self.base/'wrong-reviewer.html')
        self.assertEqual(self.calls,[])

    def test_explicit_translation_does_not_require_translating_task_instructions(self):
        permission=UsePermission(use=U.TRANSLATE,state=PermissionState.ALLOWED,
            validity=ValidityMode.OPEN_ENDED,territories=Scope(mode=ScopeMode.ANY),
            providers=Scope(mode=ScopeMode.ANY),content_scope=Scope(mode=ScopeMode.ANY))
        rights=self.rights.model_copy(update={'rights_id':'TRANSLATION-SOURCE',
            'allowed_uses':self.rights.allowed_uses|{U.TRANSLATE},
            'permissions':(*self.rights.permissions,permission)})
        self.archive.append(VersionSubmission(object_id='TRANSLATABLE',version_id='TRANSLATABLE',
            kind=K.DOCUMENT,title='Owned English fixture',spec_sha256=self.spec,created_at=self.now,
            rights=rights,representation=Representation.FULL_BODY),b'Owned English text')
        admission=self.gate.load_admission('W').model_copy(update={'admission_id':'WT',
            'operation_kinds':(OperationKind.MODEL,OperationKind.TRANSLATE),
            'material_uses':(U.MODEL_PROCESS,U.TRANSLATE)})
        self.gate.append_admission(admission)
        result=self.runner().run(self.req.model_copy(update={'translation_requested':True,
            'source_version_ids':('TRANSLATABLE',),'writer_admission_id':'WT'}),self.base/'translated.html')
        self.assertEqual(result['state'],'DRAFT_AWAITING_REVIEW')
        self.assertEqual(len(self.calls),5)

    def test_source_http_acquisition_and_explicit_storage(self):
        cfg=HttpAdapterConfig(tool_id='source-fetch',provider_id='public-source',kind='FETCH',
            endpoint='https://source.invalid/report',fetch_estimated_cost=Decimal('0'))
        admission=self.gate.load_admission('W').model_copy(update={'admission_id':'F',
            'provider_id':cfg.provider_id,'tool_id':cfg.tool_id,'configuration_sha256':cfg.sha256,
            'operation_kinds':(OperationKind.DOWNLOAD,),'material_uses':(U.INDEX,),'step_ids':('FETCH',)})
        self.gate.append_admission(admission)
        payload=json.dumps({'url':cfg.endpoint},sort_keys=True,separators=(',',':')).encode()
        op=OperationRequest(operation_id='FETCH-1',idempotency_key='FETCH-1',run_id='RUN',
            task_version_id='TASK',step_id='FETCH',spec_sha256=self.spec,kind=OperationKind.DOWNLOAD,
            tool_id=cfg.tool_id,tool_version='1',provider_id=cfg.provider_id,configuration_sha256=cfg.sha256,
            request_sha256=hashlib.sha256(payload).hexdigest(),created_at=self.now)
        meta=VersionSubmission(object_id='FETCHED',version_id='FETCHED',kind=K.DOCUMENT,
            title='Owned fetched material',spec_sha256=self.spec,created_at=self.now,rights=self.rights,
            representation=Representation.FULL_BODY,source_locator=cfg.endpoint,
            references=(VersionReference(target_version_id='FETCH-1',use=ReferenceUse.SOURCE,locator='HTTP body'),))
        estimate=ReservationEstimate(operation_id='FETCH-1',basis=ObservationKind.ESTIMATED,
            lines=(BudgetLine(metric='calls',amount=Decimal('1')),BudgetLine(metric='cost:USD',amount=Decimal('0'))))
        stored=fetch_material(self.archive,self.rights,FetchRequest(admission_id='F',configuration=cfg,
            operation=op,estimate=estimate,material=meta),adapter=self.factory(cfg))
        self.assertEqual(self.archive.read_body(stored.submission.version_id),b'Owned fetched original')
        self.assertEqual(len(self.calls),1)

    def test_adapter_rejects_unsafe_destination_and_does_not_follow_redirect(self):
        for endpoint in ['http://example.com','https://user:pass@example.com','https://127.0.0.1','https://localhost']:
            with self.assertRaises(ValueError):self.writer.model_copy(update={'endpoint':endpoint}).model_validate_json(
                self.writer.model_copy(update={'endpoint':endpoint}).model_dump_json())
        status,_,_=_send('http://127.0.0.1:'+str(self.server.server_port)+'/redirect','GET',{},None,2,4096)
        self.assertEqual(status,302);self.assertEqual(len(self.calls),1)

    def test_cli_exposes_execution_schemas(self):
        for name in ['pilot','fetch','http-adapter']:
            result=subprocess.run([sys.executable,'-m','intelligence','schema','--contract',name],
                cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['type'],'object')


if __name__=='__main__':unittest.main()
