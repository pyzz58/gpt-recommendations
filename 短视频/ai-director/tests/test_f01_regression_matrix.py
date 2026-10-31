from copy import deepcopy
from itertools import combinations
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import director_acting

COMPARISON = ROOT / "examples/acting-f01/public_performance_directions.json"


def hands():
    return {"left": "free", "right": "free"}


def phase(cast, postures=None, hand_map=None):
    postures = postures or {}
    hand_map = hand_map or {}
    return {
        actor: {
            "posture": postures.get(actor, "standing"),
            "facing": "scene center",
            "hands": deepcopy(hand_map.get(actor, hands())),
        }
        for actor in cast
    }


def relationship_rows(cast):
    rows = []
    for first, second in combinations(sorted(cast), 2):
        rows.append({
            "actor_id": first,
            "target_id": second,
            "gaze": first + " watches " + second,
            "body_orientation": first + " angles toward " + second,
            "distance": "one conversational distance",
            "interaction": first + " and " + second + " negotiate the same object",
        })
        if len(cast) == 2:
            rows.append({
                "actor_id": second,
                "target_id": first,
                "gaze": second + " watches " + first,
                "body_orientation": second + " angles toward " + first,
                "distance": "one conversational distance",
                "interaction": second + " answers " + first,
            })
    return rows


def feasibility(complexity="low", fallback=None):
    return {
        "professional_intent": "Keep the performance readable in a single social unit.",
        "physical_complexity": complexity,
        "model_risk": "No provider test has been run for this scenario.",
        "capability_evidence": "none",
        "evidence_ref": "",
        "test_environment": "",
        "fallback_route": fallback or (
            "Split the scene into a reaction shot and a close insert of the handled object, "
            "then join on the characters' eyeline."),
        "fallback_preserves_story": "The same objective, obstacle and reaction remain visible.",
    }


def source(cast, props=("PROP_OBJECT",)):
    return {
        "id": "S01",
        "duration": 6,
        "character_ids": list(cast),
        "continuity_contract": {
            "props": {prop: {"initial": "LOC01:table"} for prop in props}
        },
    }


def shot_for(cast, *, complexity="low", environment=None, handoffs=None,
             postures=None, hand_map=None, action_units=None):
    return {
        "staging": {
            "physical_state": {
                "start": phase(cast, postures, hand_map),
                "end": phase(cast, postures, hand_map),
                "posture_changes": [],
            },
            "relationship_map": relationship_rows(cast) if len(cast) >= 2 else [],
            "handoffs": handoffs or [],
            "cut_note": "",
            "environment_state": environment or {},
            "production_feasibility": feasibility(complexity),
        },
        "shootability": {
            "mode": "single_take",
            "action_units": action_units or [{
                "id": "A1",
                "beat_index": 0,
                "actor_id": next(iter(cast)) if cast else None,
                "hand": "none",
                "prop_id": None,
                "from_s": 0.0,
                "to_s": 1.0,
                "action": "hold a readable reaction",
                "visible_result": "the reaction stays visible",
            }],
            "fallback": "Use a reaction insert if the continuous take is unstable.",
        },
    }


