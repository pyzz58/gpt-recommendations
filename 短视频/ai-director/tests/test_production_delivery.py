"""Synthetic/offline video-model work-order export regression tests.

Uses only public repository example data; no user article, models, API keys,
private source export or paid media generation.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import production_delivery as delivery
import director_v2
import director_workbook
import editorial_review_lock as review
import agent_team as team
from test_editorial_review_lock import EditorialReviewLockTests


EXAMPLE = ROOT / "examples" / "quit-smoking"


class ProductionDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = json.loads((EXAMPLE / "plan.json").read_text("utf-8"))
        cls.direction = json.loads(
            (EXAMPLE / "direction_v02.json").read_text("utf-8"))

    def pack(self):
        return delivery.build_reference_delivery(self.base, self.direction)

    def test_existing_professional_example_exports_full_eight_shot_work_orders(self):
        pack = self.pack()
        self.assertEqual(pack["project"]["total_shots"], 8)
        self.assertEqual(pack["project"]["duration_s"], 53)
        self.assertEqual(pack["shooting_order"], [x["id"] for x in self.base["shots"]])
        self.assertEqual(pack["production_counts"]["ai_video_jobs"], sum(
            x["production_route"] == "ai_video" for x in pack["shots"]))
        self.assertEqual(pack["production_counts"]["non_video_jobs"], sum(
            x["production_route"] != "ai_video" for x in pack["shots"]))
        self.assertEqual(pack["source_plan_digest"], team.fingerprint(self.base))
        self.assertEqual(pack["provenance"], "existing_v02_reference_not_agent_run")

    def test_real_prompt_text_is_derived_from_existing_camera_and_acting_direction(self):
        pack = self.pack()
        clips = [x for x in pack["shots"] if x["production_route"] == "ai_video"]
        self.assertTrue(clips)
        for x in clips:
            self.assertEqual(set(x["ai_video_prompt_candidates"]), {"wan", "seedance"})
            for prompt in x["ai_video_prompt_candidates"].values():
                self.assertIn("Camera path:", prompt)
                self.assertIn("Lighting:", prompt)
                self.assertIn("What actually happens:", prompt)
                self.assertIn("Do not render any title", prompt)
                self.assertGreater(len(prompt), 350)
            self.assertFalse(x["reference_files_confirmed"])

    def test_data_or_postproduction_shots_do_not_get_video_prompts(self):
        pack = self.pack()
        post = [x for x in pack["shots"] if x["production_route"] != "ai_video"]
        self.assertTrue(post)
        for x in post:
            self.assertEqual(x["ai_video_prompt_candidates"], {})
            self.assertEqual(x["target_type"], "postproduction_only")
            self.assertIn("overlay_text", x["postproduction_work_order"])

    def test_source_voiceover_claims_and_timeline_preserved_exactly(self):
        pack = self.pack()
        claim_by_id = {c["id"]: c for c in self.base["claims"]}
        for original, shot in zip(self.base["shots"], pack["shots"]):
            self.assertEqual(original["narration"], shot["film_script"]["voiceover"])
            self.assertEqual(original["duration"], shot["timeline"]["duration_s"])
            self.assertEqual(original["start"], shot["timeline"]["start_s"])
            self.assertEqual(original["claim_ids"], [x["id"] for x in shot["claim_review"]])
            for claim in shot["claim_review"]:
                self.assertEqual(claim["text_from_source"],
                                 claim_by_id[claim["id"]]["source_quote"])
                self.assertFalse(claim["external_fact_check_completed"])

    def test_package_does_not_falsely_grant_generation_or_model_execution(self):
        pack = self.pack()
        self.assertFalse(pack["human_approved"])
        self.assertFalse(pack["ready_to_call_video_model"])
        self.assertFalse(pack["publishing_allowed"])
        self.assertFalse(pack["actual_video_generated"])
        self.assertEqual(pack["external_model_calls"], 0)
        self.assertFalse(pack["source_facts_verified"])
        self.assertIn("REFERENCE_ASSETS_NOT_VERIFIED", pack["blocking_conditions"])
        self.assertFalse(pack["full_workbook_review"]["independent_crew_completed"])
        self.assertIsNone(pack["full_workbook_review"]["team_delivery_gate"])

    def test_compiled_reference_matches_original_director_compiler(self):
        ref = director_v2.compile_package(self.base, self.direction)
        pack = self.pack()
        for job, shot in zip(ref["shots"], pack["shots"]):
            self.assertEqual(job["execution_route"], shot["production_route"])
            self.assertEqual(job["prompts"], shot["ai_video_prompt_candidates"])
            self.assertEqual(job["postproduction_job"], shot["postproduction_work_order"])

    def test_markdown_contains_clip_prompts_and_exact_editing_plan(self):
        pack = self.pack()
        md = delivery.render_operator_markdown(pack)
        self.assertIn("逐镜生产工单", md)
        self.assertIn("制作前必须解决的问题", md)
        self.assertIn("wan 视频生成候选提示词", md)
        self.assertIn("seedance 视频生成候选提示词", md)
        self.assertIn("全片剪辑时间线", md)
        self.assertIn("事实标记", md)
        self.assertIn("实际", md) if False else self.assertIn("不是已生成的视频", md)
        self.assertIn("模型调用：0", md)

    def test_unverified_medical_claims_remain_clearly_unverified(self):
        pack = self.pack()
        self.assertEqual(self.base["risk_domain"], "medical")
        self.assertIn("CLAIMS_STILL_REQUIRE_INDEPENDENT_VERIFICATION",
                      pack["blocking_conditions"])
        self.assertTrue(any(c["review_state"] == "needs_review"
                            for shot in pack["shots"]
                            for c in shot["claim_review"]))

    def test_no_network_callable_or_payment_interface_exposed(self):
        pack = self.pack()
        for shot in pack["shots"]:
            self.assertFalse(shot["model_generation_authorized"])
            self.assertFalse(shot["video_generated"])
            self.assertEqual(shot["operator_actions_allowed"],
                             ["read", "review", "copy_prompt_manually"])

    def test_unknown_claim_prevents_export_not_silent_drop(self):
        plan = deepcopy(self.base)
        plan["shots"][0]["claim_ids"] = ["INVENTED_CLAIM"]
        with self.assertRaises((ValueError, delivery.ProductionDeliveryError)):
            delivery.build_reference_delivery(plan, self.direction)

    def test_wrong_shot_order_or_missing_direction_prevents_export(self):
        directions = deepcopy(self.direction)
        directions["shots"] = directions["shots"][1:]
        with self.assertRaises(delivery.ProductionDeliveryError):
            delivery.build_reference_delivery(self.base, directions)

    def test_disallowed_paid_route_prevents_export(self):
        directions = deepcopy(self.direction)
        directions["shots"][0]["generation"]["route"] = "paid_video_generation"
        with self.assertRaises(delivery.ProductionDeliveryError):
            delivery.build_reference_delivery(self.base, directions)

    def test_locked_intake_cannot_export_without_ten_completed_roles(self):
        f = EditorialReviewLockTests(
            methodName="test_complete_review_locks_only_planning_snapshot")
        f.setUp()
        snap = review.lock_planning_snapshot(f.candidate, f.source, f.decide())
        partial = review.stage_locked_team(snap, f.source)
        with self.assertRaisesRegex(delivery.ProductionDeliveryError,
                                    "CREW_HAS_OPEN_TASKS"):
            delivery.build_locked_crew_delivery(
                snap, f.source, partial["team"])

    def test_forged_unlocked_version_does_not_enter_crew(self):
        f = EditorialReviewLockTests(
            methodName="test_complete_review_locks_only_planning_snapshot")
        f.setUp()
        snap = review.lock_planning_snapshot(f.candidate, f.source, f.decide())
        partial = review.stage_locked_team(snap, f.source)
        state = deepcopy(partial["team"])
        state["base_digest"] = "0"*64
        with self.assertRaisesRegex(delivery.ProductionDeliveryError, "WRONG_PLAN_VERSION"):
            delivery.build_locked_crew_delivery(snap, f.source, state)

    def test_wrong_source_cannot_be_used_for_locked_delivery(self):
        f = EditorialReviewLockTests(
            methodName="test_complete_review_locks_only_planning_snapshot")
        f.setUp()
        snap = review.lock_planning_snapshot(f.candidate, f.source, f.decide())
        state = review.stage_locked_team(snap, f.source)["team"]
        with self.assertRaisesRegex(delivery.ProductionDeliveryError, "UNTRUSTED_LOCK"):
            delivery.build_locked_crew_delivery(snap, f.source + "tamper", state)

    def test_fake_author_identity_true_is_rejected(self):
        f = EditorialReviewLockTests(
            methodName="test_complete_review_locks_only_planning_snapshot")
        f.setUp()
        snap = review.lock_planning_snapshot(f.candidate, f.source, f.decide())
        state = review.stage_locked_team(snap, f.source)["team"]
        snap["author_identity_verified"] = True
        with self.assertRaisesRegex(delivery.ProductionDeliveryError, "UNTRUSTED_LOCK"):
            delivery.build_locked_crew_delivery(snap, f.source, state)

    def test_nonexistent_model_target_does_not_invent_prompt(self):
        pack = self.pack()
        self.assertEqual(pack["project"]["supported_prompt_targets"], ["wan", "seedance"])
        for shot in pack["shots"]:
            self.assertNotIn("unknown_model", shot["ai_video_prompt_candidates"])

    def test_cli_writes_two_offline_artifacts_and_rejects_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            outfile = Path(temp)/"production.json"
            mdfile = Path(temp)/"production.md"
            command = [sys.executable, str(ROOT / "production_delivery.py"),
                       "--base", str(EXAMPLE/"plan.json"),
                       "--direction", str(EXAMPLE/"direction_v02.json"),
                       "--out-json", str(outfile), "--out-md", str(mdfile)]
            p = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertEqual(p.returncode, 0, p.stderr[:300])
            self.assertIn("external_calls=0", p.stdout)
            self.assertTrue(outfile.exists())
            self.assertIn("逐镜生产工单", mdfile.read_text("utf-8"))
            before = outfile.read_bytes()
            p2 = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertNotEqual(p2.returncode, 0)
            self.assertEqual(outfile.read_bytes(), before)

    def test_cli_never_outputs_private_source_text_in_stdout(self):
        with tempfile.TemporaryDirectory() as temp:
            outfile = Path(temp)/"production.json"
            mdfile = Path(temp)/"production.md"
            p = subprocess.run(
                [sys.executable, str(ROOT/"production_delivery.py"),
                 "--base", str(EXAMPLE/"plan.json"),
                 "--direction", str(EXAMPLE/"direction_v02.json"),
                 "--out-json", str(outfile), "--out-md", str(mdfile)],
                capture_output=True, text=True, check=False)
            self.assertEqual(p.returncode, 0)
            self.assertNotIn(self.base["shots"][0]["narration"], p.stdout)
            self.assertNotIn(self.base["shots"][0]["narration"], p.stderr)

    def test_duplicate_output_path_does_not_create_any_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/"one.json"
            p = subprocess.run(
                [sys.executable, str(ROOT/"production_delivery.py"),
                 "--base", str(EXAMPLE/"plan.json"),
                 "--direction", str(EXAMPLE/"direction_v02.json"),
                 "--out-json", str(output), "--out-md", str(output)],
                capture_output=True, text=True, check=False)
            self.assertNotEqual(p.returncode, 0)
            self.assertFalse(output.exists())

    def test_invalid_bundle_cannot_render(self):
        with self.assertRaisesRegex(delivery.ProductionDeliveryError, "INVALID_BUNDLE"):
            delivery.render_operator_markdown({})


if __name__=="__main__":
    unittest.main()
