from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import agent_role_contracts as roles
import agent_team
import director_acting
sys.path.insert(0, str(ROOT / "tests"))
from test_agent_role_contracts import ProfessionalRoleContractsTests

FIXTURE = ROOT / "examples/acting-f01/public_letter_strict_contract.json"


class DirectorActingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def bound_state_and_bible(self):
        base = deepcopy(self.data["base"])
        state = agent_team.start(base, source_text=self.data["source_text"])
        bible = deepcopy(
            self.data["director_lock"]["global_direction"]["performance_bible"])
        bible["source_digest"] = state["source_digest"]
        state["tasks"]["director_lock"]["deliverable"] = {
            "global_direction": {"performance_bible": bible},
        }
        return base, state, bible

    def inspect(self, base=None, state=None, acting=None):
        base = base or deepcopy(self.data["base"])
        state = state or agent_team.start(base, source_text=self.data["source_text"])
        bible = deepcopy(
            self.data["director_lock"]["global_direction"]["performance_bible"])
        bible["source_digest"] = state["source_digest"]
        state["tasks"]["director_lock"]["deliverable"] = {
            "global_direction": {"performance_bible": bible},
        }
        acting = acting or deepcopy(self.data["acting"])
        return base, state, bible, director_acting.inspect_delivery(base, state, acting)

    def test_positive_strict_contract_passes(self):
        base, state, bible = self.bound_state_and_bible()
        bible_report = director_acting.inspect_bible(
            base, state, {"performance_bible": bible})
        self.assertEqual(bible_report["blockers"], [])
        delivery = director_acting.inspect_delivery(
            base, state, deepcopy(self.data["acting"]))
        self.assertEqual(delivery["blockers"], [])

    def test_missing_character_contracts_blocks(self):
        base, state, _ = self.bound_state_and_bible()
        acting = deepcopy(self.data["acting"])
        acting["shots"]["S01"]["performance"].pop("character_contracts")
        report = director_acting.inspect_delivery(base, state, acting)
        self.assertIn("ACTING_CHARACTER_CONTRACTS_MISSING",
                      {row["code"] for row in report["blockers"]})

    def test_stale_bible_blocks(self):
        base, state, bible = self.bound_state_and_bible()
        bible["source_digest"] = "f" * 64
        report = director_acting.inspect_bible(
            base, state, {"performance_bible": bible})
        self.assertIn("ACTING_BIBLE_SOURCE_STALE",
                      {row["code"] for row in report["blockers"]})

    def test_overlapping_hand_prop_blocks(self):
        base, state, _ = self.bound_state_and_bible()
        acting = deepcopy(self.data["acting"])
        acting["shots"]["S01"]["staging"]["hand_prop"].append({
            "actor_id": "CH_DAUGHTER",
            "hand": "right",
            "prop_id": "PROP_LETTER",
            "from_s": 4.5,
            "to_s": 5.5,
            "action": "hold the letter with the same right hand",
            "visible_result": "letter remains below the table edge",
        })
        report = director_acting.inspect_delivery(base, state, acting)
        self.assertIn("ACTING_HAND_OVERLAP",
                      {row["code"] for row in report["blockers"]})

    def test_generic_language_is_review_not_automatic_block(self):
        base, state, _ = self.bound_state_and_bible()
        acting = deepcopy(self.data["acting"])
        acting["shots"]["S01"]["performance"]["character_contracts"][
            "CH_DAUGHTER"]["tactic"] = "自然地表演"
        report = director_acting.inspect_delivery(base, state, acting)
        self.assertEqual(report["blockers"], [])
        self.assertIn("ACTING_GENERIC_LANGUAGE",
                      {row["code"] for row in report["reviews"]})

    def test_zero_actor_shot_needs_reason_and_passes(self):
        base, state, _ = self.bound_state_and_bible()
        base["shots"][0]["character_ids"] = []
        acting = deepcopy(self.data["acting"])
        performance = acting["shots"]["S01"]["performance"]
        performance["character_contracts"] = {}
        performance["no_performer_reason"] = "Pure tabletop insert; no performer enters this diagram shot."
        report = director_acting.inspect_delivery(base, state, acting)
        self.assertEqual(report["blockers"], [])

    def test_schema_requires_strict_fields(self):
        base, state, _ = self.bound_state_and_bible()
        lock_schema = roles.execution_output_schema(base, state, "director_lock")
        self.assertIn(
            "performance_bible",
            lock_schema["properties"]["global_direction"]["required"])
        acting_schema = roles.execution_output_schema(base, state, "acting")
        shot_schema = acting_schema["properties"]["shots"]["properties"]["S01"]
        self.assertIn(
            "character_contracts",
            shot_schema["properties"]["performance"]["required"])

    def test_legacy_mode_is_not_forced(self):
        base = deepcopy(self.data["base"])
        base.pop("acting_contract_mode")
        state = agent_team.start(base, source_text=self.data["source_text"])
        report = director_acting.inspect_delivery(
            base, state, deepcopy(self.data["acting"]))
        self.assertTrue(report.get("not_required"))

    def test_invalid_mode_is_rejected_by_schema(self):
        base = deepcopy(self.data["base"])
        base["acting_contract_mode"] = {"kind": "wrong", "version": 1}
        state = agent_team.start(base, source_text=self.data["source_text"])
        with self.assertRaisesRegex(
                ValueError, "CREW_ACTING_CONTRACT_MODE_INVALID"):
            roles.execution_output_schema(base, state, "acting")

    def test_strict_director_lock_validation_is_wired(self):
        base, state, bible = self.bound_state_and_bible()
        payload = {
            "global_direction": {
                "audience_emotion_arc": "Hesitation to a controlled answer",
                "visual_grammar": "A fixed two-shot at the table",
                "audio_grammar": "Quiet room tone and restrained dialogue",
                "graphic_safety": "No text in generated footage",
                "reference_strategy": "No reference images exist yet",
                "generation_budget": "No paid generation is authorized",
                "performance_bible": bible,
            },
            "shot_objectives": {
                "S01": {
                    "emotion": "Controlled alarm",
                    "observable_turn": "The letter leaves the tabletop",
                    "visual_focus": "The daughter's right hand",
                },
            },
        }
        with patch.object(roles.executor, "_check"), \
             patch.object(roles.team, "ready", return_value=["director_lock"]), \
             patch.object(roles, "parse_strict_json", return_value=payload), \
             patch.object(roles.acting_contract, "inspect_bible",
                          return_value={"blockers": [{"code": "TEST"}]}):
            with self.assertRaisesRegex(ValueError, "CREW_ACTING_BIBLE_BLOCKED"):
                roles.validate_role_output(
                    base, state, "director_lock", "{}",
                    source_text=self.data["source_text"])

    def test_strict_acting_validation_is_wired(self):
        base, state, _ = self.bound_state_and_bible()
        payload = deepcopy(self.data["acting"])
        with patch.object(roles.executor, "_check"), \
             patch.object(roles.team, "ready", return_value=["acting"]), \
             patch.object(roles, "parse_strict_json", return_value=payload), \
             patch.object(roles.acting_contract, "inspect_delivery",
                          return_value={"blockers": [{"code": "TEST"}]}):
            with self.assertRaisesRegex(ValueError, "CREW_ACTING_CONTRACT_BLOCKED"):
                roles.validate_role_output(
                    base, state, "acting", "{}",
                    source_text=self.data["source_text"])

    def test_strict_role_messages_include_f01_boundaries(self):
        base, state, _ = self.bound_state_and_bible()
        source = self.data["source_text"]

        def fake_context(base_arg, state_arg, task_id, *, source_text=None):
            spec = roles.team.SPECS[task_id]
            return {
                "packet": {
                    "role": spec["role"],
                    "task_kind": spec["kind"],
                    "revision_scope": None,
                    "shot_ids": list(state["shot_ids"]),
                    "allowed_fields": list(spec["fields"]),
                    "dependency_revisions": {},
                    "base_digest": state["base_digest"],
                    "source_digest": state["source_digest"],
                    "source_review_bound": True,
                    "upstream_artifacts": {},
                    "independent_handoff_audit": None,
                },
                "authoritative_base": base,
                "original_script": source,
                "next_revision": 1,
            }

        with patch.object(roles.executor, "role_context", side_effect=fake_context):
            lock = roles.build_role_messages(
                base, state, "director_lock", source_text=source)
            acting = roles.build_role_messages(
                base, state, "acting", source_text=source)
        self.assertIn("F01 人物表演圣经",
                      lock["messages"][0]["content"])
        self.assertIn("F01 逐镜表演合同",
                      acting["messages"][0]["content"])

    def _two_shot_case(self):
        base = deepcopy(self.data["base"])
        second = deepcopy(base["shots"][0])
        second["id"] = "S02"
        second["start"] = 6
        second["source_adaptation"] = {
            "beat_id": "B002",
            "covered_beat_ids": ["B002"],
        }
        base["shots"].append(second)
        base["duration"] = 12
        state = agent_team.start(base, source_text=self.data["source_text"])
        bible = deepcopy(
            self.data["director_lock"]["global_direction"]["performance_bible"])
        bible["source_digest"] = state["source_digest"]
        state["tasks"]["director_lock"]["deliverable"] = {
            "global_direction": {"performance_bible": bible},
        }
        acting = deepcopy(self.data["acting"])
        acting["shots"]["S02"] = deepcopy(acting["shots"]["S01"])
        acting["shots"]["S02"]["performance"]["character_contracts"][
            "CH_DAUGHTER"]["source_beat_id"] = "B002"
        acting["shots"]["S02"]["performance"]["character_contracts"][
            "CH_MOTHER"]["source_beat_id"] = "B002"
        return base, state, bible, acting

    def test_dual_person_handoff_positive_passes(self):
        base, state, _ = self.bound_state_and_bible()
        acting = deepcopy(self.data["acting"])
        staging = acting["shots"]["S01"]["staging"]
        staging["hand_prop"] = [{
            "actor_id": "CH_DAUGHTER",
            "hand": "right",
            "prop_id": "PROP_LETTER",
            "from_s": 4.0,
            "to_s": 5.4,
            "action": "Hand the letter across the table to CH_MOTHER.",
            "visible_result": "The mother takes the letter into her right hand.",
        }]
        staging["physical_state"]["start"]["CH_DAUGHTER"]["hands"]["right"] = "PROP_LETTER"
        staging["physical_state"]["end"]["CH_DAUGHTER"]["hands"]["right"] = "free"
        staging["physical_state"]["end"]["CH_MOTHER"]["hands"]["right"] = "PROP_LETTER"
        staging["handoffs"] = [{
            "order": 1,
            "from_actor": "CH_DAUGHTER",
            "to_actor": "CH_MOTHER",
            "prop_id": "PROP_LETTER",
            "from_s": 4.0,
            "to_s": 5.4,
            "action": "Hand the letter across the table.",
            "visible_result": "The letter changes hands and stays in frame.",
            "visible": True,
        }]
        report = director_acting.inspect_delivery(base, state, acting)
        self.assertEqual(report["blockers"], [])

    def test_dual_person_handoff_without_event_blocks(self):
        base, state, _ = self.bound_state_and_bible()
        acting = deepcopy(self.data["acting"])
        staging = acting["shots"]["S01"]["staging"]
        staging["physical_state"]["start"]["CH_DAUGHTER"]["hands"]["right"] = "PROP_LETTER"
        staging["physical_state"]["end"]["CH_DAUGHTER"]["hands"]["right"] = "free"
        staging["physical_state"]["end"]["CH_MOTHER"]["hands"]["right"] = "PROP_LETTER"
        staging["handoffs"] = []
        report = director_acting.inspect_delivery(base, state, acting)
        self.assertIn("ACTING_HANDOFF_MISSING",
                      {row["code"] for row in report["blockers"]})

    def test_dual_person_relationship_map_is_required(self):
        base, state, _ = self.bound_state_and_bible()
        acting = deepcopy(self.data["acting"])
        acting["shots"]["S01"]["staging"].pop("relationship_map")
        report = director_acting.inspect_delivery(base, state, acting)
        self.assertIn("ACTING_RELATIONSHIP_MAP_MISSING",
                      {row["code"] for row in report["blockers"]})

    def test_cross_shot_posture_jump_blocks(self):
        base, state, _, acting = self._two_shot_case()
        acting["shots"]["S01"]["staging"]["physical_state"]["end"][
            "CH_DAUGHTER"]["posture"] = "seated"
        acting["shots"]["S02"]["staging"]["physical_state"]["start"][
            "CH_DAUGHTER"]["posture"] = "standing"
        acting["shots"]["S02"]["staging"]["physical_state"]["end"][
            "CH_DAUGHTER"]["posture"] = "standing"
        report = director_acting.inspect_delivery(base, state, acting)
        self.assertIn("ACTING_POSTURE_STATE_JUMP",
                      {row["code"] for row in report["blockers"]})

    def test_cross_shot_hand_jump_blocks_unless_explained(self):
        base, state, _, acting = self._two_shot_case()
        acting["shots"]["S01"]["staging"]["physical_state"]["end"][
            "CH_DAUGHTER"]["hands"]["right"] = "PROP_LETTER"
        acting["shots"]["S02"]["staging"]["physical_state"]["start"][
            "CH_MOTHER"]["hands"]["right"] = "PROP_LETTER"
        acting["shots"]["S02"]["staging"]["physical_state"]["end"][
            "CH_MOTHER"]["hands"]["right"] = "PROP_LETTER"
        report = director_acting.inspect_delivery(base, state, acting)
        self.assertIn("ACTING_HAND_STATE_JUMP",
                      {row["code"] for row in report["blockers"]})
        acting["shots"]["S02"]["staging"]["cut_note"] = (
            "Intentional match cut; the handoff occurs in the edit gap and is not a visible action.")
        report = director_acting.inspect_delivery(base, state, acting)
        self.assertNotIn("ACTING_HAND_STATE_JUMP",
                         {row["code"] for row in report["blockers"]})
        self.assertIn("ACTING_INTENTIONAL_CUT_STATE_CHANGE",
                      {row["code"] for row in report["reviews"]})

    def test_door_change_with_cause_passes(self):
        base, state, _ = self.bound_state_and_bible()
        acting = deepcopy(self.data["acting"])
        acting["shots"]["S01"]["staging"]["environment_state"] = {
            "doors": {
                "DOOR_01": {
                    "start": "closed",
                    "end": "open",
                    "changed_by": "CH_MOTHER",
                    "cause": "The mother opens the door behind her while keeping eye contact.",
                }
            },
            "windows": {},
        }
        report = director_acting.inspect_delivery(base, state, acting)
        self.assertEqual(report["blockers"], [])

    def test_door_change_without_cause_blocks(self):
        base, state, _ = self.bound_state_and_bible()
        acting = deepcopy(self.data["acting"])
        acting["shots"]["S01"]["staging"]["environment_state"] = {
            "doors": {
                "DOOR_01": {
                    "start": "closed",
                    "end": "open",
                    "changed_by": "CH_MOTHER",
                    "cause": "",
                }
            }
        }
        report = director_acting.inspect_delivery(base, state, acting)
        self.assertIn("ACTING_ENVIRONMENT_CHANGE_UNMOTIVATED",
                      {row["code"] for row in report["blockers"]})

    def test_cross_shot_environment_jump_blocks_unless_explained(self):
        base, state, _, acting = self._two_shot_case()
        acting["shots"]["S01"]["staging"]["environment_state"] = {
            "doors": {
                "DOOR_01": {
                    "start": "closed",
                    "end": "open",
                    "changed_by": "CH_MOTHER",
                    "cause": "The mother opens the door.",
                }
            }
        }
        acting["shots"]["S02"]["staging"]["environment_state"] = {
            "doors": {
                "DOOR_01": {
                    "start": "closed",
                    "end": "closed",
                    "changed_by": "",
                    "cause": "",
                }
            }
        }
        report = director_acting.inspect_delivery(base, state, acting)
        self.assertIn("ACTING_ENVIRONMENT_STATE_JUMP",
                      {row["code"] for row in report["blockers"]})
        acting["shots"]["S02"]["staging"]["cut_note"] = (
            "Intentional cut to a second angle; the door closes in the edit gap.")
        report = director_acting.inspect_delivery(base, state, acting)
        self.assertNotIn("ACTING_ENVIRONMENT_STATE_JUMP",
                         {row["code"] for row in report["blockers"]})
        self.assertIn("ACTING_INTENTIONAL_CUT_STATE_CHANGE",
                      {row["code"] for row in report["reviews"]})

    def test_three_person_relationship_pairs_required(self):
        source = {
            "id": "S01",
            "duration": 6,
            "continuity_contract": {"props": {}},
        }
        cast = {"CH_A", "CH_B", "CH_C"}
        phase = {
            actor: {
                "posture": "standing",
                "facing": "the group center",
                "hands": {"left": "free", "right": "free"},
            }
            for actor in cast
        }
        rows = [
            {
                "actor_id": "CH_A",
                "target_id": "CH_B",
                "gaze": "CH_A watches CH_B",
                "body_orientation": "CH_A turns toward CH_B",
                "distance": "one step apart",
                "interaction": "A challenges B",
            },
            {
                "actor_id": "CH_B",
                "target_id": "CH_C",
                "gaze": "CH_B glances at CH_C",
                "body_orientation": "CH_B angles toward CH_C",
                "distance": "one step apart",
                "interaction": "B asks C to choose a side",
            },
            {
                "actor_id": "CH_C",
                "target_id": "CH_A",
                "gaze": "CH_C looks at CH_A",
                "body_orientation": "CH_C faces CH_A",
                "distance": "across the group",
                "interaction": "C refuses the challenge",
            },
        ]
        shot = {
            "staging": {
                "physical_state": {
                    "start": phase,
                    "end": deepcopy(phase),
                    "posture_changes": [],
                },
                "relationship_map": rows,
                "handoffs": [],
                "cut_note": "",
            }
        }
        report = {"blockers": [], "reviews": []}
        director_acting._inspect_dual_person(source, shot, cast, report)
        self.assertEqual(report["blockers"], [])
        shot["staging"]["relationship_map"] = rows[:2]
        report = {"blockers": [], "reviews": []}
        director_acting._inspect_dual_person(source, shot, cast, report)
        self.assertIn("ACTING_RELATIONSHIP_PAIR_MISSING",
                      {row["code"] for row in report["blockers"]})

    def test_missing_production_feasibility_blocks(self):
        base, state, _ = self.bound_state_and_bible()
        acting = deepcopy(self.data["acting"])
        acting["shots"]["S01"]["staging"].pop("production_feasibility")
        report = director_acting.inspect_delivery(base, state, acting)
        self.assertIn("ACTING_FEASIBILITY_MISSING",
                      {row["code"] for row in report["blockers"]})

    def test_tested_capability_without_evidence_blocks(self):
        base, state, _ = self.bound_state_and_bible()
        acting = deepcopy(self.data["acting"])
        feasibility = acting["shots"]["S01"]["staging"]["production_feasibility"]
        feasibility["capability_evidence"] = "tested"
        feasibility["evidence_ref"] = ""
        feasibility["test_environment"] = ""
        report = director_acting.inspect_delivery(base, state, acting)
        codes = {row["code"] for row in report["blockers"]}
        self.assertIn("ACTING_CAPABILITY_EVIDENCE_MISSING", codes)
        self.assertIn("ACTING_TEST_ENVIRONMENT_MISSING", codes)

    def test_high_complexity_single_take_requires_fallback(self):
        base, state, _ = self.bound_state_and_bible()
        acting = deepcopy(self.data["acting"])
        shot = acting["shots"]["S01"]
        shot["shootability"]["action_units"].extend([
            {
                "id": f"A{i}",
                "beat_index": 0,
                "actor_id": "CH_DAUGHTER",
                "hand": "left" if i % 2 else "right",
                "prop_id": None,
                "from_s": 0.1 * i,
                "to_s": 0.1 * i + 0.3,
                "action": "hold a readable reaction beat",
                "visible_result": "the actor holds the reaction",
            }
            for i in range(2, 5)
        ])
        feasibility = shot["staging"]["production_feasibility"]
        feasibility["physical_complexity"] = "high"
        feasibility["fallback_route"] = ""
        report = director_acting.inspect_delivery(base, state, acting)
        self.assertIn("ACTING_FALLBACK_MISSING",
                      {row["code"] for row in report["blockers"]})

    def test_high_complexity_single_take_with_fallback_is_review(self):
        base, state, _ = self.bound_state_and_bible()
        acting = deepcopy(self.data["acting"])
        shot = acting["shots"]["S01"]
        shot["shootability"]["action_units"].extend([
            {
                "id": f"A{i}",
                "beat_index": 0,
                "actor_id": "CH_DAUGHTER",
                "hand": "left" if i % 2 else "right",
                "prop_id": None,
                "from_s": 0.1 * i,
                "to_s": 0.1 * i + 0.3,
                "action": "hold a readable reaction beat",
                "visible_result": "the actor holds the reaction",
            }
            for i in range(2, 5)
        ])
        shot["staging"]["production_feasibility"]["physical_complexity"] = "high"
        report = director_acting.inspect_delivery(base, state, acting)
        self.assertNotIn("ACTING_FALLBACK_MISSING",
                         {row["code"] for row in report["blockers"]})
        self.assertIn("ACTING_SINGLE_TAKE_REVIEW",
                      {row["code"] for row in report["reviews"]})

    def test_documented_capability_with_reference_passes(self):
        base, state, _ = self.bound_state_and_bible()
        acting = deepcopy(self.data["acting"])
        feasibility = acting["shots"]["S01"]["staging"]["production_feasibility"]
        feasibility["capability_evidence"] = "documented"
        feasibility["evidence_ref"] = "https://example.org/reviewed-provider-capability"
        report = director_acting.inspect_delivery(base, state, acting)
        self.assertEqual(report["blockers"], [])