class F01RegressionMatrixTests(unittest.TestCase):
    def report(self):
        return {"blockers": [], "reviews": []}

    def inspect(self, src, shot):
        report = self.report()
        cast = set(src["character_ids"])
        director_acting._inspect_dual_person(src, shot, cast, report)
        director_acting._inspect_production_feasibility(src, shot, cast, report)
        return report

    def test_single_restrained_and_dual_conflict_pass(self):
        single = {"CH_A"}
        src = source(single)
        report = self.inspect(src, shot_for(single))
        self.assertEqual(report["blockers"], [])

        dual = {"CH_A", "CH_B"}
        src = source(dual)
        report = self.inspect(src, shot_for(dual))
        self.assertEqual(report["blockers"], [])

    def test_absurd_comedy_can_use_causal_environment_interaction(self):
        cast = {"CH_A", "CH_B"}
        src = source(cast)
        shot = shot_for(
            cast,
            complexity="medium",
            environment={
                "doors": {
                    "DOOR_01": {
                        "start": "closed",
                        "end": "open",
                        "changed_by": "CH_B",
                        "cause": "CH_B opens the door at the worst possible moment while CH_A hides the receipt.",
                    }
                }
            },
        )
        report = self.inspect(src, shot)
        self.assertEqual(report["blockers"], [])

    def test_zero_actor_scene_is_not_forced_into_performance(self):
        src = source(set())
        shot = shot_for(set(), complexity="low")
        report = self.inspect(src, shot)
        self.assertEqual(report["blockers"], [])

    def test_three_person_complex_action_with_fallback_passes_with_review(self):
        cast = {"CH_A", "CH_B", "CH_C"}
        src = source(cast)
        start_hands = {
            "CH_A": {"left": "free", "right": "PROP_OBJECT"},
            "CH_B": hands(),
            "CH_C": hands(),
        }
        end_hands = {
            "CH_A": hands(),
            "CH_B": {"left": "free", "right": "PROP_OBJECT"},
            "CH_C": hands(),
        }
        shot = shot_for(cast, complexity="high", hand_map=start_hands)
        shot["staging"]["physical_state"]["end"] = phase(cast, {}, end_hands)
        shot["staging"]["physical_state"]["posture_changes"] = [{
            "actor_id": "CH_C",
            "from": "standing",
            "to": "seated",
            "cause": "CH_C sits down after the object changes hands.",
        }]
        shot["staging"]["physical_state"]["end"]["CH_C"]["posture"] = "seated"
        shot["staging"]["handoffs"] = [{
            "order": 1,
            "from_actor": "CH_A",
            "to_actor": "CH_B",
            "prop_id": "PROP_OBJECT",
            "from_s": 2.0,
            "to_s": 3.0,
            "action": "CH_A hands the object to CH_B.",
            "visible_result": "CH_B now holds the object.",
            "visible": True,
        }]
        shot["shootability"]["action_units"] = [
            {
                "id": f"A{i}",
                "beat_index": 0,
                "actor_id": "CH_A",
                "hand": "left" if i % 2 else "right",
                "prop_id": None,
                "from_s": 0.2 * i,
                "to_s": 0.2 * i + 0.1,
                "action": "hold a reaction",
                "visible_result": "the group reaction stays visible",
            }
            for i in range(1, 5)
        ]
        report = self.inspect(src, shot)
        self.assertEqual(report["blockers"], [])
        self.assertIn("ACTING_SINGLE_TAKE_REVIEW",
                      {row["code"] for row in report["reviews"]})

    def test_unmotivated_handoff_is_blocked(self):
        cast = {"CH_A", "CH_B"}
        src = source(cast)
        start_hands = {
            "CH_A": {"left": "free", "right": "PROP_OBJECT"},
            "CH_B": hands(),
        }
        end_hands = {
            "CH_A": hands(),
            "CH_B": {"left": "free", "right": "PROP_OBJECT"},
        }
        shot = shot_for(cast, hand_map=start_hands)
        shot["staging"]["physical_state"]["end"] = phase(cast, {}, end_hands)
        report = self.inspect(src, shot)
        self.assertIn("ACTING_HANDOFF_MISSING",
                      {row["code"] for row in report["blockers"]})

    def test_two_performance_directions_are_explicitly_not_human_blind_review(self):
        data = json.loads(COMPARISON.read_text(encoding="utf-8"))
        self.assertEqual(data["review_status"],
                         "self_authored_textual_comparison_not_human_blind_review")
        directions = data["directions"]
        self.assertEqual(len(directions), 2)
        tactics = [tuple(item["tactic_sequence"]) for item in directions]
        self.assertNotEqual(tactics[0], tactics[1])
        for item in directions:
            for field in ("objective", "obstacle", "reaction",
                          "audience_effect", "tradeoffs"):
                self.assertTrue(item[field])


if __name__ == "__main__":
    unittest.main()
