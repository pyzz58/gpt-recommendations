"""QO-D18: public fixture verifies REAL authorized runner receives director craft.

All calls use StaticHTTPSFrame and never connect, purchase video, or
send private user manuscripts. Permission tokens here are synthetic.
"""
from __future__ import annotations

from copy import deepcopy
import json
import unittest

import agent_live_crew as live
import agent_live_pilot as pilot
import agent_team as team
import editorial_review_lock as lock
import director_department_command as command
import director_artistic_methods as art
import director_visual_language as visual
from test_agent_live_crew import LockedCrewPilotTests
from test_director_department_command import _command
from test_director_artistic_methods import plan_for
from test_director_audiovisual_delivery import _visual


class DirectorContextLiveTests(unittest.TestCase):
    def setUp(self):
        self.fx = LockedCrewPilotTests("test_first_three_roles_real_protocol_contract_offline")
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        # Re-lock a REAL editorial candidate BEFORE creating the new team.
        # Updating only plan hash after locking would be an unsafe bypass.
        cand = deepcopy(self.fx.fixture.candidate)
        cand["candidate_plan"]["director_command_mode"] = {
            "kind": "director_department_conference_required",
            "command_before_specialists": True}
        cand["candidate_plan"]["director_audiovisual_mode"] = {
            "kind": "director_audiovisual_plan_required",
            "audiovisual_intent_before_specialists": True}
        cand["candidate_plan"]["director_artistic_mode"] = {
            "kind": "director_artistic_method_required",
            "artistic_intent_before_specialists": True}
        cand["candidate_base_digest"] = team.fingerprint(cand["candidate_plan"])
        sheet = lock.build_review_sheet(cand, self.fx.original)
        decision = lock.decision_template(sheet)
        decision["review_intent"] = "accept_for_planning"
        decision["global_direction"]["choice"] = "keep"
        for row in decision["shots"]:
            row["choice"] = "keep"
        decision["omissions"]["choice"] = "acknowledge_as_omitted"
        decision["claims"]["choice"] = "acknowledge_unverified_for_planning"
        for row in decision["source_change_proposals"]:
            row["choice"] = "do_not_apply"
        self.fx.snapshot = lock.lock_planning_snapshot(cand, self.fx.original, decision)
        self.fx.plan = self.fx.snapshot["plan"]
        self.fx.state = lock.stage_locked_team(self.fx.snapshot, self.fx.original)["team"]
        self.fx.template.base = self.fx.plan
        self.fx.template.state = self.fx.state
        self.fx.config = pilot.create_pilot_config(
            model="deepseek-flash", source_digest=self.fx.state["source_digest"],
            base_digest=self.fx.state["base_digest"], cap_cny="10",
            max_attempts=10, max_output_tokens=4096,
            cache_hit_cny_m="0.5", cache_miss_cny_m="2",
            output_cny_m="4")
        self.state = self.fx.state

    def _director_locked(self, journal):
        state = self.state
        for tid in ("director_brief", "script_edit", "director_lock"):
            state, _ = self.fx._step(journal, state, tid)
        meeting = _command(self.fx.plan, state)
        methods = plan_for(self.fx.plan, state, meeting, comedy=False)
        # Adapt the public two-shot example to the actual locked shot count.
        for i, shot in enumerate(methods["shots"]):
            shot["shot_id"] = state["shot_ids"][i]
            if i > 1:
                shot["visible_or_audible_change"] += f" 这是第{i+1}个不同的剧作证据点。"
                shot["chosen_screen_language"] += f" 根据第{i+1}镜头的观众信息重新分配注意力。"
                shot["audience_after"] += f" 第{i+1}镜头让观众再重新理解一次此行为。"
        methods_proof = art.validate(self.fx.plan, state, meeting, methods)
        viz = _visual(self.fx.plan, state, meeting)
        n = len(state["shot_ids"])
        # The visual fixture begins with two separate shots and one bridge.
        # For an N-shot professional pilot, replicate distinct views and exact
        # N-1 ordered bridges; all text is fictional and contains no real media.
        if n > 2:
            for i in range(2,n):
                copy = deepcopy(viz["shots"][-1])
                copy["shot_id"] = state["shot_ids"][i]
                copy["observable_screen_event"] += f" 本镜头第{i+1}次观察动作。"
                copy["visual_emphasis_and_reason"] += f" 本镜头第{i+1}个具体叙事原因。"
                copy["cut_or_hold_causal_reason"] += f" 在第{i+1}镜头之后揭示下一行为。"
                copy["viewer_belief_after"] += f" 观众在第{i+1}处增加理解。"
                viz["shots"].append(copy)
                link = deepcopy(viz["handoffs"][-1])
                link["from_shot"] = state["shot_ids"][i-1]
                link["to_shot"] = state["shot_ids"][i]
                viz["handoffs"].append(link)
        for i, shot in enumerate(viz["shots"]):
            shot["shot_id"] = state["shot_ids"][i]
        if n == 1:
            viz["shots"] = viz["shots"][:1]
            viz["handoffs"] = []
        viz["artistic_methods_digest"] = methods_proof["plan_digest"]
        visual.validate(self.fx.plan, state, meeting, viz,
                        artistic_method_plan=methods)
        return state, meeting, viz, methods

    def test_real_runner_fails_closed_if_all_director_context_is_missing(self):
        with pilot.PilotJournal(self.fx.tmp.name, self.fx.config) as journal:
            state, meeting, viz, methods = self._director_locked(journal)
            payload = self.fx._payload("acting", state)
            fake = pilot.StaticHTTPSFrame(self.fx._frame(payload))
            before = len(journal.summary()["attempts"])
            with self.assertRaisesRegex(pilot.PilotError, "DIRECTOR_CREATIVE_CONTEXT_REQUIRED"):
                live.run_one_locked_role(
                    self.fx.snapshot, self.fx.original, state, journal,
                    task_id="acting", permit=self.fx._permit("acting"),
                    client=fake)
            self.assertEqual(fake.calls,0)
            self.assertEqual(len(journal.summary()["attempts"]),before)
            with self.assertRaisesRegex(pilot.PilotError, "DIRECTOR_CREATIVE_CONTEXT_REQUIRED"):
                live.run_one_locked_role(
                    self.fx.snapshot, self.fx.original, state, journal,
                    task_id="acting", permit=self.fx._permit("acting"),
                    client=fake, department_command=meeting,
                    audiovisual_plan=viz)
            self.assertEqual(fake.calls,0)

    def test_real_offline_https_frame_receives_and_validates_three_artistic_layers(self):
        with pilot.PilotJournal(self.fx.tmp.name, self.fx.config) as journal:
            state, meeting, viz, methods = self._director_locked(journal)
            proof = live.inspect_locked_role(
                self.fx.snapshot, self.fx.original, state, "acting",
                department_command=meeting, audiovisual_plan=viz,
                artistic_method_plan=methods)
            self.assertTrue(proof["director_department_context_supplied"])
            self.assertTrue(proof["director_visual_context_supplied"])
            self.assertTrue(proof["director_artistic_context_supplied"])
            prompt = __import__("agent_role_contracts").build_role_messages(
                self.fx.plan, state, "acting", source_text=self.fx.original,
                editorial_handoff=self.fx.snapshot["creative_handoff"],
                department_command=meeting, audiovisual_plan=viz,
                artistic_method_plan=methods)
            data = json.loads(prompt["messages"][1]["content"].split(
                "\\n仅返回符合 output_json_schema 的 JSON，内容还必须满足专业岗位细则：\\n",1)[1])
            self.assertEqual(data["director_artistic_method_context"]["chosen_methods"][0]["method_id"],
                             methods["chosen_methods"][0]["method_id"])
            self.assertEqual(data["director_department_command"]["this_department"],"acting")
            self.assertEqual(data["director_audiovisual_intention"]["artistic_methods_digest"],
                             art.validate(self.fx.plan,state,meeting,methods)["plan_digest"])
            fake = pilot.StaticHTTPSFrame(self.fx._frame(self.fx._payload("acting",state)))
            result, receipt = live.run_one_locked_role(
                self.fx.snapshot, self.fx.original, state, journal,
                task_id="acting", permit=self.fx._permit("acting"),
                client=fake, department_command=meeting,
                audiovisual_plan=viz, artistic_method_plan=methods)
            self.assertEqual(fake.calls,1)
            self.assertEqual(result["tasks"]["acting"]["status"],"completed")
            self.assertFalse(receipt["network_attempted"])
            self.assertFalse(receipt["media_created"])

    def test_changed_director_method_is_rejected_before_budget_reservation(self):
        with pilot.PilotJournal(self.fx.tmp.name, self.fx.config) as journal:
            state, meeting, viz, methods = self._director_locked(journal)
            bad = deepcopy(methods)
            bad["director"]["directorial_position"] += " 一个未批准的修改。"
            fake = pilot.StaticHTTPSFrame(self.fx._frame(self.fx._payload("acting", state)))
            before = len(journal.summary()["attempts"])
            with self.assertRaisesRegex(pilot.PilotError, "ROLE_PROMPT_INVALID"):
                live.run_one_locked_role(
                    self.fx.snapshot, self.fx.original, state, journal,
                    task_id="acting",permit=self.fx._permit("acting"),client=fake,
                    department_command=meeting,audiovisual_plan=viz,
                    artistic_method_plan=bad)
            self.assertEqual(fake.calls,0)
            self.assertEqual(len(journal.summary()["attempts"]),before)


if __name__ == "__main__":
    unittest.main()
