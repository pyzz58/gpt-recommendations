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

    def test_cast_changes_reach_wire_without_private_reference_metadata(self):
        baseline = self.prepare()
        self.base['characters'][1]['description'] = '母亲短卷发'
        self.base['characters'][1]['wardrobe'] = '深绿色开衫'
        self.base['characters'][1]['identity_anchor'] = 'PRIVATE_REFERENCE_PATH_DO_NOT_SEND'
        changed = self.prepare()
        prompt = changed['body']['content'][0]['text']
        self.assertNotEqual(baseline['body'], changed['body'])
        self.assertIn('母亲短卷发', prompt)
        self.assertIn('深绿色开衫', prompt)
        self.assertNotIn('PRIVATE_REFERENCE_PATH_DO_NOT_SEND', prompt)
        self.network.assert_not_called()

    def test_each_structured_camera_and_layout_field_reaches_wire(self):
        baseline = self.prepare()['body']
        original = deepcopy(self.direction)
        changes = [('camera', 'screen_axis', 'AUDIT_AXIS'),
                   ('staging', 'spatial_constraints', ['AUDIT_SPATIAL']),
                   ('art', 'scene_geometry', {'anchor_positions': {'door': 'AUDIT_DOOR'}}),
                   ('art', 'practical_sources', ['AUDIT_LAMP'])]
        for group, key, value in changes:
            with self.subTest(field=key):
                self.direction = deepcopy(original)
                self.direction['shots'][1][group][key] = value
                body = self.prepare()['body']
                self.assertNotEqual(baseline, body)
                self.assertIn(json.dumps(value, ensure_ascii=False, sort_keys=True), body['content'][0]['text'])
        self.direction = deepcopy(original)
        self.direction['shots'][1]['camera'].update(focal_length_mm=85, lens_feel='85mm，胸上近景')
        self.assertIn('"focal_length_mm": 85', self.prepare()['body']['content'][0]['text'])

    def test_conflicting_numeric_lens_is_rejected_before_network(self):
        self.direction['shots'][1]['camera']['focal_length_mm'] = 85
        with self.assertRaisesRegex(ValueError, 'DIRECTOR_FOCAL_LENGTH_CONFLICT'):
            self.prepare()
        self.network.assert_not_called()

    def test_native_sound_design_and_effects_reach_wire(self):
        original = deepcopy(self.direction)
        baseline = self.prepare(audio_mode='native_dialogue')
        self.assertIn('none：无配乐', baseline['body']['content'][0]['text'])
        for key, value in [('ambient', 'AUDIT_ROOM_TONE'), ('music', 'AUDIT_NO_MUSIC'),
                           ('effects', [{'time_s': 6, 'cue': 'AUDIT_CHAIR_SOUND'}])]:
            with self.subTest(field=key):
                self.direction = deepcopy(original)
                self.direction['shots'][1]['sound'][key] = value
                changed = self.prepare(audio_mode='native_dialogue')
                self.assertNotEqual(baseline['body'], changed['body'])
                self.assertIn('AUDIT_', changed['body']['content'][0]['text'])

    def test_audio_execution_policy_is_mode_specific_and_does_not_mutate_source(self):
        original = deepcopy(self.direction)
        native = self.prepare(audio_mode='native_dialogue')
        silent = self.prepare(audio_mode='silent_post')
        self.assertEqual(native['postproduction']['audio_execution']['dialogue_and_scene_audio_owner'], 'video_provider')
        self.assertEqual(silent['postproduction']['audio_execution']['dialogue_and_scene_audio_owner'], 'postproduction')
        self.assertNotIn('先录音锁定语速再同步', native['postproduction']['speech']['lip_sync_policy'])
        self.assertEqual(silent['postproduction']['speech'], original['shots'][1]['speech'])
        self.assertNotIn('Native soundtrack design', silent['body']['content'][0]['text'])
        self.assertEqual(self.direction, original)

    def test_updated_result_is_appended_and_download_uses_latest_url(self):
        self.finish()
        first = (self.root/'result.json').read_bytes()
        self.network.return_value['content']['video_url'] = 'https://synthetic.tos-cn-beijing.volces.com/new.mp4?version=2'
        api.query_once(private_dir=self.root, api_key='synthetic-key')
        api.query_once(private_dir=self.root, api_key='synthetic-key')
        self.assertEqual(len(list(self.root.glob('result-*.json'))), 1)
        self.assertEqual((self.root/'result.json').read_bytes(), first)
        conn = self.connection()
        info = api.download_result(private_dir=self.root)
        self.assertEqual(conn.request.call_args.args, ('GET', '/new.mp4?version=2'))
        self.assertEqual(info['result_digest'], api.digest(self.network.return_value))
        self.assertEqual(sum(c.args[1] == 'POST' for c in self.network.call_args_list), 1)

    def test_result_append_failure_preserves_previous_success_without_post_retry(self):
        self.finish()
        first = (self.root/'result.json').read_bytes()
        self.network.return_value['content']['video_url'] = 'https://synthetic.tos-cn-beijing.volces.com/new.mp4'
        with patch.object(api, '_atomic_create', side_effect=OSError('synthetic disk full')):
            with self.assertRaises(OSError): api.query_once(private_dir=self.root, api_key='synthetic-key')
        self.assertEqual((self.root/'result.json').read_bytes(), first)
        self.assertEqual(list(self.root.glob('result-*.json')), [])
        api.query_once(private_dir=self.root, api_key='synthetic-key')
        self.assertTrue((self.root/'result-000001.json').exists())
        self.assertEqual(sum(c.args[1] == 'POST' for c in self.network.call_args_list), 1)

    def test_corrupt_or_unlinked_result_revision_blocks_download(self):
        self.finish()
        self.network.return_value['content']['video_url'] = 'https://synthetic.tos-cn-beijing.volces.com/new.mp4'
        api.query_once(private_dir=self.root, api_key='synthetic-key')
        path = self.root/'result-000001.json'
        record = api._read(path); record['previous_digest'] = 'wrong'
        path.write_text(json.dumps(record))
        with patch.object(api.http.client, 'HTTPSConnection') as conn:
            with self.assertRaisesRegex(api.SeedanceError, 'RESULT_REVISION_MISMATCH'):
                api.download_result(private_dir=self.root)
            conn.assert_not_called()

    def test_revision_from_different_task_is_rejected(self):
        self.finish()
        before = api._read(self.root/'result.json')
        wrong = deepcopy(before); wrong['id'] = 'other_task'
        api._atomic_create(self.root/'result-000001.json', dict(
            sequence=1, request_digest=self.packet['request_digest'],
            previous_digest=api.digest(before), result=wrong))
        with self.assertRaisesRegex(api.SeedanceError, 'RESULT_MISMATCH'):
            api.download_result(private_dir=self.root)

    def test_private_root_accepts_system_style_ancestor_alias(self):
        real = self.root/'real'; real.mkdir(mode=0o700)
        alias = self.root/'alias'; alias.symlink_to(real, target_is_directory=True)
        vault = alias/'vault'; vault.mkdir(mode=0o700)
        self.assertEqual(api._private_root(vault), (real/'vault').resolve())

    def test_private_root_rejects_symlinked_root(self):
        target = self.root/'target'; target.mkdir(mode=0o700)
        link = self.root/'linked-vault'
        link.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(api.SeedanceError, 'PRIVATE_STORAGE_REQUIRED'):
            api._private_root(link)

    def test_private_root_rejects_git_directory_and_worktree_file(self):
        repo = self.root/'repo-dir'; repo.mkdir()
        (repo/'.git').mkdir()
        (repo/'vault').mkdir(mode=0o700)
        with self.assertRaisesRegex(api.SeedanceError, 'PRIVATE_STORAGE_REQUIRED'):
            api._private_root(repo/'vault')
        worktree = self.root/'worktree-file'; worktree.mkdir()
        (worktree/'.git').write_text('gitdir: /synthetic/elsewhere\n', encoding='utf-8')
        (worktree/'vault').mkdir(mode=0o700)
        with self.assertRaisesRegex(api.SeedanceError, 'PRIVATE_STORAGE_REQUIRED'):
            api._private_root(worktree/'vault')

    def test_private_root_rejects_broad_permissions_and_missing_directory(self):
        broad = self.root/'broad'; broad.mkdir(mode=0o700)
        broad.chmod(0o755)
        with self.assertRaisesRegex(api.SeedanceError, 'PRIVATE_STORAGE_REQUIRED'):
            api._private_root(broad)
        with self.assertRaisesRegex(api.SeedanceError, 'PRIVATE_STORAGE_REQUIRED'):
            api._private_root(self.root/'does-not-exist')

    def test_private_read_rejects_symlinked_file(self):
        target = self.root/'target.json'
        target.write_text('{}', encoding='utf-8')
        target.chmod(0o600)
        link = self.root/'linked.json'
        link.symlink_to(target)
        with self.assertRaisesRegex(api.SeedanceError, 'PRIVATE_RECORD_INVALID'):
            api._read(link)

if __name__ == '__main__': unittest.main()
