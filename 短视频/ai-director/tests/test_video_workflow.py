"""Single-shot operator flow. All media/HTTP are synthetic, never real AI."""
from copy import deepcopy
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import video_workflow as flow
import seedance_adapter as api
import local_director

EXAMPLE = Path(__file__).resolve().parents[1] / 'examples/dinner-dialogue-review'

class VideoWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = json.loads((EXAMPLE/'plan.json').read_text())
        self.direction = json.loads((EXAMPLE/'direction_v02.json').read_text())
        self.state = flow.prepare_job(self.base, self.direction, 'S02', private_dir=self.root,
                                      provider='volcengine', audio_mode='native_dialogue')
        self.packet = api._read(self.root/'proposal.json')
        self.network = patch.object(api, '_request').start(); self.addCleanup(patch.stopall)
        self.network.return_value = {'id': 'synthetic_task'}

    def submit(self):
        return flow.submit_job(self.root, api_key='synthetic-key', approval={
            'request_digest': self.packet['request_digest'], 'rights_reviewed': True,
            'currency': 'CNY', 'quoted_cost': '1', 'max_cost': '2'})

    def saved(self):
        self.submit()
        self.network.return_value = dict(id='synthetic_task', status='succeeded',
                                         model=self.packet['body']['model'],
                                         content={'video_url': 'https://synthetic.tos-cn-beijing.volces.com/secret-url'})
        self.assertEqual(flow.query_job(self.root, api_key='synthetic-key')['state'], 'download_ready')
        raw = b'\x00\x00\x00\x18ftypisomsynthetic-test-only'
        response = Mock(status=200)
        response.getheader.return_value = str(len(raw)); response.read.side_effect = io.BytesIO(raw).read
        conn = Mock(); conn.getresponse.return_value = response
        with patch.object(api.http.client, 'HTTPSConnection', return_value=conn):
            return flow.download_job(self.root)

    def record(self, state, decision='retain_candidate'):
        return dict(request_digest=state['request_digest'], media_sha256=state['media_sha256'],
                    decision=decision, reviewer='synthetic operator declaration, not authenticated',
                    watched_full_clip=True, observed_duration_s=8,
                    checks={x:'pass' for x in flow.CHECKS}, notes='Synthetic assertions only; no genuine viewing occurred.')

    def test_prepare_and_readonly_page_do_not_query_or_generate(self):
        self.assertEqual(self.state['state'], 'prepared')
        page = flow.save_page(self.root)
        source = page.read_text()
        self.assertIn('今天，过得怎么样？', source)
        self.assertIn('尚无已保存的视频', source)
        self.assertNotIn('<video ', source)
        self.assertEqual(page.stat().st_mode & 0o777, 0o600)
        self.assertEqual(flow.save_page(self.root), page)
        self.network.assert_not_called()

    def test_second_prepare_does_not_overwrite_source_bound_proposal(self):
        before = (self.root/'proposal.json').read_bytes()
        with self.assertRaisesRegex(api.SeedanceError, 'NEW_EMPTY_PRIVATE_JOB_REQUIRED'):
            flow.prepare_job(self.base, self.direction, 'S03', private_dir=self.root, provider='volcengine')
        self.assertEqual(before, (self.root/'proposal.json').read_bytes())

    def test_status_remembers_last_poll_but_never_claims_live_status(self):
        self.submit()
        self.network.return_value = {'id':'synthetic_task', 'status':'running'}
        result = flow.query_job(self.root, api_key='synthetic-key')
        self.network.reset_mock()
        self.assertEqual(result['state'], 'running')
        self.assertFalse(flow.inspect_job(self.root)['live_status_checked'])
        self.assertIn('last_query_unix_ns', result)
        self.network.assert_not_called()

    def test_unknown_post_is_visible_and_never_replayed(self):
        self.network.side_effect = api.SeedanceError('synthetic timeout')
        with self.assertRaises(api.SeedanceError): self.submit()
        self.assertEqual(flow.inspect_job(self.root)['state'], 'submission_unknown')
        with self.assertRaises(api.SeedanceError): self.submit()
        self.assertEqual(self.network.call_count, 1)

    def test_completed_flow_binds_human_record_to_video_not_final_film(self):
        state = self.saved()
        self.assertEqual(state['state'], 'review_pending')
        result = flow.record_review(self.root, self.record(state))
        self.assertEqual(result['state'], 'retain_candidate')
        self.assertTrue(result['human_review_recorded'])
        self.assertFalse(result['production_approved'])
        self.assertFalse(result['final_film_completed'])
        page = flow.save_page(self.root).read_text()
        self.assertIn('src="video.mp4"', page)
        self.assertNotIn('secret-url', page)
        self.assertNotIn('synthetic-key', page)
        self.assertEqual([c.args[1] for c in self.network.call_args_list], ['POST', 'GET'])

    def test_review_cannot_be_recorded_without_media(self):
        with self.assertRaisesRegex(api.SeedanceError, 'REVIEW_REQUIRES'):
            flow.record_review(self.root, self.record(self.state))
        self.assertFalse((self.root/'review.json').exists())

    def test_wrong_video_or_unwatched_or_failed_check_cannot_be_retained(self):
        state = self.saved(); record = self.record(state)
        for key, value in [('media_sha256','wrong'), ('watched_full_clip',False), ('observed_duration_s',float('nan'))]:
            candidate = deepcopy(record); candidate[key] = value
            with self.assertRaises(api.SeedanceError): flow.record_review(self.root, candidate)
        candidate = deepcopy(record); candidate['checks']['lip_sync'] = 'fail'
        with self.assertRaisesRegex(api.SeedanceError, 'UNRESOLVED_REVIEW_CHECKS'):
            flow.record_review(self.root, candidate)
        candidate['checks']['lip_sync'] = 'not_applicable'
        with self.assertRaisesRegex(api.SeedanceError, 'NATIVE_DIALOGUE_REVIEW_REQUIRED'):
            flow.record_review(self.root, candidate)
        self.assertFalse((self.root/'review.json').exists())

    def test_revision_records_feedback_without_automatically_resubmitting(self):
        state = self.saved(); record = self.record(state, 'revise')
        record['checks']['lip_sync'] = 'fail'; record['notes'] = 'Synthetic: visible listener speaks; revise speaker control.'
        self.network.reset_mock()
        self.assertEqual(flow.record_review(self.root, record)['state'], 'revise')
        with self.assertRaises(api.SeedanceError): flow.record_review(self.root, record)
        with self.assertRaises(api.SeedanceError): self.submit()
        self.network.assert_not_called()

    def test_altered_video_invalidates_prior_review(self):
        state = self.saved(); flow.record_review(self.root, self.record(state))
        with (self.root/'video.mp4').open('ab') as f: f.write(b'altered')
        with self.assertRaisesRegex(api.SeedanceError, 'MEDIA_BINDING_MISMATCH'): flow.inspect_job(self.root)

    def test_partial_save_never_becomes_reviewable(self):
        self.saved(); (self.root/'media.json').unlink()
        self.assertEqual(flow.inspect_job(self.root)['state'], 'save_incomplete')
        with self.assertRaises(api.SeedanceError): flow.record_review(self.root, {})
        with self.assertRaises(api.SeedanceError): flow.download_job(self.root)

    def test_review_template_is_bound_but_cannot_be_submitted_unfilled(self):
        state = self.saved()
        result = flow.save_review_template(self.root)
        self.assertFalse(result['human_review_recorded'])
        draft = api._read(self.root/'review.draft.json')
        self.assertEqual(draft['media_sha256'], state['media_sha256'])
        with self.assertRaises(api.SeedanceError): flow.record_review(self.root, draft)
        with self.assertRaises(FileExistsError): flow.save_review_template(self.root)

    def test_changed_proposal_after_submit_is_rejected(self):
        self.submit()
        packet = deepcopy(self.packet); packet['shot_id'] = 'S03'; packet.pop('request_digest')
        packet['request_digest'] = api.digest(packet)
        (self.root/'proposal.json').write_text(json.dumps(packet))
        with self.assertRaisesRegex(api.SeedanceError, 'PROPOSAL_INTENT_MISMATCH'): flow.inspect_job(self.root)

    def test_page_escapes_prompt_and_review_content(self):
        packet = deepcopy(self.packet)
        packet['body']['content'][0]['text'] = '</pre><script>alert(1)</script>'
        packet.pop('request_digest'); packet['request_digest'] = api.digest(packet)
        view = dict(self.state, request_digest=packet['request_digest'])
        source = flow.render_page(packet, view)
        self.assertNotIn('<script>', source)
        self.assertIn('&lt;script&gt;', source)
        self.assertIn("default-src 'none'", source)

    def test_local_director_video_status_routes_without_network(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = local_director.main(['video','status','--job',str(self.root)])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(out.getvalue())['state'], 'prepared')
        self.network.assert_not_called()

    def test_cli_no_execute_flag_does_not_read_key_or_submit(self):
        with patch.object(flow, '_key') as key, contextlib.redirect_stderr(io.StringIO()):
            result = flow.main(['submit','--job',str(self.root),'--approval','unused'])
        self.assertEqual(result, 2); key.assert_not_called(); self.network.assert_not_called()

    def test_getpass_echo_fallback_fails_before_network(self):
        with patch.object(sys.stdin, 'isatty', return_value=True), patch.object(flow.getpass, 'getpass') as get:
            def warning(*args):
                import warnings
                warnings.warn('synthetic echo risk', flow.getpass.GetPassWarning)
            get.side_effect = warning
            with self.assertRaises(flow.getpass.GetPassWarning): flow._key()
        self.network.assert_not_called()

    def test_cli_errors_do_not_echo_private_paths_or_payloads(self):
        err = io.StringIO()
        with patch.object(flow, 'inspect_job', side_effect=ValueError('PRIVATE-PROMPT-SECRET')):
            with contextlib.redirect_stderr(err): result=flow.main(['status','--job','PRIVATE-PATH'])
        self.assertEqual(result, 2)
        self.assertNotIn('PRIVATE-', err.getvalue())

    def test_refresh_after_review_preserves_selected_media_and_review(self):
        state = self.saved(); flow.record_review(self.root, self.record(state))
        before = {name:(self.root/name).read_bytes() for name in ('video.mp4', 'media.json', 'review.json')}
        self.network.return_value['content']['video_url'] = 'https://synthetic.tos-cn-beijing.volces.com/new-url'
        refreshed = flow.query_job(self.root, api_key='synthetic-key')
        self.assertEqual(refreshed['state'], 'retain_candidate')
        self.assertEqual(refreshed['media_sha256'], state['media_sha256'])
        for name, raw in before.items(): self.assertEqual((self.root/name).read_bytes(), raw)
        with self.assertRaisesRegex(api.SeedanceError, 'DOWNLOAD_NOT_READY'): flow.download_job(self.root)

    def test_result_revision_gap_is_not_silently_ignored(self):
        self.saved()
        self.network.return_value['content']['video_url'] = 'https://synthetic.tos-cn-beijing.volces.com/new-url'
        flow.query_job(self.root, api_key='synthetic-key')
        (self.root/'result-000001.json').rename(self.root/'result-000002.json')
        with self.assertRaisesRegex(api.SeedanceError, 'RESULT_REVISION_GAP'): flow.inspect_job(self.root)

    def test_orphan_result_revision_is_not_prepared(self):
        api._atomic_create(self.root/'result-000001.json', {})
        with self.assertRaisesRegex(api.SeedanceError, 'ORPHANED_MEDIA_RECORD'):
            flow.inspect_job(self.root)

if __name__ == '__main__': unittest.main()
