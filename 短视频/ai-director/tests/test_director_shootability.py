"""Off-line action shootability/hand/prop scheduling regressions.

No vendor model, no image generation, no local Mac access.
"""
import copy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import director_v2 as v2
import director_shootability as subject
import director_workbook as workbook


class ShootabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=v2.read_json(ROOT/"examples/quit-smoking/plan.json")
        cls.direction=v2.read_json(ROOT/"examples/quit-smoking/direction_v02.json")

    def fixture(self):
        return copy.deepcopy(self.base),copy.deepcopy(self.direction)

    def authored(self):
        base, direction=self.fixture()
        for shot, d in zip(base["shots"], direction["shots"]):
            if shot["visual_type"] != "ai_video" or not shot.get("character_ids"):
                continue
            d["shootability"]={"mode":"single_take","action_units":[{
                "id":"A"+str(i+1),"beat_index":i,
                "actor_id":shot["character_ids"][0],
                "hand":"none", "prop_id":None,
                "from_s":beat["from_s"],"to_s":beat["to_s"],
                "action":beat["visible_change"],
                "visible_result":"End state follows the documented beat"
            } for i,beat in enumerate(d["beats"])]}
        return base,direction

    def review(self, base, direction):
        return subject.review(base,direction,v2.production_route)

    def test_legacy_public_example_is_draft_not_falsely_ready(self):
        base,direction=self.fixture()
        report=self.review(base,direction)
        self.assertEqual(report["blockers"],0)
        self.assertGreater(report["pending"],0)
        self.assertFalse(report["director_structure_ready"])
        self.assertFalse(report["model_capability_verified"])
        self.assertFalse(report["real_footage_tested"])
        self.assertIn("PHYSICAL_ACTION_PLAN_MISSING",{f["code"] for f in report["findings"]})

    def test_all_beats_explicitly_authored_can_pass_structural_preflight(self):
        b,d=self.authored()
        report=self.review(b,d)
        self.assertTrue(report["director_structure_ready"],report["findings"])
        self.assertEqual(report["blockers"],0)
        self.assertEqual(report["pending"],0)
        self.assertFalse(report["model_capability_verified"])

    def test_nonphysical_graphic_requires_no_fake_actor_actions(self):
        b,d=self.fixture()
        report=self.review(b,d)
        g=next(x for x in report["shots"] if x["shot_id"]=="S02")
        self.assertEqual(g["status"],"not_required")
        self.assertEqual(g["units"],[])

    def test_empty_units_cannot_fake_physical_completion(self):
        b,d=self.authored()
        d["shots"][0]["shootability"]["action_units"]=[]
        report=self.review(b,d)
        codes={f["code"] for f in report["findings"]}
        self.assertIn("ACTION_UNITS_MISSING",codes)
        self.assertIn("ACTION_BEAT_UNDESIGNED",codes)
        self.assertFalse(report["director_structure_ready"])

    def test_missing_beat_explicitly_reported(self):
        b,d=self.authored()
        d["shots"][0]["shootability"]["action_units"].pop()
        report=self.review(b,d)
        self.assertIn("ACTION_BEAT_UNDESIGNED",{f["code"] for f in report["findings"]})

    def test_same_hand_overlap_blocked(self):
        b,d=self.authored()
        units=d["shots"][0]["shootability"]["action_units"]
        units.append({"id":"A_EXTRA","beat_index":0,"actor_id":"CHAR01",
                      "hand":"right","prop_id":None,
                      "from_s":0.2,"to_s":0.9,"action":"hold other item",
                      "visible_result":"item rests"})
        units[0]["hand"]="right"
        report=self.review(b,d)
        self.assertIn("SAME_HAND_OVERLAP",{f["code"] for f in report["findings"]})
        self.assertGreater(report["blockers"],0)

    def test_two_hands_can_work_simultaneously(self):
        b,d=self.authored()
        units=d["shots"][0]["shootability"]["action_units"]
        units.append({"id":"A_EXTRA","beat_index":0,"actor_id":"CHAR01",
                      "hand":"left","prop_id":None,
                      "from_s":0.2,"to_s":0.9,"action":"prepare second item",
                      "visible_result":"second item ready"})
        units[0]["hand"]="right"
        report=self.review(b,d)
        self.assertNotIn("SAME_HAND_OVERLAP",{f["code"] for f in report["findings"]})
        self.assertEqual(report["blockers"],0)

    def test_both_hands_conflicts_with_other_hand_actions(self):
        b,d=self.authored()
        units=d["shots"][0]["shootability"]["action_units"]
        units[0]["hand"]="both"
        units.append({"id":"A_EXTRA","beat_index":0,"actor_id":"CHAR01",
                      "hand":"left","prop_id":None,
                      "from_s":0.2,"to_s":1.0,"action":"lift phone",
                      "visible_result":"phone rises"})
        self.assertIn("SAME_HAND_OVERLAP",
                      {f["code"] for f in self.review(b,d)["findings"]})

    def test_wrong_beat_index_is_a_blocker(self):
        b,d=self.authored()
        d["shots"][0]["shootability"]["action_units"][0]["beat_index"]=999
        codes={f["code"] for f in self.review(b,d)["findings"]}
        self.assertIn("ACTION_BEAT_INVALID",codes)

    def test_timing_must_stay_inside_declared_beat(self):
        b,d=self.authored()
        d["shots"][0]["shootability"]["action_units"][0]["to_s"]=4.9
        codes={f["code"] for f in self.review(b,d)["findings"]}
        self.assertIn("ACTION_TIME_INVALID",codes)

    def test_unknown_actor_and_unregistered_prop_needs_attention(self):
        b,d=self.authored()
        x=d["shots"][0]["shootability"]["action_units"][0]
        x["actor_id"]="EXTRA"
        x["prop_id"]="PHONE_NOT_REGISTERED"
        report=self.review(b,d)
        codes={f["code"] for f in report["findings"]}
        self.assertIn("ACTION_ACTOR_UNKNOWN",codes)
        self.assertIn("ACTION_PROP_NOT_DECLARED",codes)
        self.assertFalse(report["director_structure_ready"])

    def test_actor_list_type_fails_without_exception(self):
        b,d=self.authored()
        d["shots"][0]["shootability"]["action_units"][0]["actor_id"]=[]
        report=self.review(b,d)
        self.assertIn("ACTION_ACTOR_UNKNOWN",{f["code"] for f in report["findings"]})

    def test_unknown_shootability_mode_is_blocked(self):
        b,d=self.authored()
        d["shots"][0]["shootability"]["mode"]="AI_magic"
        self.assertIn("SHOOTABILITY_MODE_INVALID",
                      {f["code"] for f in self.review(b,d)["findings"]})

    def test_duplicate_action_ids_are_blocked(self):
        b,d=self.authored()
        d["shots"][0]["shootability"]["action_units"][1]["id"]="A1"
        self.assertIn("ACTION_ID_INVALID",
                      {f["code"] for f in self.review(b,d)["findings"]})

    def test_high_density_recommends_fallback_without_claiming_model_failure(self):
        b,d=self.authored()
        b["continuity_contract"]={"props":{
            "PHONE":{"label":"phone"},"BOOK":{"label":"book"},"KEY":{"label":"key"}}}
        units=d["shots"][0]["shootability"]["action_units"]
        units[0].update(hand="right",prop_id="PHONE",from_s=0,to_s=0.35)
        units.extend([
          {"id":"A_EXTRA1","beat_index":0,"actor_id":"CHAR01","hand":"left",
           "prop_id":"BOOK","from_s":0.36,"to_s":0.7,
           "action":"take book","visible_result":"book held"},
          {"id":"A_EXTRA2","beat_index":0,"actor_id":"CHAR01","hand":"right",
           "prop_id":"KEY","from_s":0.72,"to_s":1.15,
           "action":"take key","visible_result":"key held"}
        ])
        report=self.review(b,d)
        codes={f["code"] for f in report["findings"]}
        self.assertIn("DENSE_PROP_SEQUENCE_REVIEW",codes)
        self.assertIn("DENSE_ACTION_FALLBACK_PENDING",codes)
        self.assertFalse(report["director_structure_ready"])
        d["shots"][0]["shootability"]["fallback"]="Split 0–1.2s across two takes"
        report=self.review(b,d)
        self.assertNotIn("DENSE_ACTION_FALLBACK_PENDING",
                         {f["code"] for f in report["findings"]})
        self.assertTrue(report["director_structure_ready"])
        self.assertGreater(report["review_signals"],0)
        self.assertFalse(report["model_capability_verified"])

    def test_fast_manipulation_only_warns_not_auto_rejects(self):
        b,d=self.authored()
        b["continuity_contract"]={"props":{"PHONE":{"label":"phone"}}}
        d["shots"][0]["shootability"]["action_units"][0].update(
            hand="right",prop_id="PHONE",from_s=0,to_s=0.4)
        report=self.review(b,d)
        self.assertIn("FAST_FINE_MOTOR_REVIEW",{f["code"] for f in report["findings"]})
        self.assertTrue(report["director_structure_ready"])

    def test_workbook_includes_shootability_without_claiming_completed_video(self):
        b,d=self.authored()
        out=workbook.compile_workbook(b,d)
        self.assertIn("shootability_review",out)
        self.assertTrue(out["director_review"]["shootability_structure_ready"])
        self.assertFalse(out["is_video"])
        self.assertFalse(out["human_approved"])
        self.assertFalse(out["publishing_allowed"])
        self.assertIn("动作可拍性",workbook.render_markdown(out))

    def test_split_stitch_segments_need_full_timeline_and_join_rules(self):
        b,d=self.authored()
        d["shots"][0]["shootability"].update(
            mode="split_stitch",
            segments=[
              {"id":"SEG1","from_s":0,"to_s":2.5,"route":"ai_video",
               "join_rule":"hold identical hand position, cut on natural pause"},
              {"id":"SEG2","from_s":2.5,"to_s":5,"route":"ai_video",
               "join_rule":"match cigarette position and camera angle before crossfade"}
            ])
        r=self.review(b,d)
        self.assertTrue(r["director_structure_ready"],r["findings"])
        self.assertEqual(len(r["shots"][0]["segments"]),2)
        self.assertFalse(r["model_capability_verified"])

    def test_split_stitch_without_two_segments_is_not_ready(self):
        b,d=self.authored()
        d["shots"][0]["shootability"].update(mode="split_stitch",segments=[])
        r=self.review(b,d)
        self.assertIn("SPLIT_SEGMENTS_MISSING",{f["code"] for f in r["findings"]})
        self.assertFalse(r["director_structure_ready"])

    def test_split_stitch_detects_gap_between_segments(self):
        b,d=self.authored()
        d["shots"][0]["shootability"].update(mode="split_stitch",segments=[
            {"id":"SEG1","from_s":0,"to_s":2,"route":"ai_video","join_rule":"cut on hand pause"},
            {"id":"SEG2","from_s":2.5,"to_s":5,"route":"static_post","join_rule":"match prop mask"}])
        r=self.review(b,d)
        self.assertIn("SPLIT_SEGMENT_GAP_OR_OVERLAP",{f["code"] for f in r["findings"]})
        self.assertFalse(r["director_structure_ready"])

    def test_split_stitch_rejects_unknown_route_and_missing_join(self):
        b,d=self.authored()
        d["shots"][0]["shootability"].update(mode="split_stitch",segments=[
            {"id":"SEG1","from_s":0,"to_s":2,"route":"magic","join_rule":""},
            {"id":"SEG2","from_s":2,"to_s":5,"route":"ai_video","join_rule":"matching action"}])
        r=self.review(b,d)
        codes={f["code"] for f in r["findings"]}
        self.assertIn("SPLIT_SEGMENT_ROUTE_INVALID",codes)
        self.assertIn("SPLIT_JOIN_UNDESIGNED",codes)

    def test_split_stitch_requires_last_segment_to_end_at_shot_boundary(self):
        b,d=self.authored()
        d["shots"][0]["shootability"].update(mode="split_stitch",segments=[
            {"id":"SEG1","from_s":0,"to_s":2,"route":"ai_video","join_rule":"cut on pause"},
            {"id":"SEG2","from_s":2,"to_s":4,"route":"ai_video","join_rule":"match last still"}])
        self.assertIn("SPLIT_SEGMENT_INCOMPLETE",
                      {f["code"] for f in self.review(b,d)["findings"]})

    def test_inputs_not_mutated(self):
        b,d=self.authored()
        before=copy.deepcopy((b,d))
        self.review(b,d)
        self.assertEqual((b,d),before)


if __name__=="__main__":
    unittest.main()
