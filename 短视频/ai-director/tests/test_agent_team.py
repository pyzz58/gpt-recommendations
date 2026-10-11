"""Tests for manager-led, dependency-scoped AI filmmaking team, without AI calls."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import agent_team as team


class DirectorTeamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=json.loads((ROOT/"examples/quit-smoking/plan.json").read_text(encoding="utf-8"))

    def new(self):
        return team.start(copy.deepcopy(self.base))

    def _submit(self, state, tid, payload=None):
        if payload is None:
            spec = team.SPECS[tid]
            if spec["kind"] == "shots":
                ids = state["tasks"][tid]["revision_scope"]
                if ids is None:
                    ids = state["shot_ids"]
                payload = {"shots":{sid:{
                    field: None if field=="shootability" else
                           ([{"visible_change": "test beat"}] if field=="beats"
                            else {"design": tid + "/" + field})
                    for field in spec["fields"]} for sid in ids}}
            elif tid=="director_brief":
                payload = {"creative_brief":{"vision":"Accessible short-form drama",
                                             "immutable_source":"preserve base wording"}}
            elif tid=="script_edit":
                payload = {"story_treatment":{"hook":"Audience curiosity",
                                               "source_change_proposals":[]}}
            elif tid=="director_lock":
                payload = {"global_direction":{
                    "audience_emotion_arc":"Curiosity -> relief",
                    "visual_grammar":"Coherent 9:16 lens, palette and axis",
                    "audio_grammar":"Quiet VO, low ambience",
                    "graphic_safety":"Keep text readable and verified",
                    "reference_strategy":"All assets uncreated; no claims of locks",
                    "generation_budget":"No model calls or charges"}}
            elif tid=="quality_review":
                payload={"qa_report":{"blockers":[],"findings":[],
                                       "recommendation":"ready_for_director_review"}}
            elif tid=="director_final":
                payload={"director_decision":{"decision":"ready_for_user_review",
                                               "rationale":"Structured team draft; human review next"}}
        return team.submit(state, team.packet(state,tid), payload)

    def completed(self):
        ledger=self.new()
        for tid in team.SPECS:
            ledger=self._submit(ledger,tid)
        return ledger

    def test_plans_are_episode_batched_not_agents_times_shots(self):
        state=self.new()
        self.assertEqual(len(state["tasks"]),10)
        self.assertEqual(team.ready(state),["director_brief"])
        self.assertEqual(state["release"]["human_approved"],False)
        self.assertEqual(state["budget_policy"]["llm_requests_enabled"],False)
        self.assertEqual(state["budget_policy"]["paid_media_enabled"],False)

    def test_showrunner_review_precedes_script_specialists(self):
        state=self.new()
        with self.assertRaises(ValueError):
            team.packet(state,"script_edit")
        state=self._submit(state,"director_brief")
        self.assertEqual(team.ready(state),["script_edit"])
        state=self._submit(state,"script_edit")
        self.assertEqual(team.ready(state),["director_lock"])
        state=self._submit(state,"director_lock")
        self.assertEqual(set(team.ready(state)),{"acting","camera_art","sound"})

    def test_role_packets_share_locked_bible_and_source_hash(self):
        state=self.new()
        for tid in ("director_brief","script_edit","director_lock"):
            state=self._submit(state,tid)
        packet=team.packet(state,"acting")
        self.assertEqual(packet["role"],"acting_coach")
        self.assertEqual(packet["base_digest"],team.fingerprint(self.base))
        self.assertIn("director_lock",packet["upstream_artifacts"])
        self.assertIn("script_edit",packet["upstream_artifacts"])
        self.assertEqual(packet["upstream_artifacts"]["director_lock"]["global_direction"]
                         ["visual_grammar"], "Coherent 9:16 lens, palette and axis")
        self.assertTrue(packet["no_authorized_model_calls"])

    def test_actors_cannot_write_camera_or_script_fields(self):
        state=self.new()
        for tid in ("director_brief","script_edit","director_lock"):
            state=self._submit(state,tid)
        wrong={"shots": {sid:{
            "staging":{"design":"blocking"},"performance":{"design":"acting"},
            "beats":[{"visible_change":"test"}],"continuity":{"design":"locks"},
            "shootability":None,"camera":{"movement":"pan"}}
            for sid in state["shot_ids"]}}
        with self.assertRaises(ValueError):
            self._submit(state,"acting",wrong)

    def test_no_agent_can_submit_source_plan_replacement(self):
        state=self.new()
        wrong={"creative_brief":{"vision":"movie"},"source_plan":{"claims":[]}}
        with self.assertRaises(ValueError):
            self._submit(state,"director_brief",wrong)
        self.assertEqual(team.fingerprint(self.base),state["base_digest"])

    def test_first_specialist_handoff_covers_all_shots(self):
        state=self.new()
        for tid in ("director_brief","script_edit","director_lock"):
            state=self._submit(state,tid)
        payload={"shots":{"S01":{
            "staging":{"design":"blocking"},"performance":{"design":"acting"},
            "beats":[{"visible_change":"test"}],"continuity":{"design":"locks"},
            "shootability":None}}}
        with self.assertRaises(ValueError):
            self._submit(state,"acting",payload)

    def test_merged_team_direction_is_in_original_schema_and_not_user_approved(self):
        state=self.completed()
        draft=team.assemble_direction(self.base,state)
        self.assertEqual(draft["schema_version"],"0.2")
        self.assertEqual(len(draft["shots"]),len(self.base["shots"]))
        self.assertEqual(draft["shots"][0]["shot_id"],"S01")
        self.assertFalse(draft["shots"][0]["qa"]["human_approved"])
        self.assertNotIn("narration",draft["shots"][0])
        self.assertEqual(self.base["shots"][0]["narration"],
                         self.base["shots"][0]["narration"])
        self.assertFalse(state["release"]["human_approved"])
        self.assertFalse(state["release"]["paid_api_authorized"])

    def test_does_not_modify_input_ledger(self):
        base=self.new(); original=copy.deepcopy(base)
        future=self._submit(base,"director_brief")
        self.assertEqual(base,original)
        self.assertEqual(base["tasks"]["director_brief"]["status"],"pending")
        self.assertEqual(future["tasks"]["director_brief"]["status"],"completed")

    def test_old_dependency_envelope_is_rejected(self):
        state=self.new()
        state=self._submit(state,"director_brief")
        early=team.packet(state,"script_edit")
        bad=copy.deepcopy(early);bad["base_digest"]="fake"
        with self.assertRaises(ValueError):
            team.submit(state,bad,{"story_treatment":{"hook":"X"}})

    def test_specialist_revision_invalidates_only_downstream_stages(self):
        state=self.completed()
        changed=team.request_revision(state,"acting",["S01"],"Make prop hold physically coherent")
        self.assertEqual(changed["tasks"]["acting"]["status"],"needs_revision")
        self.assertEqual(changed["tasks"]["camera_art"]["status"],"completed")
        self.assertEqual(changed["tasks"]["sound"]["status"],"completed")
        self.assertEqual(changed["tasks"]["editing_animation"]["status"],"stale")
        self.assertEqual(changed["tasks"]["editing_animation"]["revision_scope"],["S01","S02"])
        self.assertEqual(changed["tasks"]["ai_technical"]["revision_scope"],["S01"])
        self.assertFalse(changed["release"]["director_ai_review_complete"])
        self.assertEqual(team.ready(changed),["acting"])
        self.assertEqual(state["tasks"]["acting"]["status"],"completed")

    def test_revised_shot_patch_preserves_other_shots_and_history(self):
        state=self.completed()
        original=copy.deepcopy(state["tasks"]["acting"]["deliverable"]["shots"]["S02"])
        state=team.request_revision(state,"acting",["S01"],"Fix hand grip")
        state=self._submit(state,"acting")
        self.assertEqual(state["tasks"]["acting"]["revision"],2)
        self.assertEqual(state["tasks"]["acting"]["deliverable"]["shots"]["S02"],original)
        self.assertEqual(len(state["tasks"]["acting"]["previous_versions"]),1)
        self.assertEqual(team.ready(state),["editing_animation"])

    def test_qa_does_not_authorize_rework_without_showrunner(self):
        state=self.completed()
        with self.assertRaises(ValueError):
            team.request_revision(state,"acting",["S01"],"QA says fix",source_task="quality_review")

    def test_document_revision_invalidates_all_downstream_episode_shots(self):
        state=self.completed()
        changed=team.request_revision(state,"director_lock",[],"Change color grammar")
        self.assertEqual(changed["tasks"]["acting"]["status"],"stale")
        self.assertIsNone(changed["tasks"]["acting"]["revision_scope"])
        self.assertIsNone(changed["tasks"]["camera_art"]["revision_scope"])
        self.assertIsNone(changed["tasks"]["editing_animation"]["revision_scope"])
        changed=self._submit(changed,"director_lock")
        self.assertEqual(set(team.ready(changed)),{"acting","camera_art","sound"})

    def test_qa_blockers_prevent_director_final_acceptance(self):
        state=self.new()
        for tid in list(team.SPECS)[:-2]:
            state=self._submit(state,tid)
        qa={"qa_report":{"blockers":[{"task_id":"acting","shot_ids":["S01"],
                                    "detail":"bad prop continuity"}],
                         "findings":[],"recommendation":"revise"}}
        state=self._submit(state,"quality_review",qa)
        with self.assertRaises(ValueError):
            self._submit(state,"director_final")
        state=self._submit(state,"director_final",{
            "director_decision":{"decision":"request_changes",
                                 "rationale":"Fix handedness before review"}})
        self.assertFalse(state["release"]["director_ai_review_complete"])
        self.assertFalse(state["release"]["human_approved"])

    def test_same_stage_cannot_submit_twice_without_revision(self):
        state=self.new()
        state=self._submit(state,"director_brief")
        with self.assertRaises(ValueError):
            self._submit(state,"director_brief")

    def test_real_director_workbook_compilation_needs_valid_authored_design(self):
        state=self.completed()
        # Synthetic field placeholders intentionally do not pass the existing
        # production schema; no agent is allowed to fake a finished film.
        with self.assertRaises((ValueError, KeyError)):
            team.compile_team_workbook(self.base,state)

    def test_base_fingerprint_guards_source_versions(self):
        state=self.completed()
        altered=copy.deepcopy(self.base)
        altered["shots"][0]["narration"]="Unapproved text replacement"
        with self.assertRaises(ValueError):
            team.assemble_direction(altered,state)

    def test_cli_plan_is_offline_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/"team.json"
            cmd=[sys.executable,str(ROOT/"agent_team.py"),"plan",
                 "--base",str(ROOT/"examples/quit-smoking/plan.json"),
                 "--out",str(target)]
            first=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(first.returncode,0,first.stderr)
            original=target.read_bytes()
            self.assertEqual(json.loads(original)["release"]["paid_api_authorized"],False)
            second=subprocess.run(cmd,capture_output=True,text=True)
            self.assertNotEqual(second.returncode,0)
            self.assertEqual(target.read_bytes(),original)

    def test_resubmission_envelopes_validate_dependency_versions(self):
        state=self.completed()
        state=team.request_revision(state,"acting",["S01"],"Fix gesture")
        state=self._submit(state,"acting")
        next_packet=team.packet(state,"editing_animation")
        forged=copy.deepcopy(next_packet)
        forged["dependency_revisions"]["acting"]=1
        with self.assertRaises(ValueError):
            team.submit(state,forged,
                {"shots":{sid:{
                    "editing":{"design":"edit"},"animation":{"design":"graphic"},
                    "graphics":{"design":"labels"}}
                 for sid in next_packet["revision_scope"]}})

    def test_real_public_example_can_merge_into_existing_professional_workbook(self):
        import director_v2
        direction = director_v2.read_json(ROOT/"examples/quit-smoking/direction_v02.json")
        state=self.new()
        state=self._submit(state,"director_brief")
        state=self._submit(state,"script_edit")
        state=self._submit(state,"director_lock",{
            "global_direction":copy.deepcopy(direction["global_direction"])})
        by_id={x["shot_id"]:x for x in direction["shots"]}
        for tid in ("acting","camera_art","sound","editing_animation","ai_technical"):
            bundle={"shots":{}}
            for sid in state["shot_ids"]:
                src=by_id[sid]
                fields=team.SPECS[tid]["fields"]
                item={}
                for key in fields:
                    if key=="shootability":
                        item[key]=None
                    elif key=="speech":
                        original=next(x for x in self.base["shots"] if x["id"]==sid)
                        item[key]={
                            "voiceover":{"text":original["narration"],"delivery":"natural",
                                         "timing":"subject to director timing approval"},
                            "dialogue":[],"subtitle_direction":"safe area",
                            "lip_sync_policy":"narrator only"}
                    elif key=="editing":
                        item[key]={"cut_reason":"must be precisely directed"}
                    elif key=="animation":
                        item[key]={"mode":"none","timing":"none","elements":[],
                                   "render_in_post":False,"style":"restrained"}
                    else:
                        item[key]=copy.deepcopy(src[key])
                bundle["shots"][sid]=item
            # Only submit when prerequisites complete
            state=self._submit(state,tid,bundle)
        state=self._submit(state,"quality_review")
        state=self._submit(state,"director_final")
        book=team.compile_team_workbook(self.base,state)
        self.assertEqual(len(book["shots"]),len(self.base["shots"]))
        self.assertTrue(book["team_handoff"]["manager_review_only"])
        self.assertFalse(book["team_handoff"]["human_approved"])
        self.assertFalse(book["team_handoff"]["paid_media_generated"])
        self.assertFalse(book["director_review"]["production_blueprint_ready"])

    def test_no_runtime_actions_behind_helpers(self):
        state=self.completed()
        self.assertEqual(team.overview(state)["ready_tasks"],[])
        self.assertFalse(team.overview(state)["paid_api_authorized"])
        self.assertTrue(state["release"]["director_ai_review_complete"])
        self.assertFalse(state["release"]["human_approved"])


if __name__=="__main__":
    unittest.main()