class StrictActingPipelineTests(ProfessionalRoleContractsTests):
    """Reuse the existing ten-role fixture with the strict F01 mode enabled."""

    def _acting_context(self, packet):
        marker = "\n仅返回符合 output_json_schema 的 JSON，内容还必须满足专业岗位细则：\n"
        _, _, encoded = packet["messages"][1]["content"].partition(marker)
        self.assertTrue(encoded)
        return json.loads(encoded)["acting_contract_context"]

    def setUp(self):
        super().setUp()
        self.base["characters"] = [
            {"id": "CHAR01"},
            {"id": "CHAR02"},
        ]
        self.base["scenes"] = [
            {"id": "SC01", "description": "Synthetic table scene"}
        ]
        for index, shot in enumerate(self.base["shots"], 1):
            shot["source_adaptation"] = {"beat_id": f"B{index:03d}"}
        self.base["acting_contract_mode"] = {
            "kind": "source_bound_acting_bible_required",
            "version": 1,
        }
        self.state = agent_team.start(self.base, source_text=self.original)

    def payload(self, name, scope=None):
        payload = super().payload(name, scope)
        if name == "director_lock":
            payload["global_direction"]["performance_bible"] = {
                "version": 1,
                "source_digest": self.state["source_digest"],
                "characters": {
                    "CHAR01": {
                        "given_circumstances": "A synthetic letter sits on a table in a quiet room.",
                        "relationships": [
                            {
                                "character_id": "CHAR02",
                                "relation": "synthetic scene partner",
                                "stakes": "The partner may see the letter first."
                            }
                        ],
                        "objective": "Open the letter before the partner can stop the action.",
                        "obstacle": "The character fears what the letter will reveal.",
                        "tactic_habits": [
                            "Reach for the envelope while keeping the other hand still.",
                            "Pause with the fingers above the seal."
                        ],
                        "subtext": "I need to know, even if I am not ready.",
                        "entry_state": "Seated with the sealed envelope within reach.",
                        "exit_state": "Envelope open, held in the right hand.",
                        "source_spans": [
                            {
                                "scene_id": "SC01",
                                "beat_id": "B001",
                                "quote": "A sealed envelope waits on the table."
                            }
                        ]
                    }
                }
            }
        if name == "acting":
            ids = list(self.state["shot_ids"] if scope is None else scope)
            for sid in ids:
                source = next(
                    shot for shot in self.base["shots"] if shot["id"] == sid)
                beat_id = source["source_adaptation"]["beat_id"]
                payload["shots"][sid]["performance"]["character_contracts"] = {
                    "CHAR01": {
                        "trigger": "The envelope is within reach and the partner is not looking away.",
                        "objective": "Open the envelope before the partner intervenes.",
                        "obstacle": "Fear of the letter's contents makes the hand hesitate.",
                        "tactic": "Reach, pause above the seal, then break the seal with the right hand.",
                        "subtext": "I need to know, even if I am not ready.",
                        "reaction": "The right hand trembles, then moves decisively.",
                        "visible_change": "The right hand moves from hesitation to opening the envelope.",
                        "ending_state": "The opened letter is held in the right hand.",
                        "source_beat_id": beat_id
                    }
                }
                staging = payload["shots"][sid]["staging"]
                staging["physical_state"] = {
                    "start": {
                        "CHAR01": {
                            "posture": "seated",
                            "facing": "SCREEN_LEFT",
                            "hands": {"left": "free", "right": "free"}
                        }
                    },
                    "end": {
                        "CHAR01": {
                            "posture": "seated",
                            "facing": "SCREEN_LEFT",
                            "hands": {"left": "free", "right": "free"}
                        }
                    },
                    "posture_changes": []
                }
                staging["relationship_map"] = []
                staging["handoffs"] = []
                staging["cut_note"] = ""
                staging["production_feasibility"] = {
                    "professional_intent": "Keep the hand and letter action in one readable beat.",
                    "physical_complexity": "low",
                    "model_risk": "A small prop action; no provider test exists.",
                    "capability_evidence": "none",
                    "evidence_ref": "",
                    "test_environment": "",
                    "fallback_route": "Use two smaller shots with a close-up of the hand and a separate reaction if the single take fails.",
                    "fallback_preserves_story": "The envelope action and reaction remain visible in the edit.",
                }
        return payload

    def test_strict_ten_role_pipeline_passes(self):
        self.advance()
        self.assertEqual(agent_team.ready(self.state), [])
        self.assertFalse(self.state["release"]["human_approved"])
        self.assertFalse(self.state["release"]["paid_api_authorized"])

    def test_downstream_roles_receive_versioned_acting_context(self):
        self.advance("director_lock")
        planning = roles.build_role_messages(
            self.base, self.state, "camera_art", source_text=self.original)
        context = self._acting_context(planning)
        self.assertEqual(context["status"], "planning_only")
        self.assertTrue(context["performance_bible_digest"])
        self.assertIsNone(context["acting_delivery_digest"])

        self.state = agent_team.start(self.base, source_text=self.original)
        self.advance("acting")
        for task_id in ("camera_art", "sound"):
            packet = roles.build_role_messages(
                self.base, self.state, task_id, source_text=self.original)
            context = self._acting_context(packet)
            self.assertEqual(context["status"], "completed")
            self.assertTrue(context["acting_delivery_digest"])
            self.assertEqual(context["consumer_task"], task_id)

        self.state = agent_team.start(self.base, source_text=self.original)
        self.advance("editing_animation")
        packet = roles.build_role_messages(
            self.base, self.state, "ai_technical", source_text=self.original)
        self.assertEqual(self._acting_context(packet)["status"], "completed")

        self.state = agent_team.start(self.base, source_text=self.original)
        self.advance("ai_technical")
        packet = roles.build_role_messages(
            self.base, self.state, "quality_review", source_text=self.original)
        self.assertEqual(self._acting_context(packet)["status"], "completed")

    def test_scoped_acting_revision_scopes_downstream_context(self):
        self.advance()
        before = director_acting.downstream_context(
            self.base, self.state, "editing_animation")
        revised = agent_team.request_revision(
            self.state, "acting", ["S02"], "Correct the right-hand handoff")
        self.state = revised
        self.assertEqual(self.state["tasks"]["camera_art"]["status"], "completed")
        self.assertEqual(self.state["tasks"]["sound"]["status"], "completed")
        for task_id in ("editing_animation", "ai_technical",
                        "quality_review", "director_final"):
            self.assertEqual(self.state["tasks"][task_id]["status"], "stale")
        after = director_acting.downstream_context(
            self.base, self.state, "editing_animation")
        self.assertEqual(after["status"], "needs_revision")
        self.assertEqual(after["acting_revision_scope"], ["S02"])
        self.assertIsNone(after["acting_delivery_digest"])
        self.assertTrue(after["previous_acting_delivery_digest"])
        self.assertNotEqual(before["contract_digest"], after["contract_digest"])
        self.assertIn("S02",
                      self.state["tasks"]["editing_animation"]["revision_scope"])


if __name__ == "__main__":
    unittest.main()
