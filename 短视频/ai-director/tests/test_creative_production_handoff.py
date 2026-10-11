"""First AI director idea survives the v0.1 planning lock -> full film crew.

Entirely fictional fixtures. Neither DeepSeek requests nor private user scripts.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import creative_production_handoff as bridge
import editorial_review_lock as review
import agent_role_contracts as roles
import agent_team as team
import production_delivery
import test_editorial_review_lock as source_fixture
import test_agent_live_crew as crew_fixture


class IntentHandoffTests(unittest.TestCase):
    def setUp(self):
        self.f=source_fixture.EditorialReviewLockTests(
            "test_complete_review_locks_only_planning_snapshot")
        self.f.setUp()
        self.candidate=self.f.candidate
        self.source=self.f.source
        self.lock=review.lock_planning_snapshot(
            self.candidate,self.source,self.f.decide())

    def test_lock_persists_real_early_vision_not_just_restarted_team(self):
        bound=bridge.validate_locked_handoff(self.lock,self.source)
        self.assertEqual(bound["creative_concept"],
                         self.candidate["editorial_concept"])
        self.assertEqual(bound["candidate_plan_digest"],
                         self.lock["plan_digest"])
        self.assertEqual(bound["episode_source_digest"],
                         self.lock["source_digest"])
        self.assertFalse(bound["human_approved"])
        staged=review.stage_locked_team(self.lock,self.source)
        self.assertTrue(staged["first_editorial_vision_bound"])
        self.assertFalse(staged["production_ready"])
        self.assertFalse(staged["paid_api_authorized"])

    def test_tampered_or_removed_intent_fails_closed_before_role_dispatch(self):
        for mutation in ("missing","altered","rebased","different_source",
                         "edited_preflight","missing_preflight"):
            snapshot=deepcopy(self.lock)
            source=self.source
            if mutation=="missing":
                del snapshot["creative_handoff"]
            if mutation=="altered":
                snapshot["creative_handoff"]["creative_concept"]["shot_designs"][0][
                    "camera_intention"]="unapproved change to first director vision"
            if mutation=="rebased":
                snapshot["creative_handoff"]["candidate_plan_digest"]="a"*64
                snapshot["creative_handoff_digest"]=team.fingerprint(
                    snapshot["creative_handoff"])
            if mutation=="different_source":
                source=self.source+"CHANGED"
            if mutation=="edited_preflight":
                snapshot["production_preflight"]["issues"]=[]
            if mutation=="missing_preflight":
                del snapshot["production_preflight"]
            with self.subTest(mutation=mutation):
                with self.assertRaises((bridge.HandoffError,
                                        review.EditorialReviewError)):
                    review.stage_locked_team(snapshot,source)

    def test_well_formed_role_prompt_carries_original_exact_visual_plan(self):
        team_state=review.stage_locked_team(self.lock,self.source)["team"]
        packet=roles.build_role_messages(
            self.lock["plan"],team_state,"director_brief",
            source_text=self.source,
            editorial_handoff=self.lock["creative_handoff"])
        body=packet["messages"][1]["content"]
        self.assertIn("first_director_editor_vision",body)
        self.assertIn("production_gaps_to_resolve",body)
        exact=self.candidate["editorial_concept"]["shot_designs"][0][
            "visual_intention"]
        self.assertIn(exact,body)
        self.assertIn(self.lock["plan_digest"],body)
        self.assertFalse(packet["external_model_call_authorized"])
        self.assertFalse(packet["human_approved"])

    def test_handoff_role_prompt_refuses_other_source_state(self):
        state=review.stage_locked_team(self.lock,self.source)["team"]
        tampered=deepcopy(self.lock["creative_handoff"])
        tampered["episode_source_digest"]="b"*64
        with self.assertRaises(ValueError):
            roles.build_role_messages(
                self.lock["plan"],state,"director_brief",
                source_text=self.source,editorial_handoff=tampered)

    def test_real_2026_failure_patterns_filled_into_synthetic_plan_are_flagged(self):
        # Synthetic reproducer of structural errors found in public fiction
        # DeepSeek report: ai_video still carries a postproduction template.
        candidate=deepcopy(self.candidate)
        plan=candidate["candidate_plan"]
        scene=plan["scenes"][0]
        scene["description"]="纯后期图卡占位，待摄影美术与总导演设计"
        shot=plan["shots"][0]
        shot["visual_type"]="ai_video"
        shot["camera"]["shot_size"]="postproduction"
        shot["camera"]["angle"]="n/a"
        shot["camera"]["lens"]="n/a"
        shot["art"]["set_props"]="文字或数据图形"
        shot["character_ids"]=[]
        candidate["editorial_concept"]["shot_designs"][0]["visual_type"]="ai_video"
        candidate["candidate_base_digest"]=team.fingerprint(plan)
        handoff=bridge.bound_handoff(candidate,self.source)
        report=bridge.inspect_preproduction(plan,handoff)
        codes={x["code"] for x in report["issues"] if "S01" in x["shot_ids"]}
        self.assertIn("VIDEO_CAMERA_SHOT_SIZE_UNRESOLVED",codes)
        self.assertIn("VIDEO_CAMERA_LENS_UNRESOLVED",codes)
        self.assertIn("VIDEO_SCENE_FLOORPLAN_UNRESOLVED",codes)
        self.assertIn("VIDEO_CAST_BINDING_NOT_DECLARED",codes)
        self.assertIn("VIDEO_PHYSICAL_PROPS_UNRESOLVED",codes)
        self.assertFalse(report["physical_floorplan_verified"])
        self.assertFalse(report["production_ready"])
        self.assertFalse(report["human_approved"])

    def test_light_handoff_gaps_are_review_not_unverified_semantic_truth(self):
        candidate=deepcopy(self.candidate)
        intent=candidate["editorial_concept"]["shot_designs"]
        intent[0]["light_intention"]="前一镜近全黑，没有门缝漏光"
        intent[1]["light_intention"]="后一镜门缝有微光"
        handoff=bridge.bound_handoff(candidate,self.source)
        rep=bridge.inspect_preproduction(candidate["candidate_plan"],handoff)
        lighting=[x for x in rep["issues"]
                  if x["code"]=="ADJACENT_LIGHT_SOURCE_TRANSITION_UNVERIFIED"]
        self.assertTrue(lighting)
        self.assertEqual(lighting[0]["shot_ids"],[
            intent[0]["shot_id"],intent[1]["shot_id"]])
        self.assertTrue(all(x["severity"]=="review" for x in lighting))
        self.assertFalse(rep["lighting_continuity_verified"])

    def test_non_video_requires_review_but_no_invalid_video_job(self):
        candidate=deepcopy(self.candidate)
        for shot,design in zip(candidate["candidate_plan"]["shots"],
                               candidate["editorial_concept"]["shot_designs"]):
            shot["visual_type"]=design["visual_type"]="motion_graphic"
        candidate["candidate_base_digest"]=team.fingerprint(
            candidate["candidate_plan"])
        bound=bridge.bound_handoff(candidate,self.source)
        report=bridge.inspect_preproduction(candidate["candidate_plan"],bound)
        self.assertFalse(any(x["code"].startswith("VIDEO_CAMERA_")
                             for x in report["issues"]))
        self.assertTrue(any(x["severity"]=="info" for x in report["issues"]))
        self.assertFalse(report["production_ready"])

    def test_fully_compiled_operator_document_retains_first_director_idea(self):
        fixture=crew_fixture.LockedCrewPilotTests(
            "test_full_ten_role_synthetic_pipeline_never_claims_real_approval")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        with __import__("agent_live_pilot").PilotJournal(
                fixture.tmp.name,fixture.config) as j:
            state=fixture.state
            for tid in team.SPECS:
                state,_=fixture._step(j,state,tid)
        bundle=production_delivery.build_locked_crew_delivery(
            fixture.snapshot,fixture.original,state)
        source_visions=fixture.snapshot["creative_handoff"][
            "creative_concept"]["shot_designs"]
        self.assertEqual(len(bundle["shots"]),len(source_visions))
        self.assertEqual(
            bundle["creative_intent_provenance"][
                "first_director_editor_intent_digest"],
            fixture.snapshot["creative_handoff_digest"])
        for row,pitch in zip(bundle["shots"],source_visions):
            self.assertEqual(row["first_director_editor_vision"][
                "camera_intention"],pitch["camera_intention"])
            self.assertFalse(row["film_script"]["voiceover"] is None)
        text=production_delivery.render_operator_markdown(bundle)
        self.assertIn("第一轮导演与剧本编辑的原始创意依据",text)
        self.assertFalse(bundle["publishing_allowed"])
        self.assertFalse(bundle["ready_to_call_video_model"])


if __name__=="__main__":
    unittest.main()
