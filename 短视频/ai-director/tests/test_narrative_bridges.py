"""Synthetic, provider-free narrative/visual transition tests."""
import copy
import sys
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import director_v2 as v2
import director_narrative_bridges as bridge
import director_workbook as workbook


def authored_contract(prev, nxt):
    return {
        "cut_intention": {
            "viewer_question": "What does this beat make the audience want to know next?",
            "answer_or_reframe": "The next shot shows the consequence",
            "why_cut_here": "Visible beat completes; moving to its consequence now",
            "information_change": "From subjective choice to visible result",
            "cut_type": "reveal",
        },
        "emotion_pacing": {
            "emotion_before": "hesitation", "emotion_after": "recognition",
            "audience_effect": "Allow attention to shift with the information",
            "tempo_change": "decelerate",
            "tempo_reason": "Give the idea room instead of adding empty speed",
            "hold_before_s": min(0.6, prev["duration"]),
            "settle_after_s": min(0.5, nxt["duration"]),
        },
        "visual_handoff": {
            "outgoing_frame_anchor": "Person stops their hand motion",
            "incoming_frame_anchor": "Graph symbol appears on the same side",
            "axis_or_gaze_rule": "Keep the viewer's reading axis stable",
            "motion_or_prop_link": "Hand motion resolves as the following symbol",
            "relation": "match_shape"
        },
        "style_handoff": {
            "strategy": "graphic_match",
            "palette_target": "Muted cool grey with a restrained warm accent",
            "lighting_logic": "Match direction of tonal emphasis, not fake sunlight",
            "composition_rule": "Keep subject in safe central vertical 9:16 area",
            "texture_rule": "Avoid photo-to-graphic over-sharpening and noisy grain",
            "typography_rule": "Use the same title/safe-margin treatment",
            "implementation": "Use a graded still of the outgoing frame, then same matte"
        }
    }


class NarrativeBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=v2.read_json(ROOT/"examples/quit-smoking/plan.json")
        cls.direction=v2.read_json(ROOT/"examples/quit-smoking/direction_v02.json")

    def copy(self):
        return copy.deepcopy(self.base),copy.deepcopy(self.direction)

    def authored(self):
        base,d=self.copy()
        for i in range(len(base["shots"])-1):
            d["shots"][i]["editing"]={"narrative_bridge":authored_contract(
                base["shots"][i],base["shots"][i+1])}
        return base,d

    def test_missing_bridges_are_marked_pending_instead_of_assumed(self):
        b,d=self.copy()
        bridges,findings=bridge.review(b,d,v2.production_route)
        self.assertEqual(len(bridges),len(b["shots"])-1)
        self.assertEqual(sum(f["code"]=="NARRATIVE_BRIDGE_MISSING" for f in findings),
                         len(b["shots"])-1)
        self.assertEqual(bridges[0]["design_status"],"missing")
        self.assertTrue(bridges[0]["human_visual_review_required"])

    def test_all_authored_paired_connections_handoff_ready_but_unapproved(self):
        b,d=self.authored()
        bridges,findings=bridge.review(b,d,v2.production_route)
        self.assertTrue(all(t["design_status"]=="authored" for t in bridges))
        self.assertEqual([f for f in findings if f["severity"] in ("pending","blocker")],[])
        result=workbook.compile_workbook(b,d)
        self.assertTrue(result["director_review"]["narrative_handoff_ready"])
        self.assertFalse(result["human_approved"])
        self.assertFalse(result["publishing_allowed"])
        self.assertFalse(result["director_review"]["production_blueprint_ready"])  # Other creative fields missing

    def test_both_shots_and_exact_cut_timeline_are_kept(self):
        b,d=self.authored()
        cuts,_=bridge.review(b,d,v2.production_route)
        self.assertEqual(cuts[0]["from_shot_id"],"S01")
        self.assertEqual(cuts[0]["to_shot_id"],"S02")
        self.assertEqual(cuts[0]["cut_at_s"],5)
        self.assertEqual(cuts[1]["cut_at_s"],11)
        self.assertEqual(cuts[-1]["cut_at_s"],b["shots"][-1]["start"])
        self.assertEqual(cuts[0]["from_route"],"ai_video")
        self.assertEqual(cuts[0]["to_route"],"post_production")

    def test_route_switch_requires_visual_review_even_if_contract_authored(self):
        b,d=self.authored()
        d["shots"][0]["editing"]["narrative_bridge"]["style_handoff"]["strategy"]="preserve"
        _,findings=bridge.review(b,d,v2.production_route)
        self.assertIn("MIXED_MEDIA_STYLE_REVIEW",{f["code"] for f in findings})

    def test_missing_story_question_makes_handoff_incomplete(self):
        b,d=self.authored()
        d["shots"][0]["editing"]["narrative_bridge"]["cut_intention"]["viewer_question"]="待导演设计"
        routes,issues=bridge.review(b,d,v2.production_route)
        self.assertEqual(routes[0]["design_status"],"incomplete")
        self.assertIn("NARRATIVE_FIELD_MISSING",{f["code"] for f in issues})
        w=workbook.compile_workbook(b,d)
        self.assertFalse(w["director_review"]["narrative_handoff_ready"])

    def test_invalid_emotional_hold_cannot_claim_valid(self):
        b,d=self.authored()
        d["shots"][0]["editing"]["narrative_bridge"]["emotion_pacing"]["hold_before_s"]=900
        _,issues=bridge.review(b,d,v2.production_route)
        self.assertIn("RHYTHM_HOLD_INVALID",{f["code"] for f in issues})

    def test_bad_enum_type_does_not_crash(self):
        b,d=self.authored()
        cont=d["shots"][0]["editing"]["narrative_bridge"]
        cont["style_handoff"]["strategy"]=[]
        cont["cut_intention"]["cut_type"]=[]
        cont["emotion_pacing"]["tempo_change"]=[]
        _,issues=bridge.review(b,d,v2.production_route)
        self.assertTrue({"CUT_TYPE_INVALID","STYLE_STRATEGY_INVALID","TEMPO_INVALID"}
                        .issubset({f["code"] for f in issues}))

    def test_non_object_contract_is_explicit_blocker(self):
        b,d=self.authored()
        d["shots"][0]["editing"]["narrative_bridge"]=[]
        _,issues=bridge.review(b,d,v2.production_route)
        self.assertIn("NARRATIVE_BRIDGE_INVALID",{f["code"] for f in issues})

    def test_no_last_shot_to_nonexistent_next(self):
        b,d=self.authored()
        cuts,_=bridge.review(b,d,v2.production_route)
        self.assertFalse(any(x["from_shot_id"]==b["shots"][-1]["id"] for x in cuts))

    def test_workbook_md_exposes_pairwise_reason_and_visual_handoff(self):
        b,d=self.authored()
        w=workbook.compile_workbook(b,d)
        md=workbook.render_markdown(w)
        self.assertIn("下一镜的叙事、节奏与混合制作风格衔接",md)
        self.assertIn("S01",md)
        self.assertIn("S02",md)
        self.assertIn("viewer_question",md)

    def test_missing_authoring_preserves_source_unchanged(self):
        b,d=self.copy()
        previous=copy.deepcopy([b,d])
        workbook.compile_workbook(b,d)
        self.assertEqual([b,d],previous)
        w=workbook.compile_workbook(b,d)
        self.assertFalse(w["director_review"]["production_blueprint_ready"])

    def test_legacy_directions_retained_without_breaking_compilation(self):
        b,d=self.copy()
        w=workbook.compile_workbook(b,d)
        self.assertEqual(len(w["narrative_bridges"]),len(b["shots"])-1)
        self.assertFalse(w["director_review"]["narrative_handoff_ready"])
        self.assertEqual(w["director_review"]["narrative_handoff_pending"],len(b["shots"])-1)


if __name__=="__main__":
    unittest.main()
