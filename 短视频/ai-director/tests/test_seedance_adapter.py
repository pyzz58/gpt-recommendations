"""Public fiction and mocked HTTPS only; never request paid generation."""
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import seedance_adapter as api
import director_timeline
import production_delivery

EXAMPLE = Path(__file__).resolve().parents[1] / 'examples/dinner-dialogue-review'

class SeedanceAdapterTests(unittest.TestCase):
    def setUp(self):
        self.base = json.loads((EXAMPLE / 'plan.json').read_text())
        self.direction = json.loads((EXAMPLE / 'direction_v02.json').read_text())
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.packet = self.prepare()
        self.approval = dict(request_digest=self.packet['request_digest'], rights_reviewed=True,
                             currency='CNY', quoted_cost='1', max_cost='2')
        self.network = patch.object(api, '_request').start()
        self.addCleanup(patch.stopall)
        self.network.return_value = {'id': 'task_synthetic'}

    def prepare(self, **kwargs):
        return api.prepare_shot(self.base, self.direction, kwargs.pop('shot_id', 'S02'),
                                provider='volcengine', **kwargs)

    def submit(self):
        return api.submit_once(self.packet, private_dir=self.root, api_key='synthetic-key', approval=self.approval)

    def finish(self, **overrides):
        self.submit()
        result = dict(id='task_synthetic', status='succeeded', model=self.packet['body']['model'],
                      content={'video_url': 'https://synthetic.tos-cn-beijing.volces.com/movie.mp4?synthetic=1'})
        result.update(overrides)
        self.network.return_value = result
        return api.query_once(private_dir=self.root, api_key='synthetic-key')

    def connection(self, raw=b'\x00\x00\x00\x18ftypisomsynthetic', status=200, length=None):
        conn = Mock()
        response = Mock(status=status)
        response.read.side_effect = io.BytesIO(raw).read
        response.getheader.return_value = str(len(raw)) if length is None else length
        conn.getresponse.return_value = response
        patch.object(api.http.client, 'HTTPSConnection', return_value=conn).start()
        return conn

    def test_dialogue_survives_delivery_and_postproduction(self):
        original = deepcopy(self.direction)
        bundle = production_delivery.build_reference_delivery(self.base, self.direction)
        for source, out in zip(self.direction['shots'], bundle['shots']):
            self.assertEqual(source['speech'], out['film_script']['speech'])
            self.assertEqual(source['speech'], out['postproduction_work_order']['speech'])
        text = production_delivery.render_operator_markdown(bundle)
        self.assertIn(self.direction['shots'][1]['speech']['dialogue'][0]['text'], text)
        bundle['shots'][1]['film_script']['speech']['dialogue'].clear()
        self.assertEqual(original, self.direction)

    def test_timeline_distinguishes_visible_and_offscreen_speech(self):
        tracks, issues = director_timeline.assemble(self.base, self.direction)
        self.assertTrue(tracks[1]['sync_dialogue'][0]['lip_sync_required'])
        self.assertFalse(tracks[3]['sync_dialogue'][0]['lip_sync_required'])
        self.assertEqual(tracks[3]['sync_dialogue'][0]['kind'], 'offscreen_dialogue')

    def test_legacy_dialogue_kind_is_unknown_and_invalid_kind_blocks(self):
        line = self.direction['shots'][1]['speech']['dialogue'][0]
        del line['kind']
        tracks, _ = director_timeline.assemble(self.base, self.direction)
        self.assertIsNone(tracks[1]['sync_dialogue'][0]['lip_sync_required'])
        line['kind'] = 'guess'
        _, issues = director_timeline.assemble(self.base, self.direction)
        self.assertTrue(any(x['code'] == 'DIALOGUE_KIND_INVALID' and x['severity'] == 'blocker' for x in issues))

    def test_native_audio_keeps_exact_text_and_removes_post_only_instruction(self):
        packet = self.prepare(audio_mode='native_dialogue')
        prompt = packet['body']['content'][0]['text']
        self.assertTrue(packet['body']['generate_audio'])
        self.assertIn(self.direction['shots'][1]['speech']['dialogue'][0]['text'], prompt)
        self.assertNotIn('Voiceover, sound effects, music and exact charts are handled in post-production.', prompt)
        self.assertNotIn("先录音锁定语速再同步", prompt)
        self.assertIn("Provider watermark is controlled by the API setting", prompt)
        self.assertFalse(self.packet['body']['generate_audio'])
        self.assertFalse(packet['media_generated'])
        self.network.assert_not_called()

    def test_native_voiceover_and_unknown_dialogue_are_rejected(self):
        with self.assertRaises(api.SeedanceError): self.prepare(shot_id='S01', audio_mode='native_dialogue')
        del self.direction['shots'][1]['speech']['dialogue'][0]['kind']
        with self.assertRaisesRegex(api.SeedanceError, 'EXPLICIT_DIALOGUE_KIND_REQUIRED'):
            self.prepare(audio_mode='native_dialogue')

    def test_reference_role_and_provider_are_explicit(self):
        packet = self.prepare(reference_images=['https://example.com/reviewed-fiction.png'])
        self.assertEqual(packet['body']['content'][1]['role'], 'reference_image')
        self.assertEqual(packet['scope'], 'reference_guided_candidate')
        other = api.prepare_shot(self.base, self.direction, 'S02', provider='byteplus')
        self.assertEqual(other['body']['model'], api.PROVIDERS['byteplus'][1])
        with self.assertRaises(api.SeedanceError): self.prepare(reference_images=['http://example.com/x'])

    def test_modified_request_and_rehashed_unsupported_options_rejected(self):
        self.packet['body']['duration'] = 100
        with self.assertRaisesRegex(api.SeedanceError, 'PACKET_CHANGED'): self.submit()
        self.packet.pop('request_digest')
        self.packet['request_digest'] = api.digest(self.packet)
        self.approval['request_digest'] = self.packet['request_digest']
        with self.assertRaisesRegex(api.SeedanceError, 'REQUEST_OUTSIDE_REVIEWED_SUBSET'): self.submit()
        self.network.assert_not_called()

    def test_missing_approval_or_excess_estimate_never_posts(self):
        for field, value in [('rights_reviewed', False), ('quoted_cost', '3'), ('currency', 'USD'), ('max_cost', 'NaN')]:
            saved = self.approval.copy(); self.approval[field] = value
            with self.assertRaises(api.SeedanceError): self.submit()
            self.approval = saved
        self.network.assert_not_called()
        self.assertFalse((self.root / 'intent.json').exists())

    def test_public_storage_rejected_before_post(self):
        self.root.chmod(0o755)
        with self.assertRaises(ValueError): self.submit()
        self.network.assert_not_called()

    def test_intent_write_failure_never_posts(self):
        with patch.object(api, '_atomic_create', side_effect=OSError('synthetic disk failure')):
            with self.assertRaises(OSError): self.submit()
        self.network.assert_not_called()

    def test_timeout_blocks_resubmission(self):
        self.network.side_effect = api.SeedanceError('API_RESULT_UNKNOWN_NO_AUTOMATIC_RETRY')
        with self.assertRaises(api.SeedanceError): self.submit()
        with self.assertRaisesRegex(api.SeedanceError, 'SUBMISSION_ALREADY_ATTEMPTED'): self.submit()
        self.assertEqual(self.network.call_count, 1)
        self.assertFalse((self.root / 'receipt.json').exists())

    def test_receipt_failure_cannot_trigger_second_post(self):
        real = api._atomic_create
        def fail_receipt(path, value):
            if path.name == 'receipt.json': raise OSError('synthetic failure')
            real(path, value)
        with patch.object(api, '_atomic_create', side_effect=fail_receipt):
            with self.assertRaises(OSError): self.submit()
        with self.assertRaises(api.SeedanceError): self.submit()
        self.assertEqual(self.network.call_count, 1)

    def test_successful_submit_is_immutable_and_private(self):
        receipt = self.submit()
        self.assertEqual(receipt['task_id'], 'task_synthetic')
        self.assertEqual((self.root / 'intent.json').stat().st_mode & 0o777, 0o600)
        with self.assertRaises(api.SeedanceError): self.submit()
        self.assertEqual(self.network.call_count, 1)

    def test_query_running_and_failed_never_reposts(self):
        self.submit()
        for status in ['queued', 'running', 'failed', 'expired', 'cancelled']:
            self.network.return_value = {'id': 'task_synthetic', 'status': status}
            result = api.query_once(private_dir=self.root, api_key='synthetic-key')
            self.assertEqual(result['status'], status)
            self.assertFalse(result['human_approved'])
        self.assertEqual([c.args[1] for c in self.network.call_args_list], ['POST'] + ['GET'] * 5)
        self.assertFalse((self.root / 'result.json').exists())

    def test_query_rejects_wrong_task_or_model(self):
        self.submit()
        for result in [dict(id='wrong', status='running'), dict(id='task_synthetic', status='succeeded', model='wrong')]:
            self.network.return_value = result
            with self.assertRaises(api.SeedanceError): api.query_once(private_dir=self.root, api_key='synthetic-key')
        self.assertFalse((self.root / 'result.json').exists())

    def test_download_saves_bytes_without_authorization_or_claiming_decode(self):
        self.assertFalse(self.finish()['locally_saved'])
        conn = self.connection()
        info = api.download_result(private_dir=self.root)
        self.assertTrue((self.root / 'video.mp4').is_file())
        self.assertEqual(conn.request.call_args.args[0], 'GET')
        self.assertEqual(conn.request.call_args.kwargs, {})
        self.assertFalse(info['fully_decoded'])
        self.assertFalse(info['final_film_completed'])
        with self.assertRaisesRegex(api.SeedanceError, 'MEDIA_ALREADY_SAVED'): api.download_result(private_dir=self.root)

    def test_unreviewed_media_host_never_connects(self):
        self.finish(content={'video_url': 'https://attacker.example/movie.mp4'})
        with patch.object(api.http.client, 'HTTPSConnection') as connection:
            with self.assertRaisesRegex(api.SeedanceError, 'MEDIA_HOST_NOT_REVIEWED'): api.download_result(private_dir=self.root)
            connection.assert_not_called()

    def test_redirect_truncation_and_invalid_media_are_not_saved(self):
        self.finish()
        for config in [dict(status=302), dict(length='999'), dict(raw=b'not a video at all'), dict(length=str(api.MAX_VIDEO + 1))]:
            self.connection(**config)
            with self.assertRaises(api.SeedanceError): api.download_result(private_dir=self.root)
            self.assertFalse((self.root / 'video.mp4').exists())
            self.assertEqual(list(self.root.glob('.video-*')), [])

    def test_http_transport_posts_once_and_never_follows_redirects(self):
        patch.stopall()
        conn = Mock(); conn.getresponse.return_value.status = 302
        with patch.object(api.http.client, 'HTTPSConnection', return_value=conn):
            with self.assertRaisesRegex(api.SeedanceError, 'API_HTTP_FAILURE_NO_AUTOMATIC_RETRY'):
                api._request('volcengine', 'POST', api.TASK_PATH, 'synthetic-key', {})
        self.assertEqual(conn.request.call_count, 1)
        conn.close.assert_called_once()

if __name__ == '__main__': unittest.main()
