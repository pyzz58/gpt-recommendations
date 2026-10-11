"""Provider-free, synthetic regression for cross-department crew QA and release gate."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import agent_team as crew
import agent_handoff_audit as audit


class HandoffAuditTests(unittest.TestCase):
    def setUp(self):
        self.base = {
            "title": "Synthetic letter story",
            "claims": [{"id": "C01"}],
            "shots": [
                {"id": sid, "start": i * 4, "duration": 4,
                 "narration": f"Narration for {sid}",
                 "transition": "hard_cut" if i < 2 else "fade_out"}
                for i, sid in enumerate(("S01", "S02", "S03"))
            ]
        }

    def submit(self, state, tid, payload=None):
        if payload is None:
            if tid == "director_brief":
                payload = {"creative_brief": {"vision": "Show a letter slowly and clearly"}}
            elif tid == "script_edit":
                payload = {"story_treatment": {"hook": "Find out what the letter contains"}}
            elif tid == "director_lock":
                payload = {
                    "global_direction": {
                        "audience_emotion_arc": "Quiet suspense moving to recognition",
                        "visual_grammar": "Restrained close-ups and steady compositions",
                        "audio_grammar": "Delicate non-diegetic music",
                        "graphic_safety": "No fake textual evidence",
                        "reference_strategy": "No reference images created",
                        "generation_budget": "No model execution permitted",
                    },
                    "shot_objectives": {
                        sid: {"emotion": "Curiosity",
                              "observable_turn": "Envelope opens in frame",
                              "visual_focus": "The envelope in the foreground"}
                        for sid in state["shot_ids"]
                    },
                }
            elif crew.SPECS[tid]["kind"] == "shots":
                payload = {"shots": {}}
                for i, sid in enumerate(state["shot_ids"]):
                    if tid == "acting":
                        item = {
                            "staging": {"blocking": "Actor seated at table, hand by envelope"},
                            "performance": {"ending_pose": "Hand rests on table after the letter opens"},
                            "beats": [{"from_s": 0, "to_s": 4,
                                       "visible_change": "Envelope opens in actor's right hand"}],
                            "continuity": {"start_state": "Sealed letter remains on table"},
                            "shootability": None,
                        }
                    elif tid == "camera_art":
                        item = {
                            "camera": {"move_trigger_s": 2,
                                       "movement": "Push steadily toward the hand at 2 seconds"},
                            "art": {"lighting": "Soft window light from the left"},
                        }
                    elif tid == "sound":
                        item = {
                            "sound": {"effects": [{"time_s": 2, "cue": "Letter rustles audibly"}]},
                            "speech": {
                                "voiceover": {"text": self.base["shots"][i]["narration"],
                                              "timing": "Starts at the beginning of the shot"},
                                "dialogue": [],
                            },
                        }
                    elif tid == "editing_animation":
                        edit = {"outgoing_transition": self.base["shots"][i]["transition"]}
                        if i < 2:
                            edit["narrative_bridge"] = {
                                "beat_link": {
                                    "outgoing_beat_index": 0, "incoming_beat_index": 0,
                                    "cut_on_visible_event": "Envelope opens and the letter is visible",
                                }}
                        item = {
                            "editing": edit,
                            "animation": {"mode": "none", "elements": []},
                            "graphics": {"claims_used": ["C01"],
                                         "treatment": "No generated text in camera"},
                        }
                    else:
                        item = {"generation": {
                            "route": "ai_video",
                            "limits": "Never generate words inside footage",
                        }}
                    payload["shots"][sid] = item
            elif tid == "quality_review":
                payload = {"qa_report": {
                    "blockers": [], "findings": [],
                    "recommendation": "ready_for_director_review"}}
            elif tid == "director_final":
                payload = {"director_decision": {
                    "decision": "ready_for_user_review",
                    "rationale": "Present synthetic crew directions for human review"}}
        return crew.submit(state, crew.packet(state, tid), payload)

    def through(self, tid="director_final"):
        state = crew.start(self.base)
        for name in crew.SPECS:
            state = self.submit(state, name)
            if name == tid:
                break
        return state

    def test_cross_handoff_consistent_synthetic_contract(self):
        state = self.through("ai_technical")
        report = audit.audit_handoffs(state, self.base)
        self.assertEqual(report["status"], "no_explicit_conflicts")
        self.assertEqual(report["issues"], [])
        self.assertFalse(report["media_verified"])

    def test_audit_read_only_and_voiceover_drift_is_blocking(self):
        state = self.through()
        state["tasks"]["sound"]["deliverable"]["shots"]["S01"]["speech"]["voiceover"]["text"] = "Changed without approval"
        original = copy.deepcopy(state)
        report = audit.audit_handoffs(state, self.base)
        self.assertIn("SOURCE_VOICEOVER_DRIFT", {x["code"] for x in report["issues"]})
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(original, state)
        self.assertNotIn("Changed without approval", str(report))

    def test_incorrect_beat_index_is_cross_department_blocker(self):
        state = self.through("ai_technical")
        state["tasks"]["editing_animation"]["deliverable"]["shots"]["S01"]["editing"]["narrative_bridge"]["beat_link"]["incoming_beat_index"] = 2
        report = audit.audit_handoffs(state)
        self.assertIn("HANDOFF_BEAT_INDEX_CONFLICT", [x["code"] for x in report["issues"]])
        self.assertEqual(report["issues"][0]["task_id"], "editing_animation")

    def test_invalid_beat_boundary_when_base_available(self):
        state = self.through("ai_technical")
        state["tasks"]["acting"]["deliverable"]["shots"]["S01"]["beats"][0]["to_s"] = 3.5
        codes = {x["code"] for x in audit.audit_handoffs(state, self.base)["issues"]}
        self.assertIn("HANDOFF_BEAT_TIME_CONFLICT", codes)

    def test_invalid_route_unknown_claim_and_animation_contradiction(self):
        state = self.through("ai_technical")
        shots = state["tasks"]
        shots["ai_technical"]["deliverable"]["shots"]["S01"]["generation"]["route"] = "unsupported_provider"
        shots["editing_animation"]["deliverable"]["shots"]["S01"]["graphics"]["claims_used"] = ["C99"]
        shots["editing_animation"]["deliverable"]["shots"]["S02"]["animation"]["elements"] = [
            {"layer": "Text overlay appears at second 2"}]
        codes = {x["code"] for x in audit.audit_handoffs(state, self.base)["issues"]}
        self.assertTrue({"HANDOFF_INVALID_PRODUCTION_ROUTE", "HANDOFF_UNKNOWN_CLAIM",
                         "HANDOFF_ANIMATION_CONFLICT"} <= codes)

    def test_actor_camera_sound_timing_limits(self):
        state = self.through("ai_technical")
        state["tasks"]["acting"]["deliverable"]["shots"]["S01"]["beats"][0]["to_s"] = 9
        state["tasks"]["camera_art"]["deliverable"]["shots"]["S01"]["camera"]["move_trigger_s"] = 9
        state["tasks"]["sound"]["deliverable"]["shots"]["S01"]["sound"]["effects"][0]["time_s"] = 9
        codes = {x["code"] for x in audit.audit_handoffs(state, self.base)["issues"]}
        self.assertTrue({"HANDOFF_ACTING_TIME_CONFLICT", "HANDOFF_CAMERA_TIME_CONFLICT",
                         "HANDOFF_SOUND_TIME_CONFLICT"} <= codes)

    def test_qa_packet_sees_independent_evidence(self):
        state = self.through("ai_technical")
        state["tasks"]["editing_animation"]["deliverable"]["shots"]["S02"]["editing"]["narrative_bridge"]["beat_link"]["outgoing_beat_index"] = 5
        packet = crew.packet(state, "quality_review")
        self.assertEqual(packet["independent_handoff_audit"]["status"], "blocked")
        self.assertTrue(packet["no_authorized_model_calls"])
        with self.assertRaisesRegex(ValueError, "independent"):
            self.submit(state, "quality_review")

    def test_qa_may_report_revise_and_director_must_request_changes(self):
        state = self.through("ai_technical")
        state["tasks"]["ai_technical"]["deliverable"]["shots"]["S02"]["generation"]["route"] = "unknown"
        state = self.submit(state, "quality_review", {
            "qa_report": {
                "blockers": [{"task_id": "ai_technical", "shot_ids": ["S02"],
                              "detail": "Route invalid"}],
                "findings": [], "recommendation": "revise",
            }})
        with self.assertRaises(ValueError):
            self.submit(state, "director_final")
        state = self.submit(state, "director_final", {
            "director_decision": {"decision": "request_changes",
                                  "rationale": "Route must be revised"}})
        self.assertFalse(state["release"]["director_ai_review_complete"])

    def test_explicit_base_transition_change_requires_review(self):
        state = self.through()
        state["tasks"]["editing_animation"]["deliverable"]["shots"]["S02"]["editing"]["outgoing_transition"] = "smash_cut"
        report = audit.audit_handoffs(state, self.base)
        self.assertIn("HANDOFF_SOURCE_CUT_CONFLICT", [x["code"] for x in report["issues"]])

    def test_revision_proposal_groups_many_shots_of_one_owner(self):
        state = self.through()
        for sid in ("S01", "S03"):
            state["tasks"]["sound"]["deliverable"]["shots"][sid]["speech"]["voiceover"]["text"] = "rewritten"
        old = copy.deepcopy(state)
        result = crew.propose_director_revisions(self.base, state)
        proposals = result["proposals"]
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]["task_id"], "sound")
        self.assertEqual(proposals[0]["shot_ids"], ["S01", "S03"])
        self.assertEqual(result["status"], "director_decision_required")
        self.assertEqual(old, state)

    def test_showrunner_gate_stale_proposal_and_scoped_invalidation(self):
        state = self.through()
        state["tasks"]["acting"]["deliverable"]["shots"]["S02"]["beats"][0]["to_s"] = 8
        proposal = crew.propose_director_revisions(self.base, state)["proposals"][0]
        with self.assertRaisesRegex(ValueError, "showrunner decision"):
            crew.request_planned_revision(self.base, state, proposal)
        altered = copy.deepcopy(proposal)
        altered["shot_ids"] = ["S03"]
        with self.assertRaisesRegex(ValueError, "no longer"):
            crew.request_planned_revision(self.base, state, altered, showrunner_approved=True)
        revised = crew.request_planned_revision(
            self.base, state, proposal, showrunner_approved=True)
        self.assertEqual(revised["tasks"]["acting"]["status"], "needs_revision")
        self.assertEqual(revised["tasks"]["editing_animation"]["status"], "stale")
        self.assertEqual(revised["tasks"]["camera_art"]["status"], "completed")
        self.assertEqual(revised["tasks"]["sound"]["status"], "completed")
        self.assertEqual(revised["tasks"]["editing_animation"]["revision_scope"],
                         ["S01", "S02", "S03"])
        self.assertFalse(revised["release"]["director_ai_review_complete"])

    def test_compiler_fails_closed_when_source_drifts_after_qa(self):
        state = self.through()
        # Simulate stale/tampered payload after an earlier QA conclusion.
        state["tasks"]["sound"]["deliverable"]["shots"]["S03"]["speech"]["voiceover"]["text"] = "unapproved"
        with self.assertRaisesRegex(ValueError, "handoff blockers"):
            crew.compile_team_workbook(self.base, state)

    def test_compiler_fails_closed_on_unresolved_authored_qa(self):
        state = self.through()
        state["tasks"]["quality_review"]["deliverable"]["qa_report"]["blockers"].append(
            {"task_id": "acting", "shot_ids": ["S02"], "detail": "prop jumps"})
        state["tasks"]["quality_review"]["deliverable"]["qa_report"]["recommendation"] = "revise"
        with self.assertRaisesRegex(ValueError, "QA blockers"):
            crew.compile_team_workbook(self.base, state)

    def test_source_plan_fingerprint_is_part_of_revisions(self):
        state = self.through()
        changed = copy.deepcopy(self.base)
        changed["shots"][0]["narration"] = "new narration"
        with self.assertRaisesRegex(ValueError, "base digest"):
            crew.propose_director_revisions(changed, state)


    def test_malformed_route_fails_closed_without_type_error(self):
        state = self.through("ai_technical")
        state["tasks"]["ai_technical"]["deliverable"]["shots"]["S01"]["generation"]["route"] = ["invalid"]
        report = audit.audit_handoffs(state, self.base)
        self.assertIn("HANDOFF_INVALID_PRODUCTION_ROUTE",
                      [issue["code"] for issue in report["issues"]])

    def test_compiler_blocks_missing_specialist_shot_after_qa(self):
        state = self.through()
        del state["tasks"]["camera_art"]["deliverable"]["shots"]["S02"]
        with self.assertRaisesRegex(ValueError, "creative blockers"):
            crew.compile_team_workbook(self.base, state)

    def test_strict_review_gate_needs_bound_source_digest(self):
        state = self.through()
        self.assertFalse(state["source_review_bound"])
        self.assertFalse(state["release"]["human_approved"])
        # A complete source fingerprint is a prerequisite, not a substitute
        # for real creative approval or the production blueprint checks.
        with self.assertRaises((ValueError, KeyError)):
            crew.compile_team_workbook(self.base, state, strict=True)

    def test_cli_audit_propose_and_approval_are_offline(self):
        state = self.through()
        state["tasks"]["sound"]["deliverable"]["shots"]["S01"]["speech"]["voiceover"]["text"] = "changed"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_p, state_p = root / "base.json", root / "state.json"
            base_p.write_text(json.dumps(self.base), encoding="utf-8")
            state_p.write_text(json.dumps(state), encoding="utf-8")
            command = [sys.executable, str(ROOT / "agent_team.py")]
            audit_out = root / "audit.json"
            checked = subprocess.run(command + [
                "audit-handoffs", "--base", str(base_p), "--state", str(state_p),
                "--out", str(audit_out)], capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertEqual(json.loads(audit_out.read_text())["status"], "blocked")

            proposals_out = root / "proposals.json"
            proposed = subprocess.run(command + [
                "propose-revisions", "--base", str(base_p), "--state", str(state_p),
                "--out", str(proposals_out)], capture_output=True, text=True)
            self.assertEqual(proposed.returncode, 0, proposed.stderr)
            proposal = json.loads(proposals_out.read_text())["proposals"][0]
            self.assertEqual(proposal["task_id"], "sound")
            chosen = root / "proposal.json"
            chosen.write_text(json.dumps(proposal), encoding="utf-8")

            revised_out = root / "revised.json"
            blocked = subprocess.run(command + [
                "approve-revision", "--base", str(base_p), "--state", str(state_p),
                "--proposal", str(chosen), "--out", str(revised_out)],
                capture_output=True, text=True)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertFalse(revised_out.exists())
            approved = subprocess.run(command + [
                "approve-revision", "--base", str(base_p), "--state", str(state_p),
                "--proposal", str(chosen), "--approve-showrunner-rework",
                "--out", str(revised_out)], capture_output=True, text=True)
            self.assertEqual(approved.returncode, 0, approved.stderr)
            self.assertEqual(json.loads(revised_out.read_text())["tasks"]["sound"]["status"],
                             "needs_revision")
            self.assertEqual(state_p.read_text(encoding="utf-8"),
                             json.dumps(state))

    def test_cli_workbook_does_not_publish_synthetic_incomplete_draft(self):
        state = self.through()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_p, state_p, out = root / "base.json", root / "state.json", root / "book.json"
            base_p.write_text(json.dumps(self.base), encoding="utf-8")
            state_p.write_text(json.dumps(state), encoding="utf-8")
            result = subprocess.run([
                sys.executable, str(ROOT / "agent_team.py"), "workbook",
                "--base", str(base_p), "--state", str(state_p),
                "--strict", "--out", str(out)],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(out.exists())



if __name__ == "__main__":
    unittest.main()
