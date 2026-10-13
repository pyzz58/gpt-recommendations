"""QO-D19: public synthetic spoken scene, exact timecoded sound over visual cuts."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agent_team
import director
import director_speech_cues as cues
import director_shot_coverage as coverage
import screenplay_series_delivery as series
from test_director_shot_coverage import proposal, shot, span
from test_screenplay_series_delivery import assemble_original, dossier, series_plan


def timed_plan(h, ds, plan):
    proof = series.validate_breakdown(h, ds, plan)
    episode = plan["episodes"][0]
    originals = {s["source_adaptation"]["beat_id"]: s
                 for s in h["reconstructed_base"]["shots"]}
    beats = {b["id"]: b for scene in h["screenplay_scenes"]
             for b in scene["beats"]}
    speech, subtitles = [], []
    for bid in episode["beat_ids"]:
        beat = beats[bid]
        duration = beat["duration_s"]
        source = []
        if beat["voiceover"]:
            source.append(("voiceover", 0, "NARRATOR", beat["voiceover"]))
        elif originals[bid]["narration"]:
            source.append(("narration", 0, "NARRATOR",
                           originals[bid]["narration"]))
        for i, d in enumerate(beat["dialogue"]):
            source.append(("dialogue", i, d["speaker"], d["line"]))
        # One original word sequence per spoken source. First B01 cue crosses
        # the 2.5-second picture cut: no duplication of its words.
        beat_speech = []
        for i, (kind, index, speaker, line) in enumerate(source):
            speech.append({
                "cue_id": f"C{len(speech)+1:03d}",
                "beat_id": bid, "source_kind": kind, "source_index": index,
                "speaker": speaker, "text_exact": line,
                "from_s": 1.0 + i * 1.5,
                "to_s": 4.0 + i * 1.5 if bid == "B01"
                        else min(duration - .25, 2.0 + i * 1.5),
                "audio_mode": "voiceover" if kind != "dialogue" else "off_screen",
            })
            beat_speech.append(speech[-1])
        caption = originals[bid]["subtitles"]["text"]
        if caption:
            separated = (beat_speech if caption == " ".join(c["text_exact"]
                           for c in beat_speech) else [])
            for item in (separated or [None]):
                subtitles.append({
                    "subtitle_id": f"T{len(subtitles)+1:03d}",
                    "beat_id": bid,
                    "source_cue_id": item["cue_id"] if item else None,
                    "text_exact": item["text_exact"] if item else caption,
                    "from_s": max(0, item["from_s"] - .2) if item else .5,
                    "to_s": min(duration, item["to_s"] + .2)
                            if item else duration - .25,
                })
    return {
        "version": cues.VERSION, "episode_id": "EP01",
        "source_screenplay_digest": proof["screenplay_digest"],
        "director_breakdown_digest": proof["director_breakdown_digest"],
        "cues": speech, "subtitles": subtitles,
    }


class TimedDialogueCoverageTests(unittest.TestCase):
    def setUp(self):
        self.h = assemble_original()
        self.ds = dossier(self.h)
        self.beats = [b for scene in self.h["screenplay_scenes"]
                      for b in scene["beats"]]
        self.plan = series_plan(self.h, self.ds, [len(self.beats)])
        self.packet = series.build_per_episode_crew(
            self.h, self.ds, self.plan)
        self.cues = timed_plan(self.h, self.ds, self.plan)
        first = self.beats[0]
        self.approved = proposal(
            self.h, self.ds, self.plan,
            [shot(1, [span(first["id"], 0, 2.5)]),
             shot(2, [span(first["id"], 2.5, first["duration_s"])])] +
            [shot(i, [span(b["id"], 0, b["duration_s"])])
             for i, b in enumerate(self.beats[1:], 3)])
        self.approved["speech_cue_timeline"] = deepcopy(self.cues)

    def test_dialogue_crosses_picture_cut_without_speech_or_caption_duplication(self):
        verified = coverage.validate(
            self.h, self.ds, self.plan, self.approved)
        self.assertEqual(verified["split_beats"], ["B01"])
        self.assertTrue(verified["speech_cue_receipt"]["source_text_exact"])
        rebuilt = coverage.reblock_episode(
            self.h, self.ds, self.plan, self.packet, self.approved)
        ep = rebuilt["episodes"][0]
        base = ep["authoritative_episode_base"]
        self.assertFalse(director.validate(base)[0])
        self.assertEqual(len(base["shots"]), len(self.beats) + 1)
        self.assertEqual(
            [x["id"] for x in base["shots"][0]["speech_cue_refs"]],
            ["C001"])
        self.assertEqual(
            [x["id"] for x in base["shots"][1]["speech_cue_refs"]],
            ["C001"])
        self.assertEqual(
            [x["source_adaptation"]["dialogue"] for x in base["shots"][:2]],
            [self.beats[0]["dialogue"], []])
        self.assertTrue(rebuilt["director_coverage_applied"]
                        ["speech_cue_timeline_attached"])
        self.assertEqual(agent_team.ready(ep["crew"]), ["director_brief"])
        self.assertEqual(len([s for s in self.cues["subtitles"]
                              if s["beat_id"] == "B03"]), 2)

    def test_real_director_role_request_receives_exact_audio_subtitle_timeline(self):
        import json
        rebuilt = coverage.reblock_episode(
            self.h, self.ds, self.plan, self.packet, self.approved)
        request = series.episode_director_request(
            self.h, self.ds, self.plan, rebuilt, "EP01",
            director_coverage=self.approved)
        self.assertFalse(request["external_model_call_authorized"])
        sep = "\n仅返回符合 output_json_schema 的 JSON，内容还必须满足专业岗位细则：\n"
        context = json.loads(request["messages"][1]["content"].split(sep, 1)[1])
        self.assertEqual(context["director_creative_shot_coverage"]
                         ["speech_cue_timeline"], self.cues)
        self.assertEqual(context["authoritative_base"]
                         ["director_speech_cue_timeline"], self.cues)

    def test_refuse_all_untrusted_cue_edits(self):
        for mutate in (
            lambda t: t["cues"][0].update(text_exact="改写台词"),
            lambda t: t["cues"][0].update(speaker="陌生人"),
            lambda t: t["cues"][0].update(from_s=-1),
            lambda t: t["cues"][0].update(to_s=8),
            lambda t: t["cues"].pop(0),
            lambda t: t["subtitles"][0].update(text_exact="假字幕"),
            lambda t: t["subtitles"][0].update(source_cue_id="C999"),
            lambda t: t["subtitles"][0].update(to_s=.7),
            lambda t: t["cues"][0].update(audio_mode="invalid"),
            lambda t: t.update(source_screenplay_digest="stale"),
        ):
            with self.subTest(mutate=mutate):
                bad = deepcopy(self.approved)
                mutate(bad["speech_cue_timeline"])
                with self.assertRaises(cues.SpeechCueError):
                    coverage.validate(self.h, self.ds, self.plan, bad)

    def test_without_cue_timeline_old_fail_closed_behavior_remains(self):
        bad = deepcopy(self.approved)
        del bad["speech_cue_timeline"]
        with self.assertRaisesRegex(
                coverage.ShotCoverageError,
                "COVERAGE_CANNOT_SPLIT_UNTIMED_SPEECH"):
            coverage.validate(self.h, self.ds, self.plan, bad)

    def test_overlapping_consecutive_dialogue_rejected(self):
        bad = deepcopy(self.approved)
        # B03 has two utterances; overlapping windows violate spoken order.
        by_b03 = [c for c in bad["speech_cue_timeline"]["cues"]
                  if c["beat_id"] == "B03"]
        self.assertEqual(len(by_b03), 2)
        by_b03[1]["from_s"] = by_b03[0]["from_s"] + .1
        with self.assertRaisesRegex(cues.SpeechCueError, "OVERLAPPING"):
            coverage.validate(self.h, self.ds, self.plan, bad)


if __name__ == "__main__":
    unittest.main()
