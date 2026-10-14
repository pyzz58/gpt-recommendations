"""QO-D19 real public synthetic audio+subtitle mux validation, no actor footage."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import math
from pathlib import Path
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agent_team
import director_av_sync_smoke as av
import director_media_otio_export as media
import director_picture_render_smoke as picture
from test_director_picture_render_smoke import public_order


def pcm_tone(spans, *, fps=30, total_frames=90):
    count = total_frames * (48000 // fps)
    signal = []
    for i in range(count):
        active = any(a*48000//fps <= i < b*48000//fps
                     for a, b in spans)
        signal.append(int(9000 * math.sin(2*math.pi*997*i/48000))
                      if active else 0)
    return struct.pack("<"+str(count)+"h", *signal)


class RequiredSyntheticAVDependencies(unittest.TestCase):
    def test_libass_subtitles_are_mandatory_in_ci(self):
        if os.environ.get("CI") == "true":
            self.assertIsNotNone(shutil.which("ffmpeg"))
            self.assertIsNotNone(shutil.which("ffprobe"))
            completed = subprocess.run(
                ["ffmpeg", "-hide_banner", "-filters"],
                capture_output=True, text=True, check=True, timeout=15)
            self.assertRegex(completed.stdout, r"(?m)^\\s*\\.\\.\\. subtitles\\s")


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "Requires local FFmpeg with libass")
class AVSyncSyntheticSmokeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.assets = root / "assets"
        self.assets.mkdir()
        self.source = root / "source"
        self.source.mkdir()
        self.output = root / "output"
        self.output.mkdir()
        self.picture_order = public_order()
        self.av_order = deepcopy(self.picture_order)
        self.av_order["speech_events"] = [
            {"start_frame":10, "end_frame_exclusive":25,
             "source_text_exact":"SYNTHETIC TONE A"},
            {"start_frame":43, "end_frame_exclusive":55,
             "source_text_exact":"SYNTHETIC TONE B"},
        ]
        self.av_order["subtitle_events"] = [
            {"start_frame":12, "end_frame_exclusive":26,
             "source_text_exact":"RED TEST CAPTION"},
            {"start_frame":42, "end_frame_exclusive":57,
             "source_text_exact":"GREEN TEST CAPTION"},
        ]
        rows=[]
        for i,color in enumerate(("red","green","blue")):
            name=f"public_{color}.mp4"
            path=self.assets/name
            subprocess.run([
                "ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
                "-f","lavfi","-i",f"color=c={color}:s=160x288:r=30:d=1",
                "-an","-c:v","mpeg4","-q:v","2",str(path)
            ],check=True,capture_output=True,timeout=25)
            rows.append({
                "editor_segment_id":self.picture_order["segments"][i]["editor_segment_id"],
                "relative_path":name,
                "source_in_frame":0,
                "expected_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            })
        manifest={
            "version":media.VERSION,
            "work_order_digest":agent_team.fingerprint(self.picture_order),
            "assets":rows
        }
        otio=media.export_native_otio_preview(
            self.picture_order,manifest,media_root=self.assets)
        self.picture_receipt=picture.render_synthetic_picture_smoke(
            self.picture_order,manifest,otio_json=otio["otio_json"],
            media_root=self.assets,output_dir=self.source)
        self.speech_spans=[(10,25),(43,55)]
        self.write_tone(pcm_tone(self.speech_spans))

    def write_tone(self,raw):
        path=self.source/"synthetic_tone.wav"
        with wave.open(str(path),"wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(48000)
            f.writeframes(raw)

    def mux(self, **kw):
        return av.render_public_synthetic_av_smoke(
            self.picture_receipt,self.av_order,
            source_dir=self.source,output_dir=self.output,
            picture_name="synthetic_smoke.mp4",
            tone_name="synthetic_tone.wav",**kw)

    def test_actual_pcm_decode_exact_and_subtitle_pixels_appear_on_time(self):
        result=self.mux()
        self.assertEqual(result["frames_picture_verified"],90)
        self.assertEqual(result["pcm_samples_verified"],144000)
        self.assertTrue(result["sample_exact_audio_roundtrip_verified"])
        self.assertTrue(result["subtitle_overlay_filter_executed"])
        self.assertFalse(result["subtitle_pixel_content_verified"])
        self.assertFalse(result["real_speech_or_lip_sync_verified"])
        self.assertFalse(result["render_or_publish_authorized"])
        mov=self.output/"synthetic_av_check.mkv"
        self.assertTrue(mov.exists())
        frames=subprocess.run([
            "ffmpeg","-hide_banner","-loglevel","error","-nostdin",
            "-i",str(mov),"-vf",
            "select=eq(n\\,5)+eq(n\\,18)+eq(n\\,35)+eq(n\\,50)",
            "-vsync","0","-f","rawvideo","-pix_fmt","rgb24","-"
        ],capture_output=True,check=True,timeout=25).stdout
        stride=160*288*3
        self.assertEqual(len(frames),4*stride)

        def white_count(frame):
            region=frames[frame*stride:(frame+1)*stride]
            bright=0
            for y in range(196,286):
                for x in range(160):
                    j=(y*160+x)*3
                    if all(v>180 for v in region[j:j+3]):
                        bright+=1
            return bright
        self.assertGreater(white_count(1), white_count(0)+20)
        self.assertGreater(white_count(3), white_count(2)+20)

    def test_tone_start_too_early_is_fatal_not_auto_trimmed(self):
        early=pcm_tone([(9,25),(43,55)])
        self.write_tone(early)
        with self.assertRaisesRegex(av.AVSmokeError,
                                    "TONE_LEAK_OUTSIDE_CUE"):
            self.mux()

    def test_missing_tone_in_any_approved_cue_is_fatal(self):
        self.write_tone(pcm_tone([(10,25)]))
        with self.assertRaisesRegex(av.AVSmokeError,
                                    "TONE_MISSING_IN_CUE_FRAME"):
            self.mux()

    def test_missing_audio_and_out_of_bounds_captions_fail_closed(self):
        (self.source/"synthetic_tone.wav").unlink()
        with self.assertRaisesRegex(av.AVSmokeError,
                                    "LOCAL_FILE_MISSING"):
            self.mux()
        self.write_tone(pcm_tone(self.speech_spans))
        bad=deepcopy(self.av_order)
        bad["subtitle_events"][1]["start_frame"]=25
        self.av_order=bad
        with self.assertRaisesRegex(
                media.MediaConformError, "SUBTITLE_FRAME_OVERLAP"):
            self.mux()

    def test_refuse_publish_or_complex_effect_or_stale_picture_receipt(self):
        self.av_order["render_or_publish_authorized"]=True
        with self.assertRaisesRegex(
                media.MediaConformError,"WORK_ORDER_UNTRUSTED"):
            self.mux()
        self.av_order["render_or_publish_authorized"]=False
        self.av_order["montage_cut_jobs"][0]["edit_type_exact"]="sound_bridge"
        with self.assertRaisesRegex(av.AVSmokeError,"NONHARDCUT"):
            self.mux()
        self.av_order=deepcopy(self.picture_order)
        self.av_order["speech_events"]=[{"start_frame":10,
            "end_frame_exclusive":25,"source_text_exact":"SYNTHETIC"}]
        self.av_order["subtitle_events"]=[{"start_frame":12,
            "end_frame_exclusive":26,"source_text_exact":"CAPTION"}]
        self.picture_receipt["output_sha256"]="f"*64
        with self.assertRaisesRegex(av.AVSmokeError,"PICTURE_CHANGED"):
            self.mux()


if __name__=="__main__":
    unittest.main()
