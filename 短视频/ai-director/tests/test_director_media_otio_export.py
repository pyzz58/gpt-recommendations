"""QO-D09 private local video probe + native OTIO / SRT exchange."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agent_team
import director_media_otio_export as media
import director_montage_editor_conform as conform
from test_director_editorial_montage import plan_fixture


def manifest(order, rows=None):
    return {
        "version": media.VERSION,
        "work_order_digest": agent_team.fingerprint(order),
        "assets": rows if rows is not None else [],
    }


@unittest.skipUnless(shutil.which("ffprobe") and shutil.which("ffmpeg"),
                     "local FFmpeg tools not installed in runtime")
class MediaOTIOExportTests(unittest.TestCase):
    def setUp(self):
        h, ds, plan, packet, cov = plan_fixture()
        self.order = conform.compile_work_order(h, ds, plan, packet, cov, fps=30)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def clip(self, name="clip.mp4", fps=30, seconds=5):
        path = self.root / name
        subprocess.run(
            ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi",
             "-i", f"color=c=black:s=162x288:r={fps}", "-t", str(seconds),
             "-an", "-c:v", "mpeg4", "-q:v", "12", str(path)],
            check=True, timeout=30, capture_output=True)
        return path

    def row(self, path, *, sid="story_01", start=0, sha=None):
        return {
            "editor_segment_id": sid,
            "relative_path": path.name,
            "source_in_frame": start,
            "expected_sha256": sha or hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    def test_ffmpeg_real_probe_hash_framecount_and_source_handles(self):
        path = self.clip(seconds=8)
        receipt = media.inspect_local_media(
            self.order, manifest(self.order, [self.row(path, start=30)]),
            media_root=self.root)
        a = receipt["assets"]["story_01"]
        self.assertEqual(a["verified_video_metadata"]["frame_count"], 240)
        self.assertEqual(a["source_in_frame"], 30)
        self.assertEqual(a["source_out_frame_exclusive"], 180)
        self.assertEqual(a["available_head_frames"], 30)
        self.assertEqual(a["available_tail_frames"], 60)
        self.assertTrue(a["local_probe_and_hash_passed"])
        self.assertFalse(a["picture_artistry_verified"])
        self.assertEqual(len(receipt["missing_editor_segments"]), 5)
        self.assertFalse(receipt["permission_to_render_or_publish"])

    def test_file_checksum_and_framerate_cannot_be_asserted_without_probe(self):
        path = self.clip(fps=25)
        with self.assertRaisesRegex(media.MediaConformError, "FPS"):
            media.inspect_local_media(
                self.order, manifest(self.order, [self.row(path)]),
                media_root=self.root)
        wrong = self.row(path, sha="a" * 64)
        with self.assertRaisesRegex(media.MediaConformError, "SHA256"):
            media.inspect_local_media(
                self.order, manifest(self.order, [wrong]), media_root=self.root)

    def test_source_frames_outside_media_fail_even_if_hash_matches(self):
        path = self.clip()
        with self.assertRaisesRegex(media.MediaConformError, "INSUFFICIENT_SOURCE"):
            media.inspect_local_media(
                self.order, manifest(self.order, [self.row(path, start=1)]),
                media_root=self.root)

    def test_duplicate_forged_digest_and_unsafe_local_paths_rejected(self):
        path = self.clip()
        row = self.row(path)
        for entries in ([row, row],):
            with self.assertRaisesRegex(media.MediaConformError, "DUPLICATE"):
                media.inspect_local_media(
                    self.order, manifest(self.order, entries),
                    media_root=self.root)
        bad = manifest(self.order, [row])
        bad["work_order_digest"] = "faked"
        with self.assertRaisesRegex(media.MediaConformError, "STALE"):
            media.inspect_local_media(self.order, bad, media_root=self.root)
        for rel in ("../escape.mp4", "/tmp/absolute.mp4", "a/../clip.mp4"):
            with self.subTest(rel=rel), self.assertRaisesRegex(
                    media.MediaConformError, "UNSAFE_RELATIVE_PATH"):
                bad = manifest(self.order, [dict(row, relative_path=rel)])
                media.inspect_local_media(self.order, bad, media_root=self.root)
        link = self.root / "alias.mp4"
        link.symlink_to(path)
        with self.assertRaisesRegex(media.MediaConformError, "UNSAFE_FILE"):
            media.inspect_local_media(
                self.order,
                manifest(self.order, [dict(row, relative_path="alias.mp4")]),
                media_root=self.root)

    def test_full_native_otio_json_roundtrips_real_clip_and_placeholders(self):
        import opentimelineio as otio
        path = self.clip(seconds=7)
        project = media.export_native_otio_preview(
            self.order, manifest(self.order, [self.row(path, start=30)]),
            media_root=self.root)
        self.assertEqual(project["extension"], ".otio")
        self.assertEqual(project["total_frames"], 1320)
        self.assertEqual(project["media_clips_probed"], 1)
        self.assertFalse(project["render_or_publish_authorized"])
        tl = otio.adapters.read_from_string(project["otio_json"],
                                             adapter_name="otio_json")
        self.assertEqual(len(tl.tracks), 1)
        self.assertEqual(len(tl.tracks[0]), 6)
        self.assertIsInstance(tl.tracks[0][0], otio.schema.Clip)
        self.assertIsInstance(tl.tracks[0][1], otio.schema.Gap)
        self.assertEqual(tl.duration().rescaled_to(30).value, 1320)
        meta = tl.metadata["ai_director"]
        self.assertEqual(len(meta["montage_cut_jobs"]), 2)
        self.assertFalse(meta["render_or_publish_authorized"])
        self.assertEqual(tl.tracks[0][0].media_reference.target_url, path.as_uri())

    def test_effect_handle_capacity_is_computed_but_not_rendered(self):
        path = self.clip(seconds=12)
        items = [self.row(path, sid="story_01", start=30),
                 self.row(path, sid="story_02", start=180)]
        report = media.inspect_local_media(
            self.order, manifest(self.order, items), media_root=self.root)
        seam = report["montage_cut_handle_inspections"][0]
        self.assertTrue(seam["both_picture_files_probed"])
        self.assertEqual(seam["maximum_symmetric_handle_frames"], 180)
        self.assertTrue(seam["nonhard_transition_effect_not_rendered"])
        self.assertFalse(seam["director_art_review_verified"])

    def test_empty_otio_is_importable_preview_not_a_fabricated_film(self):
        import opentimelineio as otio
        project = media.export_native_otio_preview(
            self.order, manifest(self.order), media_root=self.root)
        tl = otio.adapters.read_from_string(project["otio_json"],
                                             adapter_name="otio_json")
        self.assertEqual(len(tl.tracks[0]), 6)
        self.assertTrue(all(isinstance(x, otio.schema.Gap)
                            for x in tl.tracks[0]))
        self.assertEqual(len(project["missing_picture_slots"]), 6)
        self.assertTrue(project["montage_effects_not_auto_rendered"])

    def test_srt_is_exact_director_planned_text_not_verified_dubbing(self):
        work = deepcopy(self.order)
        work["subtitle_events"] = [
            {"start_frame": 30, "end_frame_exclusive": 120,
             "source_text_exact": "这里是公开虚构故事中的原稿字幕。"},
            {"start_frame": 150, "end_frame_exclusive": 210,
             "source_text_exact": "这里是下一句经过编剧确认的原话。"},
        ]
        srt = media.export_subtitle_srt_plan(work)
        self.assertEqual(srt["subtitle_count"], 2)
        self.assertIn("00:00:01,000 --> 00:00:04,000", srt["srt_text"])
        self.assertIn("00:00:05,000 --> 00:00:07,000", srt["srt_text"])
        self.assertFalse(srt["render_or_publish_authorized"])
        bad = deepcopy(work)
        bad["subtitle_events"][1]["start_frame"] = 119
        with self.assertRaisesRegex(media.MediaConformError, "OVERLAP"):
            media.export_subtitle_srt_plan(bad)
        bad = deepcopy(work)
        bad["subtitle_events"][0]["source_text_exact"] = "inject --> invalid"
        with self.assertRaisesRegex(media.MediaConformError, "TEXT_UNSAFE"):
            media.export_subtitle_srt_plan(bad)


if __name__ == "__main__":
    unittest.main()
