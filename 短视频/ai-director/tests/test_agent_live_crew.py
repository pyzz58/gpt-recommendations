"""Locked ten-role DeepSeek connection: offline fixtures, never real network.

Tests the actual ten-task DAG, real source-locked director candidate,
stage dependencies and provider-wire envelopes. All responses are synthetic.
"""
from __future__ import annotations

from copy import deepcopy
import json
import tempfile
import unittest
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))

import agent_live_pilot as pilot
import agent_live_crew as live
import agent_role_contracts as roles
import agent_team as team
import agent_handoff_audit as audit
import production_delivery as delivery
import creative_production_handoff as creative_bridge
import director_v2
import director_workbook
import editorial_review_lock as review
import test_editorial_review_lock as review_fixture
import test_agent_role_contracts as role_fixture


class LockedCrewPilotTests(unittest.TestCase):
    def setUp(self):
        self.fixture=review_fixture.EditorialReviewLockTests(
            "test_complete_review_locks_only_planning_snapshot")
        self.fixture.setUp()
        self.original=self.fixture.source
        self.snapshot=review.lock_planning_snapshot(
            self.fixture.candidate,self.original,self.fixture.decide())
        self.plan=self.snapshot["plan"]
        self.state=review.stage_locked_team(self.snapshot,self.original)["team"]
        self.config=pilot.create_pilot_config(
            model="deepseek-flash",source_digest=self.state["source_digest"],
            base_digest=self.state["base_digest"],cap_cny="10",
            max_attempts=10,max_output_tokens=4096,
            cache_hit_cny_m="0.5",cache_miss_cny_m="2",
            output_cny_m="4")
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.template=role_fixture.ProfessionalRoleContractsTests(
            "test_complete_ten_role_strict_pipeline")
        self.template.setUp()
        self.template.base=self.plan
        self.template.original=self.original
        self.template.state=self.state

    def _payload(self, task, state):
        self.template.state=state
        p=self.template.payload(task)
        if "shots" in p:
            for i,shot in enumerate(self.plan["shots"]):
                sid=shot["id"]
                item=p["shots"].get(sid)
                if item is None:
                    continue
                d=shot["duration"]
                if task=="acting":
                    mid=d/2
                    item["beats"][0]["from_s"]=0
                    item["beats"][0]["to_s"]=mid
                    item["beats"][1]["from_s"]=mid
                    item["beats"][1]["to_s"]=d
                    if item["shootability"]:
                        item["shootability"]["action_units"][0]["from_s"]=0
                        item["shootability"]["action_units"][0]["to_s"]=d
                elif task=="camera_art":
                    item["camera"]["move_trigger_s"]=min(1,d/2)
                    item["art"]["lighting_state"]="lit"
                    item["art"]["practical_sources"]=[
                        "One existing fictional interior table lamp"]
                    item["art"]["lighting_change_reason"]=(
                        "Key practical source remains unchanged; "
                        "do not invent a different wall position")
                    if shot["visual_type"]=="ai_video":
                        item["camera"]["shot_size"]="close_up"
                        item["camera"]["focal_length_mm"]=50
                        item["camera"]["screen_axis"]=(
                            "Camera stays on the room side of the desk axis, "
                            "looking toward the same sealed paper letter")
                        item["art"]["scene_geometry"]={
                            "anchor_positions":{
                                "desk":"Center of west wall, aligned north-south",
                                "door":"East wall left corner facing the desk"},
                            "key_light_position":
                                "Same table lamp beside the wooden desk",
                            "camera_axis":
                                "East-to-west room axis behind the desk"}

                elif task=="sound":
                    item["sound"]["effects"][0]["time_s"]=min(d/2,2)
                    item["speech"]["voiceover"]["cues"][0]["from_s"]=0
                    item["speech"]["voiceover"]["cues"][0]["to_s"]=min(d,3)
                    item["speech"]["subtitle_cues"][0]["from_s"]=0
                    item["speech"]["subtitle_cues"][0]["to_s"]=min(d,3.5)
                elif task=="ai_technical" and shot["visual_type"]=="ai_video":
                    item["generation"]={
                        "route":"ai_video",
                        "clip_type":"single_continuous_take",
                        "negative_constraints":[
                            "No readable text or numbers in generated footage",
                            "No extra fingers and no duplicate envelope"],
                        "reference_roles":[
                            "Identity and wardrobe photo awaiting human creation",
                            "Wooden desk and sealed letter visual reference"],
                        "limits":"No real media created. Model capability unknown; human review required",
                        "fallback":"Use a still-image motion-compositing shot if hand anatomy fails",
                        "asset_requirements":[
                            {"role":"identity_reference",
                             "description":"Synthetic character reference not provided"}],
                        "prompt_candidates":[{
                            "positive":"One continuous close-up: a protagonist's right hand hovers over a sealed paper envelope, then cautiously reaches toward the seal. The camera moves slowly forward in soft side-window daylight. Realistic hands and spatial continuity.",
                            "negative":"No extra fingers, no duplicate letter, no readable text, no jump cuts, no camera teleportation."}]
                    }
                elif task=="editing_animation":
                    # The test film is a mixture of AI footage and text cards.
                    # Base data owns transition and claims; do not forge new ones.
                    item["editing"]["outgoing_transition"]=shot["transition"]
                    if i:
                        item["editing"]["incoming_transition"]=self.plan["shots"][i-1]["transition"]
                    else:
                        item["editing"]["incoming_transition"]="start"
                    item["graphics"]["claims_used"]=shot["claim_ids"]
                    if "narrative_bridge" in item["editing"]:
                        item["editing"]["narrative_bridge"]["beat_link"]["outgoing_beat_index"]=1
                        item["editing"]["narrative_bridge"]["beat_link"]["incoming_beat_index"]=0
        return p

    def _frame(self,payload):
        return {"object":"chat.completion","model":"deepseek-flash",
                "choices":[{"finish_reason":"stop","message":{
                    "role":"assistant","content":json.dumps(payload,ensure_ascii=False)}}],
                "usage":{"prompt_tokens":500,"completion_tokens":350,
                         "total_tokens":850,"prompt_cache_hit_tokens":0,
                         "prompt_cache_miss_tokens":500}}

    def _permit(self,tid,revision=1):
        return pilot.explicit_pilot_permit(
            self.config,task_id=tid,revision=revision,
            acknowledgement=pilot.CONSENT_TEXT,
            privacy_consent=True,spending_consent=True)

    def _step(self,journal,state,tid):
        frame=pilot.StaticHTTPSFrame(self._frame(self._payload(tid,state)))
        return live.run_one_locked_role(
            self.snapshot,self.original,state,journal,
            permit=self._permit(tid,state["tasks"][tid]["revision"]+1),
            client=frame,task_id=tid)

    def test_ten_role_stage_signatures_are_consistent_with_team(self):
        self.assertEqual(set(pilot.PILOT_TASKS),set(team.SPECS))
        self.assertEqual(team.ready(self.state),["director_brief"])
        summary=live.locked_crew_overview(self.snapshot,self.original,self.state)
        self.assertEqual(summary["open_tasks"],list(team.SPECS))
        self.assertFalse(summary["automatic_dispatch_enabled"])
        self.assertFalse(summary["human_approved"])
        self.assertFalse(summary["media_created"])

    def test_first_three_roles_real_protocol_contract_offline(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            st=self.state
            for tid in ("director_brief","script_edit","director_lock"):
                st,receipt=self._step(journal,st,tid)
                self.assertFalse(receipt["network_attempted"])
                self.assertEqual(receipt["task_id"],tid)
                self.assertFalse(receipt["human_approved"])
            self.assertEqual(team.ready(st),["acting","camera_art","sound"])
            self.assertEqual(len(journal.summary()["attempts"]),3)
            self.assertTrue(all(r["status"]=="response_accepted"
                                for r in journal.summary()["attempts"]))
            self.assertEqual(self.state["tasks"]["director_brief"]["status"],"pending")

    def test_separate_acting_camera_sound_can_be_called_by_explicit_choice(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            st=self.state
            for tid in ("director_brief","script_edit","director_lock"):
                st,_=self._step(journal,st,tid)
            st,first=self._step(journal,st,"sound")
            self.assertEqual(first["task_id"],"sound")
            self.assertEqual(team.ready(st),["acting","camera_art"])
            st,_=self._step(journal,st,"acting")
            st,_=self._step(journal,st,"camera_art")
            self.assertEqual(team.ready(st),["editing_animation"])

    def test_camera_art_real_provider_role_contract_rejects_n_a_parameters(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            state=self.state
            for name in ("director_brief","script_edit","director_lock"):
                state,_=self._step(journal,state,name)
            bad=self._payload("camera_art",state)
            sid=next(s["id"] for s in self.plan["shots"]
                     if s["visual_type"]=="ai_video")
            bad["shots"][sid]["camera"]["shot_size"]="postproduction"
            client=pilot.StaticHTTPSFrame(self._frame(bad))
            with self.assertRaisesRegex(
                    pilot.PilotError,"SPECIALIST_RESPONSE_REJECTED_NO_RETRY"):
                live.run_one_locked_role(
                    self.snapshot,self.original,state,journal,
                    permit=self._permit("camera_art"),client=client,
                    task_id="camera_art")
            self.assertEqual(client.calls,1)
            self.assertEqual(journal.summary()["attempts"][-1]["status"],
                             "response_rejected")
            self.assertEqual(state["tasks"]["camera_art"]["status"],"pending")

    def test_moved_door_between_ai_video_shots_is_rejected(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            state=self.state
            for name in ("director_brief","script_edit","director_lock"):
                state,_=self._step(journal,state,name)
            bad=self._payload("camera_art",state)
            videos=[s["id"] for s in self.plan["shots"]
                    if s["visual_type"]=="ai_video"]
            self.assertGreaterEqual(len(videos),2)
            bad["shots"][videos[1]]["art"]["scene_geometry"][
                "anchor_positions"]["door"]="Door magically moved to north wall"
            with self.assertRaisesRegex(
                    pilot.PilotError,"SPECIALIST_RESPONSE_REJECTED_NO_RETRY"):
                live.run_one_locked_role(
                    self.snapshot,self.original,state,journal,
                    permit=self._permit("camera_art"),
                    client=pilot.StaticHTTPSFrame(self._frame(bad)),
                    task_id="camera_art")
            self.assertEqual(journal.summary()["attempts"][-1]["status"],
                             "response_rejected")

    def test_scoped_camera_revision_cannot_move_room_geometry(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            state=self.state
            for name in ("director_brief","script_edit","director_lock",
                         "camera_art"):
                state,_=self._step(journal,state,name)
            vids=[s["id"] for s in self.plan["shots"]
                  if s["visual_type"]=="ai_video"]
            self.assertGreaterEqual(len(vids),2)
            revised=team.request_revision(
                state,"camera_art",[vids[1]],
                "Manually requested revision must preserve physical room",
                source_task="director_final")
            self.assertIn("camera_art",team.ready(revised))
            bad=self._payload("camera_art",revised)
            bad["shots"]={vids[1]:bad["shots"][vids[1]]}
            bad["shots"][vids[1]]["art"]["scene_geometry"][
                "anchor_positions"]["door"]="Now located on north wall"
            fake=pilot.StaticHTTPSFrame(self._frame(bad))
            with self.assertRaisesRegex(
                    pilot.PilotError,"SPECIALIST_RESPONSE_REJECTED_NO_RETRY"):
                live.run_one_locked_role(
                    self.snapshot,self.original,revised,journal,
                    permit=self._permit("camera_art",revision=2),
                    client=fake,task_id="camera_art")
            self.assertEqual(fake.calls,1)
            self.assertEqual(journal.summary()["attempts"][-1]["status"],
                             "response_rejected")
            self.assertEqual(revised["tasks"]["camera_art"]["status"],
                             "needs_revision")

    def test_nonvideo_blackout_needs_explanation_for_next_video_light(self):
        state=self.state
        for name in ("director_brief","script_edit","director_lock"):
            state=roles.submit_role_output(
                self.plan,state,name,
                json.dumps(self._payload(name,state),ensure_ascii=False),
                source_text=self.original)
        draft=self._payload("camera_art",state)
        shots=self.plan["shots"]
        # A normal lit video/graphic sequence with a deliberately dark graphic
        # followed by video must provide a valid changed-state reason.
        s1=shots[1]["id"]
        draft["shots"][s1]["art"]["lighting_state"]="blackout"
        draft["shots"][s1]["art"]["lighting_change_reason"]="No visible sources because deliberately black screen"
        if len(shots)>2:
            s2=shots[2]["id"]
            draft["shots"][s2]["art"]["lighting_state"]="lit"
            draft["shots"][s2]["art"]["lighting_change_reason"]="unchanged"
            with self.assertRaisesRegex(
                    creative_bridge.HandoffError,
                    "LIGHT_TRANSITION_DENIED_AS_UNCHANGED"):
                creative_bridge.camera_requirements_for_role(
                    self.plan,draft)

    def test_camera_art_role_prompt_has_typed_video_spec_schema(self):
        state=self.state
        for name in ("director_brief","script_edit","director_lock"):
            payload=self._payload(name,state)
            state=roles.submit_role_output(
                self.plan,state,name,json.dumps(payload,ensure_ascii=False),
                source_text=self.original)
        prompt=roles.build_role_messages(
            self.plan,state,"camera_art",
            source_text=self.original,
            editorial_handoff=self.snapshot["creative_handoff"])
        schema=prompt["output_json_schema"]["properties"]["shots"][
            "properties"]
        sid=next(s["id"] for s in self.plan["shots"]
                 if s["visual_type"]=="ai_video")
        required=schema[sid]["properties"]["camera"]["required"]
        self.assertIn("shot_size",required)
        self.assertIn("focal_length_mm",required)
        self.assertIn("screen_axis",required)
        art=schema[sid]["properties"]["art"]
        self.assertIn("practical_sources",art["required"])
        self.assertIn("lighting_state",art["required"])

    def test_source_locked_schema_preflight_failed_before_reservation(self):
        from unittest.mock import patch
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            frame=pilot.StaticHTTPSFrame(self._frame(
                self._payload("director_brief",self.state)))
            with patch("agent_live_crew.schema_guard.preflight_schema",
                       side_effect=ValueError("BROKEN_SYNTHETIC_SCHEMA")):
                with self.assertRaisesRegex(
                        pilot.PilotError,"PILOT_ROLE_PROMPT_INVALID"):
                    live.run_one_locked_role(
                        self.snapshot,self.original,self.state,journal,
                        permit=self._permit("director_brief"),
                        client=frame,task_id="director_brief")
            self.assertEqual(frame.calls,0)
            self.assertEqual(journal.summary()["attempts"],[])

    def test_missing_permit_rejects_without_model_call(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            fake=pilot.StaticHTTPSFrame(self._frame(self._payload("director_brief",self.state)))
            with self.assertRaisesRegex(pilot.PilotError,"EXPLICIT_CONSENT_MISSING"):
                live.run_one_locked_role(
                    self.snapshot,self.original,self.state,journal,
                    client=fake,task_id="director_brief")
            self.assertEqual(fake.calls,0)
            self.assertEqual(journal.summary()["attempts"],[])

    def test_permit_stale_role_revision_rejected_prior_to_reservation(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            fake=pilot.StaticHTTPSFrame(self._frame(self._payload("director_brief",self.state)))
            with self.assertRaisesRegex(pilot.PilotError,"WRONG_REVISION"):
                live.run_one_locked_role(
                    self.snapshot,self.original,self.state,journal,
                    permit=self._permit("director_brief",revision=2),
                    client=fake,task_id="director_brief")
            self.assertEqual(fake.calls,0)

    def test_wrong_candidate_source_blocks_even_with_valid_permit(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            fake=pilot.StaticHTTPSFrame(self._frame(self._payload("director_brief",self.state)))
            with self.assertRaisesRegex(pilot.PilotError,"LOCKED_SNAPSHOT_OR_TEAM_INVALID"):
                live.run_one_locked_role(
                    self.snapshot,self.original+"x",self.state,journal,
                    permit=self._permit("director_brief"),
                    client=fake,task_id="director_brief")
            self.assertEqual(fake.calls,0)

    def test_tampering_locked_plan_changes_fingerprint_and_stops(self):
        fake=deepcopy(self.snapshot)
        fake["plan"]["shots"][0]["narration"]="newly invented story"
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            with self.assertRaisesRegex(pilot.PilotError,"LOCKED_SNAPSHOT_OR_TEAM_INVALID"):
                live.run_one_locked_role(
                    fake,self.original,self.state,journal,
                    permit=self._permit("director_brief"),
                    client=pilot.StaticHTTPSFrame(self._frame(self._payload("director_brief",self.state))),
                    task_id="director_brief")
            self.assertEqual(journal.summary()["attempts"],[])

    def test_source_hash_mismatch_between_lock_and_budget_is_blocked(self):
        other=pilot.create_pilot_config(
            model="deepseek-flash",source_digest="a"*64,
            base_digest=self.config["base_digest"],cap_cny="10",
            max_attempts=10,max_output_tokens=4096,
            cache_hit_cny_m="0.5",cache_miss_cny_m="2",
            output_cny_m="4")
        with pilot.PilotJournal(self.tmp.name,other) as journal:
            fake=pilot.StaticHTTPSFrame(self._frame(self._payload("director_brief",self.state)))
            perm=pilot.explicit_pilot_permit(
                other,task_id="director_brief",acknowledgement=pilot.CONSENT_TEXT,
                privacy_consent=True,spending_consent=True)
            with self.assertRaisesRegex(pilot.PilotError,"JOURNAL_WRONG_LOCKED_VERSION"):
                live.run_one_locked_role(
                    self.snapshot,self.original,self.state,journal,
                    permit=perm,client=fake,task_id="director_brief")
            self.assertEqual(fake.calls,0)

    def test_non_ready_camera_cannot_skip_director_lock(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            fake=pilot.StaticHTTPSFrame(self._frame(self._payload("camera_art",self.state)))
            with self.assertRaisesRegex(pilot.PilotError,"TASK_NOT_READY"):
                live.run_one_locked_role(
                    self.snapshot,self.original,self.state,journal,
                    permit=self._permit("camera_art"),client=fake,task_id="camera_art")
            self.assertEqual(fake.calls,0)

    def test_unsupported_transport_is_rejected_before_spend(self):
        class BadClient:
            def complete(self,*args):
                raise AssertionError("should not execute")
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            with self.assertRaisesRegex(pilot.PilotError,"TRANSPORT_NOT_ALLOWED"):
                live.run_one_locked_role(
                    self.snapshot,self.original,self.state,journal,
                    permit=self._permit("director_brief"),
                    client=BadClient(),task_id="director_brief")
            self.assertEqual(journal.summary()["attempts"],[])

    def test_full_ten_role_synthetic_pipeline_never_claims_real_approval(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            st=self.state
            for tid in team.SPECS:
                st,receipt=self._step(journal,st,tid)
                self.assertEqual(receipt["transport"],"synthetic_fixture")
                self.assertFalse(receipt["network_attempted"])
            self.assertEqual(team.ready(st),[])
            self.assertEqual(len(journal.summary()["attempts"]),10)
            self.assertFalse(st["release"]["human_approved"])
            self.assertFalse(st["release"]["paid_api_authorized"])
            self.assertTrue(st["release"]["director_ai_review_complete"])
            self.assertFalse(st["release"]["publishing_allowed"])

    def test_full_chain_exports_real_video_model_work_orders_not_only_team_flags(self):
        """Long article -> reviewed plan -> ten fixture roles -> candidate prompts."""
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            state=self.state
            for task_id in team.SPECS:
                state,_=self._step(journal,state,task_id)
            self.assertFalse(state["release"]["human_approved"])
            # This is the real production compiler, NOT a mocked output.
            exported=delivery.build_locked_crew_delivery(
                self.snapshot,self.original,state)
            self.assertEqual(exported["provenance"],"locked_ten_role_crew")
            self.assertEqual(exported["shooting_order"],
                             [s["id"] for s in self.plan["shots"]])
            self.assertEqual(exported["project"]["total_shots"],len(self.plan["shots"]))
            self.assertGreater(exported["production_counts"]["ai_video_jobs"],0)
            self.assertGreater(exported["production_counts"]["non_video_jobs"],0)
            self.assertTrue(exported["full_workbook_review"]["independent_crew_completed"])
            self.assertEqual(exported["project"]["duration_s"],self.plan["duration"])
            self.assertFalse(exported["ready_to_call_video_model"])
            self.assertFalse(exported["human_approved"])
            self.assertFalse(exported["publishing_allowed"])
            self.assertIn("逐镜生产工单",delivery.render_operator_markdown(exported))
            for shot,base_shot in zip(exported["shots"],self.plan["shots"]):
                self.assertEqual(shot["film_script"]["voiceover"],base_shot["narration"])
                self.assertEqual(shot["timeline"]["duration_s"],base_shot["duration"])
                if shot["production_route"]=="ai_video":
                    self.assertEqual(set(shot["ai_video_prompt_candidates"]),{"wan","seedance"})
                else:
                    self.assertEqual(shot["ai_video_prompt_candidates"],{})

    def test_end_to_end_source_corruption_never_exports(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            state=self.state
            for task_id in team.SPECS:
                state,_=self._step(journal,state,task_id)
            with self.assertRaisesRegex(delivery.ProductionDeliveryError,
                                        "UNTRUSTED_LOCK"):
                delivery.build_locked_crew_delivery(
                    self.snapshot,self.original+"unauthorized change",state)

    def test_unapproved_narration_changed_in_sound_blocks_quality_review_acceptance(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            st=self.state
            for tid in list(team.SPECS)[:8]:
                st,_=self._step(journal,st,tid)
            contaminated=deepcopy(st)
            sid=contaminated["shot_ids"][0]
            contaminated["tasks"]["sound"]["deliverable"]["shots"][sid]["speech"]["voiceover"]["text"]="FAKE CLAIM"
            self.assertEqual(team.ready(contaminated),["quality_review"])
            self.assertEqual(audit.audit_handoffs(contaminated,self.plan)["status"],"blocked")
            qa=self._payload("quality_review",contaminated)
            fake=pilot.StaticHTTPSFrame(self._frame(qa))
            with self.assertRaisesRegex(pilot.PilotError,"SPECIALIST_RESPONSE_REJECTED_NO_RETRY"):
                live.run_one_locked_role(
                    self.snapshot,self.original,contaminated,journal,
                    permit=self._permit("quality_review"),client=fake,task_id="quality_review")
            self.assertEqual(journal.summary()["attempts"][-1]["status"],"response_rejected")

    def test_qa_may_report_real_blockers_as_revision_instead_of_falsely_approving(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            st=self.state
            for tid in list(team.SPECS)[:8]:
                st,_=self._step(journal,st,tid)
            corrupt=deepcopy(st)
            sid=corrupt["shot_ids"][0]
            corrupt["tasks"]["sound"]["deliverable"]["shots"][sid]["speech"]["voiceover"]["text"]="MISMATCH"
            payload={"qa_report":{"blockers":[
                {"task_id":"sound","shot_ids":[sid],
                 "code":"SOURCE_VOICEOVER_DRIFT",
                 "detail":"Source narration differs from recorded original",
                 "recommended_change":"Restore the exact authoritative voiceover text"}],
                "findings":[],"recommendation":"revise"}}
            result,_=live.run_one_locked_role(
                self.snapshot,self.original,corrupt,journal,
                permit=self._permit("quality_review"),
                client=pilot.StaticHTTPSFrame(self._frame(payload)),
                task_id="quality_review")
            self.assertEqual(result["tasks"]["quality_review"]["deliverable"]
                             ["qa_report"]["recommendation"],"revise")

    def test_invalid_response_from_acting_blocks_advance_and_resend(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            st=self.state
            for tid in ("director_brief","script_edit","director_lock"):
                st,_=self._step(journal,st,tid)
            bad={"shots":{}}
            fake=pilot.StaticHTTPSFrame(self._frame(bad))
            before=deepcopy(st)
            with self.assertRaisesRegex(pilot.PilotError,"SPECIALIST_RESPONSE_REJECTED_NO_RETRY"):
                live.run_one_locked_role(
                    self.snapshot,self.original,st,journal,
                    permit=self._permit("acting"),client=fake,task_id="acting")
            self.assertEqual(st,before)
            with self.assertRaisesRegex(pilot.PilotError,"NO_AUTOMATIC_RETRY"):
                self._step(journal,st,"acting")

    def test_network_timeout_keeps_no_retry_record(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            with self.assertRaisesRegex(pilot.PilotError,"TIMEOUT_CHARGE_UNKNOWN"):
                live.run_one_locked_role(
                    self.snapshot,self.original,self.state,journal,
                    permit=self._permit("director_brief"),
                    client=pilot.StaticHTTPSFrame("TIMEOUT"),task_id="director_brief")
            self.assertEqual(journal.summary()["attempts"][0]["status"],"timeout_unknown")

    def test_source_prompt_never_written_to_private_budget_journal(self):
        with pilot.PilotJournal(self.tmp.name,self.config) as journal:
            self._step(journal,self.state,"director_brief")
            contents=journal.journal.read_text("utf-8")
            self.assertNotIn(self.original,contents)
            self.assertNotIn("story_treatment",contents)
            self.assertNotIn("api_key",contents)
            self.assertEqual(journal.journal.stat().st_mode&0o777,0o600)

    def test_status_api_contains_no_private_original_manuscript(self):
        safe=live.locked_crew_overview(self.snapshot,self.original,self.state)
        self.assertNotIn(self.original,json.dumps(safe,ensure_ascii=False))
        self.assertFalse(safe["automatic_dispatch_enabled"])
        self.assertEqual(safe["model_requests_executed_by_this_function"],0)


if __name__=="__main__":
    unittest.main()
