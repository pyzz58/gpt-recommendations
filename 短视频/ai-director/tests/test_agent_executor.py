"""Synthetic integration tests for the fixture-only directing-team executor."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import agent_team as team
import agent_executor as executor


class CrewExecutorTests(unittest.TestCase):
    def setUp(self):
        self.base = {
            "title": "Synthetic envelope short",
            "claims": [],
            "shots": [
                {"id": sid, "start": idx * 4, "duration": 4,
                 "narration": f"Original line for {sid}",
                 "transition": "cut" if idx < 2 else "fade_out",
                 "visual_type": "ai_video", "character_ids": ["CHAR01"]}
                for idx, sid in enumerate(("S01", "S02", "S03"))
            ],
        }
        self.secret = "PRIVATE: not for public repository or execution receipts"
        self.fixtures = self._fixtures()

    def _shot_payload(self, role, sids):
        shots = {}
        for sid in sids:
            idx = self._ids.index(sid)
            if role == "acting":
                item = {
                    "staging": {"blocking": "Actor sits at the writing desk, envelope in right hand"},
                    "performance": {"motivation": "Actor hesitates before opening the envelope"},
                    "beats": [{"from_s": 0, "to_s": 4,
                               "visible_change": "Actor holds and then opens envelope with right hand"}],
                    "continuity": {"start_state": "The sealed envelope is in actor's right hand"},
                    "shootability": None,
                }
            elif role == "camera_art":
                item = {
                    "camera": {"movement": "Camera slowly pushes toward envelope",
                               "move_trigger_s": 2},
                    "art": {"light_source": "Warm window light from screen left"},
                }
            elif role == "sound":
                item = {
                    "sound": {"effects": [{"time_s": 2, "cue": "Quiet envelope opening sound"}]},
                    "speech": {"voiceover": {
                        "text": self.base["shots"][idx]["narration"],
                        "timing": "Narrate evenly across the complete shot"},
                        "dialogue": []},
                }
            elif role == "editing_animation":
                item = {
                    "editing": {"cut_reason": "The action completes and the next shot begins",
                                "outgoing_transition": self.base["shots"][idx]["transition"]},
                    "animation": {"mode": "none", "elements": []},
                    "graphics": {"treatment": "Letter is overlaid later in post, never generated",
                                 "claims_used": []},
                }
            elif role == "ai_technical":
                item = {"generation": {"route": "post_production",
                                        "limits": "No external model calls are allowed"}}
            else:
                raise ValueError("unknown fixture role")
            shots[sid] = item
        return {"shots": shots}

    @property
    def _ids(self):
        return [shot["id"] for shot in self.base["shots"]]

    def _fixtures(self):
        global_dir = {
            "audience_emotion_arc": "Suspense grows into relief",
            "visual_grammar": "Stable shots with selective slow camera movement",
            "audio_grammar": "Understated voiceover above quiet ambience",
            "graphic_safety": "No numeric or written claims generated in camera",
            "reference_strategy": "All character and location images remain not_created",
            "generation_budget": "Fixture tests only; zero API or media spending",
        }
        data = {
            "director_brief": {"1": {"creative_brief": {
                "vision": "A quiet story about opening an important envelope"}}},
            "script_edit": {"1": {"story_treatment": {
                "hook": "What is hidden in the handwritten envelope?",
                "source_change_proposals": []}}},
            "director_lock": {"1": {
                "global_direction": global_dir,
                "shot_objectives": {sid: {
                    "emotion": "Curiosity",
                    "observable_turn": "Actor uncovers an important letter",
                    "visual_focus": "The letter and actor's right hand"} for sid in self._ids},
            }},
            "quality_review": {
                "1": {"qa_report": {
                    "blockers": [], "findings": [],
                    "recommendation": "ready_for_director_review"}},
                "2": {"qa_report": {
                    "blockers": [], "findings": [],
                    "recommendation": "ready_for_director_review"}},
            },
            "director_final": {
                "1": {"director_decision": {
                    "decision": "ready_for_user_review",
                    "rationale": "Mock directions ready for human checking only"}},
                "2": {"director_decision": {
                    "decision": "ready_for_user_review",
                    "rationale": "Mock revised directions ready for human checking"}},
            },
        }
        for role in ("acting", "camera_art", "sound", "editing_animation", "ai_technical"):
            data[role] = {"1": self._shot_payload(role, self._ids)}
        # Subsequent rework from acting S02 must refresh adjacent cuts.
        data["acting"]["2"] = self._shot_payload("acting", ["S02"])
        data["editing_animation"]["2"] = self._shot_payload(
            "editing_animation", self._ids)
        data["ai_technical"]["2"] = self._shot_payload(
            "ai_technical", ["S02"])
        return data

    def new(self, bind=False):
        return team.start(self.base, source_text=self.secret if bind else None)

    def run(self, *, bind=False, final=False, adapter=None):
        state = self.new(bind)
        return executor.execute_until_pause(
            self.base, state, adapter or executor.FixtureOnlyAdapter(self.fixtures),
            source_text=self.secret if bind else None,
            allow_fixture_director_final=final)

    def test_all_ten_stages_execute_from_explicit_fixture_inputs(self):
        original = self.new()
        state, report = executor.execute_until_pause(
            self.base, original, executor.FixtureOnlyAdapter(self.fixtures),
            allow_fixture_director_final=True)
        self.assertEqual(report["processed_count"], 10)
        self.assertEqual(report["status"], "no_ready_tasks")
        self.assertEqual([x["task_id"] for x in report["processed"]], list(team.SPECS))
        self.assertEqual(team.ready(state), [])
        self.assertFalse(original["release"]["director_ai_review_complete"])
        self.assertTrue(state["release"]["director_ai_review_complete"])
        self.assertFalse(state["release"]["human_approved"])
        self.assertFalse(state["release"]["paid_api_authorized"])
        self.assertEqual(report["actual_ai_roles_invoked"], 0)
        self.assertEqual(report["external_requests"], 0)
        self.assertNotIn("original_script", json.dumps(report))

    def test_stop_before_final_showrunner_stage_by_default(self):
        state, report = self.run()
        self.assertEqual(report["processed_count"], 9)
        self.assertEqual(report["ready_tasks"], ["director_final"])
        self.assertEqual(report["status"], "director_final_requires_explicit_fixture_permission")
        self.assertFalse(state["release"]["director_ai_review_complete"])
        with self.assertRaisesRegex(ValueError, "explicit fixture-only"):
            executor.execute_one(
                self.base, state, executor.FixtureOnlyAdapter(self.fixtures),
                "director_final")

    def test_partial_mock_fixture_set_pauses_without_tampering_input(self):
        data = deepcopy(self.fixtures)
        del data["camera_art"]
        original = self.new()
        ledger, report = executor.execute_until_pause(
            self.base, original, executor.FixtureOnlyAdapter(data))
        self.assertEqual(report["status"], "fixture_missing")
        self.assertEqual(report["processed_count"], 4)  # director 3 + acting
        self.assertEqual(team.ready(ledger), ["camera_art", "sound"])
        self.assertEqual(original["tasks"]["acting"]["status"], "pending")

    def test_exact_revision_fixture_is_required_for_second_submission(self):
        state, _ = self.run(final=True)
        revised = team.request_revision(state, "acting", ["S02"], "Fix envelope hand continuity")
        data = deepcopy(self.fixtures)
        del data["acting"]["2"]
        ledger, report = executor.execute_until_pause(
            self.base, revised, executor.FixtureOnlyAdapter(data))
        self.assertEqual(report["status"], "fixture_missing")
        self.assertEqual(ledger["tasks"]["acting"]["status"], "needs_revision")
        self.assertFalse(ledger["release"]["director_ai_review_complete"])

    def test_director_rework_preserves_independent_departments(self):
        state, _ = self.run(final=True)
        changed = team.request_revision(state, "acting", ["S02"], "Correct hand action")
        updated, report = executor.execute_until_pause(
            self.base, changed, executor.FixtureOnlyAdapter(self.fixtures),
            allow_fixture_director_final=True)
        self.assertEqual([v["task_id"] for v in report["processed"]],
                         ["acting", "editing_animation", "ai_technical",
                          "quality_review", "director_final"])
        self.assertEqual(updated["tasks"]["acting"]["revision"], 2)
        self.assertEqual(updated["tasks"]["camera_art"]["revision"], 1)
        self.assertEqual(updated["tasks"]["sound"]["revision"], 1)
        self.assertEqual(updated["tasks"]["acting"]["deliverable"]["shots"]["S01"],
                         state["tasks"]["acting"]["deliverable"]["shots"]["S01"])
        self.assertEqual(len(updated["tasks"]["acting"]["previous_versions"]), 1)
        self.assertTrue(updated["release"]["director_ai_review_complete"])

    def test_invalid_field_ownership_is_rejected_without_state_change(self):
        original = self.new()
        updated, _ = executor.execute_until_pause(
            self.base, original, executor.FixtureOnlyAdapter(self.fixtures),
            max_steps=3)
        altered = deepcopy(self.fixtures)
        altered["acting"]["1"]["shots"]["S01"]["camera"] = {
            "movement": "unauthorized department change"}
        snapshot = deepcopy(updated)
        with self.assertRaisesRegex(ValueError, "ownership"):
            executor.execute_one(self.base, updated, executor.FixtureOnlyAdapter(altered))
        self.assertEqual(updated, snapshot)

    def test_source_bound_cannot_proceed_without_correct_private_text(self):
        state = self.new(bind=True)
        adapter = executor.FixtureOnlyAdapter(self.fixtures)
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            executor.execute_one(self.base, state, adapter)
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            executor.execute_one(self.base, state, adapter, source_text="wrong source")
        output, receipt = executor.execute_until_pause(
            self.base, state, adapter, source_text=self.secret, max_steps=1)
        self.assertEqual(receipt["processed_count"], 1)
        self.assertNotIn(self.secret, json.dumps(receipt))
        self.assertNotIn(self.secret, json.dumps(output))
        with self.assertRaisesRegex(ValueError, "cannot attach"):
            executor.execute_one(self.base, self.new(), adapter, source_text=self.secret)

    def test_base_tampering_blocks_all_execution(self):
        state = self.new()
        base = deepcopy(self.base)
        base["shots"][0]["narration"] = "tampered"
        with self.assertRaisesRegex(ValueError, "digest"):
            executor.execute_until_pause(
                base, state, executor.FixtureOnlyAdapter(self.fixtures))

    def test_non_fixture_adapters_are_not_accepted(self):
        class NetworkLike:
            def supply(self, context):
                raise AssertionError("must never invoke")

        class SneakySubclass(executor.FixtureOnlyAdapter):
            def supply(self, context):
                raise AssertionError("must never invoke")

        for adapter in (NetworkLike(), SneakySubclass(self.fixtures)):
            with self.assertRaisesRegex(ValueError, "only exact FixtureOnlyAdapter|model adapters"):
                executor.execute_one(self.base, self.new(), adapter)

    def test_no_automatic_qa_approval_with_source_aware_conflict(self):
        altered = deepcopy(self.fixtures)
        altered["sound"]["1"]["shots"]["S02"]["speech"]["voiceover"]["text"] = "Unapproved narration"
        adapter = executor.FixtureOnlyAdapter(altered)
        partial, report = executor.execute_until_pause(
            self.base, self.new(), adapter, max_steps=8)
        self.assertEqual(report["processed_count"], 8)
        self.assertEqual(team.ready(partial), ["quality_review"])
        with self.assertRaisesRegex(ValueError, "source-aware department blockers"):
            executor.execute_one(self.base, partial, adapter, "quality_review")
        self.assertEqual(partial["tasks"]["quality_review"]["status"], "pending")

    def test_qa_can_report_conflicts_instead_of_falsely_passing(self):
        altered = deepcopy(self.fixtures)
        altered["sound"]["1"]["shots"]["S02"]["speech"]["voiceover"]["text"] = "changed narration"
        altered["quality_review"]["1"] = {"qa_report": {
            "blockers": [{"task_id": "sound", "shot_ids": ["S02"],
                          "detail": "Source narration changed without permission"}],
            "findings": [], "recommendation": "revise"}}
        altered["director_final"]["1"] = {"director_decision": {
            "decision": "request_changes", "rationale": "Return to sound department"}}
        state, report = executor.execute_until_pause(
            self.base, self.new(), executor.FixtureOnlyAdapter(altered),
            allow_fixture_director_final=True)
        self.assertEqual(report["processed_count"], 10)
        self.assertFalse(state["release"]["director_ai_review_complete"])
        self.assertFalse(state["release"]["human_approved"])

    def test_run_limit_checks(self):
        adapter = executor.FixtureOnlyAdapter(self.fixtures)
        for limit in (0, -1, 1.2, True, 51):
            with self.assertRaisesRegex(ValueError, "max_steps"):
                executor.execute_until_pause(self.base, self.new(), adapter, max_steps=limit)

    def test_role_context_is_ephemeral_and_contains_working_contract(self):
        state = self.new(bind=True)
        ctx = executor.role_context(self.base, state, "director_brief",
                                    source_text=self.secret)
        self.assertEqual(ctx["original_script"], self.secret)
        self.assertEqual(ctx["packet"]["source_digest"], state["source_digest"])
        self.assertFalse(ctx["packet"]["source_review_bound"] is False)
        self.assertTrue(ctx["no_external_calls_authorized"])
        self.assertEqual(ctx["role_output_contract"], ["creative_brief"])
        self.assertNotIn(self.secret, json.dumps(state))

    def test_cli_dry_run_and_existing_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            base = folder / "base.json"
            state = folder / "state.json"
            fixtures = folder / "fixtures.json"
            new_state = folder / "new_state.json"
            receipt = folder / "receipt.json"
            base.write_text(json.dumps(self.base), encoding="utf-8")
            state.write_text(json.dumps(self.new()), encoding="utf-8")
            fixtures.write_text(json.dumps(self.fixtures), encoding="utf-8")
            cmd = [sys.executable, str(ROOT / "agent_executor.py"),
                   "--base", str(base), "--state", str(state),
                   "--fixtures", str(fixtures),
                   "--out-state", str(new_state), "--out-receipt", str(receipt),
                   "--max-steps", "3"]
            first = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            data = json.loads(receipt.read_text())
            self.assertEqual(data["processed_count"], 3)
            self.assertEqual(data["actual_ai_roles_invoked"], 0)
            frozen = new_state.read_bytes()
            again = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(again.returncode, 0)
            self.assertEqual(new_state.read_bytes(), frozen)


if __name__ == "__main__":
    unittest.main()
