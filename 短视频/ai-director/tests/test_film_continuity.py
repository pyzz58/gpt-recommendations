"""Offline FilmDSL-inspired cross-shot cast, wardrobe, prop and cut QA.

Synthetic data only. No video/media or model inference is claimed.
"""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import film_continuity as film
import agent_team as team


class FilmContinuityTests(unittest.TestCase):
    def setUp(self):
        self.source="Invented fictional character opens one sealed paper envelope."
        self.base={
            "characters":[{"id":"CHAR01","name":"Fiction Person"}],
            "props":[{"id":"PROP01","description":"One paper letter envelope"}],
            "scenes":[{"id":"LOC01","description":"One locked apartment layout"}],
            "shots":[
                {"id":"S01","scene_id":"LOC01","visual_type":"ai_video",
                 "duration":4,"character_ids":["CHAR01"],
                 "prop_ids":["PROP01"],"narration":"She reaches the table"},
                {"id":"S02","scene_id":"LOC01","visual_type":"ai_video",
                 "duration":3,"character_ids":["CHAR01"],
                 "prop_ids":["PROP01"],"narration":"She opens the letter"},
                {"id":"S03","scene_id":"LOC01","visual_type":"ai_video",
                 "duration":2,"character_ids":["CHAR01"],
                 "prop_ids":["PROP01"],"narration":"She looks up"}]}
        self.person={"position":"standing by table",
                     "appearance":"blue coat / fixed hairstyle",
                     "condition":"uninjured","holder":"none"}
        self.envelope={"position":"wooden table",
                       "appearance":"white envelope",
                       "condition":"sealed","holder":"none"}
        self.tracks={}
        for s in self.base["shots"]:
            self.tracks[s["id"]]={
                "scene_id":s["scene_id"],
                "entity_tracks":[self.line("CHAR01",self.person),
                                 self.line("PROP01",self.envelope)]}

    def line(self,eid,state):
        return {"entity_id":eid,"start_state":deepcopy(state),
                "end_state":deepcopy(state),"events":[],
                "cut_break":"none","cut_reason":""}

    def event(self,entry,field,after,cause="Actor visibly performs the change"):
        old=entry["start_state"][field]
        entry["end_state"][field]=after
        entry["events"].append({"field":field,"from":old,"to":after,
                                "time_s":2,"cause":cause})

    def test_source_bound_registry_never_forges_reference_media(self):
        inv=film.inventory(self.base,source_digest="a"*64)
        self.assertEqual(inv["source_plan_digest"],team.fingerprint(self.base))
        self.assertEqual(set(inv["entities"]["characters"]),{"CHAR01"})
        self.assertEqual(set(inv["entities"]["props"]),{"PROP01"})
        self.assertEqual(set(inv["entities"]["scenes"]),{"LOC01"})
        self.assertEqual(inv["unverified_asset_count"],3)
        self.assertFalse(inv["reference_media_verified"])
        self.assertFalse(inv["human_approved"])
        self.assertEqual(inv["entities"]["characters"]["CHAR01"]["reference_status"],
                         "missing")

    def test_stable_states_are_consistent_but_not_media_verified(self):
        r=film.inspect_tracks(self.base,self.tracks)
        self.assertEqual(r["tracked_entity_events"],0)
        self.assertFalse(r["media_identity_verified"])
        self.assertFalse(r["semantic_plausibility_verified"])
        self.assertFalse(r["production_ready"])
        self.assertEqual(r["issues"],[])

    def test_prop_teleportation_across_shots_is_blocked(self):
        self.tracks["S02"]["entity_tracks"][1]["start_state"]["position"]="suddenly in left hand"
        self.tracks["S02"]["entity_tracks"][1]["end_state"]["position"]="suddenly in left hand"
        r=film.inspect_tracks(self.base,self.tracks)
        self.assertEqual(r["status"],"blocked")
        self.assertEqual(r["issues"][0]["code"],
                         "CONTINUITY_TELEPORT_OR_COSTUME_DRIFT")
        self.assertEqual(r["issues"][0]["shot_ids"],["S01","S02"])

    def test_costume_changes_without_cut_are_blocked(self):
        self.tracks["S02"]["entity_tracks"][0]["start_state"]["appearance"]="red suit"
        self.tracks["S02"]["entity_tracks"][0]["end_state"]["appearance"]="red suit"
        r=film.inspect_tracks(self.base,self.tracks)
        self.assertEqual(r["issues"][0]["code"],
                         "CONTINUITY_TELEPORT_OR_COSTUME_DRIFT")

    def test_on_screen_prop_change_needs_explicit_event(self):
        env=self.tracks["S01"]["entity_tracks"][1]
        env["end_state"]["condition"]="opened"
        with self.assertRaisesRegex(film.ContinuityError,
                                    "UNEXPLAINED_IN_SHOT"):
            film.inspect_tracks(self.base,self.tracks)
        env["events"]=[{"field":"condition","from":"sealed","to":"opened",
                        "time_s":2,"cause":"Hand tears the physical paper seal"}]
        self.tracks["S02"]["entity_tracks"][1]["start_state"]["condition"]="opened"
        self.tracks["S02"]["entity_tracks"][1]["end_state"]["condition"]="opened"
        self.tracks["S03"]["entity_tracks"][1]["start_state"]["condition"]="opened"
        self.tracks["S03"]["entity_tracks"][1]["end_state"]["condition"]="opened"
        r=film.inspect_tracks(self.base,self.tracks)
        self.assertEqual(r["tracked_entity_events"],1)
        self.assertFalse(r["issues"])

    def test_changed_prop_after_time_jump_remains_human_review_not_magic_pass(self):
        e=self.tracks["S02"]["entity_tracks"][1]
        e["start_state"]["holder"]="right hand"
        e["end_state"]["holder"]="right hand"
        e["cut_break"]="offscreen_transition"
        e["cut_reason"]="The letter is picked up during a deliberate invisible cut"
        next_env=self.tracks["S03"]["entity_tracks"][1]
        next_env["start_state"]["holder"]="right hand"
        next_env["end_state"]["holder"]="right hand"
        r=film.inspect_tracks(self.base,self.tracks)
        self.assertEqual(r["status"],"needs_human_review")
        self.assertEqual(r["issues"][0]["code"],
                         "CONTINUITY_OFFSCREEN_CHANGE_REVIEW")
        self.assertFalse(r["human_approved"])

    def test_same_prop_not_reinvented_under_unknown_asset_id(self):
        self.tracks["S02"]["entity_tracks"][1]["entity_id"]="PROP02"
        with self.assertRaisesRegex(film.ContinuityError,
                                    "UNKNOWN_DUPLICATE_OR_UNDECLARED"):
            film.inspect_tracks(self.base,self.tracks)

    def test_missing_character_track_is_rejected(self):
        self.tracks["S01"]["entity_tracks"].pop(0)
        with self.assertRaisesRegex(film.ContinuityError,
                                    "DECLARED_ENTITY_MISSING"):
            film.inspect_tracks(self.base,self.tracks)

    def test_scene_reference_cannot_shift_unnoticed(self):
        self.tracks["S02"]["scene_id"]="LOC02"
        with self.assertRaisesRegex(film.ContinuityError,
                                    "SHOT_TRACK_STRUCTURE"):
            film.inspect_tracks(self.base,self.tracks)

    def test_event_time_outside_shot_or_false_cause_rejected(self):
        env=self.tracks["S01"]["entity_tracks"][1]
        self.event(env,"condition","opened")
        env["events"][0]["time_s"]=99
        with self.assertRaisesRegex(film.ContinuityError,
                                    "EVENT_NOT_CAUSALLY_BOUND"):
            film.inspect_tracks(self.base,self.tracks)
        env["events"][0]["time_s"]=2
        env["events"][0]["cause"]="x"
        with self.assertRaisesRegex(film.ContinuityError,
                                    "EVENT_NOT_CAUSALLY_BOUND"):
            film.inspect_tracks(self.base,self.tracks)

    def test_mutable_plan_wrong_ids_fail_closed(self):
        bad=deepcopy(self.base)
        bad["shots"][0]["character_ids"]=["NONEXISTENT"]
        with self.assertRaisesRegex(film.ContinuityError,
                                    "UNKNOWN_SHOT_CHARACTER"):
            film.inventory(bad)

    def test_unbound_fiction_cannot_be_mistaken_for_verified_cast(self):
        for shot in self.base["shots"]:
            shot["character_ids"]=[]
            shot["prop_ids"]=[]
        inv=film.inventory(self.base)
        codes={x["code"] for x in inv["declaration_gaps"]}
        self.assertIn("CONTINUITY_CAST_NOT_DECLARED",codes)
        self.assertIn("CONTINUITY_PROPS_NOT_DECLARED",codes)
        self.assertFalse(inv["reference_media_verified"])


if __name__=="__main__":
    unittest.main()
