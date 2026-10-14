"""Actual FFmpeg picture assembly using only public synthetic color clips."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import agent_team
import director_media_otio_export as media
import director_picture_render_smoke as smoke


def public_order():
    shots = []
    for i in range(3):
        shots.append({
            "editor_segment_id": f"story_{i+1:02d}",
            "kind": "story_shot_unrendered",
            "source_shot_id": f"S{i+1:02d}",
            "in_frame": 30*i,
            "out_frame_exclusive": 30*(i+1),
            "duration_frames": 30,
        })
    return {
        "kind": "director_editor_conform_work_order_nonrendered",
        "frame_rate_integer_fps": 30,
        "final_total_frames": 90,
        "render_or_publish_authorized": False,
        "ready_for_rough_cut": False,
        "segments": shots,
        "montage_cut_jobs": [{
            "sequence_id": "M01",
            "out_shot_id": f"S{i+1:02d}",
            "in_shot_id": f"S{i+2:02d}",
            "boundary_frame": 30*(i+1),
            "edit_type_exact": "hard_cut",
            "required_gate": None,
            "transition_duration_frames": 0,
        } for i in range(2)],
        "speech_events": [], "subtitle_events": [],
        "operator_blockers": ["SOURCE_MEDIA_ASSETS_NOT_PROVIDED"],
        "director_coverage_digest": "public-synthetic-only",
    }


class RequiredCIMediaDependenciesTests(unittest.TestCase):
    def test_real_media_suite_must_not_be_silently_skipped_on_ci(self):
        if os.environ.get("CI") == "true":
            self.assertIsNotNone(shutil.which("ffmpeg"))
            self.assertIsNotNone(shutil.which("ffprobe"))


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "local open-source FFmpeg/FFprobe tools required")
class PictureRenderSmokeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.media_root = self.root / "videos"
        self.output_root = self.root / "output"
        self.media_root.mkdir()
        self.output_root.mkdir()
        self.order = public_order()

    def create_assets(self):
        assets = []
        for i, color in enumerate(("red", "green", "blue")):
            path = self.media_root / f"test_{i+1}.mp4"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
                "-y", "-f", "lavfi",
                "-i", f"color=c={color}:s=160x288:r=30:d=1",
                "-an", "-c:v", "mpeg4", "-q:v", "2", str(path)
            ], check=True, capture_output=True, timeout=30)
            assets.append({
                "editor_segment_id": self.order["segments"][i]["editor_segment_id"],
                "relative_path": path.name,
                "source_in_frame": 0,
                "expected_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            })
        manifest = {
            "version": media.VERSION,
            "work_order_digest": agent_team.fingerprint(self.order),
            "assets": assets,
        }
        self.otio_json = media.export_native_otio_preview(
            self.order, manifest, media_root=self.media_root)["otio_json"]
        return manifest

    def render(self, manifest):
        return smoke.render_synthetic_picture_smoke(
            self.order, manifest, otio_json=self.otio_json,
            media_root=self.media_root, output_dir=self.output_root)

    def test_real_render_has_exact_frames_and_color_order(self):
        manifest = self.create_assets()
        otio = media.export_native_otio_preview(
            self.order, manifest, media_root=self.media_root)
        self.assertEqual(otio["total_frames"], 90)
        result = self.render(manifest)
        self.assertEqual(result["frames_decoded_verified"], 90)
        self.assertEqual(result["frame_rate"], 30)
        self.assertFalse(result["render_or_publish_authorized"])
        self.assertFalse(result["nle_import_verified"])
        out = self.output_root / "synthetic_smoke.mp4"
        self.assertTrue(out.is_file())
        sample = subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
            "-i", str(out),
            "-vf", "select=eq(n\\,0)+eq(n\\,30)+eq(n\\,60)",
            "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"
        ], check=True, capture_output=True, timeout=30).stdout
        stride = 160*288*3
        self.assertEqual(len(sample), 3*stride)
        center = ((288//2)*160 + (160//2))*3
        colors = [list(sample[i*stride+center:i*stride+center+3])
                  for i in range(3)]
        self.assertGreater(colors[0][0], colors[0][1]*2)
        self.assertGreater(colors[1][1], colors[1][0]*2)
        self.assertGreater(colors[2][2], colors[2][0]*2)

    def test_native_otio_import_is_required_and_wrong_clip_cannot_render(self):
        import opentimelineio as otio
        m = self.create_assets()
        tl = otio.adapters.read_from_string(self.otio_json,
                                             adapter_name="otio_json")
        tl.tracks[0][1].name = "SPOOFED_SHOT"
        forged = otio.adapters.write_to_string(tl,
                                               adapter_name="otio_json")
        with self.assertRaisesRegex(smoke.SmokeError, "MEDIA_BINDING"):
            smoke.render_synthetic_picture_smoke(
                self.order, m, otio_json=forged,
                media_root=self.media_root, output_dir=self.output_root)
        with self.assertRaisesRegex(smoke.SmokeError, "OTIO_IMPORT_INVALID"):
            smoke.render_synthetic_picture_smoke(
                self.order, m, otio_json="not-valid-otio-json-" * 2,
                media_root=self.media_root, output_dir=self.output_root)

    def test_missing_clips_never_turn_into_a_successful_film(self):
        m = self.create_assets()
        m["assets"].pop()
        with self.assertRaisesRegex(smoke.SmokeError, "SOURCE_MEDIA_MISSING"):
            self.render(m)

    def test_complex_transitions_and_audio_must_fail_closed(self):
        m = self.create_assets()
        edit = self.order["montage_cut_jobs"][0]
        edit["edit_type_exact"] = "sound_bridge"
        edit["required_gate"] = "J_L_AUDIO_BRIDGE_TIMING_AND_MEDIA_REQUIRED"
        with self.assertRaisesRegex(smoke.SmokeError, "REFUSES_COMPLEX"):
            self.render(m)
        self.order = public_order()
        self.order["speech_events"] = [{"source_text_exact": "真实配音缺失"}]
        with self.assertRaisesRegex(smoke.SmokeError, "REJECTS_UNRENDERED"):
            self.render(m)
        self.order = public_order()
        self.order["operator_blockers"].append(
            "AUTHORITATIVE_SPEECH_AND_SUBTITLE_TIMING_REQUIRED")
        with self.assertRaisesRegex(smoke.SmokeError, "REJECTS_UNRENDERED"):
            self.render(m)

    def test_output_clobber_and_unsafe_names_are_blocked(self):
        m = self.create_assets()
        (self.output_root / "synthetic_smoke.mp4").write_text("existing")
        with self.assertRaisesRegex(smoke.SmokeError, "ALREADY_EXISTS"):
            self.render(m)
        with self.assertRaisesRegex(smoke.SmokeError, "FILENAME_UNSAFE"):
            smoke.render_synthetic_picture_smoke(
                self.order, m, otio_json=self.otio_json,
                media_root=self.media_root, output_dir=self.output_root,
                filename="../escape.mp4")

    def test_does_not_smuggle_extra_unrendered_credit_pages(self):
        m = self.create_assets()
        self.order["segments"][2]["kind"] = "final_evidence_postproduction"
        with self.assertRaisesRegex(smoke.SmokeError, "ONLY_SHORT"):
            self.render(m)


if __name__ == "__main__":
    unittest.main()
