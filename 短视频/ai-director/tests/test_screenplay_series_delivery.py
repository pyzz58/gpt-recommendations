"""All-public QO-W11/QO-D13: 10-minute script -> director-selected <=90s series."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import agent_team
import director
import screenplay_adaptation as adaptation
import screenplay_director_handoff as script_bridge
import screenplay_series_delivery as serial

FIXTURE = ROOT / "examples" / "dinner-dialogue-review"


def assemble_original():
    base = json.loads((FIXTURE / "plan.json").read_text("utf-8"))
    source = (FIXTURE / "source.md").read_text("utf-8")
    draft = json.loads((FIXTURE / "adaptation_proposal.json").read_text("utf-8"))
    packet = adaptation.build_review_packet(base, source, draft)
    form = script_bridge.review_form(packet)
    form["review_intent"] = "accept_for_director_planning"
    for row in form["changes"]:
        row["choice"] = "accept"
    speakers = {d["speaker"] for scene in draft["scenes"]
                for b in scene["beats"] for d in b["dialogue"]}
    bindings = {speaker: {"character_id": "CHAR01" if i == 0 else "CHAR02",
                           "identity_note": "公开虚构人物"} for i, speaker in enumerate(sorted(speakers))}
    return script_bridge.prepare_handoff(base, source, packet, form, bindings)


def dossier(h):
    return {
        "version": serial.VERSION,
        "screenplay_digest": h["screenplay_text_digest"],
        "proposal_digest": h["accepted_screenplay_proposal_digest"],
        "scenes": [{
            "scene_id": scene["id"],
            "setting_and_time": "故事发生于安静的室内，此处需要交代进入时的人物与环境。",
            "starting_state": "人物刚开始还不愿回答问题，对方仍等待具体反馈。",
            "story_purpose": "本场推动人物在选择与情绪方面出现具体而可见的变化。",
            "character_or_idea_objective": "一方想弄清楚对方真正的动机，另一方希望避免说出真相。",
            "physical_progression": "一人开口、另一人整理桌面的物件、停顿后才正面回应。",
            "emotional_or_cognitive_shift": "从回避和不理解走向理解对方有未表达的需要。",
            "sound_dialogue_silence_intent": "对白由既有剧本决定，沉默用于表现人物正在衡量自己的选择。",
            "props_and_continuity": "桌面物件在动作前后应保持一致，道具位置不能任意发生变化。",
            "handoff_to_next": "本场结束带有尚未完全解开的关系问题，自然推动后续场次。",
            "beats": [{
                "beat_id": beat["id"],
                "observable_action_and_reaction": "人物停下手中动作，听见对方的话后才抬起头回应。",
                "motivation_or_argument_link": "上一句话改变了人物对对方意图的判断，从而触发下一步行动。",
                "change_in_state": "人物态度由回避变成开始正面面对需要处理的问题。",
                "what_director_must_understand": "此处是必须看得出来的态度转折，不是让镜头随意装饰。",
            } for beat in scene["beats"]],
        } for scene in h["screenplay_scenes"]],
    }


def series_plan(h, ds, groups, *, intro=0, extra_evidence=0):
    beat_ids = [b["id"] for s in h["screenplay_scenes"] for b in s["beats"]]
    out = []
    at = 0
    for n, count in enumerate(groups, 1):
        ids = beat_ids[at:at + count]
        at += count
        out.append({
            "episode_id": f"EP{n:02d}", "episode_title": f"第{n}集·重要转折",
            "beat_ids": ids,
            "opening_hook": "观众开场要知道这一集的中心问题来自上一集哪些变化。",
            "narrative_progression": "故事在这一集发生可见的行动与明确的因果推进。",
            "emotional_or_idea_shift": "人物态度或观众认识发生了可以明确描述的变化。",
            "local_payoff": "本集提出的问题获得适度回报，不用编造新的悬念。",
            "connection_to_next": "为接下来的人物选择或下一个思想步骤自然建立关联。",
            "break_reason": "选择有意义的故事与情绪断点，而不是机械截到90秒。",
            "continuity_note": "人物身份、动作结束状态、道具和时空持续与整部剧本一致。",
            "intro_s": intro, "recap_s": 0, "bridge_s": 0,
            "outro_s": 0, "evidence_s": extra_evidence if n == len(groups) else 0,
        })
    return {
        "version": serial.VERSION,
        "screenplay_digest": h["screenplay_text_digest"],
        "writer_dossier_digest": agent_team.fingerprint(ds),
        "director_reason_for_episode_count": "按故事真实节拍拆分，留下可供单集观看的起止，并确保总计不漏。",
        "episodes": out,
    }


def long_story():
    """Expand a public in-memory 44s test film to an invented 600s whole script."""
    h = assemble_original()
    orig_base = h["reconstructed_base"]
    first = orig_base["shots"][0]
    first_scene = deepcopy(h["screenplay_scenes"][0])
    first_beat = deepcopy(first_scene["beats"][0])
    created = []
    newshots = []
    for i in range(20):
        b = deepcopy(first_beat)
        b["id"] = f"B{i+1:03d}"
        b["duration_s"] = 30
        b["action"] = f"第{i+1}次关于架桥目的的公开虚构讨论中，人物对彼此的选择有了新的认识。"
        b["voiceover"] = ""
        b["dialogue"] = []
        created.append(b)
        sh = deepcopy(first)
        sh["id"] = f"S{i+1:02d}"
        sh["start"] = i * 30
        sh["duration"] = 30
        sh["purpose"] = b["dramatic_function"]
        sh["narration"] = ""
        sh["source_adaptation"]["beat_id"] = b["id"]
        sh["source_adaptation"]["dialogue"] = []
        sh["subtitles"]["text"] = ""
        newshots.append(sh)
    first_scene["beats"] = created
    h["screenplay_scenes"] = [first_scene]
    h["screenplay_fountain"] = "Title: 虚构十分钟剧本\n" + "\n".join(
        beat["action"] for beat in created)
    h["screenplay_text_digest"] = hashlib.sha256(
        h["screenplay_fountain"].encode("utf-8")).hexdigest()
    h["accepted_screenplay_proposal_digest"] = "public-synthetic-proposal-digest"
    orig_base["shots"] = newshots
    orig_base["duration"] = 600
    orig_base["scenes"] = [orig_base["scenes"][0]]
    orig_base["editorial"]["narration_script"] = ""
    orig_base["screenplay_handoff_mode"]["screenplay_sha256"] = h["screenplay_text_digest"]
    h["director_base_digest"] = agent_team.fingerprint(orig_base)
    h["director_source_digest"] = h["screenplay_text_digest"]
    h["crew"] = agent_team.start(orig_base, source_text=h["screenplay_fountain"])
    assert not director.validate(orig_base)[0]
    return h


class WriterDirectorSeriesTests(unittest.TestCase):
    def test_writer_explains_every_scene_and_beat_not_lens_choices(self):
        h = assemble_original()
        info = dossier(h)
        result = serial.validate_dossier(h, info)
        self.assertGreater(result["fully_explained_beats"], 0)
        self.assertFalse(result["actual_creative_quality_human_verified"])
        req = serial.dossier_request(h)
        self.assertFalse(req["dispatch_allowed"])
        self.assertIn("导演无需猜测故事", req["messages"][0]["content"])
        self.assertIn("导演无需猜测故事", req["messages"][0]["content"])
        broken = deepcopy(info)
        broken["scenes"][0]["beats"].pop()
        with self.assertRaisesRegex(serial.SeriesDeliveryError, "BEAT_COVERAGE"):
            serial.validate_dossier(h, broken)
        broken = deepcopy(info)
        broken["scenes"][0]["physical_progression"] = ""
        with self.assertRaisesRegex(serial.SeriesDeliveryError, "MISSING_DETAIL"):
            serial.validate_dossier(h, broken)
        broken = deepcopy(info)
        broken["screenplay_digest"] = "stale"
        with self.assertRaisesRegex(serial.SeriesDeliveryError, "DOSSIER_STALE"):
            serial.validate_dossier(h, broken)

    def test_long_script_has_free_director_10_episode_choice(self):
        h = long_story()
        details = dossier(h)
        request = serial.director_breakdown_request(h, details)
        self.assertEqual(request["max_episode_seconds"], 90)
        self.assertEqual(len(h["screenplay_scenes"][0]["beats"]), 20)
        plan = series_plan(h, details, [2] * 10, intro=2)
        validation = serial.validate_breakdown(h, details, plan)
        self.assertEqual(validation["episode_count"], 10)
        self.assertEqual(validation["whole_story_duration_s"], 600)
        self.assertEqual(validation["total_delivery_estimate_s"], 620)
        self.assertTrue(validation["all_screenplay_beats_preserved"])
        self.assertTrue(all(x["total_s"] == 62 for x in validation["episodes"]))
        self.assertFalse(validation["director_choices_human_approved"])
        crew = serial.build_per_episode_crew(h, details, plan)
        self.assertEqual(len(crew["episodes"]), 10)
        self.assertEqual(crew["episodes"][1]["authoritative_episode_base"]["duration"], 60)
        self.assertEqual(crew["episodes"][1]["authoritative_episode_base"]["shots"][0]["start"], 0)
        first_request = serial.episode_director_request(
            h, details, plan, crew, "EP01")
        self.assertIn("90秒分集硬约束", first_request["messages"][0]["content"])
        self.assertEqual(first_request["episode_director_context"]["max_episode_s"], 90)
        self.assertFalse(first_request["external_model_call_authorized"])
        marker = "\n仅返回符合 output_json_schema 的 JSON，内容还必须满足专业岗位细则：\n"
        _, token, encoded = first_request["messages"][1]["content"].partition(marker)
        self.assertTrue(token)
        data = json.loads(encoded)
        self.assertEqual(data["original_script"], h["screenplay_fountain"])
        self.assertEqual(data["current_episode_story_and_break_reason"]["episode_id"],
                         "EP01")
        self.assertEqual(data["current_episode_detailed_writer_intent"][0]["beats"][0]
                         ["beat_id"], "B001")

    def test_no_arbitrary_three_episode_cap_and_exact_90_allowed(self):
        h = long_story()
        ds = dossier(h)
        plan = series_plan(h, ds, [3, 3, 3, 3, 3, 3, 2])
        receipt = serial.validate_breakdown(h, ds, plan)
        self.assertEqual(receipt["episode_count"], 7)
        self.assertEqual(receipt["episodes"][0]["total_s"], 90)
        self.assertEqual(receipt["episodes"][-1]["total_s"], 60)

    def test_real_90_second_overflow_or_hidden_extras_fail(self):
        h = long_story()
        ds = dossier(h)
        plan = series_plan(h, ds, [3, 3, 3, 3, 3, 3, 2], intro=1)
        with self.assertRaisesRegex(serial.SeriesDeliveryError, "EXCEEDS_90_SECONDS"):
            serial.validate_breakdown(h, ds, plan)

    def test_missing_reordered_duplicated_episode_beats_fail(self):
        h = long_story()
        ds = dossier(h)
        plan = series_plan(h, ds, [2] * 10)
        del plan["episodes"][-1]["beat_ids"][-1]
        with self.assertRaisesRegex(serial.SeriesDeliveryError, "MISSING_DUPLICATED"):
            serial.validate_breakdown(h, ds, plan)
        plan = series_plan(h, ds, [2] * 10)
        plan["episodes"][1]["beat_ids"] = list(reversed(plan["episodes"][1]["beat_ids"]))
        with self.assertRaisesRegex(serial.SeriesDeliveryError, "MISSING_DUPLICATED"):
            serial.validate_breakdown(h, ds, plan)
        plan = series_plan(h, ds, [2] * 10)
        plan["episodes"][0]["beat_ids"].append(plan["episodes"][1]["beat_ids"][0])
        with self.assertRaisesRegex(serial.SeriesDeliveryError, "MISSING_DUPLICATED"):
            serial.validate_breakdown(h, ds, plan)

    def test_no_source_no_evidence_card_and_no_made_up_bibliography(self):
        h = long_story()
        ds = dossier(h)
        plan = series_plan(h, ds, [2] * 10, extra_evidence=2)
        with self.assertRaisesRegex(serial.SeriesDeliveryError, "UNSUPPORTED_EVIDENCE_PAGE"):
            serial.validate_breakdown(h, ds, plan)
        h["source_supplied_reference_url_count"] = 1
        result = serial.validate_breakdown(h, ds, plan)
        self.assertEqual(result["episodes"][-1]["reserved_s"], 2)
        bad = deepcopy(plan)
        bad["episodes"][-1]["evidence_s"] = 3
        with self.assertRaisesRegex(serial.SeriesDeliveryError, "UNSUPPORTED_EVIDENCE_PAGE"):
            serial.validate_breakdown(h, ds, bad)

    def test_long_script_not_silently_shortened_before_director(self):
        h = long_story()
        ds = dossier(h)
        req = serial.director_breakdown_request(h, ds)
        prompt = json.loads(req["messages"][1]["content"])
        self.assertEqual(len(prompt["beat_timeline"]), 20)
        self.assertEqual(sum(x["duration_s"] for x in prompt["beat_timeline"]), 600)
        self.assertEqual(prompt["complete_screenplay"], h["screenplay_fountain"])

    def test_readable_episode_request_fails_on_tampered_crew_packet(self):
        h = long_story()
        ds = dossier(h)
        plan = series_plan(h, ds, [2] * 10)
        crew = serial.build_per_episode_crew(h, ds, plan)
        crew["episodes"][0]["authoritative_episode_base"]["title"] = "篡改剧情"
        with self.assertRaisesRegex(serial.SeriesDeliveryError, "CREW_PACKET_TAMPERED"):
            serial.episode_director_request(h, ds, plan, crew, "EP01")

    def test_actual_fulltext_pipeline_accepts_600s_then_requires_director_split(self):
        import screenplay_fulltext_intake as fulltext
        # 20 independent invented source units, no user/private manuscript.
        sentence = "村里的人逐渐发现，建造这座桥并非只是更快地完成工程，而是理解它服务于谁以及为何值得建造"
        source = "\n\n".join(
            sentence + "，第" + str(i) + "次讨论带来新的疑问。" for i in range(20))
        indexed = fulltext.prepare_fulltext(source, risk_domain="none")
        units = indexed["scope_units"]
        beats = [{
            "id": f"B{i+1:03d}",
            "source_ids": [unit["id"]],
            "operation": "keep",
            "dramatic_function": "用行动展示关于修桥目的的新信息如何改变在场人物的认识。",
            "action": f"第{i+1}次公开虚构会议上，村民走到桥梁地图前讨论新的选择。",
            "dialogue": [],
            "voiceover": "",
            "duration_s": 30,
            "editorial_reason": "保留整部故事的不同选择，交由总导演决定合理分集。",
        } for i, unit in enumerate(units)]
        self.assertGreater(len(beats), 10)
        scenes = [{
            "id": f"SC{i//4+1:02d}", "heading": "INT. 村委会会议室 - 日",
            "beats": beats[i:i+4]
        } for i in range(0, len(beats), 4)]
        proposal = {
            "version": adaptation.VERSION,
            "theme": "桥的意义", "dramatic_question": "桥究竟为谁而建？",
            "turning_point": "村民从比较工期走向对目的的探问。",
            "payoff": "结尾让问题保持开放，而不编造确定结论。",
            "scenes": scenes, "omissions": [],
        }
        packet = adaptation.build_review_packet(indexed["base"], source, proposal)
        self.assertEqual(packet["review"]["estimated_duration_s"], len(units)*30)
        self.assertGreater(packet["review"]["estimated_duration_s"], 300)
        form = script_bridge.review_form(packet)
        form["review_intent"] = "accept_for_director_planning"
        for row in form["changes"]:
            row["choice"] = "accept"
        assembled = script_bridge.prepare_handoff(
            indexed["base"], source, packet, form, {})
        self.assertEqual(assembled["next_professional_role"],
                         "director_series_breakdown")
        with self.assertRaisesRegex(script_bridge.ScriptHandoffError,
                                    "MUST_SPLIT_EPISODES_FIRST"):
            script_bridge.director_request(assembled)
        ds = dossier(assembled)
        director_request = serial.director_breakdown_request(assembled, ds)
        self.assertFalse(director_request["dispatch_allowed"])
        data = json.loads(director_request["messages"][1]["content"])
        self.assertEqual(len(data["beat_timeline"]), len(units))

    def test_dossier_must_change_when_writer_changes_screenplay(self):
        h = assemble_original()
        ds = dossier(h)
        h["screenplay_fountain"] += "\n修改后的故事"
        with self.assertRaisesRegex(serial.SeriesDeliveryError, "UNTRUSTED_SCRIPT_HANDOFF"):
            serial.validate_dossier(h, ds)


if __name__ == "__main__":
    unittest.main()
